"""Frozen Phase43-P outcomes plus R2/R3 applications and post-detour errors."""
from pathlib import Path
import numpy as np
from nomad_phase43p.metrics import audit as frozen_audit
from nomad_phase32.report import lines


def error_stats(rows):
    e=[r['abs_error'] for r in rows]
    return dict(n=len(e),mae=float(np.mean(e)) if e else None,p50=float(np.median(e)) if e else None,
                p95=float(np.quantile(e,.95)) if e else None)


def detour_windows(events,node_errors,duration):
    applied={};windows=[];selected={'HANDOVER_10S':{},'INSTALL_10S':{}}
    def add(job,event,scope):
        start=float(event['simulation_time_s']);end=min(float(duration),start+10.)
        rows=[r for r in node_errors if start-1e-9<=r['observation_s']<=end+1e-9]
        for r in rows:selected[scope][r['inference_id']]=r
        windows.append(dict(job_id=job,scope=scope,start_s=start,end_s=end,available_s=max(0.,end-start),
                            truncated=end<start+10.-1e-9,reason=event.get('reason'),**error_stats(rows)))
    for e in events:
        if e['event']=='APPLIED':
            assert e['job_id'] not in applied
            applied[e['job_id']]=e;add(e['job_id'],e,'INSTALL_10S')
        elif e['event']=='END' and e['job_id'] in applied:
            applied.pop(e['job_id']);add(e['job_id'],e,'HANDOVER_10S')
    return dict(windows=windows,active_at_termination=len(applied),
        handover_10s=error_stats(list(selected['HANDOVER_10S'].values())),
        install_10s=error_stats(list(selected['INSTALL_10S'].values())))


def audit(root):
    root=Path(root);r=frozen_audit(root);r['method']='OURS+HMM'
    for e in r['node_errors']:e['cohort']='Phase45-P'
    detours=lines(root/'detour.jsonl');apps=[e for e in lines(root/'repair.jsonl') if e['event']=='PATH_APPLIED']
    r['r2_installations']=sum(e['kind']=='REPAIR' for e in apps)
    r['r3_installations']=sum(e['kind']=='DETOUR' for e in apps)
    assert r['r3_installations']==sum(e['event']=='APPLIED' for e in detours)
    r['post_detour']=detour_windows(detours,r['node_errors'],r['duration_s'])
    return r
