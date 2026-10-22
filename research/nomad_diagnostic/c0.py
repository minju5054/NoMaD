"""Paired conditioned/exploration replay, once per saved inference input; no navigation."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from PIL import Image
import torch
from nomad_isaac.common import sha256_file, write_json
from nomad_isaac.topomap import load_map
from nomad_isaac.topomap_inference import encode_candidates, diffuse_condition
from nomad_preflight.native import load_checked
from nomad_phase0.s0_batch import git_state, exclusive_batch
from .config import protocol
from .inference import masked_condition
from .data import scope,evaluate,aggregate,csv_write


def execute(out):
    p=protocol();state=git_state();assert not state['git_status']
    assert all(sha256_file(Path(f))==h for f,h in p['protected_sha256'].items())
    runs=sorted(Path(p['source_root']).glob('s2a_*_M0'));assert len(runs)==16
    out.mkdir(parents=True,exist_ok=False)
    write_json(out/'protocol.json',p);write_json(out/'execution.json',state)
    model,coverage=load_checked(Path(p['checkpoint']),torch.device('cuda:0'))
    images,hashes=load_map(Path(p['topomap']))
    records=[];runstats=[];input_hashes={};maxerrors={'metric':0.,'normalized':0.,'condition':0.}
    tol=p['C0_reproduction_tolerance']
    with (out/'observations.jsonl').open('x') as log:
        for run in runs:
            selected,captures,box,config=scope(run);before=len(records)
            save=out/run.name;save.mkdir()
            for f in ('summary.json','phase2_oracle.jsonl','model/inference.jsonl','observations.jsonl','agent_trajectory.csv'):
                input_hashes[str(run/f)]=sha256_file(run/f)
            for n in selected:
                identifier=n['id'];frames=[]
                for fid,digest in zip(n['history_observation_ids'],n['history_frame_sha256']):
                    f=run/f'observations/{fid:04d}.png';frame=Image.open(f).convert('RGB');frames.append(frame)
                    assert hashlib.sha256(np.array(frame).tobytes()).hexdigest()==digest
                    input_hashes[str(f)]=sha256_file(f)
                history=np.stack([np.array(f) for f in frames])
                assert hashlib.sha256(history.tobytes()).hexdigest()==n['history_sha256']
                rawfile=run/f'model/raw/{identifier:04d}.npz';derived=run/f'model/derived/{identifier:04d}.npz'
                input_hashes[str(rawfile)]=sha256_file(rawfile);input_hashes[str(derived)]=sha256_file(derived)
                with np.load(rawfile) as f:raw={k:f[k] for k in f.files}
                with np.load(derived) as f:saved=f['metric'].copy()
                noise=torch.randn((8,8,2),device='cuda',generator=torch.Generator(device='cuda').manual_seed(n['seed']))
                np.testing.assert_array_equal(noise.cpu().numpy(),raw['initial_noise'])
                t=n['topomap'];a,b=t['candidate_start'],t['candidate_end_inclusive'];j=t['selected_subgoal_id']-a
                assert hashes[t['selected_subgoal_id']]['rgb_sha256']==n['goal_sha256']
                cond,dist,obs,goals=encode_candidates(model,frames,images[a:b+1]);selected_cond=cond[j:j+1]
                start=time.monotonic()
                result=diffuse_condition(model,selected_cond,noise,n['ddpm_seed']);torch.cuda.synchronize()
                arrays={k:result[k].cpu().numpy() for k in ('normalized_diffusion','metric')}
                errors={'metric':float(abs(arrays['metric']-saved).max()),
                        'normalized':float(abs(arrays['normalized_diffusion']-raw['normalized_diffusion']).max()),
                        'condition':float(abs(selected_cond.detach().cpu().numpy()-raw['selected_condition']).max())}
                for k,v in errors.items():maxerrors[k]=max(maxerrors[k],v)
                with (save/f'{identifier:04d}_conditioned.npz').open('xb') as f:np.savez_compressed(f,**arrays)
                write_json(save/f'{identifier:04d}_reproduction.json',errors)
                assert errors['metric']<=tol['metric_max_abs_m'] and errors['normalized']<=tol['normalized_max_abs'] and errors['condition']<=tol['condition_max_abs'],f'Conditioned replay mismatch {run.name}/{identifier}: {errors}'
                conditioned=evaluate(arrays['metric'],n['observation_pose'],config,box)
                masked=masked_condition(model,obs,n['ddpm_seed'])
                result=diffuse_condition(model,masked,noise,n['ddpm_seed']);torch.cuda.synchronize()
                arrays={k:result[k].cpu().numpy() for k in ('normalized_diffusion','metric')}
                with (save/f'{identifier:04d}_masked.npz').open('xb') as f:np.savez_compressed(f,**arrays)
                row={'run':run.name,'id':identifier,'observation_id':n['observation_id'],'seed':n['seed'],'ddpm_seed':n['ddpm_seed'],
                     't_obs':n['observation_sim_s'],'observation_pose':n['observation_pose'],'history_sha256':n['history_sha256'],
                     'subgoal':t['selected_subgoal_id'],'closest_node':t['closest_node'],'reproduction':errors,
                     'conditioned':conditioned,'masked':evaluate(arrays['metric'],n['observation_pose'],config,box),
                     'paired_decode_wall_s':time.monotonic()-start}
                records.append(row);log.write(json.dumps(row)+'\n');log.flush()
            rr=records[before:]
            runstats.append({'run':run.name,'capture_count':len(captures),'busy_skips':sum(o.get('status')=='busy_history_only' for o in captures),
                             **{m:aggregate([r[m] for r in rr]) for m in ('conditioned','masked')}})
            print(json.dumps({'run':run.name,'observations':len(rr),'max_reproduction_error':maxerrors}),flush=True)
    # Verify every input remained unchanged.
    assert all(sha256_file(Path(f))==h for f,h in input_hashes.items())
    write_json(out/'input_hashes.json',input_hashes)
    summary={'status':'PASS','execution':state,'coverage':coverage,'torch':torch.__version__,'gpu':torch.cuda.get_device_name(),
             'max_reproduction_error':maxerrors,'runs':runstats,'total':{m:aggregate([r[m] for r in records]) for m in ('conditioned','masked')},
             'scope':p['C0_scope'],'raw_inputs_unchanged':True}
    write_json(out/'summary.json',summary)
    csv_write(out/'observations.csv',[{'run':r['run'],'id':r['id'],'mode':m,**{k:v for k,v in r[m].items() if k!='samples'}} for r in records for m in ('conditioned','masked')])
    print(json.dumps(summary['total']),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    with exclusive_batch():execute(args.output)
