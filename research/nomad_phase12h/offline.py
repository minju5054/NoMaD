"""Hermite-only saved-input checks; no navigation, inference or Graph solve."""
import json
import tempfile
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_isaac.async_report import rows
from nomad_isaac.async_core import WaypointExecution
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase12.methods import hermite_splice,TransitionState
from nomad_phase12.offline import cases,check_hermite
from nomad_phase12.execution import BaselineExecution
from .config import HERE,protocol,assert_frozen


def check_case(case):
    check_hermite(case)
    e=case['event'];xy,meta=hermite_splice(e['chunk']['world_xy_m'],e['agent_pose_at_switch'])
    assert xy.ndim==2 and xy.shape[1]==2 and len(xy)>=2 and np.isfinite(xy).all()
    assert type(meta['join_endpoint_clamped']) is bool
    json.dumps(meta,allow_nan=False);XYPath(xy)
    return dict(passed=True,points=len(xy),endpoint_clamped=meta['join_endpoint_clamped'])


def failed_input():
    run=Path(protocol()['failed_run']);received=rows(run/'received.jsonl');apps=rows(run/'phase6_applications.jsonl');controls=rows(run/'controller.jsonl')
    assert len(apps)==1 and apps[0]['id']==0 and apps[0]['tick']==136
    app=apps[0];q=next(r for r in received if r['id']==app['id']);control=next(r for r in controls if round(r['simulation_time_s']*72)==app['tick'])
    event={**q,'agent_pose_at_switch':app['pose']}
    return run,dict(event=event),q,app,control


def check_failed_input():
    run,case,q,app,control=failed_input();out=check_case(case)
    path,meta=hermite_splice(q['chunk']['world_xy_m'],app['pose'])
    np.testing.assert_allclose(path,app['world_xy'],atol=1e-12,rtol=0)
    original=dict(meta,join_endpoint_clamped=np.bool_(meta['join_endpoint_clamped']))
    try:json.dumps(original)
    except TypeError:pass
    else:raise AssertionError('Original numpy bool failure was not reproduced')
    with tempfile.TemporaryDirectory() as tmp:
        config=json.loads((run/'scenario.json').read_text());engine=BaselineExecution(config,Path(tmp));core=WaypointExecution(app['pose'],72,9)
        try:
            core.receive(q,q['selected_waypoint_m']);engine.last_command=list(app['before_vw']);engine.plant.actual_w=app['before_vw'][1]
            refresh,switch=core.control(app['tick'],control['monotonic_ns']);assert switch is not None
            engine.apply(core,refresh,switch)
            json.dumps(refresh,allow_nan=False);json.dumps(switch,allow_nan=False)
            np.testing.assert_allclose([core.v,core.w],app['after_vw'],atol=1e-12,rtol=0)
            np.testing.assert_allclose(switch['phase12']['applied_initial_world_xy'],app['world_xy'],atol=1e-12,rtol=0)
        finally:engine.close()
    out.update(serialization='PASS',original_error_reproduced=True,command_replay='PASS',path_max_error_m=float(np.max(np.abs(path-app['world_xy']))))
    return out


def edge_cases():
    # Short path and B near/at its end: keep the pre-existing degenerate-stop rule.
    path=np.column_stack([np.linspace(0,.04,8),np.zeros(8)])
    out=[]
    for name,b in [('short',[0.,0.,0.]),('near_endpoint',[.039,0.,0.]),('past_endpoint',[.041,0.,0.])]:
        check_case(dict(event=dict(chunk=dict(world_xy_m=path),agent_pose_at_switch=b)))
        out.append(dict(name=name,passed=True))
    state=TransitionState('HERMITE-SPLICE');xy,meta=state.switch(np.repeat(path[None],8,axis=0),[.04,0.,0.],0,0,0)
    assert len(xy)==2 and np.isfinite(xy).all() and 'DEGENERATE_HERMITE' in meta['invalid_reason']
    json.dumps(meta,allow_nan=False)
    try:XYPath(xy)
    except ValueError:pass
    else:raise AssertionError('Coincident B=J must retain invalid-path stop, not invent heading')
    out.append(dict(name='coincident_endpoint',passed=True,semantics='existing explicit invalid-path stop; heading undefined, not a valid C1 splice'))
    return out


def main():
    assert_frozen();out=HERE/'offline_validation.json';assert not out.exists(),'Preserve prior check'
    selected,inputs=cases();fixed=json.loads((ROOT/'research/nomad_phase12/offline_cases_r2.json').read_text())
    assert [(c['key'],c['event']['id']) for c in selected]==[(r['run'],r['id']) for r in fixed['cases']]
    results=[]
    for c in selected:
        inputs[c['file']]=c['sha256']
        try:r=check_case(c)
        except Exception as exc:r=dict(passed=False,error=repr(exc))
        results.append(dict(run=c['key'],id=c['event']['id'],**r))
    try:failed=check_failed_input()
    except Exception as exc:failed=dict(passed=False,error=repr(exc))
    try:edges=edge_cases()
    except Exception as exc:edges=[dict(passed=False,error=repr(exc))]
    passed=all(r['passed'] for r in results+[failed]+edges)
    sources=[ROOT/'research/nomad_phase12/methods.py',ROOT/'research/nomad_phase12/execution.py',ROOT/'research/nomad_phase12/offline.py']+list(HERE.glob('*.py'))+[HERE/'protocol.json']
    out.write_text(json.dumps(dict(passed=passed,phase8_cases=len(results),failed_run_cases=1,cases=results,failed_actual_input=failed,edge_cases=edges,input_sha256=inputs,
        source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in sources},navigation=0,inference=0,graph_solves=0),indent=2)+'\n')
    print('Phase8 30 handoffs: '+('PASS' if all(r['passed'] for r in results) else 'FAIL')+'; index25 actual input + switch JSON: '+('PASS' if failed['passed'] else 'FAIL')+'; short/endpoint checks: '+('PASS' if all(r['passed'] for r in edges) else 'FAIL'))
    if not passed:raise SystemExit(1)

if __name__=='__main__':main()
