"""Kit --exec entry point: open and loop an existing recorded USD animation only."""
import argparse
import json
import math

import carb
import omni.kit.app
import omni.kit.async_engine
import omni.kit.viewport.utility
import omni.timeline
import omni.usd
from pxr import Gf, UsdGeom


async def open_and_play(path):
    try:
        context = omni.usd.get_context()
        success, error = await context.open_stage_async(path)
        if not success:
            raise RuntimeError(error)
        app = omni.kit.app.get_app()
        for _ in range(3):
            await app.next_update_async()
        stage = context.get_stage()
        agent = UsdGeom.Xformable(stage.GetPrimAtPath("/World/Agent"))
        assert agent and len(agent.GetTimeSamples()) > 1, "Scene must contain recorded agent animation"
        camera = stage.GetMetadataByDictKey("customLayerData", "cameraSettings:boundCamera")
        assert camera and UsdGeom.Camera(stage.GetPrimAtPath(camera))
        viewport = omni.kit.viewport.utility.get_active_viewport()
        assert viewport is not None
        viewport.camera_path = camera
        rate = stage.GetTimeCodesPerSecond()
        start = stage.GetStartTimeCode()/rate
        end = stage.GetEndTimeCode()/rate
        assert end > start
        timeline = omni.timeline.get_timeline_interface()
        timeline.set_start_time(start)
        timeline.set_end_time(end)
        timeline.set_current_time(start)
        timeline.set_looping(True)
        timeline.play()
        print("RECORDED_REPLAY_STARTED " + json.dumps({
            "scene": path, "camera": str(viewport.camera_path), "duration_s": end-start,
            "time_codes_per_second": rate, "looping": True, "new_inference_count": 0}), flush=True)
        # Observe native GUI playback advancing; no pose/controller updates here.
        sample_at = start + min(2., (end-start)/2)
        for _ in range(600):
            await app.next_update_async()
            if timeline.get_current_time() >= sample_at:
                break
        seconds = timeline.get_current_time()
        matrix = agent.ComputeLocalToWorldTransform(seconds*rate)
        origin = matrix.ExtractTranslation()
        forward = matrix.TransformDir(Gf.Vec3d(1, 0, 0))
        print("RECORDED_REPLAY_SAMPLE " + json.dumps({
            "playing": timeline.is_playing(), "simulation_time_s": seconds,
            "pose": [origin[0], origin[1], math.atan2(forward[1], forward[0])]}), flush=True)
    except Exception as exc:
        carb.log_error("Recorded animation playback failed: " + str(exc))
        raise


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("path")
options = parser.parse_args()
omni.kit.async_engine.run_coroutine(open_and_play(options.path))
