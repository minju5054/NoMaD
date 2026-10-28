"""Unchanged Phase17 audit plus RTC-generation/selection provenance checks."""
import json
from pathlib import Path
import numpy as np
import nomad_phase17.metrics as base
from nomad_phase8.request import rtc_target
from .config import METHODS,RTC

def assert_target_equal(a,b):
    """Discrete RTC choices exact; only float arithmetic permits roundoff."""
    assert a.keys()==b.keys()
    floating=('Y','W','target_local_xy_m','projected_arclength_m','v_now','T_est_s','frozen_distance_m')
    for key in a:
        if key in floating:np.testing.assert_allclose(a[key],b[key],rtol=0,atol=1e-12)
        else:assert a[key]==b[key],key

def audit(run):
    # The parent audit's SAFE membership affects only posthoc diagnostics, not
    # control. Extend it locally for the new RTC name without editing its source.
    old=base.SAFE
    try:
        base.SAFE=METHODS
        result=base.audit(run)
    finally:base.SAFE=old
    run=Path(run);config=json.loads((run/'scenario.json').read_text())
    requests=base.rows(run/'requests.jsonl');inference=base.rows(run/'model/inference.jsonl')
    result.update(rtc_d0_count=None,rtc_prefix_error_m=None,rtc_inference_count=None,
        inference_samples_ms=[x['inference_ms'] for x in inference],
        graph_solve_samples_s=[x['solver']['solver_wall_s'] for x in base.rows(run/'stage2_graph.jsonl') if x['event']=='RESULT' and 'solver' in x])
    if config['phase15b_method']!=RTC:return result
    errors=[];d0=empty=zero_speed=0
    for q,inf in zip(requests,inference):
        target=q['rtc_target'];assert inf['rtc_target']==target
        reproduced=rtc_target(q['rtc_snapshot']);assert_target_equal(reproduced,target)
        d=target['d'];d0+=d==0;empty+=target['H_old']==0
        zero_speed+=d==0 and q['rtc_snapshot'].get('actual_vw',[0,0])[0]==0
        with np.load(run/f"model/derived/{q['id']:04d}.npz") as z:metric=z['metric']
        assert metric.shape==(8,8,2)
        if d:
            e=np.linalg.norm(metric[:,:d]-np.array(target['target_local_xy_m'])[None,:d],axis=2)
            assert e.max()<=1e-6
            errors.extend(e.ravel().tolist())
    for event in base.rows(run/'events.jsonl'):
        with np.load(run/f"model/derived/{event['id']:04d}.npz") as z:
            np.testing.assert_array_equal(z['metric'],event['overnight_metric_samples'])
    result.update(rtc_d0_count=int(d0),rtc_empty_old_count=int(empty),rtc_zero_speed_d0_count=int(zero_speed),
        rtc_inference_count=len(inference),rtc_prefix_error_m=base.stats(errors),
        rtc_prefix_error_max_m=float(max(errors)) if errors else None,
        rtc_label='RTC hard-masking ablation (DDPM adaptation)',
        rtc_generation_sha256=base.sha256_file(Path(__file__).parents[1]/'nomad_phase8/rtc_hard.py'))
    return result
