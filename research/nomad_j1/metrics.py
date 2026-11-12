"""Same J0 geometric outcome/checkpoint audit with EC braking and RTC checks."""
import inspect
import json
from pathlib import Path
import numpy as np
from nomad_j0 import metrics as frozen
from nomad_phase16.execution import stop_command
from .config import protocol,METHODS,bind

source=inspect.getsource(frozen.audit)
replacements=[("c['j0'] and c['j_method']==METHOD", "c['j1'] and c['j_method'] in METHODS"),
    ("c['timeout_sim_s']==90 and c['phase4c_method']=='GRAPH'", "c['timeout_sim_s'] in (30,90) and c['phase4c_method'] in ('GRAPH','CURV')"),
    ("'fallback.jsonl','exec_cert.jsonl'", "'fallback.jsonl'"),
    ("if row['valid'] and diag['stop_reason'] is None:", "if row['applied_command_source']=='EC_BRAKE':\n            expected=stop_command(previous)\n        elif row['valid'] and diag['stop_reason'] is None:"),
    (" and not row['j_execution']['EC']", "")]
for old,new in replacements:
    assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new)
ns=dict(frozen.audit.__globals__,METHODS=METHODS,stop_command=stop_command,
        checkpoint=bind(frozen.checkpoint,protocol=protocol))
exec(compile(source,__file__,'exec'),ns);base_audit=ns['audit']

def rtc_prefix_errors(metric,target):
    """Only the first d waypoints are hard-masked; H_old may be larger."""
    a=np.asarray(metric);desired=np.asarray(target['target_local_xy_m'],dtype=float).reshape(-1,2)
    d=int(target['d']);assert d==target['d'] and 0<=d<=len(desired)<=8
    assert a.shape==(8,8,2) and np.isfinite(a).all() and np.isfinite(desired).all()
    assert len(desired)==target['H_old']
    if d==0:return None  # N/A: no hard-masked points in this inference.
    return np.linalg.norm(a[:,:d]-desired[None,:d],axis=2)

def audit(run):
    run=Path(run);r=base_audit(run);c=json.loads((run/'scenario.json').read_text());m=c['j_method']
    assert c['timeout_sim_s']==(30 if c['seed_offset']==950000 else 90)
    checks=frozen.rows(run/'exec_cert.jsonl');ec=m in ('OURS','OURS-noGRAPH')
    assert (run/'exec_cert.jsonl').exists()==ec
    if not ec:assert not any(x['applied_command_source']=='EC_BRAKE' for x in frozen.rows(run/'controller.jsonl'))
    applied=[x for x in checks if x['event']=='PERIODIC_APPLY']
    assert all(0<=x['delay_ticks']<=4 and x['apply_tick']%8==0 for x in applied)
    r.update(ec_checks=sum(x['event']=='CHECK' for x in checks),ec_rejected=sum(x['event']=='CHECK' and not x['passed'] for x in checks),
             ec_periodic_brake_count=len(applied),inference_ms=[x['inference_ms'] for x in frozen.rows(run/'model/inference.jsonl')])
    if m=='NOMAD_RAW':
        for e in frozen.rows(run/'events.jsonl'):np.testing.assert_array_equal(e['chunk']['native_local_xy_m'],e['overnight_metric_samples'][0])
    if m not in ('OURS','OURS-noEC'):assert r['graph_calls']==0
    if m=='RTC-hard':
        from nomad_phase8.request import rtc_target
        from nomad_phase18.metrics import assert_target_equal
        requests=frozen.rows(run/'requests.jsonl');inference=frozen.rows(run/'model/inference.jsonl');prefix=[]
        for q,inf in zip(requests,inference):
            target=q['rtc_target'];assert inf['rtc_target']==target;assert_target_equal(rtc_target(q['rtc_snapshot']),target)
            with np.load(run/f"model/derived/{q['id']:04d}.npz") as z:a=z['metric']
            assert a.shape==(8,8,2)
            error=rtc_prefix_errors(a,target)
            if error is not None:
                assert error.max()<=1e-6;prefix.extend(error.ravel().tolist())
        r.update(rtc_inferences=len(inference),rtc_prefix_max_m=max(prefix) if prefix else None,
                 rtc_hard_prefix_point_count=len(prefix),rtc_prefix_validation='FIRST_D_ONLY',
                 rtc_prefix_na_reason=None if prefix else 'NO_HARD_MASKED_WAYPOINTS')
    return r
