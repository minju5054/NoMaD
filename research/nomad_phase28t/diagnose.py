"""Legacy368-case log diagnosis and one matched saved-input offline replay."""
import json,csv,time
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase20d.recent import RecentSnapshot
from nomad_phase28.alignment import NoAlignment
from nomad_phase28.tracking import predict
from nomad_phase28.graph_r1 import solve as frozen_solve

OUT=ROOT/'research/results/phase28t/preparation'
def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s]
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def csv_write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def freeze():
    assert not (OUT/'legacy_manifest.json').exists()
    root=ROOT.parent/'artifacts/isaac6/phase28_pilot_01';runs=[read(p) for p in sorted((root/'metrics').glob('*.json'))];cases=[];hashes={}
    for run in runs:
        if run['method']!='C0-H':continue
        folder=Path(run['output']);file=folder/'phase28_handoff.jsonl';events=lines(file)
        assert not any(e['event']=='APPLIED' for e in events),'Warm history must be reconstructed if H was applied'
        summaries={e['job_id']:e for e in events if e['event']=='CASE_SUMMARY'}
        outcomes={e['job_id']:e for e in events if e['event']=='CASE_OUTCOME'}
        full={e['job_id']:e.get('result') for e in events if e['event']=='FALLBACK' and e.get('job_id') is not None}
        for e in events:
            if e['event']!='DISPATCH':continue
            r=full.get(e['job_id']);r=r.get('result',r) if isinstance(r,dict) else None
            c=dict(key=f"{run['scene']}_{run['index']}_{e['job_id']:04d}",scene=run['scene'],index=run['index'],output=str(folder),dispatch=e,
                summary=summaries[e['job_id']],outcome=outcomes[e['job_id']],numerical_result=r,snapshot_available=Path(e['snapshot']['file']).exists(),warm=None)
            if c['snapshot_available']:c['snapshot_sha256']=sha256_file(Path(e['snapshot']['file']))
            cases.append(c)
        for name in ('phase28_handoff.jsonl','phase20_commands.jsonl','repair.jsonl','agent_trajectory.csv','scenario.json'):
            f=folder/name;hashes[str(f)]=sha256_file(f)
    assert len(cases)==368
    m=dict(cases=cases,counts=368,input_sha256=hashes,warm_state='None for all cases:0H APPLIED in all10runs',replay='Frozen0.15s R1, same stored map/path/B/vw; prediction matched when reconstructed')
    save(OUT/'legacy_manifest.json',m);print(json.dumps(dict(cases=368,snapshots=sum(c['snapshot_available'] for c in cases))))

def old_controller(case,cache):
    root=Path(case['output'])
    if str(root) not in cache:
        with (root/'agent_trajectory.csv').open() as f:trajectory=list(csv.DictReader(f))
        cache[str(root)]=dict(commands=lines(root/'phase20_commands.jsonl'),apps=[e for e in lines(root/'repair.jsonl') if e['event']=='PATH_APPLIED'],trajectory=trajectory)
    d=cache[str(root)];event=case['dispatch'];tick=event['prediction']['dispatch_tick'];t=event['dispatch_sim_s']
    row=d['trajectory'][tick];B=[float(row[k]) for k in ('x_m','y_m','yaw_rad')];vw=[event['previous_vw'][0],float(row['w_rad_s'])]
    cmd=next((r for r in reversed(d['commands']) if r['time_s']<t-1e-10),None)
    if cmd is None or cmd.get('path_source_id') is None:return B,vw,None
    app=next((r for r in reversed(d['apps']) if r['id']==cmd['path_source_id'] and r['simulation_time_s']<t-1e-10),None)
    if app is None:return B,vw,None
    c=NoAlignment();c.replace_path(app['path_world'],app['pose'],app['previous_vw'][0])
    prior=next((r for r in reversed(d['commands']) if app['simulation_time_s']-1e-10<=r['time_s']<t-1e-10 and r.get('path_source_id')==app['id'] and (r.get('SP') or {}).get('mode') in ('GO','BRAKE','ROTATE','ENDPOINT')),None)
    if prior:
        mode=prior['SP']['mode'];c.mode='GO' if mode=='ENDPOINT' else mode;c.follower.progress=float(prior['SP'].get('progress',0.))
    return B,vw,c

