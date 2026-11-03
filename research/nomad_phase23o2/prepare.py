"""Registration and scheduling estimate only: does not run any dataset solver."""
import json,hashlib,subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from .inputs import HERE,OUT,OLD,read,write
from .run import definition_hash
from .report import DEFINITION

def estimate(m):
    rows=[v['row'] for split in ('training','evaluation') for f in (OLD/split).glob('*.json') for v in read(f)['methods'].values()]
    post=np.array([sum(r['execution_timing_s'].values()) for r in rows]);post_allowance=2*float(np.quantile(post,.95))
    state=read(OLD/'state.json');actual=(state['ended_ns']-state['started_ns'])/1e9
    work=sum(r['compute_s']+sum(r['execution_timing_s'].values()) for r in rows);other=max(0.,actual-work)
    train=len(m['training'])*9;nu2=train+len(m['evaluation'])+len(m['examples_only']);static=sum(c['group']=='static' for c in m['evaluation'])
    seconds=1.25*(nu2*(.5+post_allowance)+static*(.5+post_allowance)+static*(1.+post_allowance)+other+60.)
    return dict(expected_minutes=seconds/60,over_2h=seconds>7200,old_actual_minutes=actual/60,training_solves=train,U2_total=nu2,new_U=static,new_C0=static,reused_seen_comparators=34*3+2*2,
        per_rollout_allowance_s=post_allowance,prior_non_solver_overhead_s=other,safety_multiplier=1.25,
        assumptions='Full500ms for every U/U2 solve,1s for every C0 call,2x prior postprocessing p95 per record, full prior non-solver overhead+60s and25% allowance. Prediction estimate, not a new dataset benchmark.')

def prepare():
    assert not (HERE/'protocol.json').exists(),'Preserve registration'
    m=read(OUT/'manifest.json');oldp=read(ROOT/'research/nomad_phase23/protocol.json');timing=estimate(m)
    sources=dict(oldp['source_sha256']);sources['research/nomad_phase23/protocol.json']=sha256_file(ROOT/'research/nomad_phase23/protocol.json')
    for f in HERE.glob('*.py'):sources[str(f.relative_to(ROOT))]=sha256_file(f)
    p=dict(phase='23-O2',version='U2',base_commit='cab5d87',configuration_registered=True,dataset_matches_unused_definition=True,status='REGISTERED',selected=None,selection_evidence=None,
        fixed_weights=dict(time=1.,goal=1.,curvature=.01),grid=dict(c=[1.,2.,4.],T_m=[.5,1.,2.]),
        solver=oldp['solver'],deadline_s=.5,pool_workers=4,initializations='8current candidates plus existing left/right when available; no history starts',
        acceleration_sigma=.05,hard_unchanged=['depth node/midpoint constraints','v<=.3','abs(omega)<=.4','dt[.05,1]'],
        memory=dict(window_s=2.,max_sets_including_current=8,age_time='actual post-delay receipt to snapshot dispatch',prior_sets='only saved native candidates strictly earlier than current receipt',
          current='retained, including actual input age',sigma='original current-eight dispersion times(1+age/T_m)',cost='sum pointwise Cauchy plus age/T_m',ASTAR_OLD='never a historical component; current supplementation retains original A* exclusion'),
        selection_order=oldp['selection_order'],decision='Same23-O group-level UNIFIED_READY/PARTIAL/NOT_READY; compare U2 vs C0',
        data=dict(training=242,heldout_static=524,seen_sudden=34,seen_static_examples_only=2,count_note=m['sampling']),
        prior_departure='maxfuture-node distance>=.30m; report mean/max and accepted-plan denominator',motion='Import frozen23-O prefix/anytime/executor unchanged',
        frozen_sources=sources,manifest_sha256=sha256_file(OUT/'manifest.json'),timing_estimate=timing)
    p['definition_sha256']=definition_hash(p);write(HERE/'protocol.json',p);write(OUT/'preparation.json',dict(status='HOLD_OVER_2H' if timing['over_2h'] else 'READY_FOR_USER_RUN',estimate=timing,new_training_records=0,new_evaluation_records=0))
    (ROOT/'docs/PHASE23O2_UNIFIED.md').write_text('# Phase23-O2 — preregistered preparation; NOT_EVALUATED\n\n'+DEFINITION+'\n## Execution preparation\n\nFixed U2 definitions registered; c/T_m are not selected. Training242×9; primary evaluation524HELDOUT_STATIC+34SEEN_SUDDEN, plus2illustration-only seen static cases. Scheduling estimate: '+str(round(timing['expected_minutes'],1))+'min. No new training/evaluation results or U2 verdict exist.\n')
    print(json.dumps(timing))
if __name__=='__main__':prepare()
