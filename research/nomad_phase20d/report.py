"""Frozen descriptive preflight and new-seed pilot report; no model/solver execution."""
import argparse,json,subprocess,csv
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase17.report import table
from nomad_phase19r.evaluate import clean,csv_write
from .config import protocol,METHODS


def groups(records):
    result=[]
    for level in ('L2','L3'):
        for method in METHODS:
            rr=[r for r in records if r['scene']==level and r['method']==method];valid=[r for r in rr if r.get('technical_validation')=='PASS']
            def mean(k):
                x=[r[k] for r in valid if r.get(k) is not None];return float(np.mean(x)) if x else None
            def total(k):return sum(r.get(k,0) for r in valid)
            times=[j['pool_wall_s'] for r in valid for j in r.get('detour_job_timings',[])]
            result.append(dict(scene=level,method=method,planned=3,valid=len(valid),success=total('success'),collision=total('collision'),corridor=total('corridor'),stuck=total('stuck'),technical=len(rr)-len(valid),
                goal_time_s=mean('goal_time_s'),passed_box=total('passed_box'),box_passage_time_s=mean('box_passage_time_s'),all_unsafe=total('all_unsafe'),recovery_count=total('recovery_count'),stopped_fraction=mean('stopped_fraction'),
                trigger_A=sum(r.get('detour_triggers',{}).get('A',0) for r in valid),trigger_B=sum(r.get('detour_triggers',{}).get('B',0) for r in valid),detour_attempts=total('detour_attempts'),detour_applied=total('detour_applied'),detour_timeout=total('detour_timeout'),
                detour_execution_s=total('detour_execution_s'),detour_collision_count=total('detour_collision_count'),post_detour_progress_recovered=total('post_detour_progress_recovered'),post_detour_outcome_count=total('post_detour_outcome_count'),
                detour_then_box_pass_count=total('detour_then_box_pass_count'),detour_before_box_pass_count=total('detour_before_box_pass_count'),
                solve_median_s=float(np.median(times)) if times else None,solve_p95_s=float(np.quantile(times,.95)) if times else None,snapshot_max_age_s=max([r['snapshot_max_age_s'] for r in valid if r.get('snapshot_max_age_s') is not None],default=None)))
    return result


def decisions(summary):
    out=[]
    for level in ('L2','L3'):
        a,b=[next(r for r in summary if r['scene']==level and r['method']==m) for m in METHODS]
        label='INCONCLUSIVE' if min(a['valid'],b['valid'])<3 else 'DETOUR_HELPS' if b['success']>=a['success']+1 and b['detour_applied']>=2 else 'DETOUR_UNUSED' if b['detour_applied']<2 else 'DETOUR_NO_HELP'
        out.append(dict(scene=level,label=label,scope=protocol()['pilot_label'],M1_success=a['success'],M3_success=b['success'],detour_applied=b['detour_applied']))
    return out


def preflight_text():
    diag=json.loads((ROOT/'research/results/phase20d_diagnosis/diagnosis.json').read_text());gate=json.loads((ROOT/'research/results/phase20d_offline/decision.json').read_text())
    text='## Saved-log diagnosis / offline recheck\n\n'
    text+='Historical gap attribution is observational. CPU overlap is not proof of CPU causation; queue lengths and CPU utilization were not instrumented in the old logs. No old result is relabelled. The old FIFO preserved every recorded capture but synchronous compressed archival/hash delayed publication. The new immutable latest pointer is published before archival on a separate thread, for both methods. New logs record capture, processing, publication, archive, queue lengths and zero drops separately.\n\n'
    text+='Publication gaps and snapshot age differ: a regular stream can still deliver queued old frames. Saved22 runs yielded27 gaps≥0.5s (PUBLISH_BUG23, CPU_CONTENTION2, OTHER2), maxgap2.170357s and maxcapture-age14.430556s; two Phase20B runs lacked required technical artifacts and remain excluded from this diagnosis. Full gap intervals, states, repair overlap, evidence and per-run summaries are in phase20d_diagnosis CSVs.\n\n'
    rr=list(csv.DictReader((ROOT/'research/results/phase20d_diagnosis/runs.csv').read_text().splitlines()))
    by_method=[]
    for method in sorted({r['method'] for r in rr}):
        group=[r for r in rr if r['method']==method]
        by_method.append(dict(method=method,runs=len(group),maximum_snapshot_age_s=max(float(r['max_snapshot_age_s']) for r in group),maximum_publication_gap_s=max(float(r['max_publication_gap_s']) for r in group),mean_gap_time_fraction=float(np.mean([float(r['gap_full_time_fraction']) for r in group])),mean_excess_gap_fraction=float(np.mean([float(r['no_update_after_0p5_fraction']) for r in group]))))
    text+=table(by_method)+'\n\n'
    text+='Offline label: **사후 수정 후 재점검 2**. Exactly the same69 archived trigger events were solved once. Replayed occupancy/observed/SDF arrays were bitwise equal to20C shadow maps; only last-free evidence times were added. Old capture/publication eligibility is retained in this counterfactual, so it does not claim to predict the publication fix.\n\n'
    text+=table([{k:gate.get(k) for k in ('label','triggers','accepted_triggers','acceptance_fraction','accepted_initializations','accepted_path_oracle_penetrations','selected_path_oracle_penetrations','rollout_overlaps','rollout_count','seven_parallel_s','timeout_events')}])+'\n\n'
    text+='All accepted/selected penetrating paths are zero, so penetration-specific snapshot ages/recent-cell fractions have an empty denominator. Per-candidate recent-free/unknown fractions and snapshot ages are retained in offline CSVs. u_ref uses displacement from the run start (start heading within0.5m); the saved event list contains one negative-X u_ref. This recheck never gates the new-seed pilot.\n\n'
    text+='R3 far cells are blocked if occupied, unknown or last-free age>2.0s. The original first0.30m path-arclength exception stays unchanged. One EDT per (source frame,evaluation tick) is shared by all7 optimizations and exact certificates; the EDT provides an upper bound for pruning exact segment-to-cell calculations, not a sampled substitute. Current-time validation between updates checks the same blocked-cell definition with an exact local threshold test and no EDT rebuild.\n\n'
    return text


