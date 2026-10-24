"""Full existing command/RGB/clearance audit, SELECT replay and run-level mechanisms."""
import json
from pathlib import Path
import numpy as np
from nomad_isaac.async_report import rows, stats
from nomad_isaac.common import sha256_file
from nomad_phase0.chunk_report import trace
from nomad_phase0.chunk_execution import tangent_at_projection
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase4c.metrics import audit as base_audit
from .config import protocol, base_method
from .selection import select


def audit(run, run_id, offset, delay):
    run=Path(run);c=json.loads((run/'summary.json').read_text())['scenario']
    method=c['phase6_method'];p=protocol();prov=json.loads((run/'provenance.json').read_text())
    assert prov['phase6_method']==method and c['phase4c_method']==base_method(method) and c['plant_alpha']=='inf'
    assert delay in ((.75,) if method=='SELECT' else tuple(p['delay_sweep']))
    assert json.loads((run/'phase6_protocol.json').read_text())==p
    assert int(run_id[-2:]) in p['indices'] and offset==10000*int(run_id[-2:])
    switched={};decisions=[]
    def switch_path(raw,b,e):
        xy=raw
        if method=='SELECT':
            with np.load(run/f"model/derived/{e['id']:04d}.npz") as f:
                samples=f['metric']
                np.testing.assert_array_equal(e['phase6_metric_samples'],samples)
                xy,detail=select(samples,e['observation_pose'],b,c)
            assert detail==e['phase6_selection']
            decisions.append(detail)
        switched[e['id']]=xy
        return xy
    r=base_audit(run,run_id,offset,delay,switch_world_xy=switch_path)
    _,poses=trace(run);control=rows(run/'controller.jsonl');events=rows(run/'events.jsonl')
    graph=rows(run/'stage2_graph.jsonl');apps=rows(run/'phase6_applications.jsonl')
    accepted={x['applied_tick']:x for x in graph if x['event']=='RESULT' and x['disposition']=='ACCEPTED'}
    switches={round(e['application_sim_s']*72):e for e in events}
    assert [a['tick'] for a in apps]==sorted(set(switches)|set(accepted))
    assert len(apps)==len(switches)+len(accepted)
    for a in apps:
        tick=a['tick'];ctrl=control[tick//8]
        np.testing.assert_allclose(a['pose'],poses[tick],atol=1e-12,rtol=0)
        xy=accepted[tick]['applied_world_xy'] if tick in accepted else switched[a['id']]
        try:path=XYPath(xy)
        except ValueError:assert a['world_xy'] is None and a['staleness'] is None
        else:
            np.testing.assert_allclose(a['world_xy'],path.points,atol=1e-12,rtol=0)
            s,d=path.project(poses[tick,:2])
            assert abs(s/path.s[-1]-a['staleness'])<1e-12 and abs(d-a['projection_distance_m'])<1e-12
        expected='GRAPH' if tick in accepted else 'SELECT' if method=='SELECT' else 'RAW'
        assert a['kind']==expected
        if expected=='SELECT':assert a['selected_sample']==switches[tick]['phase6_selection']['selected_sample']
        np.testing.assert_array_equal(a['after_vw'],[ctrl['commanded_v_m_s'],ctrl['commanded_w_rad_s']])
        before=[control[tick//8-1][k] for k in ('commanded_v_m_s','commanded_w_rad_s')] if tick else [0.,0.]
        np.testing.assert_array_equal(a['before_vw'],before)
    r.update(method=method,label=p['label'],selection=dict(switches=len(decisions),
        replacements=sum(x['selected_sample']!=0 for x in decisions),all_unsafe=sum(x['all_unsafe'] for x in decisions)))
    for n in ('phase6_protocol.json','phase6_applications.jsonl'):
        r['input_log_sha256'][n]=sha256_file(run/n)
    # Preserve raw sample evidence as well as command/timing hashes for report verification.
    for e in rows(run/'received.jsonl'):
        for kind in ('raw','derived'):
            n=f"model/{kind}/{e['id']:04d}.npz";r['input_log_sha256'][n]=sha256_file(run/n)
    return r


def application_measure(a, pose):
    try:path=XYPath(a['world_xy'])
    except (ValueError,TypeError):
        return dict(time_s=a['simulation_time_s'],kind=a['kind'],id=a['id'],heading_abs_rad=None,
                    cross_track_m=None,heading_invalid_reason='invalid_path')
    _,distance=path.project(pose[:2]);t=tangent_at_projection(path,pose[:2],.02)
    error=abs(float((pose[2]-t['heading_rad']+np.pi)%(2*np.pi)-np.pi)) if t['valid'] else None
    return dict(time_s=a['simulation_time_s'],kind=a['kind'],id=a['id'],heading_abs_rad=error,
                cross_track_m=distance,heading_invalid_reason=t['reason'])


def summarize_window(applications, curvature, poses, times, gaps, start, end):
    apps=[a for a in applications if start<=a['time_s']<=end]
    ks=[v for t,v in curvature if start<=t<=end]
    mask=(times>=start)&(times<=end)
    interval=np.maximum(0.,np.minimum(times[1:],end)-np.maximum(times[:-1],start))
    active=interval>0
    # All-wall footprint distance uses the same conservative swept lower bound as runtime.
    wall=[gaps[i+1]['corridor_lower_m'] for i in np.flatnonzero(active)]
    return dict(window_start_s=start,window_end_s=end,applications=len(apps),
        heading_invalid_count=sum(a['heading_abs_rad'] is None for a in apps),
        heading_abs_rad=stats([a['heading_abs_rad'] for a in apps if a['heading_abs_rad'] is not None]),
        cross_track_m=stats([a['cross_track_m'] for a in apps if a['cross_track_m'] is not None]),
        abs_kappa_m_inv=stats(ks),curvature_ticks=len(ks),
        kappa_over2_fraction=float(np.mean(np.asarray(ks)>2)) if ks else None,
        max_abs_y_m=float(np.abs(poses[mask,1]).max()) if np.any(mask) else None,
        time_abs_y_over1_s=float(np.sum(interval*(np.abs(poses[1:,1])>1.))),
        minimum_wall_footprint_clearance_lower_m=min(wall) if wall else None)


def mechanisms(run, success):
    run=Path(run);records,poses=trace(run);times=np.array([float(r['simulation_time_s']) for r in records])
    controls=rows(run/'controller.jsonl');gaps=rows(run/'clearance.jsonl')
    path=run/('phase6_applications.jsonl' if (run/'phase6_applications.jsonl').exists() else 'phase5_applications.jsonl')
    apps=rows(path);measured=[]
    for a in apps:
        tick=a['tick'];np.testing.assert_allclose(a['pose'],poses[tick],atol=1e-12,rtol=0)
        measured.append(application_measure(a,poses[tick]))
    curvature=[(c['simulation_time_s'],abs(c['stage2']['kappa_pp'])) for c in controls
               if c['pure_pursuit']['stop_reason'] is None and c['stage2']['kappa_pp'] is not None]
    whole=summarize_window(measured,curvature,poses,times,gaps,0.,float(times[-1]))
    last=None if success else summarize_window(measured,curvature,poses,times,gaps,max(0.,float(times[-1])-3.),float(times[-1]))
    return dict(full=whole,failure_last3s=last,applications=measured,
        input_sha256={n:sha256_file(run/n) for n in (path.name,'agent_trajectory.csv','controller.jsonl','clearance.jsonl')})
