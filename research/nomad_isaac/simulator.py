"""Isaac Sim 6 process. Kinematic SE(2) clock; USD scene rendered by actual RTX."""
import argparse
from collections import deque
import csv
import hashlib
import json
import math
from pathlib import Path
import socket
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--socket")
parser.add_argument("--prepare-only", action="store_true")
parser.add_argument("--scenario", type=Path)
args, _ = parser.parse_known_args()
out = args.output.resolve()
runtime = out / "isaac_runtime"
runtime.mkdir(exist_ok=False)

# The launcher keeps this process separate from the NoMaD .venv.
from isaacsim import SimulationApp
app = SimulationApp({"headless": True, "width": 320, "height": 240,
                     "renderer": "RaytracedLighting", "anti_aliasing": 0,
                     "multi_gpu": False, "active_gpu": 0, "max_gpu_count": 1,
                     "limit_cpu_threads": 8, "enable_crashreporter": False,
                     "extra_args": ["--/app/settings/persistent=false",
                                    "--/rtx/hydra/supportMultiTickRate=false",
                                    f"--/app/userConfigPath={runtime}/user.config.json",
                                    f"--/log/file={runtime}/kit.log",
                                    "--/app/extensions/registryEnabled=false"]})

import numpy as np
from PIL import Image
import omni.usd
import omni.timeline
import omni.replicator.core as rep
from pxr import Gf, UsdGeom, UsdLux, UsdShade, Sdf

from nomad_isaac.common import (SCENARIO_PATH, integrate_se2, original_controller,
                                read_scenario, receive_packet, send_packet, write_json, export_view_scene)
from nomad_isaac.clearance import ObstacleMonitor, obstacle_bounds


def build_scene(config):
    stage = omni.usd.get_context().get_stage()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    def box(name, xyz, scale, color, double_scale=False):
        prim = UsdGeom.Cube.Define(stage, "/World/" + name)
        prim.CreateSizeAttr(1.0)
        prim.AddTranslateOp().Set(Gf.Vec3d(*xyz))
        if double_scale:
            prim.AddScaleOp(precision=UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*scale))
        else:
            prim.AddScaleOp().Set(Gf.Vec3f(*scale))
        material = UsdShade.Material.Define(stage, "/World/Materials/" + name)
        shader = UsdShade.Shader.Define(stage, material.GetPath().AppendChild("Shader"))
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.85)
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        UsdShade.MaterialBindingAPI.Apply(prim.GetPrim()).Bind(material)

    box("Floor", (2, 0, -.05), (8, 3, .1), (.22, .23, .24))
    box("LeftWall", (2, 1.55, 1.3), (8, .1, 2.6), (.78, .76, .70))
    box("RightWall", (2, -1.55, 1.3), (8, .1, 2.6), (.76, .77, .79))
    box("EndWall", (6.05, 0, 1.3), (.1, 3.2, 2.6), (.70, .64, .52))
    # Surface markings only: nothing blocks the corridor or protrudes into the path.
    for i, x in enumerate(np.arange(-1.5, 6, .5)):
        box(f"FloorSeam{i}", (float(x), 0, .001), (.012, 3, .002), (.12, .12, .12))
    for i, x in enumerate([-1., .5, 2., 3.5, 5.]):
        for side in [-1, 1]:
            color = (.43, .37, .29)
            if x == 2.:
                color = (.7, .04, .04) if side == 1 else (.04, .04, .7)
            box(f"Panel{i}_{'L' if side == 1 else 'R'}", (x, side * 1.498, 1.15),
                (.65, .004, 1.7), color)
    box("EndDoor", (5.998, .15, 1.1), (.004, .9, 2.2), (.32, .22, .13))
    if "obstacle" in config:
        obstacle = config["obstacle"]
        box("StaticObstacle", (*obstacle["center_xy_m"], obstacle["size_xyz_m"][2]/2),
            obstacle["size_xyz_m"], obstacle["color_rgb"], double_scale=True)
    dome = UsdLux.DomeLight.Define(stage, "/World/Light")
    dome.CreateIntensityAttr(1000.)
    agent = UsdGeom.Xform.Define(stage, "/World/Agent")
    translate = agent.AddTranslateOp()
    rotate = agent.AddRotateZOp(precision=UsdGeom.XformOp.PrecisionDouble)
    camera = UsdGeom.Camera.Define(stage, "/World/Agent/Camera")
    height = config["camera"]["height_m"]
    # USD camera -Z forward, +Y image-up; agent +X forward, +Y left, +Z up.
    camera_local = Gf.Matrix4d().SetLookAt(Gf.Vec3d(0, 0, height),
                                        Gf.Vec3d(1, 0, height), Gf.Vec3d(0, 0, 1)).GetInverse()
    camera.AddTransformOp().Set(camera_local)
    camera.CreateFocalLengthAttr(config["camera"]["focal_length_mm"])
    camera.CreateHorizontalApertureAttr(config["camera"]["horizontal_aperture_mm"])
    camera.CreateVerticalApertureAttr(config["camera"]["vertical_aperture_mm"])
    camera.CreateClippingRangeAttr(Gf.Vec2f(.02, 100.))
    product = rep.create.render_product(str(camera.GetPath()), (320, 240))
    annotator = rep.AnnotatorRegistry.get_annotator("rgb", device="cpu")
    annotator.attach([product])
    return stage, agent, translate, rotate, camera, annotator, product


