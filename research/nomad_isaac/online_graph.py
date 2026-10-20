"""Stop-and-plan Graph action scheduling; CPU solve never runs on the 72 Hz thread."""
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

import numpy as np

from .common import ROOT, original_controller, write_json
from .oracle_safety_stop import evaluate


class CPUClient:
    def __init__(self, out):
        out.mkdir(exist_ok=False)
        self.out = out
        self.log = (out/"worker.log").open("x")
        env = os.environ.copy()
        for key in ("LD_LIBRARY_PATH", "LD_PRELOAD", "VIRTUAL_ENV", "PYTHONHOME", "PYTHONPYCACHEPREFIX"):
            env.pop(key, None)
        env["PYTHONPATH"] = str(ROOT/"research")
        self.process = subprocess.Popen(["/usr/bin/python3", "-u", "-m", "nomad_isaac.online_graph_worker", str(out)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, text=True, env=env, cwd=ROOT)
        ready = json.loads(self.process.stdout.readline())
        assert ready["ready"]
        write_json(out/"environment.json", ready)
        self.jobs, self.results = queue.Queue(1), queue.Queue(1)
        self.error = None
        self.thread = threading.Thread(target=self.run, name="graph-cpu-ipc", daemon=True)
        self.thread.start()

    def run(self):
        try:
            while True:
                job = self.jobs.get()
                self.process.stdin.write(json.dumps({"stop": True} if job is None else job)+"\n")
                self.process.stdin.flush()
                if job is None:
                    return
                line = self.process.stdout.readline()
                if not line:
                    raise RuntimeError("Graph worker exited without a result")
                result = json.loads(line)
                result["cpu_packet_received_monotonic_ns"] = time.monotonic_ns()
                self.results.put(result)
        except BaseException as exc:
            self.error = repr(exc)

    def poll(self):
        if self.error:
            raise RuntimeError(self.error)
        try:
            return self.results.get_nowait()
        except queue.Empty:
            return None

    def close(self):
        # Navigation has already terminated; preserve any pending result as unapplied.
        self.jobs.put(None)
        self.thread.join(120)
        if self.thread.is_alive():
            self.process.terminate()
            self.thread.join(5)
            write_json(self.out/"shutdown_timeout.json", {"pending_result_unapplied": True})
        self.process.wait(timeout=10)
        self.log.close()


class GraphRecovery:
    def __init__(self, config, out, client=None):
        self.config = config
        self.client = client if client is not None else CPUClient(out/"graph")
        self.log = (out/"graph_control.jsonl").open("x")
        self.pending = None
        self.action = None
        self.next_id = 0
        self.attempted = set()

    def apply(self, core, refresh, switch, tick, box, sample):
        now = time.monotonic_ns()
        nominal = [core.v, core.w]
        active = box is not None and tick >= box["spawn_tick"]
        check = evaluate(self.config, core.pose, nominal, box) if active else None
        geometry = {**self.config, "obstacles": [*self.config["obstacles"], box]} if active else None
        decision = {"tick": tick, "simulation_time_s": tick/72, "monotonic_ns": now,
                    "pose": core.pose.tolist(), "nominal_waypoint_id": core.applied_id,
                    "nominal_valid": core.command_valid, "nominal_vw": nominal,
                    "nominal_check": check, "source": "NOMINAL", "graph_id": None}
        result = self.client.poll()
        if result is not None:
            job = self.pending
            assert job is not None and result["graph_id"] == job["graph_id"]
            self.pending = None
            valid_B = np.max(np.abs(core.pose-np.array(job["boundary"]))) <= 1e-9
            valid_geometry = geometry == job["geometry"]
            acceptance = None
            if result["status"] == "CONVERGED" and valid_B and valid_geometry:
                acceptance = evaluate(self.config, core.pose, result["command_vw"], box)
                if acceptance["safe"]:
                    self.action = {"graph_id": job["graph_id"], "fresh_id": job["fresh_id"],
                        "end_tick": tick+16, "command_vw": result["command_vw"],
                        "original_waypoint": job["sample0"][2],
                        "corrected_waypoint": result["corrected_B_local_waypoint"],
                        "original_input_age_at_application_s": (now-job["observation_monotonic_ns"])/1e9,
                        "original_receive_age_at_application_s": (now-job["fresh_received_monotonic_ns"])/1e9}
            decision["result"] = {"graph_id": job["graph_id"], "fresh_id": job["fresh_id"],
                "status": result["status"], "valid_B": bool(valid_B), "valid_geometry": valid_geometry,
                "acceptance_check": acceptance, "accepted": self.action is not None,
                "solve_start_monotonic_ns": result["solve_start_monotonic_ns"],
                "solve_end_monotonic_ns": result["solve_end_monotonic_ns"],
                "packet_received_monotonic_ns": result["cpu_packet_received_monotonic_ns"],
                "wait_wall_s": (now-job["submit_monotonic_ns"])/1e9}
        if self.action is not None and tick >= self.action["end_tick"]:
            self.action = None
        actual = nominal
        if self.action is not None:
            action_check = evaluate(self.config, core.pose, self.action["command_vw"], box)
            decision["action_check"] = action_check
            if action_check["safe"]:
                actual = self.action["command_vw"]
                decision.update(source="GRAPH", graph_id=self.action["graph_id"], action=dict(self.action))
            else:
                self.action = None
                actual = [0., 0.]
                decision["source"] = "GRAPH_SAFETY_STOP"
        elif self.pending is not None:
            actual = [0., 0.]
            decision.update(source="GRAPH_WAIT", graph_id=self.pending["graph_id"])
        elif active and core.command_valid and not check["safe"]:
            actual = [0., 0.]
            decision["source"] = "SAFETY_STOP"
            fresh = core.latest
            if fresh["id"] not in self.attempted:
                assert sample is not None and sample[0] == fresh["id"]
                job = {"graph_id": self.next_id, "fresh_id": fresh["id"], "sample0": sample[1].tolist(),
                    "observation_pose": fresh["observation_pose"], "observation_sim_s": fresh["observation_sim_s"],
                    "observation_monotonic_ns": fresh["observation_monotonic_ns"],
                    "fresh_received_monotonic_ns": fresh["received_monotonic_ns"],
                    "boundary": core.pose.tolist(), "boundary_tick": tick, "geometry": geometry,
                    "submit_monotonic_ns": time.monotonic_ns(), "nominal_vw_at_submit": nominal}
                self.attempted.add(fresh["id"])
                self.next_id += 1
                self.pending = job
                self.client.jobs.put_nowait(job)
                decision.update(source="GRAPH_WAIT", graph_id=job["graph_id"], submitted_fresh_id=fresh["id"])
        if not core.command_valid and decision["source"] == "NOMINAL":
            decision["source"] = "WAYPOINT_"+refresh["status"].upper()
        core.v, core.w = map(float, actual)
        decision["applied_vw"] = [core.v, core.w]
        decision["decision_end_monotonic_ns"] = time.monotonic_ns()
        fields = {"applied_v_m_s": core.v, "applied_w_rad_s": core.w,
                  "execution_source": decision["source"], "graph_action_id": decision["graph_id"],
                  "command_decision_monotonic_ns": decision["decision_end_monotonic_ns"]}
        refresh.update(fields)
        if switch is not None:
            switch.update(fields)  # This event remains a nominal FRESH switch, not a Graph action.
        self.log.write(json.dumps(decision)+"\n")
        self.log.flush()
        return decision

    def close(self):
        self.client.close()
        self.log.close()
