"""Short read-only replay and one synthetic CPU solve; never imports Isaac."""
import csv
import json
from pathlib import Path
import tempfile
import time
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,local_to_world,write_json
from nomad_isaac.async_report import rows
from nomad_phase15.depth_sdf import intrinsics
from nomad_phase15.occupancy import make_field,ray_kernel
from nomad_phase15.occupancy_report import rng_for
from .config import HERE,protocol
from .depth import Snapshot,evaluate_samples
from .graph import DepthGraph
from .test_depth_pilot import synthetic

def saved_depth_check():
    root=Path(json.loads((ROOT/'research/results/phase15a/summary.json').read_text())['render_root'])
    plan=json.loads((root/'plan.json').read_text());source=next(r for r in plan['runs'] if r['method']=='FRESHEST')
    folder=root/source['key'];frames=json.loads((folder/'frames.json').read_text());run=Path(source['output'])
    events=rows(run/'events.jsonl');begin=next(i for i,e in enumerate(events) if e['agent_pose_at_switch'][0]>=1.)
    chosen=events[begin:begin+3];ids={e['id'] for e in chosen};reference={}
    csvpath=ROOT/'research/results/phase15a2/unknown_risk.csv'
    with csvpath.open() as stream:
        for row in csv.DictReader(stream):
            if row['run']==source['key'] and row['variant']=='V1' and row['noise']=='gaussian' and int(row['fresh_id']) in ids:
                reference[int(row['fresh_id']),int(row['sample'])]=float(row['depth_clearance_m'])
    field=make_field(protocol()['depth']['bounds_m'],'V1');ray_kernel();cursor=0;errors=[];selected=[]
    with np.load(folder/'depth.npz') as z:
        depth=z['depth'];transforms=z['camera_to_world']
        for event in chosen:
            while cursor<len(frames) and frames[cursor]['capture_end_monotonic_ns']<=event['application_monotonic_ns']:
                fr=frames[cursor];field.update(depth[cursor],intrinsics(source['scenario']['camera']),transforms[cursor],True,rng_for(source['key'],fr));cursor+=1
            with np.load(run/f"model/derived/{event['id']:04d}.npz") as pred:metric=pred['metric']
            worlds=np.array([local_to_world(x,event['observation_pose']) for x in metric]);snap=Snapshot(field,dict(frame_id=cursor-1))
            _,detail=evaluate_samples(worlds,event['agent_pose_at_switch'],snap)
            for candidate in detail['candidates']:errors.append(abs(candidate['clearance_m']-reference[event['id'],candidate['index']]))
            safe=[i for i in range(8) if reference[event['id'],i]>=.025]
            expected=min(safe,key=lambda i:(-detail['candidates'][i]['remaining_length_m'],i)) if safe else min(range(8),key=lambda i:(-reference[event['id'],i],i))
            assert expected==detail['selected_sample'];selected.append(expected)
    assert max(errors)==0.,max(errors)
    return dict(run=source['key'],fresh_ids=sorted(ids),samples=len(errors),depth_frames=cursor,max_clearance_error_m=max(errors),selected=selected,input_sha256={str(p):sha256_file(p) for p in (folder/'depth.npz',folder/'frames.json',csvpath)})

def synthetic_graph_check():
    field=synthetic();xy=np.column_stack([np.linspace(.08,.8,8),np.zeros(8)])
    graph=DepthGraph(xy,[0,0,0],[.2,0],field)
    before=field.exact_clearance(xy);poses,result=graph.solve();after=field.exact_clearance(poses[:,:2])
    assert after>before and after>=.025-1e-8 and result['feasible'],result
    return dict(solves=1,initial_clearance_m=before,corrected_clearance_m=after,solver=result)

def infrastructure_check():
    # One stored frame, no rendering. The prior snapshot remains unchanged.
    from .depth import DepthMapThread
    from .worker import Client
    root=Path(json.loads((ROOT/'research/results/phase15a/summary.json').read_text())['render_root'])
    source=json.loads((root/'plan.json').read_text())['runs'][0]
    frame=json.loads((root/source['key']/'frames.json').read_text())[0]
    with np.load(root/source['key']/'depth.npz') as z:depth=z['depth'][0]
    with tempfile.TemporaryDirectory() as tmp:
        out=Path(tmp);manager=DepthMapThread(out,source['scenario']['camera'],470000);old=manager.snapshot()
        manager.submit(depth,frame['pose'],frame['sim_s'],time.monotonic_ns(),0);manager.close();current=manager.snapshot()
        assert old.metadata['frame_id']==-1 and not old.occupied.any() and current.metadata['frame_id']==0
        client=Client(out,True);client.snapshot_file=current.metadata['file']
        job=dict(job_id=0,id=0,world_xy=[[.1+i*.1,0] for i in range(8)],boundary=[0,0,0],previous_command=[0,0],previous_commanded_vw=[0,0],observation_pose=[0,0,0],previous_xy=None,dispatch_ns=time.monotonic_ns(),switch_monotonic_ns=time.monotonic_ns(),switch_sim_s=0.,observation_sim_s=0.,distance_m=0.,public_config={'phase4c_method':'GRAPH','plant_alpha':'inf'})
        try:
            client.submit(job);deadline=time.monotonic()+5;response=None
            while response is None and time.monotonic()<deadline:
                time.sleep(.01);response=client.poll()
            assert response and response['initialization_rejected'] and 'speed is zero' in response['error']
        finally:client.close()
    return dict(depth_fifo=True,immutable_snapshot=True,worker_ipc=True,zero_speed_v4_rejection_preserved=True,navigation=0)


def source_hashes():
    files=list(HERE.glob('*.py'))+[HERE/'protocol.json']
    files += [ROOT/'research/nomad_isaac'/n for n in ('launch.py','simulator.py','async_runtime.py')]
    return {str(p.relative_to(ROOT)):sha256_file(p) for p in files}

def main():
    out=HERE/'offline_validation.json';assert not out.exists(),'Preserve verification evidence'
    result=dict(passed=True,infrastructure=infrastructure_check(),new_navigation=0,new_render=0,new_inference=0,saved_depth=saved_depth_check(),synthetic_graph=synthetic_graph_check(),source_sha256=source_hashes())
    write_json(out,result)
    print('V1 replay: PASS (24 samples, exact); synthetic depth Graph: PASS; navigation/render/inference: 0')
if __name__=='__main__':main()