def main():
    config = read_scenario(args.scenario or SCENARIO_PATH)
    write_json(out / "scenario.json", config)
    rep.orchestrator.set_capture_on_play(False)
    stage, agent, translate, rotate, camera, annotator, product = build_scene(config)
    timeline = omni.timeline.get_timeline_interface()
    timeline.pause()

    def set_pose(pose):
        translate.Set(Gf.Vec3d(float(pose[0]), float(pose[1]), 0))
        rotate.Set(float(np.degrees(pose[2])))

    def get_pose():
        matrix = UsdGeom.Xformable(agent).ComputeLocalToWorldTransform(0)
        origin = matrix.ExtractTranslation()
        forward = matrix.TransformDir(Gf.Vec3d(1, 0, 0))
        return np.array([origin[0], origin[1], math.atan2(forward[1], forward[0])])

    def capture(sim_time):
        timeline.set_current_time(sim_time)
        # Annotator attachment is asynchronous on startup; wait for valid RGB.
        for _ in range(20):
            rep.orchestrator.step(rt_subframes=4, delta_time=0.0, pause_timeline=True)
            array = np.asarray(annotator.get_data())
            if array.shape == (240, 320, 4):
                break
        assert array.shape == (240, 320, 4) and array.dtype == np.uint8, (array.shape, array.dtype)
        rgb = np.ascontiguousarray(array[:, :, :3])  # RGB annotator is RGBA, never BGR.
        assert rgb.std() > 5 and rgb.max() > 50, "Invalid/dark rendered camera"
        assert abs(timeline.get_current_time() - sim_time) < 1e-6
        return rgb

    goal_pose = np.array(config["goal_pose"])
    pose = np.array(config["start_pose"])
    set_pose(goal_pose)
    for _ in range(3):
        goal = capture(0.)
    Image.fromarray(goal).save(out / "goal.png")
    set_pose(pose)
    start_rgb = capture(0.)
    Image.fromarray(start_rgb).save(out / "observation_start.png")
    camera_matrix = UsdGeom.Xformable(camera).ComputeLocalToWorldTransform(0)
    forward = np.array(camera_matrix.TransformDir(Gf.Vec3d(0, 0, -1)))
    up = np.array(camera_matrix.TransformDir(Gf.Vec3d(0, 1, 0)))
    right = np.array(camera_matrix.TransformDir(Gf.Vec3d(1, 0, 0)))
    np.testing.assert_allclose(forward, [1, 0, 0], atol=1e-8)
    np.testing.assert_allclose(up, [0, 0, 1], atol=1e-8)
    np.testing.assert_allclose(right, [0, -1, 0], atol=1e-8)
    rgb_float = start_rgb.astype(float)
    red = (rgb_float[:, :, 0] > 1.5 * rgb_float[:, :, 2]) & (rgb_float[:, :, 0] > 1.5 * rgb_float[:, :, 1])
    blue = (rgb_float[:, :, 2] > 1.5 * rgb_float[:, :, 0]) & (rgb_float[:, :, 2] > 1.5 * rgb_float[:, :, 1])
    red_x = np.where(red)[1]; blue_x = np.where(blue)[1]
    assert len(red_x) > 20 and len(blue_x) > 20 and red_x.mean() < 160 < blue_x.mean(), "Camera color/left-right gate failed"
    render_check = {"status": "PASS", "rgb_shape": list(start_rgb.shape), "rgb_dtype": str(start_rgb.dtype),
                    "forward_world": forward.tolist(), "up_world": up.tolist(), "right_world": right.tolist(),
                    "red_left_pixels": len(red_x), "red_mean_pixel_x": float(red_x.mean()),
                    "blue_right_pixels": len(blue_x), "blue_mean_pixel_x": float(blue_x.mean()),
                    "goal_start_mean_abs_pixel_difference": float(np.abs(goal.astype(float) - rgb_float).mean()),
                    "python": sys.version, "executable": sys.executable, "numpy": np.__version__}
    if "obstacle" in config:
        green = (rgb_float[:, :, 1] > 1.5*rgb_float[:, :, 0]) & (rgb_float[:, :, 1] > 1.5*rgb_float[:, :, 2])
        assert int(green.sum()) > 100, "Obstacle must be visible in actual starting RGB before inference"
        bounds = UsdGeom.BBoxCache(0, [UsdGeom.Tokens.default_]).ComputeWorldBound(
            stage.GetPrimAtPath("/World/StaticObstacle")).ComputeAlignedRange()
        lower, upper = obstacle_bounds(config)
        np.testing.assert_allclose(np.array(bounds.GetMin())[:2], lower, rtol=0, atol=1e-12)
        np.testing.assert_allclose(np.array(bounds.GetMax())[:2], upper, rtol=0, atol=1e-12)
        render_check["obstacle_green_pixels"] = int(green.sum())
        render_check["obstacle_actual_world_aabb"] = [list(bounds.GetMin()), list(bounds.GetMax())]
    write_json(out / "render_check.json", render_check)
    stage.Export(str(out / "scene.usda"))
    if "obstacle" in config:
        export_view_scene(out / "scene.usda", out / "scene_gui.usda")
    if args.prepare_only:
        print("RENDER_GATE_PASS", flush=True)
        return

    controller = original_controller()
    history = deque(maxlen=4)
    history_times = deque(maxlen=4)
    history_hashes = deque(maxlen=4)
    dt = 1 / config["integration_hz"]
    obs_ticks = config["integration_hz"] // config["observation_hz"]
    control_ticks = config["integration_hz"] // config["controller_hz"]
    steps = int(config["timeout_sim_s"] * config["integration_hz"])
    begin_ns = time.monotonic_ns()
    minimum_distance = float(np.linalg.norm(pose[:2] - goal_pose[:2]))
    waypoint = None
    v = w = 0.
    request_id = -1
    applied_id = -1
    reason = "simulation_timeout"
    entry = False
    distance_travelled = 0.
    summaries = []
    monitor = ObstacleMonitor(config, out) if "obstacle" in config else None
    with socket.socket(socket.AF_UNIX) as connection, (out / "agent_trajectory.csv").open("x") as tf, \
            (out / "events.jsonl").open("x") as ef, (out / "controller.jsonl").open("x") as cf:
        connection.settimeout(30.)
        connection.connect(args.socket)
        writer = csv.writer(tf)
        writer.writerow(["simulation_time_s", "x_m", "y_m", "yaw_rad", "v_m_s", "w_rad_s", "goal_distance_m", "monotonic_ns"])
        for tick in range(steps + 1):
            sim_time = tick * dt
            actual_pose = get_pose()
            np.testing.assert_allclose(actual_pose, pose, atol=1e-8)
            distance = float(np.linalg.norm(actual_pose[:2] - goal_pose[:2]))
            minimum_distance = min(minimum_distance, distance)
            writer.writerow([sim_time, *actual_pose, v, w, distance, time.monotonic_ns()])
            if monitor is not None:
                monitor.observe_interval(previous if tick else actual_pose, actual_pose, v, w,
                                         sim_time-dt if tick else 0., dt if tick else 0.)
                if monitor.stop_reason is not None:
                    reason = monitor.stop_reason
                    entry = distance <= config["goal_tolerance_m"]
                    break  # Terminal measurement only: no avoidance or replacement command.
            if distance <= config["goal_tolerance_m"]:
                reason = "goal_entry"; entry = True; break
            if time.monotonic_ns() - begin_ns > config["timeout_navigation_wall_s"] * 1e9:
                reason = "navigation_wall_timeout"; break
            corridor = config["corridor"]; margin = config["boundary_stop_margin_m"]
            if not (corridor["xmin"] + margin < pose[0] < corridor["xmax"] - margin and abs(pose[1]) < corridor["half_width"] - margin):
                reason = "corridor_boundary_stop"; break
            if tick == steps:
                break
            if tick % obs_ticks == 0:
                rgb = capture(sim_time)
                observation_ns = time.monotonic_ns()
                history.append(rgb)
                history_times.append(sim_time)
                history_hashes.append(hashlib.sha256(rgb.tobytes()).hexdigest())
                if tick % (config["integration_hz"] * 5) == 0:
                    Image.fromarray(rgb).save(out / f"observation_{tick:04d}.png")
                if len(history) == 4:
                    request_id += 1
                    request = {"kind": "infer", "id": request_id, "seed": config["seed"] + 2 * request_id,
                               "observation_sim_s": sim_time, "observation_monotonic_ns": observation_ns,
                               "history_sim_s": list(history_times), "history_frame_sha256": list(history_hashes),
                               "observation_pose": pose.tolist()}
                    send_packet(connection, request, history=np.stack(history), goal=goal)
                    response, arrays = receive_packet(connection)
                    assert response["id"] == request_id
                    assert arrays["normalized_diffusion"].shape == (8, 8, 2)
                    assert all(np.isfinite(array).all() for array in arrays.values())
                    waypoint = arrays["selected_waypoint"].copy()
                    np.testing.assert_array_equal(waypoint, arrays["metric"][0, 2])
                    # Neither agent pose nor kinematic simulation clock advances while waiting.
                    np.testing.assert_array_equal(get_pose(), actual_pose)
                    assert abs(timeline.get_current_time() - sim_time) < 1e-6
                    pending = {**request, **response, "received_monotonic_ns": time.monotonic_ns(),
                               "received_sim_s": sim_time, "selected_waypoint_m": waypoint.tolist()}
                    if monitor is not None:
                        monitor.plan(request_id, arrays["metric"], request)
            if tick % control_ticks == 0:
                if waypoint is not None:
                    # ROS Float32MultiArray.data supplies Python floats. Preserve
                    # those exact point values and scalar promotion under NumPy 2.
                    v, w = map(float, controller(waypoint.tolist()))
                    assert 0 <= v <= .2 and abs(w) <= .4 and np.isfinite([v, w]).all()
                    if request_id != applied_id:
                        applied_id = request_id
                        event = {**pending, "application_sim_s": sim_time,
                                 "application_monotonic_ns": time.monotonic_ns(), "v_m_s": v, "w_rad_s": w}
                        ef.write(json.dumps(event) + "\n"); ef.flush()
                        summaries.append(event)
                cf.write(json.dumps({"simulation_time_s": sim_time, "monotonic_ns": time.monotonic_ns(),
                                     "waypoint_id": applied_id, "v_m_s": v, "w_rad_s": w}) + "\n")
            previous = pose.copy()
            pose = integrate_se2(pose, v, w, dt)
            distance_travelled += float(np.linalg.norm(pose[:2] - previous[:2]))
            set_pose(pose)
        final_rgb = capture(sim_time)
        Image.fromarray(final_rgb).save(out / "observation_final.png")
        send_packet(connection, {"kind": "stop"})
        assert receive_packet(connection)[0]["kind"] == "stopped"
    summary = {"integration_success": len(summaries) > 0 and distance_travelled > 0,
               "goal_entry": entry, "termination_reason": reason, "minimum_goal_distance_m": minimum_distance,
               "final_goal_distance_m": distance, "initial_goal_distance_m": 1.5,
               "final_pose": pose.tolist(), "simulation_duration_s": sim_time,
               "navigation_wall_seconds": (time.monotonic_ns() - begin_ns) / 1e9,
               "distance_travelled_m": distance_travelled, "inference_count": request_id + 1,
               "applied_waypoints": len(summaries), "scenario": config,
               "inference_median_ms": float(np.median([e["inference_ms"] for e in summaries])),
               "all_outputs_finite": True, "simulation_paused_during_inference": True,
               "frame_and_rgb_check": render_check,
               "raw_model_output_directory": "model/raw", "derived_trajectory_directory": "model/derived"}
    if monitor is not None:
        summary["obstacle_evaluation"] = monitor.finish(entry)
    write_json(out / "summary.json", summary)
    print("NAVIGATION_RESULT " + json.dumps(summary), flush=True)


try:
    main()
except Exception:
    import traceback
    (out / "FAILED.txt").write_text(traceback.format_exc())
    raise
finally:
    app.close()