def render(records,out,doc,make_figures=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);summary=groups(records);verdict=decisions(summary)
    for name,value in [('runs',records),('decisions',verdict)]: (out/f'{name}.json').write_text(json.dumps(clean(value),indent=2,ensure_ascii=False)+'\n')
    (out/'summary.csv').unlink(missing_ok=True);csv_write(out/'summary.csv',summary)
    visualization=[]
    if make_figures:
        from .visualize import generate
        visualization=generate(records,out)
    text='# Phase 20-D — recent-depth detour / '+protocol()['pilot_label']+'\n\n'
    text+=f"Protocol SHA256 `{sha256_file(ROOT/'research/nomad_phase20d/protocol.json')}`. New seeds86–88; D750; L2/L3;12 sequential trials, no retries.\n\n"
    text+=preflight_text()
    text+='## New-seed pilot\n\n'+table(summary)+'\n\n## Frozen decisions\n\n'+table(verdict)+'\n\n'
    text+='DETOUR_HELPS requires ≥1 additional goal success and ≥2 actually applied detours; <2 applications is DETOUR_UNUSED. Otherwise DETOUR_NO_HELP. Missing/technical trials remain visible and make the interpreted comparison INCONCLUSIVE. Goal success, box passage and safety margin are separate.\n\n'
    text+='## Seed × level × method\n\n'+table(records,['scene','index','method','execution_git_sha','classification','goal_time_s','passed_box','box_passage_time_s','minimum_clearance_m','minimum_wall_clearance_m','all_unsafe','recovery_count','detour_triggers','detour_dispositions','detour_applied','detour_execution_s','detour_collision_count','seven_solve_s','snapshot_max_age_s'])+'\n\n'
    text+='## Technical failures\n\n'+table([r for r in records if r.get('technical_validation')!='PASS'],['scene','index','method','output','error'])+'\n\n'
    text+='R3 wait/execution defers new NoMaD path application while preserving all packets; the independent action ends at endpoint,6s or a failed current-depth check. R2/R3 share four CPU processes. The1s deadline includes serialization, EDT/cache preparation, scheduling and solving; late results are preserved but not applied. No oracle geometry is provided to the controller. Exact simulator pose is assumed (no odometry error).\n\n'
    text+='Detour outcomes are descriptive: box passage after an application is associated with that action, not attributed causally; first nondeferred FRESH progress recovery means selected endpoint projected on job u_ref≥0.2m. Missing outcomes are censored. Gray thick trajectory segments mark publication gaps≥0.5s, not proof of unsafe control. Orange dashed paths are actually applied detours; diamonds mark NO_PROGRESS.\n\n'
    text+='## Visualization availability\n\n'
    for case in visualization:
        if case['missing']:
            reason='; '.join(r['method']+': '+r['reason'] for r in case['missing'])
            action='All seed figures skipped (both runs unavailable)' if case['skipped'] else 'Unavailable panels display TECHNICAL_FAILURE (no data)'
            text+=f"- {case['scene']}/{case['index']}: {action}. {reason}\n"
    text+='\n'
    skipped={(r['scene'],r['index']) for r in visualization if r['skipped']}
    for level in ('L2','L3'):
        for i in (86,87,88):
            if (level,i) in skipped:continue
            for ext in ('png','gif'):text+=f'![{level}/{i}](../research/results/phase20d/drive_{level}_{i}.{ext})\n\n'
    text+='This is an exploratory pilot after repeated offline changes on the same saved data, not a confirmatory study. Old Phase20/20B outcomes are not reinterpreted.\n'
    doc.parent.mkdir(exist_ok=True);doc.write_text(text);return verdict


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--publish',action='store_true');a=ap.parse_args();root=a.run_root.resolve()
    plan=json.loads((root/'plan.json').read_text());assert len(plan['jobs'])==12
    records=[json.loads((root/'metrics'/f"main_{j['key']}.json").read_text()) for j in plan['jobs']]
    for r in records:
        f=Path(r['output'])/'provenance.json'
        if f.exists():r['execution_git_sha']=json.loads(f.read_text())['git_sha']
    out=ROOT/'research/results/phase20d';doc=ROOT/'docs/PHASE20D_RECENT.md';v=render(records,out,doc)
    if a.publish:
        assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
        subprocess.run(['git','add','--',str(out.relative_to(ROOT)),str(doc.relative_to(ROOT))],cwd=ROOT,check=True)
        media=[*out.glob('*.png'),*out.glob('*.gif')]
        if media:subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in media]],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase20D recent-depth pilot'],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
    print(json.dumps(v))
if __name__=='__main__':main()
