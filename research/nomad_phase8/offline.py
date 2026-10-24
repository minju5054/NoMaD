"""One frozen50-input GPU validation of RTC-style (DDPM adaptation), no navigation."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import traceback
import numpy as np
from PIL import Image
import torch
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.async_report import rows,stats
from nomad_isaac.topomap import load_map,select_subgoal
from nomad_isaac.topomap_inference import encode_candidates
from nomad_preflight.native import load_checked
from .rtc_hard import diffuse


def main():
    here=Path(__file__).parent;p=json.loads((here/'protocol.json').read_text())
    selection=json.loads((here.parent/'nomad_phase7/offline_inputs.json').read_text())
    out=ROOT/'research/results/phase8_offline';raw=ROOT.parent/'artifacts/isaac6/phase8_rtc_hard_offline_01'
    assert not out.exists() and not raw.exists(),'Preserve earlier attempt; no restart'
    for name,h in selection['input_sha256'].items():assert sha256_file(Path(name))==h,name
    checkpoint=ROOT.parent/'artifacts/checkpoints/nomad.pth';assert sha256_file(checkpoint)==p['checkpoint_sha256']
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert torch.cuda.is_available(),'GPU unavailable: no validation started'
    out.mkdir();raw.mkdir();write_json(raw/'frozen.json',dict(git_sha=sha,protocol=p,selection=selection,source_sha256={str(f):sha256_file(f) for f in (here/'offline.py',here/'rtc_hard.py',here/'protocol.json',here.parent/'nomad_phase7/rtc.py')}))
    assert torch.cuda.is_available();device=torch.device('cuda:0');model,coverage=load_checked(checkpoint,device)
    images,_=load_map(ROOT.parent/p['topomap']);cache={};results=[];errors=[];fixed=[];all_fixed=[];raw_overlap=[];on_overlap=[]
    with (raw/'records.jsonl').open('x') as log:
        for number,item in enumerate(selection['inputs']):
            r=dict(number=number,run=item['run'],id=item['id'],d=item['target']['d'],H_old=item['target']['H_old'])
            try:
                run=Path(item['run'])
                if str(run) not in cache:
                    cache[str(run)]=(rows(run/'requests.jsonl'),rows(run/'model/inference.jsonl'),
                        {o['observation_id']:o for o in rows(run/'observations.jsonl')})
                requests,inference,obs=cache[str(run)];q=requests[item['id']];m=inference[item['id']];t=m['topomap']
                history=[Image.open(run/obs[i]['rgb_file']).convert('RGB') for i in q['history_observation_ids']]
                assert hashlib.sha256(np.stack([np.asarray(im) for im in history]).tobytes()).hexdigest()==m['history_sha256']
                noise=torch.randn((8,8,2),device=device,generator=torch.Generator(device=device).manual_seed(q['seed']))
                with np.load(run/f"model/raw/{item['id']:04d}.npz") as f:
                    np.testing.assert_array_equal(noise.cpu().numpy(),f['initial_noise']);stored=f['normalized_diffusion'].copy()
                    stored_cond=f['selected_condition'].copy()
                outputs={};times={};cond_errors=[];goal_match=[]
                for name,w in (('off',np.zeros(8)),('on',np.array(item['target']['W']))):
                    torch.cuda.synchronize();begin=time.perf_counter()
                    condition,distance,_,_=encode_candidates(model,history,images[t['candidate_start']:t['candidate_end_inclusive']+1])
                    closest,goal,ix=select_subgoal(distance.detach().flatten().cpu().numpy(),t['candidate_start'])
                    selected=condition[ix].unsqueeze(0)
                    goal_match.append(goal==t['selected_subgoal_id'] and closest==t['closest_node'])
                    result=diffuse(model,selected,noise,q['seed']+1,item['target']['Y'],w,item['target']['d'],p['beta'])
                    torch.cuda.synchronize();times[name]=(time.perf_counter()-begin)*1000
                    cond_errors.append(float(np.max(np.abs(selected.detach().cpu().numpy()-stored_cond))))
                    outputs[name]={k:v.detach().cpu().numpy() for k,v in result.items()}
                    del condition,distance,selected,result
                with np.load(run/f"model/derived/{item['id']:04d}.npz") as f:stored_metric=f['metric'].copy()
                maximum=max(float(np.max(np.abs(outputs['off']['normalized_diffusion']-stored))),
                            float(np.max(np.abs(outputs['off']['metric']-stored_metric))))
                d,h=item['target']['d'],item['target']['H_old'];target=np.asarray(item['target']['target_local_xy_m'])
                assert all(np.isfinite(v).all() for mode in outputs.values() for v in mode.values())
                fe=np.linalg.norm(outputs['on']['metric'][0,:d]-target[:d],axis=1)
                fixed.extend(fe.tolist());all_fixed.extend(np.linalg.norm(outputs['on']['metric'][:,:d]-target[None,:d],axis=2).ravel().tolist())
                rms={name:float(np.sqrt(np.mean(np.sum((outputs[name]['metric'][0,:h]-target)**2,axis=1)))) for name in outputs}
                raw_overlap.append(rms['off']);on_overlap.append(rms['on'])
                r.update(pass_off=maximum<=1e-6 and all(goal_match),finite=True,max_off_error=maximum,
                    selected_condition_max_error=max(cond_errors),subgoal_reproduced=all(goal_match),
                    fixed_error_median_m=float(np.median(fe)),fixed_point_errors_m=fe.tolist(),
                    overlap_rmse_m=rms,inference_ms=times)
                with (raw/f'{number:03d}.npz').open('xb') as f:
                    np.savez_compressed(f,**{name+'_'+k:v for name,data in outputs.items() for k,v in data.items()})
            except Exception as exc:
                r.update(pass_off=False,finite=False,error=repr(exc),traceback=traceback.format_exc());errors.append(number)
            results.append(r);log.write(json.dumps(r)+'\n');log.flush()
    finite=len(results)==50 and all(r['finite'] for r in results)
    off=finite and all(r['pass_off'] for r in results);median=float(np.median(fixed)) if fixed else None
    on=finite and median is not None and max(all_fixed)<=1e-6
    timings={name:stats([r['inference_ms'][name] for r in results if 'inference_ms' in r]) for name in ('off','on')}
    increase=stats([r['inference_ms']['on']-r['inference_ms']['off'] for r in results if 'inference_ms' in r])
    summary=dict(label=p['rtc_hard_label'],git_sha=sha,count=len(results),verdict='RTC_HARD_INCLUDED' if off and on else 'RTC_HARD_EXCLUDED',
        off_pass=off,prefix_pass=on,prefix_max_m=max(all_fixed) if all_fixed else None,finite_all50=finite,max_off_error=max((r.get('max_off_error',float('inf')) for r in results)),
        frozen_sample0_median_m=median,frozen_all_samples_median_m=float(np.median(all_fixed)) if all_fixed else None,
        overlap_rmse_raw_m=stats(raw_overlap),overlap_rmse_rtc_m=stats(on_overlap),
        overlap_improved_inputs=sum(b<a for a,b in zip(raw_overlap,on_overlap)),timing_ms=timings,timing_increase_ms=increase,
        beta=p['beta'],beta_source=p['beta_source'],T_est_s=p['T_est_s'],errors=errors,coverage=coverage,
        input_sha256=selection['input_sha256'],raw_output=str(raw))
    write_json(out/'summary.json',summary);write_json(here/'readiness.json',{'summary_sha256':sha256_file(out/'summary.json'),'included':bool(off and on)});write_json(out/'cases.json',results)
    print(f"RTC-hard: W0 max={summary['max_off_error']:.3g}; prefix max={summary['prefix_max_m']}m; latency median/p95={timings['on'].get('median')}/{timings['on'].get('p95')}ms; {summary['verdict']}")


if __name__=='__main__':main()
