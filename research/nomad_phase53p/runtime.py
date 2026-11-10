"""Only the EC predicate and final normal handoff XY can differ from Phase47."""
import ast,inspect,json,time
import numpy as np
from nomad_phase38.ec_normal import RTCWithEC
from nomad_phase32.runtime import Execution as FrozenEC,path_key
from nomad_phase28.telemetry import builtin
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase47c.runtime import install as frozen_install,run_without_oracle as frozen_run
from .ec_tail import certify_tail

def heading(path,pose):
    if path is None:return None
    p=XYPath(path);s,_=p.project(np.asarray(pose)[:2]);delta=p.at(min(p.s[-1],s+.05))-p.at(s)
    return float(np.arctan2(delta[1],delta[0])) if np.linalg.norm(delta)>1e-9 else None

# Preserve the exact EC candidate ordering and full-speed/0.1/STOP fallback.
# The only replaced statement is its final installation call, after a CUT
# candidate passed EC-tail. Rejected Graph output uses that very same candidate.
_source=inspect.getsource(FrozenEC.ec_install)
import textwrap
_source=textwrap.dedent(_source)
_old='RAW_INSTALL(self,path,core,refresh,source_id,kind)'
assert _source.count(_old)==1
_source=_source.replace(_old,'self.install_certified(path,core,refresh,source_id,kind,cap)')
_ns=dict(FrozenEC.ec_install.__globals__);exec(compile(_source,__file__,'exec'),_ns)

class Execution(RTCWithEC):
    ec_install=_ns['ec_install']
    def __init__(self,method,out):
        self.ho_method=method;self.ho_prior=None;self.ho_n=0;self.ho_worker=None
        self.ho_log=(out/'graph_ho.jsonl').open('x');self.ho_dir=out/'graph_ho_jobs';self.ho_dir.mkdir()
        super().__init__(out)
        if method=='GRAPH-HO':
            from .worker import Client
            self.ho_worker=Client(out)
    def record(self,event,**kw):
        self.ho_log.write(json.dumps(builtin(dict(event=event,**kw)),allow_nan=False)+'\n');self.ho_log.flush()
    def ec_check(self,pose,vw,path,field,t,state,scope,cap,controller=None):
        tick=round(t*72);start=time.monotonic_ns()
        if hasattr(self.depth_maps,'archive_queue') and not getattr(self.depth_maps,'full_frames',True):self.depth_maps.archive_queue.put_nowait((field,None,None))
        r=certify_tail(pose,vw,path,field,cap,controller,tick);end=time.monotonic_ns();ident=self.ec_check_sequence;self.ec_check_sequence+=1
        self.ec_log('CHECK',check_id=ident,generation=self.ec_generation,state=state,scope=scope,check_tick=tick,
            check_started_ns=start,check_finished_ns=end,simulation_time_s=t,pose=np.asarray(pose).tolist(),actual_vw=vw,
            speed_cap_m_s=cap,snapshot=dict(field.metadata),path_sha256=path_key(path),**r)
        return dict(r,check_id=ident,check_tick=tick,check_started_ns=start,check_finished_ns=end)
    def install_certified(self,path,core,refresh,source_id,kind,cap):
        t=refresh['simulation_time_s'];tick=round(t*72);original=np.asarray(path).copy();installed=original;selected='CUT';result=None
        # Each native chunk installation (including EC alternative candidates)
        # has eight original waypoints. Never recursively refine an old Graph.
        bank=self.ec_samples.get(source_id,{}).get('worlds')
        native=original if kind=='SAFE' else (np.asarray(bank[self.active_sample]) if bank is not None else None)
        if self.ho_method=='GRAPH-HO' and native is not None:
            self.ho_n+=1;field=self.depth_maps.snapshot();file=self.ho_dir/f'input_{self.ho_n:05d}.npz';field.save(file)
            job=dict(id=source_id,sequence=self.ho_n,world_xy=native.tolist(),boundary=np.asarray(core.pose).tolist(),
                previous_command=self.actual_vw(),previous_xy=self.ho_prior,snapshot_file=str(file))
            (self.ho_dir/f'job_{self.ho_n:05d}.json').write_text(json.dumps(builtin(job),allow_nan=False)+'\n')
            result=self.ho_worker.solve(job)
            if result['accepted']:
                corrected=np.asarray(result['poses'])[:,:2]
                check=self.ec_check(core.pose,self.actual_vw(),corrected,self.depth_maps.snapshot(),t,'NORMAL','GRAPH_INSTALL',cap)
                result['tail_check_id']=check['check_id'];result['tail_pass']=check['passed']
                if check['passed']:installed=corrected;selected='GRAPH_HO';self.ho_prior=corrected.tolist()
                else:result['reason']='EC_TAIL_REJECT'
            self.record('SOLVE',id=source_id,sequence=self.ho_n,tick=tick,simulation_time_s=t,job=job,**result,applied=selected=='GRAPH_HO')
        old=self.follower.path.points if self.follower is not None else None
        before=heading(old,core.pose);after=heading(installed,core.pose)
        discontinuity=abs((after-before+np.pi)%(2*np.pi)-np.pi)*180/np.pi if before is not None and after is not None else None
        super().commit_path(installed,core,refresh,source_id,kind)
        self.record('INSTALL',id=source_id,tick=tick,simulation_time_s=t,path_type=selected,path_world=installed,
            original_candidate_world=original,pose=core.pose,heading_discontinuity_deg=discontinuity,
            heading_to_robot_deg=abs((after-core.pose[2]+np.pi)%(2*np.pi)-np.pi)*180/np.pi if after is not None else None)
    def close(self):
        try:
            if self.ho_worker is not None:self.ho_worker.close()
            super().close()
        finally:self.ho_log.close()

def install(config):
    frozen_install(config)
    from nomad_phase24.retention import retained_apply
    import nomad_phase15b.execution as factory
    import nomad_phase8.execution as overnight
    def make(c,out):return retained_apply(Execution(c['phase53p_method'],out))
    factory.make_execution=make;overnight.OvernightExecution=make

def run_without_oracle(*args,**kwargs):
    delay=kwargs.get('uniform_delivery_delay_s');assert delay==args[0]['phase53p_delay_s']
    if delay==.75:return frozen_run(*args,**kwargs)
    from nomad_phase51p.runtime import driver_tree
    from nomad_isaac import async_runtime as original
    from nomad_phase24.retention import full_frames
    tree=driver_tree(inspect.getsource(original.run_async),full_frames());ns=dict(original.__dict__,_phase24_full_frames=full_frames())
    exec(compile(tree,original.__file__,'exec'),ns);return ns['run_async'](*args,**kwargs)