def replay():
    m=read(OUT/'legacy_manifest.json');dest=OUT/'legacy_replay';dest.mkdir(exist_ok=True);assert not (dest/'results.json').exists(),'No automatic replay repeat'
    cache={};rows=[]
    for i,c in enumerate(m['cases']):
        base=c['numerical_result'];summary=c['summary'];dispatch=c['dispatch'];prediction=dispatch['prediction']
        row=dict(key=c['key'],scene=c['scene'],index=c['index'],online_reason=c['outcome']['reason'],online_compute_s=summary.get('compute_wall_s'),
            online_wait_s=c['outcome'].get('wait_wall_s'),numeric_details_available=base is not None,
            online_planning_s=base.get('planning_wall_s') if base else None,online_diagnostic_s=base.get('diagnostic_wall_s') if base else None,
            logged_iterations=base.get('iterations') if base else None,timeout_iteration_known=False,
            initial_trajectory_complete=bool(base and base.get('initialization')),last_iterate_changed=bool(base and base.get('initial_x') is not None and base.get('last_x') is not None and not np.array_equal(base['initial_x'],base['last_x'])),
            original_initial_certificate_logged=bool(base and base.get('initial_certificate')),online_prediction_s=None,online_queue_s=None,online_slsqp_s=None,online_certificate_s=None)
        if c['snapshot_available']:
            assert sha256_file(Path(dispatch['snapshot']['file']))==c['snapshot_sha256'];field=RecentSnapshot.load(dispatch['snapshot']['file']);cfg=read(Path(c['output'])/'scenario.json');alpha=float(cfg['plant_alpha']);alpha=alpha if np.isfinite(alpha) else 2.
            B,vw,controller=old_controller(c,cache);start=time.perf_counter();check=predict(B,vw,controller,prediction['dispatch_tick'],float(cfg['plant_alpha']));pred_time=time.perf_counter()-start
            matched=bool(np.allclose(check['pose'],prediction['pose'],atol=1e-10,rtol=0) and np.allclose(check['vw'],prediction['vw'],atol=1e-10,rtol=0))
            # If the live prior controller cannot be reconstructed exactly, use
            # the stored solver input and explicitly exclude prediction timing.
            if not matched:start=time.perf_counter()
            r=frozen_solve(prediction['pose'],prediction['vw'],dispatch['path'],field,alpha,None,start)
            row.update(offline_prediction_reproduced=matched,offline_prediction_s=pred_time if matched else None,
                offline_scope='PREDICTION_PLUS_SOLVE' if matched else 'SOLVER_ONLY_SAVED_B',offline_wall_s=r['wall_s'],offline_type=r['output_type'],offline_reason=r['disposition'],
                offline_iterations=r['iterations'],online_minus_offline_s=summary['compute_wall_s']-r['wall_s'] if summary.get('compute_wall_s') is not None else None)
            save(dest/(c['key']+'.json'),dict(comparison=row,offline_result=r))
        else:row['offline_scope']='MISSING_SNAPSHOT'
        rows.append(row)
        if (i+1)%50==0:print('[legacy replay]',i+1,'/368',flush=True)
    keys=list(dict.fromkeys(k for r in rows for k in r));rows=[{k:r.get(k) for k in keys} for r in rows]
    save(dest/'results.json',rows);csv_write(OUT/'legacy_timing.csv',rows)
    assert all(sha256_file(Path(p))==h for p,h in m['input_sha256'].items())
    print(json.dumps(dict(cases=len(rows),matched_prediction=sum(bool(r.get('offline_prediction_reproduced')) for r in rows),offline_types=dict(Counter(r.get('offline_type') for r in rows)))))

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--replay',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    elif a.replay:replay()
