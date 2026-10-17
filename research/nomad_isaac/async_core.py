"""ROS-free clock/waypoint state and one-outstanding-request socket bridge."""
import queue
import threading
import time

import numpy as np

from .common import integrate_se2, original_controller, receive_packet, send_packet


def deadline_ns(epoch_ns, tick, hz):
    return epoch_ns + round(tick * 1_000_000_000 / hz)


class WaypointExecution:
    def __init__(self, start_pose, integration_hz=72, controller_hz=9):
        assert integration_hz % controller_hz == 0
        self.pose = np.array(start_pose, dtype=float)
        self.hz = integration_hz
        self.control_stride = integration_hz // controller_hz
        self.controller = original_controller()
        self.latest = None
        self.applied_id = -1
        self.v = self.w = 0.
        self.command_valid = False
        self.expired_ids = set()

    def receive(self, metadata, waypoint):
        expected = 0 if self.latest is None else self.latest["id"] + 1
        if metadata["id"] != expected:
            raise ValueError(f"Out-of-order result {metadata['id']}; expected {expected}")
        point = np.asarray(waypoint)
        assert point.shape == (2,) and np.isfinite(point).all()
        self.latest = {**metadata, "selected_waypoint_m": point.tolist()}

    def integrate(self):
        self.pose = integrate_se2(self.pose, self.v, self.w, 1/self.hz)
        return self.pose.copy()

    def control(self, tick, now_ns):
        if tick % self.control_stride:
            return None, None
        age = None if self.latest is None else (now_ns-self.latest["received_monotonic_ns"])/1e9
        assert age is None or age >= 0
        self.command_valid = age is not None and age < 1.0
        status = "valid" if self.command_valid else "missing" if age is None else "expired"
        timeout_new = status == "expired" and self.latest["id"] not in self.expired_ids
        if timeout_new:
            self.expired_ids.add(self.latest["id"])
        self.v, self.w = map(float, self.controller(self.latest["selected_waypoint_m"])) if self.command_valid else (0., 0.)
        switch = None
        if self.command_valid and self.latest["id"] != self.applied_id:
            self.applied_id = self.latest["id"]
            switch = {**self.latest, "application_sim_s": tick/self.hz,
                      "application_monotonic_ns": now_ns, "agent_pose_at_switch": self.pose.tolist(),
                      "v_m_s": self.v, "w_rad_s": self.w}
        return {"simulation_time_s": tick/self.hz, "monotonic_ns": now_ns,
                "waypoint_id": self.applied_id, "latest_received_id": self.latest["id"] if self.latest else -1,
                "waypoint_age_wall_s": age, "valid": self.command_valid, "status": status,
                "new_timeout": timeout_new, "v_m_s": self.v, "w_rad_s": self.w}, switch


class AsyncClient:
    """Blocking framing stays in this thread; control/render never wait for inference.

    Busy lasts until the result is consumed, so pending requests + unread results
    are bounded by one. Stop drains a final result without applying it.
    """
    def __init__(self, connection, snapshot, delivery_delay=None):
        self.connection, self.snapshot = connection, snapshot
        self.delivery_delay = delivery_delay
        self.jobs, self.results = queue.Queue(maxsize=1), queue.Queue(maxsize=1)
        self.lock = threading.Lock()
        self.busy = False
        self.error = None
        self.last_submitted_id = -1
        self.thread = threading.Thread(target=self._run, name="nomad-ipc", daemon=True)
        self.thread.start()

    def submit(self, metadata, **arrays):
        with self.lock:
            if self.busy:
                return False
            if metadata["id"] != self.last_submitted_id+1:
                raise ValueError("Request IDs must be consecutive")
            if self.delivery_delay is not None:
                self.delivery_delay.annotate_accepted_request(metadata)
            self.last_submitted_id = metadata["id"]
            self.busy = True
            self.jobs.put_nowait((dict(metadata), arrays))
            return True

    def _run(self):
        try:
            while True:
                item = self.jobs.get()
                if item is None:
                    send_packet(self.connection, {"kind": "stop"})
                    assert receive_packet(self.connection)[0]["kind"] == "stopped"
                    return
                metadata, arrays = item
                metadata["request_send_monotonic_ns"] = time.monotonic_ns()
                send_packet(self.connection, metadata, **arrays)
                send_end = time.monotonic_ns()
                response, outputs = receive_packet(self.connection)
                received = time.monotonic_ns()
                if response["id"] != metadata["id"]:
                    raise ValueError("Worker response ID does not match outstanding request")
                snap = self.snapshot()
                record = {**metadata, **response, "request_send_end_monotonic_ns": send_end,
                          "received_monotonic_ns": received, "received_sim_s": snap["sim_s"],
                          "agent_pose_at_receive": snap["pose"], "received_pose_sample_monotonic_ns": snap["monotonic_ns"]}
                if self.delivery_delay is not None:
                    deadline = self.delivery_delay.hold_until_deadline(metadata, received)
                    released_snap = self.snapshot()
                    record.update({"packet_received_monotonic_ns": received,
                                   "packet_received_sim_s": snap["sim_s"],
                                   "agent_pose_at_packet_receive": snap["pose"],
                                   "packet_pose_sample_monotonic_ns": snap["monotonic_ns"],
                                   "release_deadline_monotonic_ns": deadline,
                                   "received_sim_s": released_snap["sim_s"],
                                   "agent_pose_at_receive": released_snap["pose"],
                                   "received_pose_sample_monotonic_ns": released_snap["monotonic_ns"]})
                    # Controller-side receive is release; OLD's receive clock is untouched.
                    release = time.monotonic_ns()
                    record.update({"release_monotonic_ns": release, "received_monotonic_ns": release})
                self.results.put_nowait((record, outputs))
        except BaseException as exc:
            self.error = exc

    def poll(self):
        if self.error is not None:
            raise RuntimeError("Async IPC failed") from self.error
        try:
            result = self.results.get_nowait()
        except queue.Empty:
            return None
        with self.lock:
            self.busy = False
        return result

    def close(self):
        leftover = None
        deadline = time.monotonic()+30
        while self.busy:
            leftover = self.poll()
            if leftover is not None:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("Final outstanding inference did not finish")
            self.thread.join(.01)  # Shutdown only; no navigation or injected delay.
        self.jobs.put_nowait(None)
        self.thread.join(15)
        if self.thread.is_alive() or self.error is not None:
            raise RuntimeError("Worker shutdown failed") from self.error
        return leftover
