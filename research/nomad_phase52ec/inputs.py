"""Read-only exact paths, candidate banks and continued follower states from logs."""
import copy,csv,hashlib,json,ctypes,math
from pathlib import Path
from collections import OrderedDict
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,local_to_world
from nomad_phase15b.depth import Snapshot
from nomad_phase33p.storage import load_snapshot
from nomad_phase32.policy import CappedNA

HASHES={}
def register(p):
    p=Path(p)
    if str(p) not in HASHES:HASHES[str(p)]=sha256_file(p)
    return p

def read(p):return json.loads(register(p).read_text())
def lines(p):return [json.loads(s) for s in register(p).read_text().splitlines() if s] if Path(p).exists() else []
def key(path):return hashlib.sha256(np.asarray(path,dtype=np.float64).tobytes()).hexdigest()

def recover_fp_paths(bank,targets):
    """Replay NumPy/BLAS coordinate arithmetic; accept only exact logged SHA.

    Isaac's NumPy/BLAS can fuse the two multiply-add terms unlike /usr/bin's
    NumPy. This search never uses an EC outcome/clearance, only its content hash.
    """
    fma=ctypes.CDLL('libm.so.6').fma;fma.argtypes=[ctypes.c_double]*3;fma.restype=ctypes.c_double
    pose=bank['pose'];angle=pose[2]
    near=lambda x:[np.nextafter(x,-np.inf),x,np.nextafter(x,np.inf)]
    cs=set(near(math.cos(angle))+near(float(np.cos(angle))));ss=set(near(math.sin(angle))+near(float(np.sin(angle))))
    found={}
    for sample,p in enumerate(bank['local']):
        for c in cs:
            for s in ss:
                for mode in range(3):
                    world=[]
                    for x,y in p:
                        a=x*c-y*s if mode==0 else fma(y,-s,x*c) if mode==1 else fma(x,c,-y*s)
                        b=x*s+y*c if mode==0 else fma(y,c,x*s) if mode==1 else fma(x,s,y*c)
                        world.append([a+pose[0],b+pose[1]])
                    h=key(world)
                    if h in targets:found[h]=np.asarray(world)
        if set(found)==targets:break
    return found

def datasets():
    result=[]
    for phase,n in (('phase47c',60),('phase52p',40)):
        rows=read(ROOT/f'research/results/{phase}/runs.json');assert len(rows)==n
        for r in rows:
            assert r['technical_validation']=='PASS';result.append((phase,r))
    return result

class Run:
    def __init__(self,phase,row):
        self.root=Path(row['output']);self.phase=phase;self.row=row;self.uid=f"{phase}/{row['scene']}/{row['index']}/{row['method']}"
        self.c=read(self.root/'scenario.json');self.checks=[e for e in lines(self.root/'exec_cert.jsonl') if e['event']=='CHECK']
        self.paths={};self.banks=[];self.controllers={};self.cache=OrderedDict()
        self.commands=lines(self.root/'phase20_commands.jsonl')
        self.apps=[e for e in lines(self.root/'repair.jsonl') if e['event']=='PATH_APPLIED']
        self.ec_installs=[e for e in lines(self.root/'exec_cert.jsonl') if e['event']=='INSTALL']
        for app in self.apps:self.paths[key(app['path_world'])]=np.asarray(app['path_world'])
        for e in lines(self.root/'received.jsonl'):
            if not e.get('overnight_metric_samples') or e.get('terminal_unapplied'):continue
            world=np.array([local_to_world(p,e['observation_pose']) for p in e['overnight_metric_samples']])
            self.banks.append(dict(id=e['id'],ns=e['latched_monotonic_ns'],time_s=e['latched_sim_s'],worlds=world,
                local=np.asarray(e['overnight_metric_samples']),pose=e['observation_pose']))
            for p in world:self.paths[key(p)]=p
        self.banks.sort(key=lambda x:x['ns'])
        for e in lines(self.root/'reconstruction.jsonl'):
            if e.get('event')=='DISPATCH' and e.get('samples_world'):
                world=np.asarray(e['samples_world'])
                for p in world:self.paths[key(p)]=p
                for bank in self.banks:
                    if bank['id']==e['id']:bank['worlds']=world
            if e.get('event')=='RESULT' and e.get('numeric_result'):
                for candidate in e['numeric_result'].get('results',[]):
                    if candidate.get('path') is not None:self.paths[key(candidate['path'])]=np.asarray(candidate['path'])
        self.fp_restored_paths=0
        for bank in self.banks:
            missing={e['path_sha256'] for e in self.checks if e['path_sha256'] not in self.paths and self.bank(e) is bank}
            if missing:
                recovered=recover_fp_paths(bank,missing);self.paths.update(recovered);self.fp_restored_paths+=len(recovered)
        if self.checks:
            assert len(self.apps)==len(self.ec_installs),(self.uid,len(self.apps),len(self.ec_installs))
            for app,install in zip(self.apps,self.ec_installs):
                assert app['id']==install['id'] and app['tick']==install['apply_tick'] and app['kind']==install['kind']
                ctl=CappedNA();ctl.replace_path(app['path_world'],app['pose'],app['previous_vw'][0]);ctl.speed_cap=install['speed_cap_m_s']
                following=[c for c in self.commands if c['time_s']>=app['simulation_time_s']-1e-10]
                self.controllers[install['generation']]=dict(controller=ctl,commands=following,cursor=0,app=app)
    def metadata(self,check):
        return dict(uid=self.uid,phase=self.phase,scene=self.c['phase16_scene'],method=self.row['method'],seed=self.row['index'],
            condition=self.row.get('condition','D075'),check_id=check['check_id'],tick=check['check_tick'],time_s=check['simulation_time_s'],
            scope=check['scope'],path_hash=check['path_sha256'],actual_v_m_s=check['actual_vw'][0],actual_w_rad_s=check['actual_vw'][1],
            map_frame=check['snapshot']['frame_id'],map_file=check['snapshot']['file'],speed_cap_m_s=check['speed_cap_m_s'],logged_passed=check['passed'])
    def bank(self,check):
        available=[b for b in self.banks if b['ns']<=check['check_started_ns']]
        return available[-1] if available else None
    def field(self,check):
        p=check['snapshot']['file']
        if not Path(p).exists():return None
        if p not in self.cache:
            obj=load_snapshot(Snapshot,register(p));assert obj.metadata['frame_id']==check['snapshot']['frame_id']
            assert abs(obj.metadata['sim_s']-check['snapshot']['sim_s'])<1e-9;self.cache[p]=obj
            while len(self.cache)>2:self.cache.popitem(last=False)
        else:self.cache.move_to_end(p)
        return self.cache[p]
    def controller(self,check):
        if not check.get('continuation'):return None
        entry=self.controllers.get(check['generation'])
        if entry is None:raise ValueError('Unresolved generation for continuation')
        app=entry['app'];assert key(app['path_world'])==check['path_sha256']
        commands=entry['commands'];cursor=entry['cursor'];ctl=entry['controller']
        # CHECK occurs before this control tick's follower call. At an install
        # tick the generation was created before its first control call.
        while cursor<len(commands) and commands[cursor]['time_s']<check['simulation_time_s']-1e-10:
            c=commands[cursor]
            if c.get('path_source_id')==app['id'] and c['source'] in ('NORMAL','KEEP_ACTIVE','ALIGN_BRAKE','ALIGN_ROTATE','REPAIR','ENDPOINT'):
                ctl.control(c['pose'],c['before_vw'][0])
            cursor+=1
        entry['cursor']=cursor
        return ctl
