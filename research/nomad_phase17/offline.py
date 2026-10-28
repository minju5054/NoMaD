"""391 immutable Phase16 inputs, one CLR attempt each; no baseline re-solve."""
import argparse
import csv
import json
import platform
import subprocess
import time
from collections import Counter
from pathlib import Path
import numpy as np
import scipy
from nomad_isaac.common import ROOT, sha256_file
from nomad_phase0.graph_v4 import menger
from nomad_phase15b.depth import Snapshot
from nomad_phase16.geometry import path_safety
from .graph import ClearanceGraph

HERE=ROOT/'research/nomad_phase17'
OUT=ROOT/'research/results/phase17'
METHOD='FRESHEST-SAFE+GRAPH-depth'


def dump(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def rows(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x]


def readiness(clr,baseline,p95):
    return 'READY' if baseline-clr<=.10+1e-12 and p95<=.15 else 'NOT_READY'


def oracle(xy,config):
    s=path_safety(xy,config)
    return min(s['obstacle_clearance_m'],s['corridor_clearance_m'])


def distribution(values):
    v=[x for x in values if x is not None and np.isfinite(x)]
    return dict(n=len(v),median=float(np.median(v)) if v else None,
                p10=float(np.percentile(v,10)) if v else None,
                p90=float(np.percentile(v,90)) if v else None,
                p95=float(np.percentile(v,95)) if v else None)


def measures(poses,job,config,raw_clearance):
    if poses is None:return {}
    xy=np.asarray(poses)[:,:2];B=np.array(job['boundary'])
    from nomad_phase0.graph_v2 import fixed_entry
    e=fixed_entry(np.array(job['world_xy']),B)
    E=(1-e['fraction'])*xy[e['a']]+e['fraction']*xy[e['b']]
    clearance=oracle(xy,config)
    return dict(oracle_clearance_m=clearance,oracle_delta_m=clearance-raw_clearance,
                boundary_error_m=float(np.linalg.norm(E-B[:2])),
                maximum_abs_curvature_m_inv=float(np.abs(menger(xy)[0]).max()),
                endpoint_progress_m=float((xy[-1]-B[:2])@np.array([np.cos(B[2]),np.sin(B[2])])) )


def run(out):
    assert not out.exists(),'Existing output preserved; no solve retries'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).strip(),'Commit code and protocol before execution'
    protocol=json.loads((HERE/'protocol.json').read_text())
    inputs={}
    def track(p,expected=None):
        p=Path(p);h=sha256_file(p)
        if expected:assert h==expected,p
        inputs[str(p.resolve())]=h
        return p
    source=track(ROOT/'research/results/phase16/runs.json')
    records=[r for r in json.loads(source.read_text()) if r['method']==METHOD]
    jobs=[]
    for r in records:
        run=Path(r['output']);assert run.parent==ROOT.parent/'artifacts/isaac6/phase16_multiscene_01'
        cfg=json.loads(track(run/'scenario.json',r['input_sha256'].get('scenario.json')).read_text())
        log=rows(track(run/'stage2_graph.jsonl',r['input_sha256'].get('stage2_graph.jsonl')))
        results={x['job_id']:x for x in log if x['event']=='RESULT'}
        for job in (x for x in log if x['event']=='SUBMIT'):
            track(job['depth_snapshot']['file'])
            jobs.append((r,job,results.get(job['job_id']),cfg))
    assert len(jobs)==391,len(jobs)
    for name,h in protocol['protected_sha256'].items():track(ROOT/name,h)
    for file in HERE.glob('*.py'):track(file)
    track(HERE/'protocol.json')
    out.mkdir(parents=True)
    dump(out/'offline_input_manifest.json',dict(git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sha256=inputs,python=platform.python_version(),scipy=scipy.__version__,numpy=np.__version__,protocol=protocol))
    data=[]
    with (out/'offline_solutions.jsonl').open('x') as journal:
        for record,job,saved,config in jobs:
            field=Snapshot.load(job['depth_snapshot']['file'])
            start=time.perf_counter();poses=None;solver=None;error=None;disposition=None
            try:
                graph=ClearanceGraph(job['world_xy'],job['boundary'],job['previous_command'],field,job['previous_xy'])
                poses,solver=graph.solve()
                disposition='NONCONVERGED' if not solver['success'] else 'ACCEPTED' if solver['feasible'] else 'CONSTRAINT_FAILED'
            except ValueError as e:
                error=str(e);disposition='INITIALIZATION_REJECTED'
            elapsed=time.perf_counter()-start
            accepted=bool(solver and solver['feasible'])
            # Evaluation geometry is first accessed after this job's solve.
            raw_gap=oracle(np.array(job['world_xy']),config)
            baseline_available=saved is not None and 'accepted' in saved
            oldposes=saved.get('poses') if baseline_available else None
            oldsolver=saved.get('solver',{}) if baseline_available else {}
            oldaccepted=bool(saved['accepted']) if baseline_available else None
            row=dict(run=record['key'],scene=record['scene'],index=record['index'],job_id=job['job_id'],fresh_id=job['id'],
                baseline_available=baseline_available,baseline_accepted=oldaccepted,
                baseline_runtime_disposition=saved.get('disposition') if saved else 'TERMINAL_UNAPPLIED_NO_RESULT',
                baseline_solver_s=oldsolver.get('solver_wall_s'),baseline_solve_certificate_s=oldsolver.get('solve_and_certificate_wall_s'),
                clr_accepted=accepted,clr_disposition=disposition,clr_error=error,clr_attempt_wall_s=elapsed,
                clr_solver_s=solver.get('solver_wall_s') if solver else None,
                clr_solve_certificate_s=solver.get('solve_and_certificate_wall_s') if solver else None,
                clr_active=solver.get('clearance_preference_active') if solver else None,raw_oracle_clearance_m=raw_gap,
                **{'baseline_'+k:v for k,v in measures(oldposes,job,config,raw_gap).items()},
                **{'clr_'+k:v for k,v in measures(poses,job,config,raw_gap).items()})
            journal.write(json.dumps(dict(run=record['key'],job_id=job['job_id'],disposition=disposition,accepted=accepted,
                poses=poses.tolist() if poses is not None else None,solver=solver,error=error,attempt_wall_s=elapsed),allow_nan=False)+'\n');journal.flush()
            data.append(row)
    names=list(dict.fromkeys(k for r in data for k in r))
    with (out/'offline_clr.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,names);w.writeheader();w.writerows(data)
    n=len(data);known=sum(r['baseline_available'] for r in data);old=sum(bool(r['baseline_accepted']) for r in data);new=sum(r['clr_accepted'] for r in data)
    times=distribution([r['clr_attempt_wall_s'] for r in data]);started=distribution([r['clr_attempt_wall_s'] for r in data if r['clr_solver_s'] is not None])
    # Missing baseline worker results cannot be invented. Test both bounds;
    # a READY declaration must satisfy the more conservative upper bound too.
    upper=(old+n-known)/n;decision=readiness(new/n,upper,max(times['p95'],started['p95']))
    summary=dict(label=decision,jobs=n,baseline_comparable_jobs=known,baseline_missing=n-known,
        baseline_accepted=old,baseline_acceptance_lower=old/n,baseline_acceptance_upper=upper,
        clr_accepted=new,clr_acceptance=new/n,clr_dispositions=dict(Counter(r['clr_disposition'] for r in data)),
        acceptance_change_pp=100*(new/n-old/n),acceptance_change_conservative_pp=100*(new/n-upper),
        clr_attempt_wall_s=times,clr_started_attempt_wall_s=started,
        baseline_solver_s=distribution([r['baseline_solver_s'] for r in data]),
        baseline_solve_certificate_s=distribution([r['baseline_solve_certificate_s'] for r in data]),
        clr_solver_s=distribution([r['clr_solver_s'] for r in data]),
        accepted_metrics={method:{key:distribution([r.get(method+'_'+key) for r in data if r.get(method+'_accepted')])
            for key in ('oracle_delta_m','oracle_clearance_m','boundary_error_m','maximum_abs_curvature_m_inv','endpoint_progress_m')}
            for method in ('baseline','clr')},
        all_finite_iterate_metrics={method:{key:distribution([r.get(method+'_'+key) for r in data])
            for key in ('oracle_delta_m','boundary_error_m','maximum_abs_curvature_m_inv','endpoint_progress_m')}
            for method in ('baseline','clr')},
        scope='Offline saved-path mechanism validation only. Oracle used only for post-solve evaluation. No navigation, inference, render, or baseline solve.',
        next_step='Continue recovery/campaign preparation' if decision=='READY' else 'Stop here; no campaign command, smoke, or main navigation')
    dump(out/'offline_summary.json',summary)
    for file,h in inputs.items():assert sha256_file(file)==h,file
    from .report import offline_report
    offline_report(out,summary)
    dump(out/'offline_complete.json',dict(attempts=n,input_hashes_unchanged=True,label=decision))
    print(f"{decision}: CLR {new}/{n}; baseline {old}/{known} available; acceptance change {summary['acceptance_change_conservative_pp']:.2f} pp (conservative); solve median/p95 {times['median']:.6f}/{times['p95']:.6f} s; started p95 {started['p95']:.6f} s")
    return summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT);a=p.parse_args();run(a.out)


if __name__=='__main__':main()
