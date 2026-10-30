"""Registered small two-parameter scan on saved20D/E/F inputs only."""
import json,time,tempfile,multiprocessing as mp,subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase19r.evaluate import clean,csv_write
from .config import protocol
from .pool import initialize,ping,evaluate_job

def select_cases():
    result=[]
    for phase in ('20d','20e','20f'):
        records=json.loads((ROOT/f'research/results/phase{phase}/runs.json').read_text());by_kind={'R2':[],'R3':[]}
        for r in sorted(records,key=lambda r:(r['index'],r['scene'])):
            if r['method']!='M3_DETOUR' or r.get('technical_validation')!='PASS':continue
            for path in sorted((Path(r['output'])/'repair_jobs').glob('transport_*.json')):
                job=json.loads(path.read_text());by_kind[job['kind']].append(dict(phase=phase,index=r['index'],scene=r['scene'],input=str(path),job=job))
        for kind in ('R2','R3'):result.extend(by_kind[kind][:6])
    return result

def main():
    p=protocol();assert p['status']=='REGISTERED' and p['astar']['selected'] is None
    out=ROOT/'research/results/phase21_tuning';out.mkdir(exist_ok=False);cases=select_cases()
    (out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');hashes={}
    for c in cases:
        for f in (c['input'],c['job']['snapshot_file']):hashes[f]=sha256_file(f)
    (out/'input_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n');results=[];summary=[];ctx=mp.get_context('spawn');q=ctx.Queue()
    with tempfile.TemporaryDirectory(prefix='phase21_tune_') as temp,ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(q,)) as pool:
        ff=[pool.submit(ping) for _ in range(4)]
        for _ in range(4):q.get(timeout=90)
        for f in ff:f.result()
        with (out/'jobs.jsonl').open('x') as log:
            for weight in p['astar']['lambda_candidates']:
                for iterations in p['astar']['smoothing_candidates']:
                    rows=[]
                    for number,c in enumerate(cases):
                        job={**c['job'],'dispatch_ns':time.monotonic_ns(),'cache_file':str(Path(temp)/f'{weight}_{iterations}_{number}.npz')}
                        r=evaluate_job(pool,job,weight,iterations);accepted=r['selected_sample'] is not None and r['dispatch_to_complete_s']<=1.
                        path=r['results'][r['selected_sample']] if accepted else None
                        row=dict(case=number,phase=c['phase'],stage=job['kind'],lambda_value=weight,smoothing_iterations=iterations,accepted=accepted,depth_clearance_m=path['depth_clearance_m'] if path else None,wall_s=r['dispatch_to_complete_s'],curvature_flag=path.get('curvature_flag') if path else None)
                        rows.append(row);results.append(row);log.write(json.dumps(clean(dict(**row,numeric=r)))+'\n');log.flush()
                    rate=np.mean([np.mean([r['accepted'] for r in rows if r['stage']==k]) for k in ('R2','R3') if any(r['stage']==k for r in rows)])
                    gaps=[r['depth_clearance_m'] for r in rows if r['accepted']]
                    summary.append(dict(lambda_value=weight,smoothing_iterations=iterations,stage_balanced_acceptance=float(rate),accepted=sum(r['accepted'] for r in rows),cases=len(rows),median_depth_clearance_m=float(np.median(gaps)) if gaps else None,p95_s=float(np.quantile([r['wall_s'] for r in rows],.95))))
                    print(f'[tune] lambda={weight} iterations={iterations} accepted={summary[-1]["accepted"]}/{len(cases)}',flush=True)
    best=min(summary,key=lambda r:(-r['stage_balanced_acceptance'],-(r['median_depth_clearance_m'] if r['median_depth_clearance_m'] is not None else -1e99),r['lambda_value'],r['smoothing_iterations']))
    csv_write(out/'jobs.csv',results);csv_write(out/'summary.csv',summary)
    selected=dict(lambda_=best['lambda_value'],smoothing_iterations=best['smoothing_iterations']);selected['lambda']=selected.pop('lambda_')
    (out/'selection.json').write_text(json.dumps(dict(selected=selected,criterion=best,git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()),indent=2)+'\n')
    p['astar']['selected']=selected;p['status']='TUNED';Path(__file__).with_name('protocol.json').write_text(json.dumps(p,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(dict(selected=selected,criterion=best)))
if __name__=='__main__':main()
