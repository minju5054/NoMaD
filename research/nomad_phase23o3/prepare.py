"""Register the unchanged training inputs and U3 grid before any new solve."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase23o2.inputs import read,write
from .run import definition_hash
from .report import HERE,OUT,DEFINITION

def prepare():
    assert not (HERE/'protocol.json').exists()
    source=ROOT/'research/results/phase23o2';previous=read(source/'manifest.json');u2p=read(ROOT/'research/nomad_phase23o2/protocol.json');training=previous['training'];hashes={}
    grid=[dict(c=c,T_m=t) for c in u2p['grid']['c'] for t in u2p['grid']['T_m']];selected_key=f"U2_{grid.index(u2p['selected']):02d}"
    for c in training:
        file=source/'training'/(c['case_id']+'.json');c['u2_record']=str(file);hashes[str(file)]=sha256_file(file)
        hashes[c['snapshot_file']]=sha256_file(c['snapshot_file']);events=Path(c['run'])/'events.jsonl';hashes[str(events)]=sha256_file(events)
    for file in (source/'manifest.json',ROOT/'research/nomad_phase23o2/protocol.json',ROOT/'research/nomad_phase23/protocol.json'):hashes[str(file)]=sha256_file(file)
    sudden=[c for c in training if c['group']=='sudden'];levels=list(dict.fromkeys(c['scene'] for c in sudden));figures=[next(c['case_id'] for c in sudden if c['scene']==s) for s in levels[:2]]
    if len(figures)<2:figures=[c['case_id'] for c in sudden[:2]]
    run=sorted({c['run'] for c in training if c['scene']=='SLW'})[0];slw=sorted([c for c in training if c['run']==run],key=lambda c:c['tick']);figures.append(slw[len(slw)//2]['case_id'])
    m=dict(training=training,u2_selected_key=selected_key,figures=figures,input_hashes=hashes,evaluation_cases=0)
    write(OUT/'manifest.json',m)
    frozen=dict(u2p['frozen_sources']);frozen['research/nomad_phase23o2/protocol.json']=sha256_file(ROOT/'research/nomad_phase23o2/protocol.json')
    for f in HERE.glob('*.py'):frozen[str(f.relative_to(ROOT))]=sha256_file(f)
    p=dict(phase='23-O3',version='U3',base_commit='fe14fc6',status='REGISTERED',selected=None,selected_index=None,selection_evidence=None,
        grid=dict(w7=[.5,1.,2.],T_m=[.5,1.,2.]),c=1.,fixed_weights=u2p['fixed_weights'],solver=u2p['solver'],deadline_s=.5,pool_workers=4,
        f7=dict(length_m=1.2,sigma_m=.1,direction='weighted unit endpoint vectors of same U2 memory candidates in predicted B frame',minimum_endpoint_distance_m=.05,age_weight='exp(-age/T_m)',undefined_resultant='inactive, numerical norm<=1e-12; no substitute direction'),
        output_policy=dict(priority=['FEASIBLE','KINEMATIC_TOLERATED','STOP'],tolerated='lowest cost among last available pre-cutoff iterate per start',f2_minimum_slack=0.,speed_max=.33,omega_max=.44,dt_min=.045,dt_max=1.1,optimizer_constraints_unchanged=True,executor_limits_unchanged=True),
        selection_order=['p95<=.5','minimum rollout collisions','maximum sudden collision-free planned passage fraction','minimum STOP fraction','maximum static progress median','minimum p50','lower grid index exact ties'],
        all_over_time='preserve prior minimum-p95 diagnostic fallback; timing gate then fails',
        gate=dict(passage_ratio_to_C0=.8,collisions='all242U3<=C0',stop_fraction_max=.1,compute_p95_max_s=.5),
        comparison_scope=dict(training=242,static=216,sudden=26,U2='reuse frozen selected training outputs',C0='same242inputs frozen pipeline',C1='same26sudden inputs',evaluation_rerun=False),
        online_if_go=dict(scenes=['L2','SLW'],methods=['U3','C0','C1'],seeds=[125,126,127,128],smoke=dict(scene='L2',seed=95,each_method_once=True),main_execution='user only',prepared=False),
        manifest_sha256=sha256_file(OUT/'manifest.json'),frozen_sources=frozen)
    p['definition_sha256']=definition_hash(p);write(HERE/'protocol.json',p)
    (ROOT/'docs/PHASE23O3_UNIFIED.md').write_text('# Phase23-O3 — registered before training\n\n'+DEFINITION+'\n## Status\n\nNOT_EVALUATED.242training cases,9fixed combinations; no held-out evaluation rerun. Representatives fixed before results: '+str(figures)+'.\n')
    print(json.dumps(dict(training=len(training),u2_selected_key=selected_key,figures=figures)))
if __name__=='__main__':prepare()
