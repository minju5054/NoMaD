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
import threading

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--socket")
parser.add_argument("--prepare-only", action="store_true")
parser.add_argument("--scenario", type=Path)
parser.add_argument("--asynchronous", action="store_true")
parser.add_argument("--pure-pursuit", action="store_true")
parser.add_argument("--s0-delay-sweep", action="store_true", help="Frozen Phase 3 S0 RAW+PP delay sweep")
parser.add_argument("--s0-stage2-method", choices=["CURV-SPEED", "HORIZON-SPEED", "GRAPH"], help="Frozen selected S0 speed/Graph experiment")
parser.add_argument("--phase4-method", choices=["RAW", "CURV-SPEED", "GRAPH-v5"])
parser.add_argument("--phase4d-confirm", action="store_true")
parser.add_argument("--phase4c-method", choices=["CURV", "CURV+ACC", "GRAPH"])
parser.add_argument("--plant-alpha", choices=["inf", "2.0", "1.0"])
parser.add_argument("--phase2-method", choices=["M0", "M3", "M5"])
parser.add_argument("--diagnostic-condition", choices=["C1", "C2", "C3"])
parser.add_argument("--phase2-distance-m", type=float, choices=[.6, .8, 1., 1.2])
parser.add_argument("--s1-mode", action="store_true")
parser.add_argument("--s1-v2-mode", action="store_true", help="Frozen obstacle-free straight corridor pilot")
parser.add_argument("--s1-distance-m", type=float, choices=[.8, 1., 1.2, 1.5])
parser.add_argument("--seed-offset", type=int, default=0)
parser.add_argument("--run-id")
parser.add_argument("--oracle-safety-stop", action="store_true")
parser.add_argument("--early-obstacle-mode", choices=["raw", "graph"])
parser.add_argument("--topomap", type=Path)
parser.add_argument("--render-topomap-reference", type=Path)
parser.add_argument("--controlled-delivery-delay", action="store_true")
parser.add_argument("--uniform-delivery-delay-s", type=float, choices=[0., .25, .5, .75])
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
from pxr import Gf, Usd, UsdGeom, UsdLux, UsdShade, Sdf

from nomad_isaac.common import (SCENARIO_PATH, integrate_se2, original_controller,
                                read_scenario, receive_packet, send_packet, write_json, export_view_scene)
