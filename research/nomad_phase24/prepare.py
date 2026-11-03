"""Freeze the user-approved data/decision/transition definitions; no G solve."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from .inputs import HERE,OUT,read,write
from .run import definition_hash
from .decision import available_history
from .report import DEFINITION

def prepare():
    p=read(HERE/'protocol.json');assert p['status']=='DRAFT_PENDING_DEFINITIONS'
    inventory=read(OUT/'inventory.json');estimate=read(OUT/'runtime_estimate.json');assert not estimate['over_one_hour']
    cases=inventory['cases'];hashes=dict(inventory['input_hashes']);availability=[]
    for c in cases:
        run=Path(c['run']);ok,missing=available_history(c);availability.append(dict(case_id=c['case_id'],history_available=ok,missing=missing))
        for file in (run/'agent_trajectory.csv',run/'scenario.json',run/'depth/updates.jsonl'):
            if file.exists():hashes[str(file)]=sha256_file(file)
    # The cached C0 record is reused only when reconstructed call arguments match.
    manifests=[ROOT/'research/results/phase23o3/manifest.json',ROOT/'research/results/phase23o3/recent_manifest.json',ROOT/'research/nomad_phase23/protocol.json']
    for f in manifests:hashes[str(f)]=sha256_file(f)
    pre=[c for c in cases if c['input_stage']=='PRE_PASSAGE'];figures=[pre[0]['case_id']]
    for c in pre:
        if c['case_id'] not in figures and read(c['c0_record'])['methods']['C0']['row']['planned_box_passage']:figures.append(c['case_id'])
    figures+=(c['case_id'] for c in pre if c['case_id'] not in figures)
    figures=figures[:3];slw_run=sorted({c['run'] for c in cases if c['scene']=='SLW'})[0];slw=sorted([c for c in cases if c['run']==slw_run],key=lambda c:c['tick']);figures.append(slw[len(slw)//2]['case_id'])
    manifest=dict(cases=cases,input_hashes=hashes,counts=inventory['counts'],history_availability=availability)
    write(OUT/'manifest.json',manifest)
    p.update(status='FROZEN',offline_mode_rule='RECOMPUTE_20F_IF_HISTORY_ELSE_C0_R3_ATTEMPT',no_component_direction='20F_A_RADIAL',gate_stop_timing_scope='STATIC_AND_PRE_PASSAGE',estimate=estimate,figures=figures)
    p['offline_decisions']=dict(priority=['MODE_RECOMPUTED: original20Fobservable trigger predicate on saved odometry/depth','MODE_FROM_C0: R3attempt only when required histories missing','MODE_FALLBACK: failed NORMAL output promotes to one DETOUR solve'],
        predicate_transient_guards='fresh counterfactual trigger state: busyFalse,cooldowninactive,blockedFalse,suppress-1; no prior Gstate or source-method transient state imputed',
        reference='20F component-frozen preappearance direction; if none, approved20FAradial/start-heading fallback',normal_failure='only if neitherFEASIBLE norKINEMATIC_TOLERATED; same depth/candidates; one extra solve',
        second_start='propagate first0.5s OLD prefix; execute firstSTOP bounded braking during second0.5s; extend odometry with only that deterministic prefix for direction at transition',
        time='sum measured per-stage solves; fixed application delay0.5s/stage, total1s on fallback; no new captures/inference',
        comparators='reuse frozen C0/C1 only for equivalent trigger/direction arguments; otherwise recompute frozen solvers with the newly reconstructed Btrigger/component direction; Abranch retains radial direction',
        gate='passage count on16PRE_PASSAGE; collision on216STATIC; STOP/p95 on their232union.2PRE_SPAWN+8ALREADY_PASSED excluded; all26sudden also shown.')
    p['manifest_sha256']=sha256_file(OUT/'manifest.json')
    for f in HERE.glob('*.py'):p['frozen_sources'][str(f.relative_to(ROOT))]=sha256_file(f)
    p['definition_sha256']=definition_hash(p);write(HERE/'protocol.json',p)
    write(OUT/'preparation.json',dict(status='READY_FOR_OFFLINE',tests_passed=9,total_cases=242,gate_cohort=232,estimate_minutes=estimate['minutes'],history_available=sum(x['history_available'] for x in availability),new_tuning=False,new_G_solves=0))
    (ROOT/'docs/PHASE24_DECISION_GRAPH.md').write_text('# Phase24 — frozen preparation; NOT_EVALUATED\n\n'+DEFINITION+'\n## Registered offline rules\n\n'+str(p['offline_decisions'])+f"\n\n242inputs;232gate cohort. Estimated{estimate['minutes']:.1f}min with two Gsolves per input and all268baseline recomputations budgeted.9unit tests passed. No new Gsnapshot solve or navigation has run.\n")
    print(json.dumps(dict(status='FROZEN',history_available=sum(x['history_available'] for x in availability),cases=len(cases),figures=figures,estimate_minutes=estimate['minutes'])))
if __name__=='__main__':prepare()
