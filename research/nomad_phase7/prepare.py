"""Freeze50 actual inputs and observed T_est before any new GPU inference."""
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.async_report import rows
from nomad_phase0.chunk_report import trace
from nomad_phase6.config import protocol as prior_protocol
from .rtc import target


def main():
    here=Path(__file__).parent;output=here/'offline_inputs.json'
    assert not output.exists() and not (here/'protocol.json').exists(),'Do not reselect/tune'
    base=prior_protocol();root=Path(base['reference_root']);sources=[];latencies=[];groups=[]
    for i in range(9,17):
        for method in ('CURV','GRAPH'):
            run=root/f'S0_{i:02d}_{method}'
            events=rows(run/'events.jsonl')
            latencies += [(e['application_monotonic_ns']-e['observation_monotonic_ns'])/1e9 for e in events]
            sources.append(str(run/'events.jsonl'))
    est=float(np.median(latencies))
    for i in range(9,17):
        for method in ('CURV','GRAPH'):
            run=root/f'S0_{i:02d}_{method}';apps=rows(run/'phase5_applications.jsonl');rec,poses=trace(run)
            requests=rows(run/'requests.jsonl');candidates=[]
            for q in requests:
                if not q['old_valid_at_observation']:continue
                before=[a for a in apps if a['monotonic_ns']<=q['pose_sample_monotonic_ns'] and a['world_xy'] is not None]
                if not before:continue
                old=before[-1];assert old['id']==q['old_id_at_observation']
                tick=round(q['observation_sim_s']*72);np.testing.assert_allclose(poses[tick],q['observation_pose'],atol=1e-12,rtol=0)
                t=target(old['world_xy'],q['observation_pose'],float(rec[tick]['v_m_s']),est)
                if t['d']<1:continue
                candidates.append(dict(run=str(run),id=q['id'],old_id=old['id'],old_application=old,target=t))
            assert len(candidates)>=4
            # First two groups4 each, remaining14 groups3 each=50; evenly spaced by input order.
            count=4 if len(groups)<2 else 3
            groups.append([candidates[j] for j in np.linspace(0,len(candidates)-1,count,dtype=int)])
    selected=[r for group in groups for r in group];assert len(selected)==50
    paths=set(sources)
    for r in selected:
        run=Path(r['run']);q=rows(run/'requests.jsonl')[r['id']]
        observations={x['observation_id']:x for x in rows(run/'observations.jsonl')}
        for n in ('requests.jsonl','observations.jsonl','agent_trajectory.csv','phase5_applications.jsonl','model/inference.jsonl','model/environment.json'):
            paths.add(str(run/n))
        for oid in q['history_observation_ids']:paths.add(str(run/observations[oid]['rgb_file']))
        for kind in ('raw','derived'):paths.add(str(run/f"model/{kind}/{r['id']:04d}.npz"))
    protocol={k:base[k] for k in ('scenario','scenario_sha256','topomap','topomap_manifest_sha256','topomap_nodes','checkpoint_sha256','protected_sha256','scope')}
    protocol.update(label='PHASE7_STATIC_BASELINES',base_commit='6d51e3f',indices=list(range(9,17)),minimum_valid=7,
        reference_root=str(root),phase6_root='/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase6_static_01',
        rtc_label='RTC-style (DDPM adaptation)',beta=5.,beta_source='https://arxiv.org/html/2506.07339v1#A1.SS4',
        T_est_s={'750':est},T_est_source='Pooled observation-to-application host monotonic delays, all Phase5 CURV+GRAPH D750 events index9..16 (reused Phase6 references)',
        rtc_guidance='10 steps, epsilon x0hat=(xt-sqrt(1-alpha)*epsilon)/sqrt(alpha), unclipped for VJP. E=sum((W*(Y-x0hat))^2); xt-=.5*min(beta*(1-alpha),alpha)*grad_xt(E); recompute epsilon at corrected xt; unchanged DDPM step incl clipping/RNG. Variance-preconditioned DDPM adaptation; not original flow ODE.',
        target_rule='Nearest XYPath projection of actual OLD applied path at observation pose A; retain later original waypoints only (no resampling or origin waypoint); transform to A; difference from A origin, divide metric scale .05, normalize [-2.5,-4]..[5,4]. d counts suffix arclength<=v_now*T_est. No intrinsic waypoint timestamps.',
        offline_selection='50 deterministic inputs from16 Phase5 CURV/GRAPH D750 runs, observation OLD valid and d>=1. Equally spaced in request order, first2 groups4 each, other14 groups3. Selection uses no FRESH outputs or outcomes.',
        offline_gate='off maximum normalized/metric error <=1e-6 AND on sample0 frozen-prefix pointwise Euclidean error pooled median <=.01m; all50 finite required. Also report8-sample frozen error, overlap pointwise RMSE and actual timing.',
        seed_rule='101+10000*index+2*request_id; DDPM+1',execution_order='index9..16 then SELECT D750, CURV D625, GRAPH D625, optionally RTC D750, RTC+GRAPH D750; serial no retries',
        timeout_sim_s=90,alpha='inf',execution_v_max_m_s=.3,metric_scaling_m=.05,
        readiness_results='research/results/phase7_offline/summary.json',results='research/results/phase7',report='docs/PHASE7_RESULTS.md',
        output_root='artifacts/isaac6/phase7_static_01',technical_policy='Any involved method with <7 valid runs => INCONCLUSIVE. No failed goal time imputation; frozen Phase5/6 original reports preserved.')
    write_json(here/'protocol.json',protocol)
    write_json(output,dict(inputs=selected,T_est_samples=len(latencies),input_sha256={n:sha256_file(Path(n)) for n in sorted(paths)}))
    print(f'Frozen inputs50; T_est D750={est:.9f}s ({len(latencies)} actual switches)')


if __name__=='__main__':main()
