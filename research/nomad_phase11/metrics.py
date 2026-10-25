"""Saved-log diagnostics; reuse original full command/pose/safety audit."""
import json
from pathlib import Path
import numpy as np
from nomad_isaac.async_report import rows
from nomad_isaac.common import sha256_file
from nomad_phase0.chunk_report import trace
from nomad_phase9.intent import intention
from nomad_phase10b.metrics import route_metrics,graph_calls as old_calls
from .graph import progress_metadata
from .config import protocol


def passage(times,poses,spawn,gaps,radius):
    if not spawn:return dict(safe_passage=None,passage_time_s=None,passage_side=None,spawned=False)
    box=spawn['obstacle'];rear=box['center_xy_m'][0]+box['size_xyz_m'][0]/2
    start=spawn['tick'];indices=np.flatnonzero((np.arange(len(poses))>=start)&(poses[:,0]-radius>rear))
    end=int(indices[0]) if len(indices) else None
    checked=gaps if end is None else gaps[:end-start+1]
    overlap=any(g['geometric_overlap'] for g in checked)
    side=None
    if end is not None:
        front=box['center_xy_m'][0]-box['size_xyz_m'][0]/2
        segment=poses[start:end+1];mask=(segment[:,0]>=front)&(segment[:,0]<=rear)
        ys=segment[mask,1]-box['center_xy_m'][1]
        side='+Y' if len(ys) and np.all(ys>0) else '-Y' if len(ys) and np.all(ys<0) else 'MIXED'
    return dict(safe_passage=end is not None and not overlap,passage_time_s=float(times[end]) if end is not None else None,
        passage_tick=end,passage_side=side,spawned=True,dynamic_overlap_before_passage=overlap,
        dynamic_minimum_clearance_m=min((g['lower_m'] for g in gaps),default=None),
        dynamic_minimum_until_passage_m=min((g['lower_m'] for g in checked),default=None))


def enrich(run,r):
    run=Path(run);c=json.loads((run/'scenario.json').read_text());rr,poses=trace(run)
    times=np.array([float(x['simulation_time_s']) for x in rr]);spawn=r.get('spawn')
    gap=rows(run/'dynamic/clearance.jsonl') if spawn else []
    if spawn:assert len(gap)==len(poses)-spawn['tick']
    r['passage']=passage(times,poses,spawn,gap,c['agent_radius_m'])
    r['route']=route_metrics(run,r['success'])
    requests={q['id']:q for q in rows(run/'requests.jsonl')};publication=r.get('oracle_publication')
    active={};counts={stage:dict(closest=0,subgoal=0,observations=0) for stage in ('intent_active','other')}
    for row in r['route']['topomap_series']:
        q=requests[row['id']];public={**c,'obstacles':list(c['obstacles'])}
        if publication and q['observation_monotonic_ns']>=publication['publication_monotonic_ns']:
            public['obstacles'].append(publication['obstacle'])
        enabled=intention(public,q['observation_pose']) is not None
        stage='intent_active' if enabled else 'other';active[row['id']]=stage;row['intent_stage']=stage
        counts[stage]['observations']+=1
    for a,b in zip(r['route']['topomap_series'],r['route']['topomap_series'][1:]):
        counts[active[b['id']]]['closest']+=int(b['closest_node']<a['closest_node'])
        counts[active[b['id']]]['subgoal']+=int(b['subgoal']<a['subgoal'])
    r['topomap_by_intent']=counts
    return r


def graph_calls(run,r,dataset):
    js=old_calls(run,r,dataset);data=rows(Path(run)/'stage2_graph.jsonl')
    submits={x['job_id']:x for x in data if x['event']=='SUBMIT'}
    results={x['job_id']:x for x in data if x['event']=='RESULT'}
    variant=r['method']=='GRAPH-v6.1'
    for j in js:
        q=submits[j['job_id']];result=results.get(j['job_id']);m=progress_metadata(q['world_xy'],q['boundary'])
        target=m['progress_target_m'] if variant else .25
        if variant:
            assert q['public_config'].get('phase11_v61') is True
            if result:
                for key,value in m.items():assert result[key]==value,(key,result.get(key),value)
                if 'solver' in result:
                    solver=result['solver']
                    for key,value in m.items():assert solver[key]==value
                    costs=solver['factor_costs']
                    assert ('endpoint_progress' in costs)==(target>0)
                    if target==0:j['progress_cost']=0.
                    endpoint=np.asarray(result['poses'])[-1,:2];b=np.asarray(q['boundary'])
                    projection=float((endpoint-b[:2])@np.array([np.cos(b[2]),np.sin(b[2])]))
                    expected=.5*(max(0.,target-projection)/.25)**2 if target>0 else 0.
                    assert np.isclose(j['progress_cost'],expected,rtol=1e-10,atol=1e-12)
        j.update(scene=r['scene'],p_native_m=m['p_native_m'],progress_target_m=target,progress_enabled=target>0)
    return js


def audit(run,run_id,offset,delay):
    run=Path(run);c=json.loads((run/'scenario.json').read_text());prov=json.loads((run/'provenance.json').read_text())
    assert c.get('phase11_v61') is True and prov.get('phase11_v61') is True
    assert c['overnight_phase']==9 and c['overnight_method']=='GRAPH-v6'
    assert json.loads((run/'phase11_protocol.json').read_text())==protocol()
    if c.get('phase10b_no_obstacle'):
        from nomad_phase10b.metrics import audit as original_audit
    else:
        from nomad_phase8.metrics import audit as original_audit
    r=original_audit(run,run_id,offset,delay)
    r.update(method='GRAPH-v6.1',index=int(run_id[-2:]),delay_s=delay,key=run.name,
             scene='noobs' if c.get('phase10b_no_obstacle') else 'sudden',phase11_v61=True)
    enrich(run,r);js=graph_calls(run,r,'11')
    assert len(js)==r['graph']['calls']
    assert sum(j['nonconverged'] for j in js)==r['graph']['independent_nonconverged']
    r['input_log_sha256']['phase11_protocol.json']=sha256_file(run/'phase11_protocol.json')
    return r
