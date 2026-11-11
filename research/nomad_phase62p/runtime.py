"""Phase55 U dispatch/install mechanics rebased onto Phase61 CUT, never HOLD."""
import inspect,json,textwrap
from pathlib import Path
import numpy as np
from nomad_phase28.telemetry import builtin
from nomad_phase55p.runtime import Execution as UBase
from nomad_phase58p.runtime import ConsExecution as CUTBase
from nomad_phase61p.runtime import install as frozen_install,run_without_oracle

# Keep the established U planning/certification/installation logic. Its only
# execution-base substitutions are the requested Phase61 CUT/latch/expiry stack.
def clone(fn,replacements):
    source=textwrap.dedent(inspect.getsource(fn))
    for old,new in replacements:
        assert source.count(old)==1,(fn.__name__,old);source=source.replace(old,new)
    ns=dict(fn.__globals__,CUTBase=CUTBase);exec(compile(source,__file__,'exec'),ns);return ns[fn.__name__]

# inspect.dedent leaves four spaces in the function body.
_prepare=clone(UBase.prepare_solution,[("    (self.u_dir/f'job_{self.u_count:05d}.json').write_text", "    job.update(self.goal_context(core,source_id))\n    (self.u_dir/f'job_{self.u_count:05d}.json').write_text")])
_apply=clone(UBase.apply,[('super().apply(core,refresh,switch)','CUTBase.apply(self,core,refresh,switch)')])

class Execution(CUTBase):
    def __init__(self,out,node_poses,worker=None):
        super().__init__('CUT',out)
        from .worker import Client
        self.u_worker=worker if worker is not None else Client(out)
        self.u_file=(out/'ugraph.jsonl').open('x');self.u_dir=out/'ugraph_jobs';self.u_dir.mkdir()
        self.u_count=0;self.u_prior=None;self.u_next=None;self.u_due=None;self.u_cycle=None
        self.node_xy=np.asarray(node_poses,float)[:,:2];assert len(self.node_xy) and np.isfinite(self.node_xy).all()
        self.target=None
    def update_goal(self,switch):
        m=switch['topomap'];node=int(m['closest_node']);goal=int(m['goal_node'])
        assert m['oracle']['analysis_only'] and m['oracle']['HMM_used'] is False
        assert goal==len(self.node_xy)-1 and 0<=node<=goal
        target=min(node+2,goal)
        self.target=dict(oracle_node=node,target_node=target,goal_xy=self.node_xy[target].tolist(),
            source_chunk_id=switch['id'],oracle_observation_s=switch['observation_sim_s'],oracle_observation_pose=switch['observation_pose'])
    def goal_context(self,core,source_id):
        assert self.target is not None and self.target['source_chunk_id']==source_id
        return dict(self.target,goal_distance_at_solve_m=float(np.linalg.norm(np.asarray(core.pose)[:2]-self.target['goal_xy'])))
    def apply(self,core,refresh,switch):
        if switch is not None:self.update_goal(switch)
        return _apply(self,core,refresh,switch)
    def ulog(self,event,**kw):
        if self.u_cycle is not None:
            job=self.u_cycle['job']
            kw.update({k:job[k] for k in ('oracle_node','target_node','goal_xy','source_chunk_id','oracle_observation_s','goal_distance_at_solve_m')})
        return UBase.ulog(self,event,**kw)
    prepare_solution=_prepare
    adopt=clone(UBase.adopt,[(";self.set_hold(False,t,'UGRAPH_STATIONARY_XY')",'')])
    record=clone(UBase.record,[('super().record(event,**kw)','CUTBase.record(self,event,**kw)')])
    ec_install=clone(UBase.ec_install,[('super().ec_install(path,core,refresh,source_id,kind,**kw)','CUTBase.ec_install(self,path,core,refresh,source_id,kind,**kw)')])
    use_fallback=clone(UBase.use_fallback,[('super().use_fallback(core,refresh)','CUTBase.use_fallback(self,core,refresh)')])
    integrate_record=clone(UBase.integrate_record,[('super().integrate_record(before,after)','CUTBase.integrate_record(self,before,after)')])
    close=clone(UBase.close,[('super().close()','CUTBase.close(self)')])

def install(c):
    frozen_install(c)
    from nomad_phase24.retention import retained_apply
    import nomad_phase15b.execution as factory
    import nomad_phase8.execution as overnight
    def make(config,out):
        nodes=json.loads(Path(config['topomap_manifest']).read_text())['nodes']
        assert [n['node_id'] for n in nodes]==list(range(len(nodes)))
        return retained_apply(Execution(out,[n['world_pose'] for n in nodes]))
    factory.make_execution=make;overnight.OvernightExecution=make