from nomad_isaac.clearance import (ObstacleMonitor, MultiObstacleMonitor, obstacle_bounds,
                                  configured_obstacles, single_obstacle_config)


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

    straight = config.get("experiment_mode") in ("phase1_s1_v2_straight", "phase2_s1_v2")
    xmin, xmax = (-1., 9.) if straight else (-2., 6.)
    center, length = (xmin+xmax)/2, xmax-xmin
    box("Floor", (center, 0, -.05), (length, 3, .1), (.22, .23, .24))
    box("LeftWall", (center, 1.55, 1.3), (length, .1, 2.6), (.78, .76, .70))
    box("RightWall", (center, -1.55, 1.3), (length, .1, 2.6), (.76, .77, .79))
    box("EndWall", (xmax+.05, 0, 1.3), (.1, 3.2, 2.6), (.70, .64, .52))
    # Surface markings only: nothing blocks the corridor or protrudes into the path.
    for i, x in enumerate(np.arange(xmin+.5, xmax, .5)):
        box(f"FloorSeam{i}", (float(x), 0, .001), (.012, 3, .002), (.12, .12, .12))
    for i, x in enumerate([-1., .5, 2., 3.5, 5.] + ([6.5, 8.] if straight else [])):
        for side in [-1, 1]:
            color = (.43, .37, .29)
            if x == 2.:
                color = (.7, .04, .04) if side == 1 else (.04, .04, .7)
            box(f"Panel{i}_{'L' if side == 1 else 'R'}", (x, side * 1.498, 1.15),
                (.65, .004, 1.7), color)
    box("EndDoor", (xmax-.002, .15, 1.1), (.004, .9, 2.2), (.32, .22, .13))
    for obstacle in configured_obstacles(config):
        box(obstacle["id"], (*obstacle["center_xy_m"], obstacle["size_xyz_m"][2]/2),
            obstacle["size_xyz_m"], obstacle["color_rgb"], double_scale=True)
    if "dynamic_obstacle" in config:
        dynamic = config["dynamic_obstacle"]
        box(dynamic["id"], (*dynamic.get("center_xy_m", [0., 0.]), dynamic["size_xyz_m"][2]/2),
            dynamic["size_xyz_m"], dynamic["color_rgb"], double_scale=True)
        prim = stage.GetPrimAtPath("/World/"+dynamic["id"])
        if "placement" not in dynamic:
            rep.functional.modify.semantics(prim, {"class": "DynamicObstacle"}, mode="add")
        stage.SetTimeCodesPerSecond(config["integration_hz"])
        stage.SetFramesPerSecond(config["integration_hz"])
        stage.SetStartTimeCode(0)
        stage.SetEndTimeCode(config["timeout_sim_s"]*config["integration_hz"])
        visibility = UsdGeom.Imageable(prim).CreateVisibilityAttr()
        visibility.Set(UsdGeom.Tokens.invisible)
        visibility.Set(UsdGeom.Tokens.invisible, Usd.TimeCode(0))
        if "placement" not in dynamic:
            visibility.Set(UsdGeom.Tokens.inherited, Usd.TimeCode(dynamic["spawn_tick"]))
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
    if args.phase4d_confirm and not args.phase4c_method:
        raise ValueError("Phase4d requires Phase4c method and alpha")
    config = read_scenario(args.scenario or SCENARIO_PATH)
    if bool(args.phase4c_method)!=bool(args.plant_alpha):
        raise ValueError("Phase4c requires method and alpha together")
    if args.phase4c_method:
        from nomad_phase4c.config import validate_options, runtime_config
        validate_options(args)
        config=runtime_config(config,args)
    if args.phase4_method:
        from nomad_phase4.config import validate_options, runtime_config
        validate_options(args)
        config = runtime_config(config, args)
    if args.s0_stage2_method:
        from nomad_phase3_stage2.config import validate_options, runtime_config
        validate_options(args)
        config = runtime_config(config, args)
    if args.s0_delay_sweep:
        from nomad_phase3.config import validate_options, runtime_config
        validate_options(args)
        config = runtime_config(config)
    if args.phase2_method:
        from nomad_phase2.config import validate_options
        validate_options(args)
    elif args.phase2_distance_m is not None:
        raise ValueError("Phase2 distance requires Phase2 method")
    if args.s1_v2_mode:
        from nomad_phase1.s1_v2 import validate_options
        validate_options(args)
    if args.s1_mode:
        from nomad_phase1.s1 import validate_options
        validate_options(args)
        config["dynamic_obstacle"]["placement"]["forward_clearance_m"] = args.s1_distance_m
    elif args.s1_distance_m is not None:
        raise ValueError("S1 distance requires S1 mode")
    from nomad_isaac.seed_offset import validate_seed_options
    validate_seed_options(args)
    if args.seed_offset or args.run_id is not None:
        config = {**config, "seed_offset": args.seed_offset, "run_id": args.run_id}
    if args.pure_pursuit:
        from nomad_phase0.chunk_execution import validate_mode
        validate_mode(args)
    if args.early_obstacle_mode:
        from nomad_isaac.early_experiment import validate_early
        validate_early(config, args.topomap, args.asynchronous, args.prepare_only,
                       args.controlled_delivery_delay, args.uniform_delivery_delay_s, args.oracle_safety_stop)
    if args.oracle_safety_stop:
        assert args.topomap and args.asynchronous and not args.prepare_only
        assert not args.controlled_delivery_delay and args.uniform_delivery_delay_s is None
        assert "placement" in config.get("dynamic_obstacle", {})
    if "dynamic_obstacle" in config and not (args.s1_mode or args.phase2_method) and (not args.asynchronous or args.controlled_delivery_delay or
                                         args.uniform_delivery_delay_s not in (None, 0.)):
        raise ValueError("Sudden obstacle requires asynchronous execution with zero additional delay")
    if args.phase2_method:
        from nomad_phase2.config import runtime_config
        config = runtime_config(config,args)
    if args.asynchronous:
        config = {**config, "synchronous": False}
    if args.topomap:
        from nomad_isaac.common import sha256_file
        assert args.asynchronous
        if "dynamic_obstacle" in config and not args.early_obstacle_mode and not args.s1_mode and not args.phase2_method:
            from nomad_isaac.topomap import validate_dynamic_combination
            validate_dynamic_combination(config, args.topomap, args.asynchronous, args.prepare_only,
                                         args.controlled_delivery_delay, args.uniform_delivery_delay_s)
        config = {**config, "goal_mode": "topomap", "topomap_manifest": str(args.topomap.resolve()),
                  "topomap_manifest_sha256": sha256_file(args.topomap)}
    obstacles = configured_obstacles(config)
    write_json(out / "scenario.json", config)
    rep.orchestrator.set_capture_on_play(False)
    stage, agent, translate, rotate, camera, annotator, product = build_scene(config)
    timeline = omni.timeline.get_timeline_interface()
    timeline.pause()
    dynamic_annotator = None
    adaptive = "placement" in config.get("dynamic_obstacle", {})
    resolved_dynamic = config["dynamic_obstacle"] if args.early_obstacle_mode else None
    main_thread_id = threading.get_ident()
    if "dynamic_obstacle" in config:
        from nomad_isaac.sudden_obstacle import active_at_tick
        dynamic_prim = stage.GetPrimAtPath("/World/"+config["dynamic_obstacle"]["id"])
        if not adaptive and not args.early_obstacle_mode:
            dynamic_annotator = rep.AnnotatorRegistry.get_annotator("instance_segmentation_fast", device="cpu")
            dynamic_annotator.attach([product])

    def sync_dynamic(snapshot):
        nonlocal resolved_dynamic
        assert threading.get_ident() == main_thread_id
        box = snapshot.get("resolved_dynamic_obstacle")
        if not (args.s1_mode or args.phase2_method) and snapshot["tick"] >= config["dynamic_obstacle"]["spawn_tick"]:
            assert snapshot.get("dynamic_placement_status") != "PENDING"
        if box is None:
            return
        if resolved_dynamic is not None:
            assert box == resolved_dynamic
            return
        translate_box = next(op for op in UsdGeom.Xformable(dynamic_prim).GetOrderedXformOps()
                             if op.GetOpType() == UsdGeom.XformOp.TypeTranslate)
        translate_box.Set(Gf.Vec3d(*box["center_xy_m"], box["size_xyz_m"][2]/2))
        UsdGeom.Imageable(dynamic_prim).GetVisibilityAttr().Set(UsdGeom.Tokens.inherited, Usd.TimeCode(box["spawn_tick"]))
        bounds = UsdGeom.BBoxCache(box["spawn_tick"], [UsdGeom.Tokens.default_]).ComputeWorldBound(dynamic_prim).ComputeAlignedRange()
        lower, upper = obstacle_bounds(single_obstacle_config(config, box))
        np.testing.assert_allclose(bounds.GetMin(), [*lower, 0.], atol=1e-12, rtol=0)
        np.testing.assert_allclose(bounds.GetMax(), [*upper, box["size_xyz_m"][2]], atol=1e-12, rtol=0)
        resolved_dynamic = dict(box)
        write_json(out/"dynamic_render_update.json", {"obstacle": box, "snapshot_tick": snapshot["tick"],
            "snapshot_sim_s": snapshot["sim_s"], "applied_host_ns": time.monotonic_ns(),
            "visibility_source_tick": box["spawn_tick"], "thread": "main",
            "usd_aabb": [list(bounds.GetMin()), list(bounds.GetMax())]})

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
            segmentation = dynamic_annotator.get_data() if dynamic_annotator is not None else None
            segmentation_valid = (dynamic_annotator is None or
                isinstance(segmentation, dict) and np.shape(segmentation.get("data")) == (240, 320))
            if array.shape == (240, 320, 4) and segmentation_valid:
                break
        assert array.shape == (240, 320, 4) and array.dtype == np.uint8, (array.shape, array.dtype)
        rgb = np.ascontiguousarray(array[:, :, :3])  # RGB annotator is RGBA, never BGR.
        assert rgb.std() > 5 and rgb.max() > 50, "Invalid/dark rendered camera"
        assert abs(timeline.get_current_time() - sim_time) < 1e-6
        if dynamic_annotator is not None:
            assert segmentation_valid
            tick = round(sim_time*config["integration_hz"])
            assert abs(tick/config["integration_hz"]-sim_time) < 1e-10
            active = active_at_tick(config, tick)
            visibility = UsdGeom.Imageable(dynamic_prim).ComputeVisibility(Usd.TimeCode(tick))
            assert (visibility == UsdGeom.Tokens.inherited) == active
            labels = segmentation["info"]["idToLabels"]
            ids = [int(key) for key, path in labels.items() if str(path) == str(dynamic_prim.GetPath())]
            mask = np.isin(np.asarray(segmentation["data"]), ids)
            if not active:
                assert not mask.any(), "Dynamic obstacle rendered before spawn timestamp"
            pixels = rgb[mask].astype(float)
            magenta = ((pixels[:, 0] > 1.5*pixels[:, 1]) & (pixels[:, 2] > 1.5*pixels[:, 1]) &
                       (pixels[:, 0] > 40) & (pixels[:, 2] > 40))
            capture.dynamic_metadata = {"capture_tick": tick, "active": active, "usd_visibility": str(visibility),
                "instance_ids": ids, "instance_pixels": int(mask.sum()), "magenta_pixels": int(magenta.sum()),
                "visible": int(mask.sum()) >= config["dynamic_obstacle"]["minimum_visible_pixels"],
                "mask_sha256": hashlib.sha256(mask.tobytes()).hexdigest(),
                "masked_rgb_median": np.median(pixels, axis=0).tolist() if len(pixels) else None}
            capture.dynamic_mask = mask
        elif adaptive or args.early_obstacle_mode:
            from nomad_isaac.old_rollout_placement import magenta_mask
            tick = round(sim_time*config["integration_hz"])
            active = resolved_dynamic is not None and (tick >= resolved_dynamic["spawn_tick"] if (args.s1_mode or args.phase2_method) else active_at_tick(config, tick))
            visibility = UsdGeom.Imageable(dynamic_prim).ComputeVisibility(Usd.TimeCode(tick))
            assert (visibility == UsdGeom.Tokens.inherited) == active
            mask = magenta_mask(rgb)
            if not active:
                assert not mask.any(), "Magenta obstacle must be absent before activation"
            capture.dynamic_metadata = {"capture_tick": tick, "active": active,
                "usd_visibility": str(visibility), "center_xy_m": resolved_dynamic["center_xy_m"] if resolved_dynamic else None,
                "evidence_mode": "RGB_MAGENTA", "magenta_pixels": int(mask.sum()),
                "visible": active and int(mask.sum()) >= config["dynamic_obstacle"]["minimum_visible_pixels"],
                "mask_sha256": hashlib.sha256(mask.tobytes()).hexdigest()}
            capture.dynamic_mask = mask
        return rgb

    if adaptive:
        capture.sync_dynamic = sync_dynamic

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
    if dynamic_annotator is not None:
        render_check["dynamic_initial"] = capture.dynamic_metadata
        dynamic_box = config["dynamic_obstacle"]
        bounds = UsdGeom.BBoxCache(config["dynamic_obstacle"]["spawn_tick"], [UsdGeom.Tokens.default_]).ComputeWorldBound(dynamic_prim).ComputeAlignedRange()
        lower, upper = obstacle_bounds(single_obstacle_config(config, dynamic_box))
        np.testing.assert_allclose(bounds.GetMin(), [*lower, 0.], atol=1e-12, rtol=0)
        np.testing.assert_allclose(bounds.GetMax(), [*upper, dynamic_box["size_xyz_m"][2]], atol=1e-12, rtol=0)
        render_check["dynamic_active_aabb"] = [list(bounds.GetMin()), list(bounds.GetMax())]
    elif args.early_obstacle_mode:
        render_check["dynamic_initial"] = capture.dynamic_metadata
        dynamic_box = config["dynamic_obstacle"]
        bounds = UsdGeom.BBoxCache(dynamic_box["spawn_tick"], [UsdGeom.Tokens.default_]).ComputeWorldBound(dynamic_prim).ComputeAlignedRange()
        lower, upper = obstacle_bounds(single_obstacle_config(config, dynamic_box))
        np.testing.assert_allclose(bounds.GetMin(), [*lower, 0.], atol=1e-12, rtol=0)
        np.testing.assert_allclose(bounds.GetMax(), [*upper, .8], atol=1e-12, rtol=0)
        render_check["fixed_dynamic_world_aabb"] = [list(bounds.GetMin()), list(bounds.GetMax())]
    elif adaptive:
        render_check["dynamic_initial"] = capture.dynamic_metadata
        render_check["dynamic_placement"] = ("Pending S1 world-region entry; hidden placeholder is not collision geometry"
                                              if (args.s1_mode or args.phase2_method) else "Pending tick 970; hidden placeholder is not collision geometry")
    if obstacles:
        green = (rgb_float[:, :, 1] > 1.5*rgb_float[:, :, 0]) & (rgb_float[:, :, 1] > 1.5*rgb_float[:, :, 2])
        assert int(green.sum()) > 100, "Obstacle must be visible in actual starting RGB before inference"
        actual_bounds = {}
        for obstacle in obstacles:
            bounds = UsdGeom.BBoxCache(0, [UsdGeom.Tokens.default_]).ComputeWorldBound(
                stage.GetPrimAtPath("/World/" + obstacle["id"])).ComputeAlignedRange()
            lower, upper = obstacle_bounds(single_obstacle_config(config, obstacle))
            np.testing.assert_allclose(np.array(bounds.GetMin()), [*lower, 0], rtol=0, atol=1e-12)
            np.testing.assert_allclose(np.array(bounds.GetMax()), [*upper, obstacle["size_xyz_m"][2]], rtol=0, atol=1e-12)
            actual_bounds[obstacle["id"]] = [list(bounds.GetMin()), list(bounds.GetMax())]
        render_check["obstacle_green_pixels"] = int(green.sum())
        if "obstacles" in config:
            render_check["obstacles_actual_world_aabb"] = actual_bounds
        else:
            render_check["obstacle_actual_world_aabb"] = actual_bounds["StaticObstacle"]
    if args.s1_v2_mode or args.phase2_method:
        cache = UsdGeom.BBoxCache(0, [UsdGeom.Tokens.default_])
        bounds = cache.ComputeWorldBound(stage.GetPrimAtPath("/World/Floor")).ComputeAlignedRange()
        np.testing.assert_allclose(list(bounds.GetMin())[:2], [-1., -1.5], atol=1e-10, rtol=0)
        np.testing.assert_allclose(list(bounds.GetMax())[:2], [9., 1.5], atol=1e-10, rtol=0)
        assert not obstacles
        assert args.phase2_method or "dynamic_obstacle" not in config
        render_check["straight_corridor_floor_xy_bounds"] = [[-1., -1.5], [9., 1.5]]
        render_check["obstacle_count"] = 0
    write_json(out / "render_check.json", render_check)
    stage.Export(str(out / "scene.usda"))
    if obstacles:
        export_view_scene(out / "scene.usda", out / "scene_gui.usda")
    if args.prepare_only:
        if args.render_topomap_reference:
            from nomad_isaac.topomap import render_reference
            manifest = render_reference(args.render_topomap_reference, out, config, capture, set_pose, get_pose)
            print(f"TOPOMAP_RENDERED {manifest['node_count']} nodes", flush=True)
        print("RENDER_GATE_PASS", flush=True)
        return

    if args.asynchronous:
        from nomad_isaac.async_runtime import run_async
        result = run_async(config, out, args.socket, goal, capture, set_pose, get_pose, render_check,
                           controlled_delivery_delay=args.controlled_delivery_delay,
                           uniform_delivery_delay_s=args.uniform_delivery_delay_s,
                           oracle_safety_stop=args.oracle_safety_stop,
                           online_graph=args.early_obstacle_mode == "graph", pure_pursuit=args.pure_pursuit)
        if adaptive:
            stage.Export(str(out/"scene_resolved.usda"))
            export_view_scene(out/"scene_resolved.usda", out/"scene_resolved_gui.usda")
        return result

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
    initial_distance = minimum_distance
    waypoint = None
    v = w = 0.
    request_id = -1
    applied_id = -1
    reason = "simulation_timeout"
    entry = False
    distance_travelled = 0.
    summaries = []
    monitor = (MultiObstacleMonitor(config, out) if "obstacles" in config else
               ObstacleMonitor(config, out) if "obstacle" in config else None)
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
               "final_goal_distance_m": distance, "initial_goal_distance_m": initial_distance,
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
