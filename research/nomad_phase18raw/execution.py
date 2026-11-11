"""Native sample0 with the exact Phase18 PP+CURV executor, no SAFE/Graph/EC."""
import json
from nomad_phase4c.execution import AccelExecution
from nomad_phase18.execution import install_runtime_adapters as frozen_install
from .config import METHOD

class RawExecution(AccelExecution):
    def __init__(self,out):
        super().__init__(dict(phase4c_method='CURV',plant_alpha='inf'),out)
        self.last_application_ns=None;self.depth_maps=None
        self.apps=(out/'phase16_applications.jsonl').open('x')
    def apply(self,core,refresh,switch):
        # ChunkExecution receives the untouched sample0 chunk from async_core.
        # This inherits the exact protected target geometry and CURV limits.
        super().apply(core,refresh,switch)
        if switch is not None:
            self.last_application_ns=refresh['monotonic_ns']
            switch['phase18raw']=dict(sample=0,depth_filter=False,graph=False,EC=False,recovery=False)
            field=self.depth_maps.snapshot()
            row=dict(tick=round(refresh['simulation_time_s']*72),simulation_time_s=refresh['simulation_time_s'],id=switch['id'],path_source_id=switch['id'],
                kind='NOMAD_RAW',pose=core.pose.tolist(),selected_sample=0,world_xy=self.follower.path.points.tolist() if self.follower else None,
                depth_snapshot=dict(field.metadata),before_vw=switch['chunk_transition']['command_before'],after_vw=list(self.last_command),fallback_mode='RAW')
            self.apps.write(json.dumps(row,allow_nan=False)+'\n');self.apps.flush()
    def close(self):
        try:super().close()
        finally:self.apps.close()

def make_execution(c,out):
    assert c['phase18raw'] and c['phase15b_method']==METHOD
    return RawExecution(out)
def install_runtime_adapters():
    frozen_install()
    import nomad_phase15b.execution as factory
    factory.make_execution=make_execution
