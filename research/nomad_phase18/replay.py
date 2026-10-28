"""One actual Phase12 RTC-hard inference input; no navigation or tuning."""
import hashlib,json,subprocess,time
from pathlib import Path
import numpy as np
from PIL import Image
from nomad_isaac.common import ROOT,sha256_file


def main():
    import torch
    from nomad_preflight.native import load_checked
    from nomad_phase8.inference import RTCPolicy
    from nomad_phase8.request import rtc_target
    from .config import verify_sources,protocol
    verify_sources();p=protocol();choice=p['rtc_replay']
    run=Path(choice['run']);identifier=choice['id'];out=ROOT/'research/results/phase18_preflight'
    out.mkdir(parents=True,exist_ok=True);dest=out/'rtc_replay.json';assert not dest.exists(),'No replay retry/overwrite'
    def rows(file):return [json.loads(x) for x in file.read_text().splitlines() if x]
    q=next(r for r in rows(run/'requests.jsonl') if r['id']==identifier)
    inf=next(r for r in rows(run/'model/inference.jsonl') if r['id']==identifier)
    observations={r['observation_id']:r for r in rows(run/'observations.jsonl')}
    history=[Image.open(run/observations[i]['rgb_file']).convert('RGB') for i in q['history_observation_ids']]
    assert hashlib.sha256(np.stack(history).tobytes()).hexdigest()==inf['history_sha256']
    assert rtc_target(q['rtc_snapshot'])==q['rtc_target']
    cfg=json.loads((run/'scenario.json').read_text());policy=RTCPolicy(cfg['topomap_manifest'])
    policy.closest_node=inf['topomap']['previous_closest_node'];policy.previous_subgoal=inf['topomap']['previous_subgoal_id']
    device=torch.device('cuda:0');assert torch.cuda.is_available()
    model,_=load_checked(ROOT.parent/'artifacts/checkpoints/nomad.pth',device)
    noise=torch.randn((8,8,2),device=device,generator=torch.Generator(device=device).manual_seed(q['seed']))
    start=time.perf_counter()
    result,top=policy.infer(model,history,noise,q['seed']+1,rtc_target=q['rtc_target'],hard=True)
    torch.cuda.synchronize();elapsed=time.perf_counter()-start
    with np.load(run/f'model/raw/{identifier:04d}.npz') as raw,np.load(run/f'model/derived/{identifier:04d}.npz') as old:
        np.testing.assert_array_equal(noise.cpu().numpy(),raw['initial_noise'])
        errors={'normalized_diffusion':float(np.max(np.abs(result['normalized_diffusion'].cpu().numpy()-raw['normalized_diffusion'])))}
        for key in ('cumulative','metric','selected_waypoint'):
            errors[key]=float(np.max(np.abs(result[key].cpu().numpy()-old[key])))
    passed=all(e<=1e-6 for e in errors.values()) and top['selected_subgoal_id']==inf['topomap']['selected_subgoal_id']
    record=dict(passed=passed,run=str(run),id=identifier,seed=q['seed'],ddpm_seed=q['seed']+1,d=q['rtc_target']['d'],
        errors=errors,wall_s=elapsed,subgoal_match=top['selected_subgoal_id']==inf['topomap']['selected_subgoal_id'],
        source_git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        protocol_sha256=sha256_file(Path(__file__).with_name('protocol.json')),scope='one stored input inference replay; no navigation')
    with dest.open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    print(f"RTC saved-input replay {'PASS' if passed else 'FAIL'}: id={identifier}, d={record['d']}, max error={max(errors.values()):.3g}")
    if not passed:raise RuntimeError('RTC replay mismatch; preserve result, no retuning')


if __name__=='__main__':main()
