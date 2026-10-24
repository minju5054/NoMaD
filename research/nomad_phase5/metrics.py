"""Reuse Phase4c RGB, timing, command/pose and clearance audit; add path diagnostics."""
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import sha256_file
from nomad_isaac.async_report import rows,stats
from nomad_phase0.chunk_report import trace
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase4c.metrics import audit as previous_audit
from .config import protocol,base_method
from .rigid import rigid_entry


def circling(poses):
    yaw=np.abs((np.diff(poses[:,2])+np.pi)%(2*np.pi)-np.pi);total=np.cumsum(yaw)
    hit=np.flatnonzero(total>=2*np.pi)
    return dict(cumulative_abs_heading_rad=float(total[-1]) if len(total) else 0.,exists=bool(len(hit)),
                first_prefix_end_tick=int(hit[0]+1) if len(hit) else None,
                first_prefix_end_sim_s=float((hit[0]+1)/72) if len(hit) else None)


def audit(run,run_id,offset,delay):
    run=Path(run);c=json.loads((run/'summary.json').read_text())['scenario'];method=c['phase5_method']
    prov=json.loads((run/'provenance.json').read_text())
    assert prov['phase5_method']==method and c['phase4c_method']==base_method(method) and c['plant_alpha']=='inf'
    assert 9<=int(run_id[-2:])<=16 and offset==10000*int(run_id[-2:])
    assert json.loads((run/'phase5_protocol.json').read_text())==protocol()
    switched_paths={}
    def switch_xy(raw,b,event):
        xy=raw
        if method=='RIGID-ENTRY':
            logged=event['phase5_rigid']
            try:
                xy,detail=rigid_entry(raw,b)
            except ValueError as e:
                assert logged['status']=='INITIALIZATION_REJECTED' and logged['error']==str(e)
                xy=raw
            else:
                assert logged['status']=='APPLIED'
                np.testing.assert_allclose(xy,logged['applied_world_xy'],atol=1e-12,rtol=0)
                assert abs(detail['edit_rms_m']-logged['edit_rms_m'])<1e-12
        switched_paths[event['id']]=xy
        return xy
    r=previous_audit(run,run_id,offset,delay,switch_world_xy=switch_xy)
    records,poses=trace(run);control=rows(run/'controller.jsonl');events=rows(run/'events.jsonl')
    logs=rows(run/'stage2_graph.jsonl');apps=rows(run/'phase5_applications.jsonl')
    accepted={x['applied_tick']:x for x in logs if x['event']=='RESULT' and x['disposition']=='ACCEPTED'}
    switches={round(e['application_sim_s']*72):e for e in events}
    assert {a['tick'] for a in apps}==set(switches)|set(accepted) and len(apps)==len(switches)+len(accepted)
    flags=protocol()['graph_flags'].get(method)
    for log in logs:
        assert log['phase5_method']==method and log['phase5_flags']==flags
        if log['event']=='RESULT' and 'solver' in log:
            sol=log['solver']
            if method.startswith('GRAPH-NO-'):
                assert sol['phase5_flags']==flags
                assert sol['certificate_scope']==('OBSTACLE_AND_CORRIDOR' if flags['obstacle_sdf'] else 'CORRIDOR_ONLY')
                if not flags['previous_prior']:assert not sol['previous_prior_applied'] and 'previous_corrected_xy' not in sol['factor_costs']
                if not flags['boundary_curvature']:assert sol['scaled_equality_error'] is None
    for a in apps:
        tick=a['tick'];ctrl=control[tick//8]
        np.testing.assert_allclose(a['pose'],poses[tick],atol=1e-12,rtol=0)
        xy=np.asarray(accepted[tick]['applied_world_xy']) if tick in accepted else switched_paths[a['id']]
        try:path=XYPath(xy)
        except ValueError:assert a['world_xy'] is None and a['staleness'] is None
        else:
            np.testing.assert_allclose(a['world_xy'],path.points,atol=1e-12,rtol=0)
            projected,_=path.project(poses[tick,:2]);assert abs(projected/path.s[-1]-a['staleness'])<1e-12
        expected_kind='GRAPH' if tick in accepted else 'RIGID' if method=='RIGID-ENTRY' and switches[tick]['phase5_rigid']['status']=='APPLIED' else 'RAW'
        assert a['kind']==expected_kind
        np.testing.assert_array_equal(a['after_vw'],[ctrl['commanded_v_m_s'],ctrl['commanded_w_rad_s']])
        before=[control[tick//8-1]['commanded_v_m_s'],control[tick//8-1]['commanded_w_rad_s']] if tick else [0.,0.]
        np.testing.assert_array_equal(a['before_vw'],before);assert abs(a['abs_dw']-abs(a['after_vw'][1]-before[1]))<1e-12
    r.update(label=protocol()['label'],method=method,circling=circling(poses),control_count=len(control),
        applied_staleness_samples=[a['staleness'] for a in apps if a['staleness'] is not None],
        corrected_staleness_samples=[a['staleness'] for a in apps if a['kind']!='RAW' and a['staleness'] is not None],
        solver_wall_samples_s=[x['solver']['solver_wall_s'] for x in logs if x['event']=='RESULT' and 'solver' in x],
        executed_path_staleness=stats([a['staleness'] for a in apps if a['staleness'] is not None]),
        corrected_path_staleness=stats([a['staleness'] for a in apps if a['kind']!='RAW' and a['staleness'] is not None]),
        path_application_abs_dw=stats([a['abs_dw'] for a in apps]),
        rigid_applied=sum(a['kind']=='RIGID' for a in apps),
        rigid_rejected=sum(e.get('phase5_rigid',{}).get('status')=='INITIALIZATION_REJECTED' for e in events))
    for name in ('phase5_protocol.json','phase5_applications.jsonl'):r['input_log_sha256'][name]=sha256_file(run/name)
    return r
