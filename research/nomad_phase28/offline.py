"""Registered200 saved-event solves, once each; no Isaac/inference/navigation."""
import csv,json,time,copy
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase20.execution import SPAlignment
from nomad_phase20d.recent import RecentSnapshot
from .config import OUT,verify,angular_limit
from .graph import solve
from .tracking import predict,na_duration,TimedFollower

def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s]
def register_samples():
    from .inputs import inventory
    inv=inventory(all_methods=True);eligible=inv['cases'];assert all(c['snapshot_available'] for c in eligible)
    cache={};aligned=[]
    for i,c in enumerate(eligible):
        if c['output'] not in cache:cache[c['output']]=[r for r in lines(Path(c['output'])/'repair.jsonl') if r['event']=='PATH_APPLIED']
        c['original_alignment']=cache[c['output']][c['application_index']]['alignment']
        if c['original_alignment']:aligned.append(i)
    rng=np.random.default_rng(20261106);all_c0=[i for i,c in enumerate(eligible) if c['source_method']=='C0'];first=rng.choice(all_c0,100,replace=False).tolist();pool=[i for i in aligned if i not in first]
    assert len(pool)>=100;second=rng.choice(pool,100,replace=False).tolist();cases=[]
    for stratum,indices in [('C0_SAFE_RANDOM',first),('ACTUAL_ALIGNMENT',second)]:
        for i in indices:
            c=dict(eligible[i],stratum=stratum,event_key=f"{eligible[i]['scene']}_{eligible[i]['index']}_{eligible[i]['source_method']}_{eligible[i]['native_id']}")
            c['snapshot_sha256']=sha256_file(Path(c['snapshot']['file']));cases.append(c)
    manifest=dict(seed=20261106,scope='First100 from all C0 SAFE FRESH; second100 from actual aligned SAFE FRESH across all depth-enabled Phase27-R methods, disjoint. RAW B0 has no depth snapshot and is ineligible for a depth-constrained solve; R2/R3 applications are not SAFE FRESH.',
        total_eligible=len(eligible),c0_eligible=len(all_c0),alignment_eligible=len(aligned),second_pool_after_exclusion=len(pool),cases=cases,input_sha256=inv['input_sha256'],
        warm_start='Only preceding accepted selected event in chronological run order; no solves on unselected events',frozen_before_solves=True)
    p=OUT/'preparation/sample_manifest.json';assert not p.exists();p.write_text(json.dumps(manifest,indent=2)+'\n');return manifest

def previous_controller(case,cache):
    run=Path(case['output'])
    if str(run) not in cache:
        cache[str(run)]=dict(apps=[r for r in lines(run/'repair.jsonl') if r['event']=='PATH_APPLIED'],commands=lines(run/'phase20_commands.jsonl'),fresh={e['id']:e for e in lines(run/'events.jsonl') if e.get('application_sim_s') is not None},fallback=lines(run/'fallback.jsonl'))
    data=cache[str(run)];cmd=next((r for r in reversed(data['commands']) if r['time_s']<case['time_s']-1e-10),None)
    if cmd is None or cmd.get('path_source_id') is None or cmd['source'] in ('STOP_WAIT','REPAIR_WAIT','DETOUR_WAIT','WAYPOINT_TIMEOUT','ENDPOINT','RECOVER_ROTATE','WAIT_FRESH'):return None
    app=next((r for r in reversed(data['apps'][:case['application_index']]) if r['id']==cmd['path_source_id']),None)
    if app is None:return None
    ctl=SPAlignment();ctl.replace_path(app['path_world'],app['pose'],app['previous_vw'][0])
    mode=(cmd.get('SP') or {}).get('mode')
    if mode in ('GO','BRAKE','ROTATE'):ctl.mode=mode
    ctl.follower.progress=float((cmd.get('SP') or {}).get('progress',0.))
    if case['source_method']=='B1_SAFE_TE':
        from nomad_phase12.methods import TemporalTargets
        from nomad_phase21.execution import TEProfile
        ensemble=TemporalTargets();ai=fi=0;apps=data['apps'][:case['application_index']];fallback=data['fallback']
        for command in data['commands']:
            if command['time_s']>=case['time_s']-1e-10:break
            while ai<len(apps) and apps[ai]['simulation_time_s']<=command['time_s']+1e-10:
                a=apps[ai];ensemble.push(a['path_world'],a['id'],data['fresh'][a['id']]['received_monotonic_ns']);ai+=1
            while fi<len(fallback) and fallback[fi]['simulation_time_s']<=command['time_s']+1e-10:
                if 'kept_chunk_ids' in fallback[fi]:ensemble.chunks=[c for c in ensemble.chunks if c['id'] in fallback[fi]['kept_chunk_ids']]
                fi+=1
            detail=(command.get('SP') or {}).get('ensemble')
            if detail is not None:
                ensemble.chunks=[c for c in ensemble.chunks if c['id'] in detail['chunk_ids']]
                for chunk in ensemble.chunks:
                    q=next(c for c in detail['components'] if c['id']==chunk['id']);chunk['follower'].progress=q['progress_m']
        wrapped=object.__new__(TEProfile);wrapped.__dict__.update(ctl.__dict__);wrapped.ensemble=ensemble
        wrapped.prediction_epoch_ns=case['application_monotonic_ns'];wrapped.prediction_epoch_tick=case['tick'];wrapped.now_ns=wrapped.prediction_epoch_ns;ctl=wrapped
    return ctl

