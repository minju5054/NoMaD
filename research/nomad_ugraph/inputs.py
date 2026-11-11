"""Fixed development-only arrival inventory; no SDF/solver/model execution."""
import csv,hashlib,json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file

HERE=Path(__file__).parent;OUT=ROOT/'research/results/ugraph';RUN_ROOT=ROOT.parent/'artifacts/isaac6/ugraph_offline_01'
COHORTS=('phase47c','phase52p','phase53p','h1v2_trial')
SCENES=('SLW','LC','L2','H1','H2','H1-v2')

def uniform_indices(n,limit=40):
    return np.rint(np.linspace(0,n-1,min(n,limit))).astype(int).tolist() if n else []

class Inventory:
    def __init__(self):self.hashes={}
    def read(self,p):
        p=Path(p);b=p.read_bytes();self.hashes[str(p)]=hashlib.sha256(b).hexdigest();return b.decode()
    def json(self,p):return json.loads(self.read(p))
    def lines(self,p):return [json.loads(l) for l in self.read(p).splitlines() if l.strip()] if Path(p).exists() else []
    def build(self):
        cases=[];runs=[];seen=set()
        for cohort in COHORTS:
            records=self.json(ROOT/f'research/results/{cohort}/runs.json')
            for r in sorted(records,key=lambda r:(r['scene'],r['index'],r['method'])):
                assert r['index'] not in (225,226),'NIGHT seed is forbidden'
                root=Path(r['output']);uid=cohort+'/'+r['key']
                if str(root) in seen:raise ValueError('Duplicate source run')
                seen.add(str(root))
                if r['technical_validation']!='PASS':runs.append(dict(uid=uid,reason='TECHNICAL_FAILURE',selected=0));continue
                config=self.json(root/'scenario.json');summary=self.json(root/'summary.json')
                received=self.lines(root/'received.jsonl');events={e['id']:e for e in self.lines(root/'events.jsonl')}
                arrivals=sorted([e for e in received if not e.get('terminal_unapplied') and e.get('latched_sim_s') is not None and e['latched_sim_s']<=r['duration_s']+1e-9],key=lambda e:(e['latched_sim_s'],e['id']))
                assert len({e['id'] for e in arrivals})==len(arrivals)
                selected=uniform_indices(len(arrivals));trajectory=list(csv.DictReader(self.read(root/'agent_trajectory.csv').splitlines()))
                trace={int(e.get('tick',round(float(e['simulation_time_s'])*72))):e for e in trajectory}
                updates=self.lines(root/'depth/updates.jsonl');updates.sort(key=lambda e:e['publication_monotonic_ns'])
                publish=np.array([e['publication_monotonic_ns'] for e in updates],dtype=np.int64)
                commands=self.lines(root/'phase20_commands.jsonl');commands.sort(key=lambda e:e['time_s']);ct=np.array([e['time_s'] for e in commands])
                apps=[e for e in self.lines(root/'repair.jsonl') if e['event']=='PATH_APPLIED'];apps.sort(key=lambda e:e['simulation_time_s'])
                at=np.array([e['simulation_time_s'] for e in apps]);dyn=summary.get('dynamic_obstacle') or {}
                boxes=dyn.get('boxes',[dyn] if dyn.get('spawn') else []);spawn=min((b['spawn']['simulation_time_s'] for b in boxes),default=None)
                begin=len(cases)
                for ordinal in selected:
                    e=arrivals[ordinal];t=float(e['latched_sim_s']);tick=round(t*72);state=trace[tick]
                    assert abs(float(state['simulation_time_s'])-t)<1e-9
                    ui=int(np.searchsorted(publish,e['latched_monotonic_ns'],side='right'))-1;update=updates[ui] if ui>=0 else None
                    file=Path(update['file']) if update else None
                    reason='READY' if file is not None and file.is_file() else 'LATEST_SNAPSHOT_NOT_RETAINED' if update else 'NO_PUBLISHED_DEPTH_MAP'
                    if file is not None and file.is_file():self.hashes.setdefault(str(file),sha256_file(file))
                    ci=int(np.searchsorted(ct,t+1e-10,side='right'))-1;command=commands[ci] if ci>=0 else None
                    ai=int(np.searchsorted(at,t+1e-10,side='right'))-1;app=apps[ai] if ai>=0 else None
                    tracking=bool(app and command and command.get('path_source_id')==app['id'] and command['source'] in ('NORMAL','KEEP_ACTIVE','ALIGN_BRAKE','ALIGN_ROTATE','REPAIR','DETOUR'))
                    dynamic_scene=config.get('scene_variant',r.get('base_scene',config['phase16_scene']))
                    cases.append(dict(case_id=f'U{len(cases):05d}',uid=uid,cohort=cohort,run=str(root),method=r['method'],scene=dynamic_scene,seed=r['index'],
                        condition=r.get('condition','D075'),arrival_ordinal=ordinal,chunk_id=e['id'],tick=tick,time_s=t,arrival_monotonic_ns=e['latched_monotonic_ns'],
                        pose=[float(state[k]) for k in ('x_m','y_m','yaw_rad')],v=float(state['v_m_s']),omega=float(state['w_rad_s']),
                        observation_pose=e['observation_pose'],snapshot_file=str(file) if file else None,snapshot_sha256=self.hashes.get(str(file)) if file else None,
                        snapshot_metadata=update,status=reason,actual_command_state=command['source'] if command else 'INITIAL_INFERENCE_WAIT',
                        actual_path=app['path_world'] if tracking else None,actual_path_kind=app['kind'] if tracking else None,actual_path_source_id=app['id'] if tracking else None,
                        after_box_spawn=bool(spawn is not None and t>=spawn),first_box_spawn_s=spawn,
                        samples_source='received.jsonl:overnight_metric_samples' if e.get('overnight_metric_samples') is not None else 'model/derived',
                        run_duration_s=r['duration_s'],source_result=r['classification']))
                segment=cases[begin:];runs.append(dict(uid=uid,scene=config.get('scene_variant',config['phase16_scene']),arrivals=len(arrivals),selected=len(segment),
                    usable=sum(c['status']=='READY' for c in segment),missing_latest=sum(c['status']=='LATEST_SNAPSHOT_NOT_RETAINED' for c in segment),
                    no_depth=sum(c['status']=='NO_PUBLISHED_DEPTH_MAP' for c in segment)))
        # Example cases are fixed by inventory order before any solve result.
        examples={s:next((c['case_id'] for c in cases if c['scene']==s and c['status']=='READY' and (s in ('SLW','LC') or c['after_box_spawn'])),None) for s in SCENES}
        return dict(cases=cases,runs=runs,examples=examples,input_sha256=self.hashes,
            selection='Each valid run:all controller-latched chunks up to40;rounded uniformly spaced ordinal indices including first/last;select before map availability check;never replace missing cases',
            map_policy='Latest publication_monotonic_ns<=latched_monotonic_ns;exact snapshot must exist;no older substitution,no rerender',
            phase_scope=list(COHORTS),night_used=False,maximum_per_run=40)

