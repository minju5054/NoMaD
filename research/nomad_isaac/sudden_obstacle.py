"""Tick-gated geometric monitoring; no policy or command modification."""
import json

from .clearance import ObstacleMonitor, single_obstacle_config
from .common import write_json


def active_at_tick(config, tick):
    return int(tick) >= config["dynamic_obstacle"]["spawn_tick"]


class SuddenObstacleMonitor:
    def __init__(self, config, output):
        self.config = config
        self.output = output / "dynamic"
        self.output.mkdir(exist_ok=False)
        self.monitor = ObstacleMonitor(single_obstacle_config(config, config["dynamic_obstacle"]), self.output)
        self.activation = (self.output/"activation.jsonl").open("x")
        self.spawn = None
        self.last_tick = -1
        self.active_checks = 0

    @property
    def stop_reason(self):
        return self.monitor.stop_reason

    def observe_tick(self, tick, previous, pose, v, w, old_id, old_valid, monotonic_ns):
        assert tick == self.last_tick + 1
        self.last_tick = tick
        hz = self.config["integration_hz"]
        active = active_at_tick(self.config, tick)
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
                              "obstacle": self.config["dynamic_obstacle"]}
                write_json(self.output/"spawn.json", self.spawn)
        self.activation.write(json.dumps(record)+"\n"); self.activation.flush()
        return record

    def finish(self, goal_entry):
        self.activation.close()
        result = self.monitor.finish(goal_entry)
        if self.spawn is None:
            for name in ("minimum_swept_clearance_lower_m", "minimum_swept_clearance_upper_m",
                         "minimum_corridor_clearance_lower_m"):
                result[name] = None
        return {"status": "SPAWNED" if self.spawn else "NOT_TRIGGERED", "spawn": self.spawn,
                "active_checks": self.active_checks, "evaluation": result}
