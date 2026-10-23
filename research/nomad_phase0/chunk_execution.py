"""Opt-in XY chunk execution; no obstacle, goal or safety input to the follower."""
import json
import math
from pathlib import Path

import numpy as np

from nomad_isaac.common import local_to_world, sha256_file
from .pure_pursuit import PurePursuit, XYPath


PROTOCOL_PATH = Path(__file__).with_name("chunk_pilot_protocol.json")


def protocol():
    return json.loads(PROTOCOL_PATH.read_text())


def validate_mode(args):
    if getattr(args, "s0_stage2_method", None):
        from nomad_phase3_stage2.config import validate_options
        validate_options(args)
        return
    if getattr(args, "s0_delay_sweep", False):
        from nomad_phase3.config import validate_options
        validate_options(args)
        return
    if getattr(args, "phase2_method", None):
        from nomad_phase2.config import validate_options
        validate_options(args)
        return
    if getattr(args, "s1_v2_mode", False):
        from nomad_phase1.s1_v2 import validate_options
        validate_options(args)
        return
    if getattr(args, "s1_mode", False):
        from nomad_phase1.s1 import validate_options
        validate_options(args)
        return
    p = protocol()
    if (not args.asynchronous or not args.topomap or args.prepare_only
            or args.oracle_safety_stop or args.early_obstacle_mode
            or args.controlled_delivery_delay or args.uniform_delivery_delay_s is not None
            or args.render_topomap_reference):
        raise ValueError("Pure Pursuit PILOT requires only static Topomap asynchronous zero-delay execution")
    if sha256_file(args.scenario) != p["scenario_sha256"]:
        raise ValueError("Pure Pursuit PILOT scenario differs from frozen S0")
    if sha256_file(args.topomap) != p["topomap_manifest_sha256"]:
        raise ValueError("Pure Pursuit PILOT requires the unchanged 14-node 2s Topomap")
    settings = json.loads(Path(__file__).with_name("follower_protocol.json").read_text())["follower"]
    assert settings == p["follower"]


def describe_chunk(local_xy, observation_pose):
    local = np.asarray(local_xy)
    assert local.shape == (8, 2) and np.isfinite(local).all()
    world = local_to_world(local, np.asarray(observation_pose))
    result = {"native_local_xy_m": local.tolist(), "world_xy_m": world.tolist(),
              "native_length_m": float(np.linalg.norm(np.diff(world, axis=0), axis=1).sum()),
              "anchor": "observation_pose", "native_point_count": 8}
    try:
        path = XYPath(world)
        result.update(path_valid=True, effective_point_count=len(path.points), invalid_reason=None)
    except ValueError as exc:
        result.update(path_valid=False, effective_point_count=None, invalid_reason=str(exc))
    return result


def tangent_at_projection(path, xy, minimum_length):
    """Diagnostic only: outgoing tangent at independent nearest projection at B."""
    if path is None:
        return {"valid": False, "reason": "no_valid_path", "heading_rad": None}
    arclength, distance = path.project(xy)
    index = min(int(np.searchsorted(path.s, arclength, side="right")-1), len(path.delta)-1)
    valid = bool(path.lengths[index] >= minimum_length)
    return {"valid": valid, "reason": None if valid else "segment_below_minimum",
            "heading_rad": math.atan2(*path.delta[index][::-1]) if valid else None,
            "segment_index": index, "segment_length_m": float(path.lengths[index]),
            "projected_arclength_m": arclength, "distance_to_path_m": distance}


class ChunkExecution:
    """Replace only actual integration commands after the original timing core."""
    def __init__(self):
        self.settings = protocol()
        self.follower = None
        self.active_id = -1
        self.last_command = [0., 0.]

    def apply(self, core, refresh, switch):
        transition = None
        if switch is not None:
            old_path = self.follower.path if self.follower is not None else None
            old_id = self.active_id
            chunk = switch["chunk"]
            self.active_id = switch["id"]
            self.follower = (PurePursuit(chunk["world_xy_m"], self.settings["follower"])
                             if chunk["path_valid"] else None)
            new_path = self.follower.path if self.follower is not None else None
            minimum = self.settings["diagnostic_tangent_minimum_segment_m"]
            old_tangent = tangent_at_projection(old_path, core.pose[:2], minimum)
            fresh_tangent = tangent_at_projection(new_path, core.pose[:2], minimum)
            difference = None
            if old_tangent["valid"] and fresh_tangent["valid"]:
                difference = (fresh_tangent["heading_rad"]-old_tangent["heading_rad"]+math.pi) % (2*math.pi)-math.pi
            transition = {"old_id": old_id, "fresh_id": self.active_id,
                          "old_tangent_at_B": old_tangent, "fresh_tangent_at_B": fresh_tangent,
                          "signed_tangent_change_rad": difference,
                          "actual_command_before": list(self.last_command),
                          "progress_reset": True,
                          "remaining_length_at_switch_m": (
                              float(new_path.s[-1]-new_path.project(core.pose[:2])[0])
                              if new_path is not None else None)}
        diagnostic = {"active_chunk_id": self.active_id, "path_valid": self.follower is not None,
                      "stop_reason": None, "endpoint_clamped": None,
                      "v_clipped": False, "w_clipped": False}
        if not refresh["valid"]:
            command = (0., 0.)
            diagnostic["stop_reason"] = refresh["status"]
        elif self.follower is None:
            command = (0., 0.)
            diagnostic["stop_reason"] = "invalid_chunk"
        else:
            assert self.active_id == refresh["waypoint_id"]
            command, details = self.follower.control(core.pose)
            diagnostic.update(details)
            length = float(self.follower.path.s[-1])
            diagnostic.update(native_length_m=length,
                              remaining_progress_length_m=length-self.follower.progress,
                              endpoint_clamped=bool(self.follower.progress+self.settings["follower"]["lookahead_m"] > length),
                              stop_reason="endpoint" if details["endpoint_stop"] else None)
        core.v, core.w = command
        self.last_command = list(command)
        actual = {"applied_v_m_s": core.v, "applied_w_rad_s": core.w,
                  "applied_command_source": "pure_pursuit" if diagnostic["stop_reason"] is None else diagnostic["stop_reason"],
                  "pure_pursuit": diagnostic}
        refresh.update(actual)
        if switch is not None:
            transition["actual_command_after"] = list(command)
            transition["actual_command_delta"] = (np.array(command)-transition["actual_command_before"]).tolist()
            switch.update(actual, chunk_transition=transition)
