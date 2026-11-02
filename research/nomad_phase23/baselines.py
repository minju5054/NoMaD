"""Comparator-only A* dependency; never imported by the unified graph or its worker."""
import json,time,tempfile
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase15b.depth import Snapshot,evaluate_samples
from nomad_phase15.evaluate import suffix
from nomad_phase20d.pool import evaluate_job as graph_job
from nomad_phase21.pool import evaluate_job as astar_job

def plan(pool,c,method,recent_file):
    field=Snapshot.load(c['snapshot_file']);started=time.monotonic();selected,detail=evaluate_samples(np.asarray(c['samples_world']),c['B'],field)
    if c.get('trigger')!='B' and not detail['all_unsafe']:
        return dict(accepted=True,path=selected.tolist(),disposition='SAFE_SAMPLE',compute_s=time.monotonic()-started,selection=detail)
    settings=json.loads((ROOT/'research/nomad_phase21/protocol.json').read_text())['astar']['selected'];stages=[]
    for kind in (['R3'] if c.get('trigger')=='B' else ['R2','R3']):
        with tempfile.TemporaryDirectory(prefix='phase23-baseline-') as tmp:
            job=dict(kind=kind,job_id=0,B=c['B'],u_ref=c['baseline_u_ref'],previous_vw=c['previous_vw'],samples_world=c['samples_world'],snapshot_file=recent_file,evaluation_tick=c['tick'],cache_file=str(Path(tmp)/'cache.npz'),dispatch_ns=time.monotonic_ns())
            r=graph_job(pool,job) if method=='C0' else astar_job(pool,job,settings['lambda'],settings['smoothing_iterations'])
        stages.append(r);index=r['selected_sample']
        if index is not None and r['dispatch_to_complete_s']<=1.:
            return dict(accepted=True,path=r['results'][index]['path'],disposition=kind,compute_s=time.monotonic()-started,stages=stages,selection=detail)
    old=c.get('baseline_old_path',c.get('old_path'))
    if old is not None:
        tail,length=suffix(old,c['B']);_,check=evaluate_samples(np.repeat(np.asarray(old)[None],8,axis=0),c['B'],field)
        if not check['all_unsafe'] and length>=.25:return dict(accepted=True,path=old,disposition='KEEP_ACTIVE',compute_s=time.monotonic()-started,stages=stages,selection=detail)
    return dict(accepted=False,path=None,disposition='STOP_WAIT_NO_FIXED_PATH',compute_s=time.monotonic()-started,stages=stages,selection=detail,recovery_replanning_not_simulated=True)
