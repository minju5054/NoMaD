"""Only allow departure rotation for a strictly backward (>90deg) suffix."""
from nomad_phase20.execution import SPAlignment

class NoAlignment(SPAlignment):
    def replace_path(self,xy,B,actual_v):
        count=self.alignment_count
        super().replace_path(xy,B,actual_v)
        self.alignment_threshold_deg=90.
        self.trigger_S=self.initial_heading_error_deg is not None and self.initial_heading_error_deg>90.
        self.alignment_count=count+int(self.trigger_S)
        if not self.trigger_S:
            self.mode='GO';self.target_yaw=None