def materialize(case):
    """World-fix all8 candidates at their logged observation pose, unfiltered."""
    from nomad_isaac.common import local_to_world
    root=Path(case['run']);target=None
    with (root/'received.jsonl').open() as f:
        for line in f:
            e=json.loads(line)
            if e['id']==case['chunk_id']:target=e;break
    assert target is not None
    local=target.get('overnight_metric_samples')
    if local is None:
        with np.load(root/'model/derived'/f"{case['chunk_id']:04d}.npz",allow_pickle=False) as z:local=z['metric'].copy()
    world=np.asarray([local_to_world(np.asarray(p),case['observation_pose']) for p in local],float)
    assert world.shape==(8,8,2) and np.isfinite(world).all();return world

def main():
    RUN_ROOT.mkdir(exist_ok=True,parents=True);manifest=Inventory().build();file=RUN_ROOT/'inventory.json'
    if file.exists():assert json.loads(file.read_text())==manifest,'Inventory changed;do not silently reselect'
    else:file.write_text(json.dumps(manifest,indent=2)+'\n')
    from collections import Counter
    print(json.dumps(dict(runs=len(manifest['runs']),selected=len(manifest['cases']),availability=dict(Counter(c['status'] for c in manifest['cases'])),examples=manifest['examples'])))
if __name__=='__main__':main()
