"""One preregistered 20-solve CPU check. No Isaac/NoMaD launch, no restart."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import traceback
import numpy as np
from nomad_isaac.common import ROOT, integrate_se2, sha256_file, write_json
from nomad_isaac.async_report import rows, stats
from nomad_phase0.chunk_execution import protocol as follower_protocol
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase3_stage2.execution import speed_command
from .config import protocol
from .graph_v5 import GraphV5, SignedDistanceField
from .execution import predict_boundary, command_policy


def short_replay(xy,boundary,v0,profile=None):
    follower=PurePursuit(xy,follower_protocol()['follower']);pose=np.array(boundary,dtype=float)
    before=float(v0);v=w=0.;distance=0.
    for tick in range(16):
        if tick%8==0:
            (v,w),diag=follower.control(pose)
            if not diag['endpoint_stop']:
                x,y=diag['target_local_x_m'],diag['target_local_y_m'];k=2*y/(x*x+y*y) if x*x+y*y>1e-24 else 0.
                if profile is None:(v,w),_=speed_command(k,before)
                else:(v,w),_=command_policy('GRAPH-v5',k,before,profile,follower.path.project(pose[:2])[0])
            before=v
        next_pose=integrate_se2(pose,v,w,1/72);distance+=float(np.linalg.norm(next_pose[:2]-pose[:2]));pose=next_pose
    return {'mean_speed_m_s':distance/(16/72),'distance_m':distance,'end_pose':pose.tolist()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'research/results/phase4_offline_preflight')
    a=parser.parse_args();assert not a.output.exists(),'No rerun/overwrite'
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'Commit code/protocol first'
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    root=ROOT.parent/'artifacts/isaac6/phase3_stage2_s0_01';p=protocol();gp=p['graph_parameters']
    selected=[];hashes={str(Path(__file__)):sha256_file(Path(__file__)),str(Path(__file__).with_name('protocol.json')):sha256_file(Path(__file__).with_name('protocol.json'))}
    for i in range(1,5):
        run=root/f'S0_{i:02d}_D750_GRAPH';logs=rows(run/'stage2_graph.jsonl');controls=rows(run/'controller.jsonl')
        jobs=[x for x in logs if x['event']=='SUBMIT'][:5];assert len(jobs)==5
        results={x['job_id']:x for x in logs if x['event']=='RESULT'}
        for file in ('stage2_graph.jsonl','controller.jsonl','provenance.json','scenario.json'):
            hashes[str(run/file)]=sha256_file(run/file)
        for job in jobs:
            tick=round(job['switch_sim_s']*72);control=controls[tick//8]
            actual=[control['applied_v_m_s'],control['applied_w_rad_s']]
            selected.append({'run':str(run),'job':job,'actual':actual,'v4_result':results.get(job['job_id'])})
    assert len(selected)==20
    a.output.mkdir(parents=True,exist_ok=False)
    write_json(a.output/'selection.json',{'git_sha':sha,'protocol':p,'input_sha256':hashes,
        'ids':[{'run':x['run'],'id':x['job']['id'],'job_id':x['job']['job_id']} for x in selected]})
    records=[];fields={}
    with (a.output/'cases.jsonl').open('x') as f:
        for item in selected:
            job=item['job'];c=job['public_config'];b=predict_boundary(job['boundary'],item['actual'])
            record={'run':item['run'],'id':job['id'],'B_app':b.tolist(),'actual_command':item['actual']}
            start=time.perf_counter()
            try:
                key=json.dumps(c['obstacles'],sort_keys=True)
                if key not in fields:fields[key]=SignedDistanceField(c,gp['sdf_resolution_m'],gp['sdf_padding_m'])
                graph=GraphV5(job['world_xy'],b,item['actual'],c,gp,fields[key],job.get('previous_xy'))
                poses,profile,solver=graph.solve() # exactly once; final iterate retained on failure
                record.update(poses=poses.tolist(),profile=profile,solver=solver)
                old=item['v4_result'];accepted=old is not None and old['disposition']=='ACCEPTED'
                xy=np.asarray(old['poses'])[:,:2] if accepted else np.asarray(job['world_xy'])
                record['v4_reference']='stored accepted correction' if accepted else 'stored RAW fallback'
                record['v4_replay']=short_replay(xy,b,item['actual'][0])
                record['v5_replay']=short_replay(poses[:,:2],b,item['actual'][0],profile)
                record['replay_scope']='offline fixed B_app16ticks; rejected v5 final iterates included, not applied actions'
            except Exception as e:record.update(error=repr(e),traceback=traceback.format_exc())
            record['total_wall_s']=time.perf_counter()-start;records.append(record)
            f.write(json.dumps(record)+'\n');f.flush()
    for name,h in hashes.items():assert sha256_file(Path(name))==h,'Input modified'
    solvers=[r['solver'] for r in records if 'solver' in r];paired=[r for r in records if 'v5_replay' in r]
    old_mean=float(np.mean([r['v4_replay']['mean_speed_m_s'] for r in paired])) if paired else None
    new_mean=float(np.mean([r['v5_replay']['mean_speed_m_s'] for r in paired])) if paired else None
    increase=100*(new_mean/old_mean-1) if old_mean else None
    summary={'git_sha':sha,'attempts':20,'solves_started':len(solvers),'converged':sum(s['success'] for s in solvers),
        'feasible':sum(s['feasible'] for s in solvers),'rejected_or_errors':20-sum(s['feasible'] for s in solvers),
        'solver_time_s':stats([s['solver_wall_s'] for s in solvers]),'paired_speed_cases':len(paired),
        'v4_mean_replay_speed_m_s':old_mean,'v5_mean_replay_speed_m_s':new_mean,'speed_increase_pct':increase,
        'speed_scope':p['offline']['speed_comparison'],'navigation_started':0,'inference_started':0}
    write_json(a.output/'summary.json',summary)
    timing=summary['solver_time_s']
    line=f"Offline20: converged {summary['converged']}/20, feasible {summary['feasible']}/20; solve median/p95 {timing.get('median',float('nan')):.4f}/{timing.get('p95',float('nan')):.4f}s; v4-relative16tick mean speed {increase:+.2f}% (all final iterates, including rejected diagnostics)." if increase is not None else 'Offline20: missing valid paired speed evidence; inspect saved errors.'
    (a.output/'summary.txt').write_text(line+'\n');print(line)

if __name__=='__main__':main()
