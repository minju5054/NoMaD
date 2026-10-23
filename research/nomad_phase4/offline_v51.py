"""201 read-only saved jobs, one preregistered v5.1 solve each; no navigation."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import subprocess
import time
import traceback
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.async_report import rows,stats
from .graph_v51 import GraphV51,SignedDistanceField
from .v51_policy import candidates,expected_tick,decision

HERE=Path(__file__).parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'research/results/phase4_v51_offline')
    a=parser.parse_args();assert not a.output.exists(),'No repeat/overwrite'
    p=json.loads((HERE/'protocol_v51.json').read_text());gp=p['graph_parameters']
    assert not subprocess.check_output(['git','diff','HEAD','--name-only'],cwd=ROOT,text=True).strip(),'Commit tracked source first'
    status=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).splitlines()
    assert all(x=='?? research/results/phase4_pilot/' for x in status),status
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    source=Path(p['offline']['root']);datasets=[];hashes={}
    for name,h in p['protected_sha256'].items():assert sha256_file(ROOT/name)==h
    for name in ('graph_v5.py','graph_v51.py','v51_policy.py','offline_v51.py','protocol_v51.json'):
        hashes[str(HERE/name)]=sha256_file(HERE/name)
    for i in range(1,5):
        run=source/f'S0_{i:02d}_D750_GRAPH-v5'
        logs=rows(run/'stage2_graph.jsonl');jobs=[x for x in logs if x['event']=='SUBMIT']
        results={x['job_id']:x for x in logs if x['event']=='RESULT'}
        controls=rows(run/'controller.jsonl')
        with (run/'agent_trajectory.csv').open() as f:trace=list(csv.DictReader(f))
        poses=np.array([[float(x[k]) for k in ('x_m','y_m','yaw_rad')] for x in trace])
        for name in ('stage2_graph.jsonl','controller.jsonl','agent_trajectory.csv','scenario.json','provenance.json','received.jsonl'):
            hashes[str(run/name)]=sha256_file(run/name)
        assert len(jobs)==len(results)
        assert all(jobs[k]['dispatch_ns']<jobs[k+1]['dispatch_ns'] for k in range(len(jobs)-1))
        for j in jobs:
            tick=round(j['switch_sim_s']*72);ctrl=controls[tick//8]
            np.testing.assert_allclose(j['dispatch_pose'],poses[tick],atol=1e-12,rtol=0)
            np.testing.assert_allclose(j['previous_command'],[ctrl['applied_v_m_s'],ctrl['applied_w_rad_s']],atol=1e-12,rtol=0)
        datasets.append((run,jobs,results,controls,poses))
    assert sum(len(x[1]) for x in datasets)==201
    a.output.mkdir(parents=True,exist_ok=False)
    write_json(a.output/'frozen_inputs.json',{'git_sha':sha,'protocol':p,'input_sha256':hashes,
        'preexisting_untracked_preserved':status,'ids':{str(run):[j['id'] for j in jobs] for run,jobs,*_ in datasets}})
    records=[];baseline=[]
    with (a.output/'cases.jsonl').open('x') as f:
        for run,jobs,old_results,controls,poses in datasets:
            completed=[];scheduled_accepts=[];worker_free=0;field=None
            ctrl_ns=np.array([c['monotonic_ns'] for c in controls],dtype=np.int64)
            for job in jobs:
                old=old_results[job['job_id']];baseline.append(old)
                dispatch=job['dispatch_ns'];cand=candidates(job['dispatch_pose'],job['previous_command'])
                known=[duration for ready,duration in completed if ready<=dispatch]
                offset,estimate=expected_tick(known,(dispatch-job['switch_monotonic_ns'])/1e9)
                available=[r for when,r in scheduled_accepts if when<=dispatch]
                warm=available[-1] if available else None
                new={'run':str(run),'id':job['id'],'job_id':job['job_id'],'dispatch_ns':dispatch,
                    'dispatch_pose':job['dispatch_pose'],'command':job['previous_command'],
                    'boundary_candidates':cand,'estimated_tick_offset':offset,'estimated_processing_s':estimate,
                    'solver_boundary':cand[str(offset)],'warm_source_id':warm['id'] if warm else None,
                    'v5_disposition':old['disposition']}
                start=max(dispatch,worker_free);clock=time.perf_counter_ns();stage='initialization'
                try:
                    c=job['public_config']
                    if field is None:field=SignedDistanceField(c,gp['sdf_resolution_m'],gp['sdf_padding_m'])
                    g=GraphV51(job['world_xy'],cand[str(offset)],job['previous_command'],c,gp,field,
                        previous_xy=np.asarray(warm['poses'])[:,:2].tolist() if warm else None,warm_start=warm)
                    stage='solve';new['solve_started']=True
                    corrected,profile,solver=g.solve() # exactly one call; never restart
                    new.update(poses=corrected.tolist(),speed_profile=profile,solver=solver,accepted=solver['feasible'])
                except Exception as e:
                    new.update(accepted=False,initialization_rejected=stage=='initialization',error=repr(e),traceback=traceback.format_exc())
                processing=time.perf_counter_ns()-clock;end=start+processing;worker_free=end
                ipc_ns=max(0,old['result_received_ns']-old['worker_end_ns']);ready=end+ipc_ns
                completed.append((ready,processing/1e9))
                new.update(worker_start_ns=start,worker_end_ns=end,result_received_ns=ready,
                    measured_processing_s=processing/1e9,reused_ipc_overhead_s=ipc_ns/1e9,queue_wait_s=(start-dispatch)/1e9)
                index=int(np.searchsorted(ctrl_ns,ready,side='left'))
                if index==len(controls):new.update(disposition='NO_RECORDED_APPLICATION',actual_tick_offset=None)
                else:
                    ctrl=controls[index];tick=round(ctrl['simulation_time_s']*72);pose=poses[tick]
                    n=(tick-round(job['switch_sim_s']*72))//8
                    status,stale,duration,detail=decision(new,ctrl['latest_received_id'],ctrl['valid'],pose,cand,n)
                    solver_error=float(np.linalg.norm(pose[:2]-np.asarray(new['solver_boundary'])[:2]))
                    new.update(disposition=status,stale_flag=stale,**detail,application_tick=tick,
                        application_monotonic_ns=ctrl['monotonic_ns'],actual_application_pose=pose.tolist(),
                        solver_boundary_error_m=solver_error,solver_boundary_over_3cm=solver_error>.03,
                        estimated_tick_matches_actual=n==offset)
                    if status=='ACCEPTED':scheduled_accepts.append((ctrl['monotonic_ns'],new))
                records.append(new);f.write(json.dumps(new)+'\n');f.flush()
    for name,h in hashes.items():assert sha256_file(Path(name))==h,'Input changed'
    def summary(rr,old=False):
        ss=[r['solver'] for r in rr if 'solver' in r]
        return {'attempts':201,'converged':sum(s['success'] for s in ss),'convergence_fraction':sum(s['success'] for s in ss)/201,
            'accepted':sum(r['disposition']=='ACCEPTED' for r in rr),'acceptance_fraction':sum(r['disposition']=='ACCEPTED' for r in rr)/201,
            'solver_time_s':stats([s['solver_wall_s'] for s in ss]),'dispositions':dict(Counter(r['disposition'] for r in rr)),
            'timing_scope':'recorded actual v5' if old else 'new single-pass CPU measurement mapped onto saved v5 clock/poses'}
    old,new=summary(baseline,True),summary(records)
    verdict='READY_FOR_PILOT' if new['acceptance_fraction']>=.8 else 'STOP'
    result={'git_sha':sha,'v5':old,'v51':new,'verdict':verdict,'navigation_started':0,'inference_started':0,
        'initialization_rejections':sum(r.get('initialization_rejected',False) for r in records),
        'solve_calls':sum(r.get('solve_started',False) for r in records),
        'warm_starts':sum(r['warm_source_id'] is not None for r in records),
        'accepted_fixed_solver_boundary_over_3cm':sum(r.get('solver_boundary_over_3cm',False) and r['disposition']=='ACCEPTED' for r in records),
        'scope':p['offline']['scope'],'boundary_caveat':p['boundary_prediction']['fixed_boundary_caveat']}
    write_json(a.output/'summary.json',result)
    def line(label,s):
        t=s['solver_time_s'];return f"{label}: convergence {s['converged']}/201 ({s['convergence_fraction']:.1%}), acceptance {s['accepted']}/201 ({s['acceptance_fraction']:.1%}), solve median/p95 {t.get('median',float('nan'))*1000:.1f}/{t.get('p95',float('nan'))*1000:.1f}ms"
    text=line('v5',old)+'; '+line('v5.1',new)+'; '+verdict
    (a.output/'summary.txt').write_text(text+'\n');print(text)

if __name__=='__main__':main()