def main():
    verify();manifest=read(OUT/'preparation/sample_manifest.json');out=OUT/'offline';out.mkdir(exist_ok=True)
    assert not (out/'events.json').exists(),'Frozen saved-event experiment already executed; no automatic rerun'
    cases=sorted(manifest['cases'],key=lambda c:(c['output'],c['time_s']));cache={};warm={};rows=[]
    for i,c in enumerate(cases):
        field=RecentSnapshot.load(c['snapshot']['file']);assert sha256_file(Path(c['snapshot']['file']))==c['snapshot_sha256']
        cfg=read(Path(c['output'])/'scenario.json');alpha,source=angular_limit(cfg);previous=previous_controller(c,cache)
        started=time.perf_counter();prediction=predict(c['B'],c['previous_vw'],previous,c['tick'],float(cfg['plant_alpha']))
        r=solve(prediction['pose'],prediction['vw'],c['selected_path'],field,alpha,warm.get(c['output']),started)
        if r['accepted']:warm[c['output']]=r
        na=na_duration(c['selected_path'],prediction['pose'],prediction['vw'][0]);r.update(event_key=c['event_key'],stratum=c['stratum'],scene=c['scene'],index=c['index'],source_method=c['source_method'],native_id=c['native_id'],
            alpha=alpha,alpha_source=source,prediction=prediction,na_expected=na,expected_time_difference_s=r.get('trajectory_time_s',0)-na['total_s'] if 'trajectory_time_s' in r else None)
        # Evaluate the same feedforward/feedback limiter at planned knots only.
        # No robot trajectory is rolled out; this is a zero-tracking-error check.
        if r['accepted']:
            tracker=TimedFollower(r,0,alpha);times=np.r_[0.,np.cumsum(r['dt'])];vw=prediction['vw'];clips=[]
            for t in np.arange(0,times[-1],1/9):
                pose=[np.interp(t,times,np.asarray(r['poses'])[:,k]) for k in (0,1)]+[np.interp(t,times,np.unwrap(np.asarray(r['poses'])[:,2]))]
                tracker.now_s=float(t);tracker.previous_w=vw[1];vw,diag=tracker.control(pose,vw[0]);clips.append(diag['any_clipped'])
            r['planned_knot_clip_fraction']=float(np.mean(clips)) if clips else 0.
        rows.append(r)
        (out/f"{c['event_key']}.json").write_text(json.dumps(r,indent=2)+'\n')
        if (i+1)%25==0:print('[offline]',i+1,'/200',flush=True)
    (out/'events.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(dict(events=len(rows),accepted=sum(r['accepted'] for r in rows),dispositions=dict(Counter(r['disposition'] for r in rows)))))

if __name__=='__main__':main()
