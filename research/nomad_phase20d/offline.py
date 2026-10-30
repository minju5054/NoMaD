"""One recheck of the same69 events; old publication clocks retained, no navigation gate."""
import json,argparse,time,multiprocessing as mp,subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase15.depth_sdf import intrinsics
from nomad_phase15b.depth import Snapshot
from nomad_phase20.metrics import rows
from nomad_phase19r.evaluate import dump,csv_write,clean
from nomad_phase20c.offline import oracle_path,rollout,decision,gap_direction
from nomad_phase20.depth import BOUNDS
from nomad_phase15.evaluate import sample_path
from .recent import RecentMap,RecentSnapshot
from .pool import initialize,ping,evaluate_job

OUT=ROOT/'research/results/phase20d_offline';ART=ROOT.parent/'artifacts/isaac6/phase20d_recent_replay_01';HERE=ROOT/'research/nomad_phase20d'

def recent_fraction(snapshot,path,tick):
    q,_=sample_path(np.array(path));cell,ok=snapshot.cells(q);recent=np.zeros(len(q),dtype=bool)
    x,y=cell[ok].T;last=snapshot.last_free_tick[y,x]
    recent[ok]=(last>=0)&(tick-last<=144)
    return float(recent.mean())

def run():
    assert not OUT.exists() and not ART.exists()
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).strip()
    p=json.loads((HERE/'protocol.json').read_text());hashes={}
    def track(file):file=Path(file).resolve();hashes[str(file)]=sha256_file(file);return file
    events=json.loads(track(ROOT/'research/results/phase20c_shadow_recheck/events_before_solve.json').read_text());assert len(events)==69
    for f,h in p['protected_sha256'].items():assert sha256_file(track(ROOT/f))==h
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();OUT.mkdir(parents=True);ART.mkdir(parents=True)
    dump(OUT/'protocol.json',p);dump(OUT/'registration.json',dict(git_sha=sha,event_ids=[e['event_id'] for e in events],new_navigation=0))
    updates_log=[]
    for name in dict.fromkeys(e['run'] for e in events):
        ee=[e for e in events if e['run']==name];run=Path(ee[0]['output']);c=json.loads(track(run/'scenario.json').read_text());field=RecentMap(BOUNDS);k=intrinsics(c['camera'])
        target={e['source_snapshot_file']:e['snapshot_file'] for e in ee};mapped={};dest=ART/name;dest.mkdir()
        for u in rows(track(run/'depth/updates.jsonl')):
            file=track(run/f"depth/depth_{u['frame_id']:04d}.npz")
            with np.load(file) as z:d=z['depth'];transform=z['camera_to_world']
            rng=np.random.default_rng(np.random.SeedSequence([20261027,c['seed_offset'],u['frame_id']]))
            stats=field.update(d,k,transform,True,rng,frame_tick=round(u['sim_s']*72))
            updates_log.append(dict(run=name,frame_id=u['frame_id'],**stats))
            if u['file'] in target:
                old=Snapshot.load(track(target[u['file']]))
                for key in ('values','occupied','observed'):np.testing.assert_array_equal(getattr(field,key),getattr(old,key))
                path=dest/f"snapshot_{u['frame_id']:04d}.npz";snap=RecentSnapshot(field,{**u,'file':str(path),'source_snapshot_file':u['file']});snap.save(path)
                mapped[u['file']]=str(path)
        assert set(mapped)==set(target)
        for e in ee:e['shadow_snapshot_file']=e['snapshot_file'];e['snapshot_file']=mapped[e['source_snapshot_file']]
        print(f'[replay] {name}: timestamps added; base occupancy/SDF exactly matches20C',flush=True)
    csv_write(OUT/'map_updates.csv',updates_log);dump(OUT/'events_before_solve.json',events);dump(OUT/'input_hashes.json',hashes)
    ctx=mp.get_context('spawn');q=ctx.Queue();solutions=[];cache_dir=ART/'r3_cache';cache_dir.mkdir();bad=[]
    with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(q,)) as pool,(OUT/'solutions.jsonl').open('x') as log:
        ff=[pool.submit(ping) for _ in range(4)];pids=[q.get(timeout=90) for _ in range(4)];assert len(set(pids))==4
        for f in ff:f.result()
        for e in events:
            job=dict(kind='R3',job_id=e['event_id'],B=e['B'],u_ref=e['u_ref'],evaluation_tick=e['tick'],snapshot_file=e['snapshot_file'],
                cache_file=str(cache_dir/f"event_{e['event_id']:04d}.npz"),dispatch_ns=time.monotonic_ns())
            result=evaluate_job(pool,job);selected=result['selected_initialization'];snap=RecentSnapshot.load(e['snapshot_file'])
            e.update(accepted=selected is not None,selected_initialization=selected,seven_wall_s=result['pool_wall_s'],cache=result['cache'])
            for r in result['results']:
                r.update(event_id=e['event_id'],initialization=r['index'],oracle_clearance_m=oracle_path(r['path'],e['oracle_config']) if r.get('path') is not None else None)
                if r.get('path') is not None:r['recent_free_fraction']=recent_fraction(snap,r['path'],e['tick'])
                log.write(json.dumps(clean(r),allow_nan=False)+'\n');log.flush();solutions.append({k:v for k,v in r.items() if k not in ('path','initial_path')})
                if r['accepted'] and r['oracle_clearance_m']<0:bad.append(dict(event_id=e['event_id'],initialization=r['index'],selected=r['index']==selected,
                    snapshot_age_s=e['snapshot_age_s'],recent_free_fraction=r['recent_free_fraction'],oracle_clearance_m=r['oracle_clearance_m']))
            if selected is not None:
                r=result['results'][selected];rr=rollout(e['B'],r['path'],e['previous_v'],e['oracle_config'])
                e.update(selected_oracle_clearance_m=r['oracle_clearance_m'],selected_recent_free_fraction=r['recent_free_fraction'],selected_unknown_fraction=r['unknown_fraction'],
                    selected_progress_m=r['progress_m'],rollout_overlap=rr['overlap'],rollout_distance_m=rr['distance_m'],**gap_direction(r['path'],e))
            if (e['event_id']+1)%10==0:print(f"[R3 recent] {e['event_id']+1}/69",flush=True)
    verdict=decision(events,solutions);verdict.update(assessment_label='사후 수정 후 재점검 2',navigation_blocked_by_this_result=False,
        pilot_label='탐색적 파일럿' if verdict['label']=='NOT_READY' else '파일럿')
    csv_write(OUT/'events.csv',[{k:v for k,v in e.items() if k!='oracle_config'} for e in events]);csv_write(OUT/'initializations.csv',solutions)
    if bad:csv_write(OUT/'penetrations.csv',bad)
    else:(OUT/'penetrations.csv').write_text('event_id,initialization,selected,snapshot_age_s,recent_free_fraction,oracle_clearance_m\n')
    dump(OUT/'decision.json',verdict)
    for file,h in hashes.items():assert sha256_file(file)==h
    dump(OUT/'complete.json',dict(git_sha=sha,events=69,initializations=len(solutions),input_hashes_unchanged=True,base_map_regression='exact',new_navigation=0,label=verdict['label']))
    print(json.dumps(clean(verdict)),flush=True)

if __name__=='__main__':run()
