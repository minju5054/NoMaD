"""One serial TS0000 grid pass, excluded from training; execution-time diagnosis only."""
import argparse,json,resource,time,subprocess,tempfile
from pathlib import Path
import numpy as np
from .run import read,write,grid,method_record
from .report import OUT,HERE
from .planner import plan
from .runtime import Journal,SerialPool,stage,SOLVE_WATCHDOG_S
from .recent import ensure
from nomad_isaac.common import sha256_file

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    p=read(HERE/'protocol.json');m=read(OUT/'manifest.json');c=next(c for c in m['training'] if c['case_id']=='TS0000')
    before=json.loads(subprocess.check_output(['git','show','4916cbf:research/nomad_phase23/protocol.json'],text=True))
    for key in ('grid','policy','fixed','selection_rule','selection_order','warm_start'):assert p[key]==before[key],key
    rows=[];pool=SerialPool()
    with Journal(out) as journal:
        for i,weights in enumerate(grid(p)):
            name=f'U{i:02d}';journal.update('COMBINATION_START','TS0000',name);started=time.perf_counter();timing={}
            result=stage('SOLVE',SOLVE_WATCHDOG_S,lambda:plan(pool,c,weights,p['policy']),journal,timing)
            write(out/f'{name}_plan.json',result)  # Preserve even if postprocessing fails.
            record=method_record(c,name,result,p,journal);elapsed=time.perf_counter()-started
            row=dict(combination=name,weights=weights,wall_s=elapsed,solve_wall_s=timing['SOLVE'],**record['row']['execution_timing_s'],rollout_ticks=record['row']['rollout_ticks'],accepted=result['accepted'],path_length_m=float(np.linalg.norm(np.diff(result['path'],axis=0),axis=1).sum()) if result.get('path') is not None else 0.)
            rows.append(row);write(out/f'{name}_record.json',record);write(out/'timings.json',rows);journal.update('COMBINATION_DONE','TS0000',name,wall_s=elapsed)
            print(f'[serial] TS0000 {name} {elapsed:.4f}s',flush=True)
        # Saved-depth preprocessing calibration, no further graph/rollout calls.
        same=[x for x in m['training'] if x['run']==c['run']];journal.update('TIMESTAMP_REPLAY_CALIBRATION');started=time.perf_counter()
        with tempfile.TemporaryDirectory(prefix='phase23-replay-timing-') as temp:ensure(same,Path(temp))
        replay_s=time.perf_counter()-started
        updates=read_lines(Path(c['run'])/'depth/updates.jsonl');last=max(int(Path(x['snapshot_file']).stem.split('_')[-1]) for x in same if not Path(x['snapshot_file']).stem.endswith('initial'))
        replay_frames=sum(x['frame_id']<=last for x in updates)
        total_frames=0;run_count=0
        for run in sorted({x['run'] for x in m['evaluation'] if x['group']=='static'}):
            cases=[x for x in m['evaluation'] if x['run']==run];frames=[int(Path(x['snapshot_file']).stem.split('_')[-1]) for x in cases if not Path(x['snapshot_file']).stem.endswith('initial')]
            total_frames+=sum(x['frame_id']<=max(frames,default=-1) for x in read_lines(Path(run)/'depth/updates.jsonl'));run_count+=1
        n_u=len(m['training'])*len(grid(p))+len(m['evaluation']);n_baseline=len(m['evaluation'])+sum(x['group']=='sudden' for x in m['evaluation'])
        post=max(sum(r[k] for k in ('ROLLOUT','ORACLE','EXACT_CLEARANCE')) for r in rows)
        lengths=[np.linalg.norm(np.diff(np.asarray(x['samples_world']),axis=1),axis=2).sum(axis=1).max() for x in m['evaluation']]
        probe_length=max(np.median([r['path_length_m'] for r in rows if r['path_length_m']>0]) if any(r['path_length_m']>0 for r in rows) else 0.,.05)
        length_factor=max(3.,float(np.quantile(lengths,.95))/probe_length)
        components=dict(U_planning_s=n_u*max(.25,max(r['solve_wall_s'] for r in rows)),baseline_planning_allowance_s=n_baseline*2.2,
            postprocessing_s=(n_u+n_baseline)*post*length_factor,timestamp_replay_s=total_frames*replay_s/max(1,replay_frames),report_io_allowance_s=120.)
        estimate=1.25*sum(components.values())
        report=dict(excluded_from_training=True,mode='single process, same250ms algorithm budget; no timing/quality equivalence claim to4-process campaign',case_id='TS0000',combinations=8,one_pass=True,total_combinations_s=sum(r['wall_s'] for r in rows),
            rows=rows,replay_calibration=dict(wall_s=replay_s,frames=replay_frames,target_frames=total_frames,target_runs=run_count),
            estimate=dict(seconds=estimate,hours=estimate/3600,over_2h=estimate>7200,components=components,U_calls=n_u,baseline_calls=n_baseline,post_length_factor=length_factor,allowance_factor=1.25,
                limitation='Scheduling estimate from one case, not a worst-case guarantee. Serial U maximum, conservative baseline2.2s/call, observed worst postprocessing scaled by at least3 and input length p95, saved-depth frame calibration, plus25% allowance.'),
            peak_rss_kb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,manifest_sha256=sha256_file(OUT/'manifest.json'),source_sha256={str(f):sha256_file(f) for f in HERE.glob('*.py')})
        write(out/'summary.json',report);journal.update('COMPLETE');print(json.dumps(dict(serial_total_s=report['total_combinations_s'],estimate_hours=estimate/3600,over_2h=estimate>7200)),flush=True)

def read_lines(f):return [json.loads(line) for line in Path(f).read_text().splitlines() if line]
if __name__=='__main__':main()
