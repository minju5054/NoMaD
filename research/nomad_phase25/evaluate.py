"""Once per saved snapshot/variant, four warmed workers, no navigation."""
import argparse, json, multiprocessing as mp, os, time, tempfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from nomad_isaac.common import ROOT, sha256_file
from nomad_phase20d.recent import RecentSnapshot,build_cache,save_cache,load_cache
from nomad_phase20d.pool import initialize,ping
from nomad_phase19r.evaluate import clean
from nomad_phase24.storage import atomic_json
from nomad_phase0.graph_v4 import menger
from nomad_phase23o2.report import plan_passage
from nomad_phase22.metrics import side_choice
from .inputs import HERE,OUT,read
from .lm import solve_start,select_detour,ANGLES,ANGLES13

_key=None;_fields=None


def one(payload):
    global _key,_fields
    variant,angle,case,file,token=payload
    if _key!=token:_fields=load_cache(file);_key=token
    return clean(solve_start(case['B'],case['u_ref'],*_fields,angle,variant))


def measure(pool,case,variant,folder):
    start=time.perf_counter();base=RecentSnapshot.load(case['snapshot_file'])
    strict,cache=build_cache(base,case['tick']);file=str(folder/'field.npz');save_cache(base,strict,file)
    preprocessing=time.perf_counter()-start
    angles=ANGLES13 if variant=='L13' else ANGLES
    token=(case['case_id'],variant)
    attempts=list(pool.map(one,[(variant,a,case,file,token) for a in angles]))
    selected=select_detour(attempts);elapsed=time.perf_counter()-start
    timed_out=elapsed>1.
    if timed_out:selected=None
    row=dict(case_id=case['case_id'],source=case['source'],scene=case['scene'],index=case['index'],
        variant=variant,input_stage=case['input_stage'],accepted=selected is not None,
        compute_s=elapsed,preprocessing_s=preprocessing,timeout_1s=timed_out,
        selected_initialization=selected,certificate_passing_starts=sum(r['accepted'] for r in attempts),
        planned_box_passage=False,side=None,original_cost=None,depth_min_clearance_m=None,
        curvature_rms=None,curvature_max=None,progress_m=None,disposition='TIMEOUT' if timed_out else 'NO_ACCEPTED_START')
    path=None
    if selected is not None:
        a=attempts[selected];path=a['path'];k=menger(np.asarray(path))[0]
        row.update(disposition='ACCEPTED',original_cost=a['original_cost'],depth_min_clearance_m=a['depth_clearance_m'],
                   curvature_rms=float(np.sqrt(np.mean(k*k))),curvature_max=float(np.max(abs(k))),progress_m=a['progress_m'])
        row.update(side_choice(path,case))
        if case['input_stage']=='PRE_PASSAGE':row['planned_box_passage']=bool(plan_passage(dict(case=case),dict(plan=dict(path=path))))
    return dict(row=row,path=path,attempts=attempts,cache=cache)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--status',action='store_true');a=ap.parse_args()
    state=OUT/'state.json'
    if a.status:
        print(json.dumps(read(state) if state.exists() else dict(status='NOT_STARTED')));return
    protocol=read(HERE/'protocol.json');assert protocol['status']=='FROZEN_OFFLINE'
    manifest=read(OUT/'manifest.json');assert sha256_file(OUT/'manifest.json')==protocol['manifest_sha256']
    for name,h in protocol['frozen_sources'].items():assert sha256_file(ROOT/name)==h,name
    for name,h in protocol['source_sha256'].items():assert sha256_file(ROOT/name)==h,name
    for c in manifest['cases']:assert sha256_file(c['snapshot_file'])==c['snapshot_sha256']
    record_dir=OUT/'records';record_dir.mkdir(exist_ok=True)
    started=time.time();done=0;ctx=mp.get_context('spawn');queue=ctx.Queue()
    def status(label,**kw):atomic_json(state,dict(status=label,pid=os.getpid() if label=='RUNNING' else None,completed=done,total=len(manifest['cases'])*3,elapsed_s=time.time()-started,**kw))
    status('RUNNING')
    try:
        with tempfile.TemporaryDirectory(prefix='phase25_') as temp,ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
            jobs=[pool.submit(ping) for _ in range(4)];pids=[queue.get(timeout=90) for _ in range(4)]
            for job in jobs:job.result()
            assert len(set(pids))==4
            for i,case in enumerate(manifest['cases']):
                methods=['S7','L7','L13'];methods=methods[i%3:]+methods[:i%3]
                for variant in methods:
                    file=record_dir/f"{case['case_id']}_{variant}.json"
                    if not file.exists():
                        status('RUNNING',current=case['case_id'],variant=variant)
                        result=measure(pool,case,variant,Path(temp));atomic_json(file,clean(result))
                    done+=1
                if (i+1)%10==0:print(f'[offline] {i+1}/{len(manifest["cases"])} snapshots',flush=True)
        status('COMPLETE');print(json.dumps(dict(status='COMPLETE',records=done,elapsed_s=time.time()-started)))
    except BaseException as exc:
        status('FAILED',error=repr(exc));raise


if __name__=='__main__':main()
