"""Frozen one-decode NoMaD policy; oracle window/closest replace HMM selection."""
import inspect
from nomad_phase43p import worker as frozen
from nomad_phase40p.launch import bind
from .localization import Localization

source=inspect.getsource(frozen.make_policy)
old="selection=self.localization.select(values,request['hmm_odometry_total_m'])"
assert source.count(old)==1;source=source.replace(old,'selection=self.localization.select(values)')
old="metadata['hmm']['odometry_tick']=request['hmm_odometry_tick']"
assert source.count(old)==1;source=source.replace(old,"metadata['oracle']['observation_tick']=round(request['observation_sim_s']*72)")

def make_policy(native,request_metadata):
    def factory(node_poses):return Localization(node_poses,position_provider=lambda:request_metadata()['observation_pose'])
    ns=dict(frozen.make_policy.__globals__,Localization=factory)
    exec(compile(source,__file__,'exec'),ns)
    return ns['make_policy'](native,request_metadata)
def main():return bind(frozen.main,make_policy=make_policy)()
if __name__=='__main__':main()
