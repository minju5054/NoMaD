"""Reuse frozen21 execution; P2F changes only its CPU solver backend."""
import numpy as np
from nomad_phase21.execution import make_execution as previous_factory
from nomad_phase20f.runtime import Execution as Frozen,run_without_oracle

def online_anchor(job,history):
    if job.get('kind')=='R3' and job.get('trigger')=='B':
        from nomad_phase20f.direction import component_direction
        birth=int(job['component']['t_new_tick']);assert 0<=birth<len(history)
        u,detail=component_direction(history,birth)
        np.testing.assert_allclose(u,job['u_ref'],atol=1e-12,rtol=0)
        return dict(anchor_xy=np.asarray(history[birth])[:2].tolist(),anchor_tick=birth,anchor_source='DEPTH_COMPONENT_T_NEW_ODOMETRY',anchor_direction=detail)
    return dict(anchor_xy=list(job['B'][:2]),anchor_tick=round(job['simulation_time_s']*72),anchor_source='TRIGGER_B_POSE_COMPONENT_ABSENT')

def make_execution(c,out):
    if c['phase22_method']!='P2F_ASTAR_GRAPH':return previous_factory(c,out)
    import nomad_phase20d.runtime as previous
    from .drive_backend import Worker
    owner={};saved=previous.Worker;previous.Worker=lambda out:Worker(out,lambda job:online_anchor(job,owner['execution'].history))
    try:
        execution=Frozen('M3_DETOUR',out);owner['execution']=execution;return execution
    finally:previous.Worker=saved

def install():
    from nomad_phase21.execution import install as previous_install
    previous_install()
    import nomad_phase15b.execution as factory
    import nomad_phase2.config as placement
    import nomad_isaac.sudden_obstacle as sudden
    from .drive_geometry import monitor
    from .drive_config import place,triggered
    factory.make_execution=make_execution;placement.place=place;placement.triggered=triggered;sudden.ObstacleMonitor=monitor
