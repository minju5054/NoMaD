"""Render recorded executed poses in Isaac 6; never run NoMaD or a controller.

The MP4 is a post-hoc RTX rendering, not footage captured during inference.
The blue footprint, white heading, orange goal ring and cyan trail are visual aids.
Run with the existing Isaac python.sh in an isolated process (see documentation).
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
from nomad_isaac.common import replay_frame_indices


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--run", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args, _ = parser.parse_known_args()
source = args.run.resolve()
out = args.output.resolve()
assert out != source and source not in out.parents, "Keep derived video outside the raw run"
out.mkdir(parents=True, exist_ok=True)
runtime = out / "isaac_runtime"
runtime.mkdir(exist_ok=False)  # Refuse an existing attempt; no artifact is overwritten.
(out / "render_recorded_source.py").write_bytes(Path(__file__).read_bytes())
inputs = [source / name for name in ("scene_gui.usda", "agent_trajectory.csv", "summary.json", "scenario.json")]
before = {path.name: digest(path) for path in inputs}
rows = list(csv.DictReader((source / "agent_trajectory.csv").open()))
config = json.loads((source / "scenario.json").read_text())
result = json.loads((source / "summary.json").read_text())
hz, fps, width, height = config["integration_hz"], 24, 1280, 720
assert hz % fps == 0
stride = hz // fps
indices = replay_frame_indices(len(rows), hz, fps)
for index, row in enumerate(rows):
    assert abs(float(row["simulation_time_s"]) - index / hz) < 1e-10

from isaacsim import SimulationApp
app = SimulationApp({
    "headless": True, "width": width, "height": height,
    "renderer": "RaytracedLighting", "anti_aliasing": 0,
    "multi_gpu": False, "active_gpu": 0, "max_gpu_count": 1,
    "limit_cpu_threads": 8, "enable_crashreporter": False,
    "extra_args": ["--/app/settings/persistent=false",
                   "--/rtx/hydra/supportMultiTickRate=false",
                   f"--/app/userConfigPath={runtime}/user.config.json",
                   f"--/log/file={runtime}/kit.log",
                   "--/app/extensions/registryEnabled=false"],
})

import carb
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import omni.usd
import omni.timeline
import omni.replicator.core as rep
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
from video_encoding import get_video_encoding_interface
from nomad_isaac.common import export_view_scene


def material(stage, prim, name, color):
    mat = UsdShade.Material.Define(stage, "/World/ReplayVisuals/Materials/" + name)
    shader = UsdShade.Shader.Define(stage, mat.GetPath().AppendChild("Shader"))
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(.8)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(prim.GetPrim()).Bind(mat)


def line(stage, name, points, color, thickness):
    curve = UsdGeom.BasisCurves.Define(stage, "/World/ReplayVisuals/" + name)
    curve.CreateTypeAttr("linear")
    curve.CreateCurveVertexCountsAttr([len(points)])
    curve.CreatePointsAttr(points)
    curve.CreateWidthsAttr([thickness])
    curve.SetWidthsInterpolation("constant")
    material(stage, curve, name, color)
    return curve


def main():
    started = time.monotonic()
    context = omni.usd.get_context()
    assert context.open_stage(str(source / "scene_gui.usda"))
    for _ in range(10):
        app.update()
    stage = context.get_stage()
    agent = UsdGeom.Xformable(stage.GetPrimAtPath("/World/Agent"))
    translate = next(op for op in agent.GetOrderedXformOps() if op.GetOpType() == UsdGeom.XformOp.TypeTranslate)
    rotate = next(op for op in agent.GetOrderedXformOps() if op.GetOpType() == UsdGeom.XformOp.TypeRotateZ)
    UsdGeom.Xform.Define(stage, "/World/ReplayVisuals")

    body = UsdGeom.Cylinder.Define(stage, "/World/Agent/ReplayFootprint")
    body.CreateRadiusAttr(config["agent_radius_m"])
    body.CreateHeightAttr(.08)
    body.CreateAxisAttr("Z")
    body.AddTranslateOp().Set(Gf.Vec3d(0, 0, .04))
    material(stage, body, "Agent", (.02, .32, 1.))
    heading = UsdGeom.Mesh.Define(stage, "/World/Agent/ReplayHeading")
    heading.CreatePointsAttr([(.115, 0, .081), (-.065, .065, .081), (-.065, -.065, .081)])
    heading.CreateFaceVertexCountsAttr([3])
    heading.CreateFaceVertexIndicesAttr([0, 1, 2])
    heading.CreateSubdivisionSchemeAttr("none")
    heading.CreateDoubleSidedAttr(True)
    material(stage, heading, "Heading", (1., 1., 1.))

    gx, gy = config["goal_pose"][:2]
    radius = config["goal_tolerance_m"]
    circle = [(gx + radius * math.cos(t), gy + radius * math.sin(t), .012)
              for t in np.linspace(0, 2 * math.pi, 97)]
    line(stage, "GoalTolerance", circle, (1., .45, .02), .018)
    line(stage, "GoalCrossX", [(gx-.06, gy, .012), (gx+.06, gy, .012)], (1., .45, .02), .015)
    line(stage, "GoalCrossY", [(gx, gy-.06, .012), (gx, gy+.06, .012)], (1., .45, .02), .015)
    trail = line(stage, "ExecutedTrail", [(0, 0, .009), (0, 0, .009)], (.02, .8, 1.), .012)

    camera = UsdGeom.Camera.Define(stage, "/World/ReplayVisuals/OverviewCamera")
    camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(
        Gf.Vec3d(2.5, 2., 8.), Gf.Vec3d(2.5, 0, 0), Gf.Vec3d(0, 1, 0)).GetInverse())
    camera.CreateFocalLengthAttr(36.)
    camera.CreateHorizontalApertureAttr(36.)
    camera.CreateVerticalApertureAttr(20.25)
    camera.CreateClippingRangeAttr(Gf.Vec2f(.02, 100.))
    product = rep.create.render_product(str(camera.GetPath()), (width, height))
    annotator = rep.AnnotatorRegistry.get_annotator("rgb", device="cpu")
    annotator.attach([product])
    rep.orchestrator.set_capture_on_play(False)
    timeline = omni.timeline.get_timeline_interface()
    timeline.pause()
    stage.SetTimeCodesPerSecond(hz)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    title_font = ImageFont.truetype(font_path, 27)
    font = ImageFont.truetype(font_path, 20)
    small = ImageFont.truetype(font_path, 18)
    encoder = get_video_encoding_interface()
    carb.settings.get_settings().set("/exts/omni.videoencoding/bitrate", 8_000_000)
    carb.settings.get_settings().set("/exts/omni.videoencoding/iframeinterval", fps)
    video = out / "nomad_static_obstacle.mp4"
    assert encoder.start_encoding(str(video), float(fps), len(indices), False)
    maximum_pose_error = 0.
    try:
        with (out / "frame_mapping.csv").open("x", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["video_frame", "source_pose_row", "simulation_time_s", "x_m", "y_m", "yaw_rad"])
            for frame, index in enumerate(indices):
                row = rows[index]
                sim_time = float(row["simulation_time_s"])
                pose = np.array([float(row[k]) for k in ("x_m", "y_m", "yaw_rad")])
                translate.Set(Gf.Vec3d(float(pose[0]), float(pose[1]), 0))
                rotate.Set(float(np.degrees(pose[2])))
                points = [(float(r["x_m"]), float(r["y_m"]), .009) for r in rows[:index+1]]
                if len(points) == 1:
                    points *= 2
                trail.GetPointsAttr().Set(points)
                trail.GetCurveVertexCountsAttr().Set([len(points)])
                timeline.set_current_time(sim_time)
                for _ in range(20):
                    rep.orchestrator.step(rt_subframes=4, delta_time=0., pause_timeline=True)
                    rgba = np.asarray(annotator.get_data())
                    if rgba.shape == (height, width, 4):
                        break
                assert rgba.shape == (height, width, 4) and rgba.dtype == np.uint8
                assert abs(timeline.get_current_time() - sim_time) < 1e-6
                transform = agent.ComputeLocalToWorldTransform(Usd.TimeCode(sim_time * hz))
                origin = transform.ExtractTranslation()
                forward = transform.TransformDir(Gf.Vec3d(1, 0, 0))
                actual = np.array([origin[0], origin[1], math.atan2(forward[1], forward[0])])
                difference = actual - pose
                difference[2] = (difference[2] + np.pi) % (2*np.pi) - np.pi
                error = float(np.max(np.abs(difference)))
                maximum_pose_error = max(error, maximum_pose_error)
                assert error < 1e-10, (index, error)
                assert rgba[:, :, :3].std() > 10

                image = Image.fromarray(rgba).convert("RGBA")
                draw = ImageDraw.Draw(image)
                draw.rectangle((0, 0, width, 87), fill=(17, 24, 36, 255))
                draw.text((24, 10), "NoMaD | Isaac Sim 6 | Static obstacle", font=title_font, fill="white")
                draw.text((24, 51), "Recorded execution replay  |  1x simulation time  |  No new navigation run", font=small, fill=(190, 207, 224))
                draw.text((1035, 21), f"t = {sim_time:05.2f} s", font=title_font, fill="white")
                draw.rectangle((0, 622, width, height), fill=(17, 24, 36, 255))
                for x, color, label in [(24, (50, 140, 255), "Agent / 0.12 m radius"),
                                        (335, (80, 210, 65), "Obstacle"),
                                        (525, (255, 155, 40), "Goal / 0.30 m tolerance")]:
                    draw.ellipse((x, 638, x+14, 652), fill=color)
                    draw.text((x+25, 632), label, font=font, fill="white")
                draw.text((920, 632), f"Goal distance: {float(row['goal_distance_m']):.3f} m", font=font, fill="white")
                clearance = result["obstacle_evaluation"]["minimum_swept_clearance_lower_m"]
                outcome = "goal reached" if result["goal_entry"] else "goal NOT reached"
                contact = "collision" if result["obstacle_evaluation"]["geometric_overlap"] else "no collision"
                draw.text((24, 673), f"Recorded result: {contact}; min clearance {100*clearance:.2f} cm; {outcome}.", font=small, fill=(255, 205, 126))
                draw.text((945, 673), f"v {float(row['v_m_s']):.2f} m/s | w {float(row['w_rad_s']):+.2f} rad/s", font=small, fill=(190, 207, 224))
                assert encoder.encode_next_frame_from_buffer(np.asarray(image), width, height), frame
                writer.writerow([frame, index, sim_time, *pose.tolist()])
                if frame % (fps * 5) == 0 or frame == len(indices)-1:
                    image.save(out / f"preview_{frame:04d}.png")
                    print(f"VIDEO_FRAME {frame}/{len(indices)-1} simulation={sim_time:.3f}s", flush=True)
    finally:
        encoder.finalize_encoding()

    # Standalone animation for Isaac's native GUI Play button, all 72 Hz poses.
    # Export only World: transient Replicator graphs do not belong in the GUI scene.
    translate.Set(Gf.Vec3d(0, 0, 0))
    rotate.Set(0.)
    unwrapped_yaw = np.unwrap([float(row["yaw_rad"]) for row in rows])
    for index, row in enumerate(rows):
        translate.Set(Gf.Vec3d(float(row["x_m"]), float(row["y_m"]), 0), Usd.TimeCode(index))
        rotate.Set(math.degrees(float(unwrapped_yaw[index])), Usd.TimeCode(index))
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(len(rows)-1)
    stage.SetFramesPerSecond(fps)
    # Full path remains visible in the optional GUI animation; MP4 uses growing trail.
    temporary = out / "render_stage.usda"
    stage.Export(str(temporary))
    animated = out / "recorded_motion.usda"
    export_view_scene(temporary, animated)
    gui_stage = Usd.Stage.Open(str(animated))
    gui_stage.SetTimeCodesPerSecond(hz)
    gui_stage.SetFramesPerSecond(fps)
    gui_stage.SetStartTimeCode(0)
    gui_stage.SetEndTimeCode(len(rows)-1)
    gui_stage.GetRootLayer().Save()
    # Kit's native viewport reads this metadata when opening the new file.
    gui_ready = out / "recorded_motion_gui.usda"
    gui_stage.SetMetadataByDictKey("customLayerData", "cameraSettings:boundCamera", str(camera.GetPath()))
    gui_stage.Export(str(gui_ready))
    assert before == {path.name: digest(path) for path in inputs}
    manifest = {
        "kind": "posthoc_isaac_rtx_render_of_recorded_executed_poses",
        "not_contemporaneous_video": True, "new_inference_count": 0,
        "source_run": str(source), "source_sha256": before,
        "renderer_script_sha256": digest(Path(__file__)),
        "git_sha_before_video_change": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "video": str(video), "video_sha256": digest(video), "video_bytes": video.stat().st_size,
        "fps": fps, "resolution": [width, height], "frame_count": len(indices),
        "source_pose_count": len(rows), "source_pose_stride": stride,
        "simulation_time_range_s": [0., float(rows[-1]["simulation_time_s"])],
        "encoded_duration_s": len(indices)/fps,
        "timing_note": "Exact source rows at 1x simulation time, not wall time. An off-grid final row occupies the next 24 fps slot, then holds for one frame.",
        "final_frame_timestamp_offset_s": (len(indices)-1)/fps-float(rows[-1]["simulation_time_s"]),
        "gui_yaw_representation": "Unwrapped equivalent yaw avoids interpolation across +/-pi; all recorded rotations preserved.",
        "max_rendered_pose_absolute_error": maximum_pose_error,
        "added_visuals": ["blue 0.12 m radius footprint", "white heading arrow", "orange 0.30 m goal ring", "cyan executed trail", "overview camera", "text overlays"],
        "scene_geometry_and_original_camera_preserved": True,
        "overview_camera_eye_world_m": [2.5, 2., 8.],
        "raw_inputs_unchanged": True, "render_wall_s": time.monotonic()-started,
        "animated_usd": str(animated), "animated_usd_sha256": digest(animated),
        "gui_usd": str(gui_ready), "gui_usd_sha256": digest(gui_ready),
        "result": {"goal_entry": result["goal_entry"], "obstacle_evaluation": result["obstacle_evaluation"]},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("VIDEO_COMPLETE " + str(video), flush=True)


try:
    main()
except Exception:
    import traceback
    (out / "FAILED.txt").write_text(traceback.format_exc())
    raise
finally:
    app.close()
