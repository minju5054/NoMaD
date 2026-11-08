"""Read saved inputs, not inferred maps or reconstructed missing jobs."""
import json,hashlib,subprocess
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT,local_to_world
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase15.evaluate import suffix
from nomad_storage_sdf.loader import load_npz
from nomad_phase32o.evaluate import save

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase39o'
INPUT_ROOT=ROOT.parent/'artifacts/isaac6/phase38_01/night1/main'
HASHES={}
def track(p):
    p=Path(p).resolve();HASHES[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();return p
def read(p):return json.loads(track(p).read_text())
def rows(p):return [json.loads(s) for s in track(p).read_text().splitlines() if s] if Path(p).exists() else []

def extra_path(native,B):
    """B+10, uniform arclength prefix <= frozen1.5m, never extrapolate."""
    try:
        tail,remaining=suffix(np.asarray(native,float),np.asarray(B,float));path=XYPath(np.vstack([np.asarray(B)[:2],tail]))
        length=min(1.5,float(path.s[-1]))
        if remaining<1.-1e-12 or length<1.-1e-12:return None,dict(reason='SHORT_SUFFIX',remaining_m=float(remaining),connected_length_m=float(path.s[-1]))
        q=np.array([path.at(s) for s in np.linspace(0,length,11)]);q[0]=np.asarray(B)[:2];segments=np.linalg.norm(np.diff(q,axis=0),axis=1)
        if segments.min()<.1-1e-12 or segments.max()>.2+1e-12:return None,dict(reason='RESAMPLED_SPACING_OUTSIDE_0.1_0.2',minimum_m=float(segments.min()),maximum_m=float(segments.max()))
        return q.tolist(),dict(reason='ADDED',remaining_m=float(remaining),used_arclength_m=length,points=11)
    except ValueError as exc:return None,dict(reason='INVALID_STORED_PATH',error=str(exc))

def collect():
    HASHES.clear();cases=[];missing=[];counts=Counter()
    for run in sorted(INPUT_ROOT.glob('*_OURS/attempt*')):
        if not run.is_dir():continue
        provenance=read(run/'provenance.json');assert provenance['method']=='OURS'
        version=provenance['protocol']['frozen_sources']
        for name in ('nomad_phase19r/repair.py','nomad_phase20/repair.py','nomad_phase20c/detour.py','nomad_phase20c/detour_known.py','nomad_phase20d/pool.py','nomad_phase20d/recent.py'):
            relative='research/'+name
            expected=version.get(relative)
            if expected is None:
                blob=subprocess.check_output(['git','show',provenance['git_sha']+':'+relative],cwd=ROOT)
                expected=hashlib.sha256(blob).hexdigest()
            assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==expected,relative
        repair=rows(run/'repair.jsonl');detour=rows(run/'detour.jsonl');numeric={e['job_id']:e for e in rows(run/'repair_pool_jobs.jsonl')}
        calls={e['job_id']:dict(e,kind='R2') for e in repair if e['event']=='SUBMIT'}
        calls.update({e['job_id']:dict(e,kind='R3') for e in detour if e['event']=='TRIGGER'})
        transports={int(f.stem.split('_')[1]):f for f in (run/'repair_jobs').glob('transport_*.json')}
        events={e['id']:e for e in rows(run/'events.jsonl')}
        applications=[e for e in repair if e['event']=='PATH_APPLIED']
        for jid in sorted(set(calls)|set(transports)|set(numeric)):
            call=calls.get(jid,{});saved=numeric.get(jid);kind=call.get('kind',(saved or {}).get('kind'))
            file=transports.get(jid);npz=run/'repair_jobs'/f'input_{jid:04d}.npz'
            recorded=Counter(r.get('disposition','NO_DISPOSITION') for r in (saved or {}).get('results',[]))
            ident=dict(case_id=f'J{len(cases)+len(missing):04d}',run=str(run.resolve()),scene=run.parent.name.split('_')[0],
                seed=int(run.parent.name.split('_')[1]),attempt=run.name,job_id=jid,kind=kind,recorded_dispositions=dict(recorded),
                recorded_execution_sha=provenance['git_sha'],frozen_solver_sources_match=True)
            if file is None or not npz.exists():
                missing.append(dict(ident,reason='MISSING_TRANSPORT' if file is None else 'MISSING_SAVED_SNAPSHOT',reconstructed=False));continue
            job=read(file);assert job['kind']==kind and job['job_id']==jid
            data=load_npz(track(npz));assert np.isfinite(data['values']).all() and data['values'].shape==data['occupied'].shape
            meta=json.loads(str(data['metadata']));assert meta['frame_id']==job['depth_snapshot']['frame_id']
            np.testing.assert_allclose(job['B'],call.get('B',job['B']),atol=0,rtol=0)
            extras=[];audit=[]
            if kind=='R3':
                event=events.get(job['id']);bank=None
                if event and event.get('overnight_metric_samples') is not None and event.get('application_sim_s') is not None and event['application_sim_s']<=job['simulation_time_s']+1e-9:
                    bank=[local_to_world(np.asarray(x),event['observation_pose']) for x in event['overnight_metric_samples']]
                    assert np.shape(bank)==(8,8,2)
                for i in range(8):
                    q,detail=extra_path(bank[i],job['B']) if bank is not None else (None,dict(reason='MISSING_SAVED_CANDIDATE_SET'))
                    audit.append(dict(source=f'NOMAD_{i}',source_id=job['id'],**detail))
                    if q is not None:extras.append(dict(source=f'NOMAD_{i}',path=q))
                previous=[e for e in applications if e['simulation_time_s']<=job['simulation_time_s']+1e-9]
                e=previous[-1] if previous else None
                q,detail=extra_path(e['path_world'],job['B']) if e is not None else (None,dict(reason='NO_PREVIOUS_INSTALLATION'))
                audit.append(dict(source='PREVIOUS_INSTALLATION',installed_s=e['simulation_time_s'] if e else None,**detail))
                if q is not None:extras.append(dict(source='PREVIOUS_INSTALLATION',path=q))
            else:assert np.shape(job['samples_world'])==(8,8,2)
            job=dict(job,snapshot_file=str(npz.resolve()),extra_initializations=extras)
            runtime=[e for e in (repair if kind=='R2' else detour) if e['event']=='RESULT' and e['job_id']==jid]
            cases.append(dict(ident,job=job,extra_audit=audit,recorded_numeric=saved,
                recorded_runtime_disposition=runtime[-1]['disposition'] if runtime else 'NO_RUNTIME_RESULT'))
            counts[(ident['scene'],kind)]+=1
    values=[c['recorded_numeric']['pool_wall_s'] for c in cases if c['recorded_numeric'] and 'pool_wall_s' in c['recorded_numeric']]
    summary=dict(saved_jobs=len(cases),missing_jobs=len(missing),missing_by_reason=dict(Counter(c['reason'] for c in missing)),
        missing_negative_depth_jobs=sum('NEGATIVE_DEPTH_AT_B' in c['recorded_dispositions'] for c in missing),
        saved_negative_depth_jobs=sum('NEGATIVE_DEPTH_AT_B' in c['recorded_dispositions'] for c in cases),
        groups=[dict(scene=s,kind=k,jobs=n) for (s,k),n in sorted(counts.items())],
        logged_job_p50_s=float(np.median(values)) if values else None,logged_job_p95_s=float(np.quantile(values,.95)) if values else None,
        extra_initializations=dict(Counter(a['reason'] for c in cases for a in c['extra_audit'])),simulations=0,dataset_solves=0)
    save(OUT/'preparation/all_inputs.json',cases);save(OUT/'preparation/missing_inputs.json',missing)
    save(OUT/'preparation/input_hashes.json',HASHES);save(OUT/'preparation/inventory.json',summary)
    return cases,summary

if __name__=='__main__':
    _,summary=collect();print(json.dumps(summary))
