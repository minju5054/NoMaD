"""Tick-gated geometric monitoring; no policy or command modification."""
import json
import time

from .clearance import ObstacleMonitor, single_obstacle_config
from .common import write_json


def active_at_tick(config, tick):
    return int(tick) >= config["dynamic_obstacle"]["spawn_tick"]


class SuddenObstacleMonitor:
    def __init__(self, config, output):
        self.config = config
        self.output = output / "dynamic"
        self.output.mkdir(exist_ok=False)
        self.adaptive = "placement" in config["dynamic_obstacle"]
        self.obstacle = None if self.adaptive else config["dynamic_obstacle"]
        self.monitor = None if self.adaptive else ObstacleMonitor(single_obstacle_config(config, self.obstacle), self.output)
        self.placement = None
        self.activation = (self.output/"activation.jsonl").open("x")
        self.spawn = None
        self.last_tick = -1
        self.active_checks = 0

    @property
    def stop_reason(self):
        if self.placement is not None and self.placement["status"] == "PLACEMENT_INFEASIBLE":
            return "placement_infeasible"
        return self.monitor.stop_reason if self.monitor is not None else None

    def observe_tick(self, tick, previous, pose, v, w, old_id, old_valid, monotonic_ns,
                     old_received_ns=None):
        assert tick == self.last_tick + 1
        self.last_tick = tick
        hz = self.config["integration_hz"]
        if self.adaptive and tick == self.config["dynamic_obstacle"]["spawn_tick"]:
            from .old_rollout_placement import place_on_old
            started = time.monotonic_ns()
            remaining = 0. if old_received_ns is None else max(0., 1.-(monotonic_ns-old_received_ns)/1e9)
            self.placement = place_on_old(self.config, pose, v, w, old_id, old_valid, remaining)
            self.placement.update({"decision_tick": tick, "decision_sim_s": tick/hz,
                                   "pose_monotonic_ns": monotonic_ns, "old_received_monotonic_ns": old_received_ns,
                                   "computation_start_ns": started, "computation_end_ns": time.monotonic_ns()})
            if self.placement["status"] == "PLACED":
                self.obstacle = self.placement["obstacle"]
                self.monitor = ObstacleMonitor(single_obstacle_config(self.config, self.obstacle), self.output)
            write_json(self.output/"placement.json", self.placement)
        active = active_at_tick(self.config, tick) and self.obstacle is not None
        record = {"tick": tick, "simulation_time_s": tick/hz, "active": active,
                  "collision_checked": active, "monotonic_ns": monotonic_ns}
        if active:
            spawning = self.spawn is None
            duration = 0. if spawning else 1/hz
            start = pose if spawning else previous
            time_start = tick/hz if spawning else (tick-1)/hz
            check = self.monitor.observe_interval(start, pose, v, w, time_start, duration)
            record.update({"checked_duration_s": duration, "clearance_row": self.active_checks})
            self.active_checks += 1
            if spawning:
                assert tick == self.config["dynamic_obstacle"]["spawn_tick"]
                self.spawn = {**record, "pose": list(pose), "old_id": old_id, "old_command_valid": old_valid,
                              "old_command_vw": [v, w], "footprint_clearance_m": check["lower_m"],
                              "obstacle": self.obstacle}
                if self.adaptive:
                    self.spawn["old_remaining_timeout_s"] = self.placement["old_remaining_timeout_s"]
                    self.spawn["old_received_monotonic_ns"] = old_received_ns
                write_json(self.output/"spawn.json", self.spawn)
        self.activation.write(json.dumps(record)+"\n"); self.activation.flush()
        return record

    def finish(self, goal_entry):
        self.activation.close()
        result = self.monitor.finish(goal_entry) if self.monitor is not None else None
        if self.spawn is None and result is not None:
            for name in ("minimum_swept_clearance_lower_m", "minimum_swept_clearance_upper_m",
                         "minimum_corridor_clearance_lower_m"):
                result[name] = None
        status = "SPAWNED" if self.spawn else "PLACEMENT_INFEASIBLE" if self.placement else "NOT_TRIGGERED"
        return {"status": status, "spawn": self.spawn, "placement": self.placement,
                "active_checks": self.active_checks, "evaluation": result}
