"""One observation-triggered post-inference hold, used only by the IPC thread."""
import time


class SingleDeliveryDelay:
    def __init__(self, protocol, clock_ns=None, wait=None):
        assert protocol["maximum_injections"] == 1
        self.protocol = protocol
        self.clock_ns = clock_ns or time.monotonic_ns
        self.wait = wait or time.sleep
        self.triggered_id = None

    def annotate_accepted_request(self, metadata):
        """Called under the client's submit lock, only after its busy check."""
        lo, hi = self.protocol["observation_world_x_inclusive_m"]
        trigger = (self.triggered_id is None and lo <= metadata["observation_pose"][0] <= hi
                   and metadata["old_valid_at_observation"] and metadata["old_id_at_observation"] >= 0)
        if trigger:
            self.triggered_id = metadata["id"]
        metadata["delivery_delay_triggered"] = bool(trigger)
        metadata["additional_delivery_delay_s"] = self.protocol["additional_delivery_delay_s"] if trigger else 0.

    def hold_until_deadline(self, metadata, packet_received_ns):
        deadline = packet_received_ns + round(metadata["additional_delivery_delay_s"] * 1e9)
        while True:
            remaining_ns = deadline - self.clock_ns()
            if remaining_ns <= 0:
                return deadline
            self.wait(remaining_ns / 1e9)
