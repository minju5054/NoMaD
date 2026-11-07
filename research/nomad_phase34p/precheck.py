"""Descriptive R3 replay of every stored Phase32 R2 call; no simulation."""
import csv,json,time,multiprocessing as mp
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase32o.evaluate import save,csvout
from nomad_phase32o.exec_cert import certify
from nomad_phase20c.detour_known import radial_reference
from nomad_phase20c.detour import select_detour
from nomad_phase20d.recent import RecentSnapshot,build_cache
from nomad_phase24r.safety import certificate
from nomad_phase20d.pool import evaluate_job,ping
from nomad_phase33p.storage import install
from .pool import initialize
from .config import OUT

def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x] if Path(p).exists() else []

def collect():
    cases=[];manifest={};verified_directions=0
    for log in sorted((ROOT.parent/'artifacts/isaac6/phase32_01/main').glob('*/attempt*/repair.jsonl')):
        run=log.parent;cfg=read(run/'scenario.json');trace=list(csv.DictReader((run/'agent_trajectory.csv').open()))
        poses=np.array([[float(x[k]) for k in ('x_m','y_m','yaw_rad')] for x in trace]);ec=lines(run/'exec_cert.jsonl')
        for e in lines(run/'detour.jsonl'):
            if e['event']=='TRIGGER' and e.get('trigger')=='A':
                u,_=radial_reference(poses,round(e['simulation_time_s']*72));np.testing.assert_allclose(u,e['u_ref'],atol=1e-12,rtol=0);verified_directions+=1
        for entry in lines(log):
            if entry['event']!='SUBMIT':continue
            tick=round(entry['simulation_time_s']*72);np.testing.assert_allclose(poses[tick],entry['B'],atol=1e-9,rtol=0)
            u,source=radial_reference(poses,tick);job=read(run/'repair_jobs'/f"transport_{entry['job_id']:04d}.json");assert job['kind']=='R2'
            previous=[x for x in ec if x['event']=='INSTALL' and x['apply_tick']<=tick];cap=previous[-1]['speed_cap_m_s'] if previous else None
            case=dict(case_id=f'A{len(cases):04d}',source_run=str(run),source_method=cfg['phase32_method'],scene=cfg['phase16_scene'],index=cfg['seed_offset']//10000,
                      original_job_id=entry['job_id'],simulation_time_s=entry['simulation_time_s'],tick=tick,B=entry['B'],previous_vw=entry['previous_vw'],
                      snapshot_file=job['snapshot_file'],u_ref=u.tolist(),reference_source=source,speed_cap_m_s=cap)
            cases.append(case)
            for p in (log,run/'agent_trajectory.csv',run/'detour.jsonl',run/'exec_cert.jsonl',Path(job['snapshot_file']),run/'repair_jobs'/f"transport_{entry['job_id']:04d}.json"):
                manifest[str(p)]=sha256_file(p)
    assert len(cases)==44
    save(OUT/'preparation/precheck_inputs.json',cases);save(OUT/'preparation/precheck_input_hashes.json',manifest)
    save(OUT/'preparation/direction_regression.json',dict(A_R3_directions_matched=verified_directions,source='unchanged radial_reference; start->current, <0.5m uses start heading'))
    return cases

def main():
    install();cases=collect();directory=OUT/'preparation';cache_dir=directory/'temporary_cache';cache_dir.mkdir(parents=True,exist_ok=True)
    ctx=mp.get_context('spawn');ready=ctx.Queue();results=[];start=time.monotonic()
    with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(ready,)) as pool:
        warm=[pool.submit(ping) for _ in range(4)];pids=[ready.get(timeout=90) for _ in range(4)];assert len(set(pids))==4
        for f in warm:f.result()
        for case in cases:
            file=directory/'precheck_cases'/f"{case['case_id']}.json"
            if file.exists():results.append(read(file)['row']);continue
            cached=cache_dir/f"{case['case_id']}.npz"
            job=dict(kind='R3',job_id=case['original_job_id'],B=case['B'],u_ref=case['u_ref'],evaluation_tick=case['tick'],snapshot_file=case['snapshot_file'],cache_file=str(cached),dispatch_ns=time.monotonic_ns())
            try:numeric=evaluate_job(pool,job)
            finally:cached.unlink(missing_ok=True)
            base=RecentSnapshot.load(case['snapshot_file']);strict,_=build_cache(base,case['tick']);checks=[];filtered=[]
            for i,candidate in enumerate(numeric['results']):
                check=certify(case['B'],case['previous_vw'],candidate['path'],base,speed_cap=case['speed_cap_m_s']) if candidate.get('accepted') else dict(passed=False,reason='NO_ACCEPTED_SOLUTION')
                checks.append(dict(index=i,**check));filtered.append(dict(candidate,accepted=bool(candidate.get('accepted') and check['passed'])))
            selected=select_detour(filtered);original=numeric['selected_sample'];cert=certificate(filtered[selected]['path'],case['B'],base,strict) if selected is not None else None
            row=dict(**case,numeric_success=original is not None,numeric_selected=original,numeric_selected_ec_pass=checks[original]['passed'] if original is not None else False,
                     ec_pass_any=selected is not None,ec_selected=selected,ec_rejected_candidates=sum(c.get('accepted',False) and not checks[i]['passed'] for i,c in enumerate(numeric['results'])),
                     application_certificate_pass=cert['passed'] if cert else False,within_1s=numeric['pool_wall_s']<=1.,pool_wall_s=numeric['pool_wall_s'],
                     available_with_existing_rules=bool(selected is not None and cert['passed'] and numeric['pool_wall_s']<=1.))
            save(file,dict(row=row,numeric=numeric,checks=checks,application_certificate=cert));results.append(row)
            print('[precheck]',len(results),'/44',flush=True)
    csvout(directory/'precheck.csv',results)
    summary=[]
    for group in ('ALL','C0-NA+EC','G18+EC'):
        rr=[r for r in results if group=='ALL' or r['source_method']==group]
        summary.append(dict(source=group,n=len(rr),R3_solution=sum(r['numeric_success'] for r in rr),pre_EC_selected_pass=sum(r['numeric_selected_ec_pass'] for r in rr),
            EC_eligible_solution=sum(r['ec_pass_any'] for r in rr),available_with_existing_rules=sum(r['available_with_existing_rules'] for r in rr),pool_p95_s=float(np.quantile([r['pool_wall_s'] for r in rr],.95))))
    save(directory/'precheck_summary.json',dict(summary=summary,elapsed_s=time.monotonic()-start,navigation_started=0,used_for_decision=False,
         limitation='fixed R2-call pose/velocity/map; no future wait motion, map updates or NoMaD regeneration; runtime R3 EC filter/selection/certificate reused'))
    print(json.dumps(summary))

if __name__=='__main__':main()
