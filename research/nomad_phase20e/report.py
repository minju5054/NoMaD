"""Frozen L2 paired pilot report; no solver or navigation in reporting."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase17.report import table
from nomad_phase19r.evaluate import clean,csv_write
from nomad_phase20d.report import groups as previous_groups
from .config import protocol,METHODS


def groups(records):
    result=[r for r in previous_groups(records) if r['scene']=='L2']
    for row in result:
        rr=[r for r in records if r['method']==row['method'] and r.get('technical_validation')=='PASS'];row['planned']=6
        row.update(no_obstacle_ahead=sum(r.get('no_obstacle_ahead_count',0) for r in rr),detour_applied_after_passage=sum(r.get('detour_applied_after_passage',0) for r in rr),
            triggers_before_passage=sum(r.get('trigger_stages',{}).get('BEFORE_PASSAGE',0) for r in rr),triggers_after_passage=sum(r.get('trigger_stages',{}).get('AFTER_PASSAGE',0) for r in rr))
    return result


def paired(records):
    lookup={(r['index'],r['method']):r for r in records};out=[]
    for i in range(89,95):
        a,b=[lookup.get((i,m),{}) for m in METHODS];row=dict(index=i)
        for m,r in zip(('M1','M3'),(a,b)):
            valid=r.get('technical_validation')=='PASS'
            row.update({m+'_classification':r.get('classification','MISSING'),m+'_success':bool(valid and r.get('success')),m+'_passed_box':bool(valid and r.get('passed_box')),
                m+'_passage_s':r.get('box_passage_time_s') if valid and r.get('passed_box') else None,m+'_goal_s':r.get('goal_time_s') if valid and r.get('success') else None})
        row['passage_difference_s']=row['M3_passage_s']-row['M1_passage_s'] if row['M1_passage_s'] is not None and row['M3_passage_s'] is not None else None
        row['goal_difference_s']=row['M3_goal_s']-row['M1_goal_s'] if row['M1_goal_s'] is not None and row['M3_goal_s'] is not None else None
        out.append(row)
    return out


def decision(summary,pairs):
    a,b=[next(r for r in summary if r['method']==m) for m in METHODS];times=[r['passage_difference_s'] for r in pairs if r['passage_difference_s'] is not None];faster=sum(t<0 for t in times)
    if b['success']>=a['success']+2:label='DETOUR_HELPS'
    elif b['success']>=a['success'] and b['passed_box']>=a['passed_box'] and times and faster>len(times)/2:label='DETOUR_PASSES_FASTER'
    elif b['success']<=a['success']-2:label='DETOUR_WORSE'
    else:label='DETOUR_MIXED'
    gt=[r['goal_difference_s'] for r in pairs if r['goal_difference_s'] is not None]
    return dict(label=label,scope='파일럿',M1_success=a['success'],M3_success=b['success'],M1_passed_box=a['passed_box'],M3_passed_box=b['passed_box'],
        M1_valid=a['valid'],M3_valid=b['valid'],paired_passage_n=len(times),M3_passage_faster_seeds=faster,paired_goal_n=len(gt),
        goal_difference_mean_s=float(np.mean(gt)) if gt else None,goal_difference_median_s=float(np.median(gt)) if gt else None)


def offline_text():
    result=json.loads((ROOT/'research/results/phase20e_offline/summary.json').read_text());a=result['BEFORE_PASSAGE'];b=result['AFTER_PASSAGE']
    return f"Saved20D L2 trigger predicate check (no solve/navigation): before passage {a['retained']}/{a['original']} retained; after passage {b['retained']}/{b['original']} retained. Before spawn {result['before_spawn_retained']}/{result['before_spawn_original']}. Later motion is held unchanged, so these are not predicted online event counts. This check does not gate execution.\n\n"


def render(records,out,doc,make_figures=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);summary=groups(records);pairs=paired(records);v=decision(summary,pairs);visual=[]
    for name,value in [('runs',records),('decisions',v)]: (out/f'{name}.json').write_text(json.dumps(clean(value),indent=2,ensure_ascii=False)+'\n')
    for name,value in [('summary',summary),('paired',pairs)]:
        (out/f'{name}.csv').unlink(missing_ok=True);csv_write(out/f'{name}.csv',value)
    if make_figures:
        from .visualize import generate,passage_summary
        visual=generate(records,out);passage_summary(pairs,out)
    text='# Phase20E — obstacle-conditional NO_PROGRESS / 파일럿\n\n'
    text+=f"Protocol SHA256 `{sha256_file(ROOT/'research/nomad_phase20e/protocol.json')}`. L2 × M1/M3 × indices89–94;12 attempts; no retries or parameter changes.\n\n"
    text+=offline_text()
    text+='The only algorithm change is NO_PROGRESS AND at least one occupied cell center in the closed1.0m×0.40m rectangle from the current robot position along u_ref. Unknown/stale cells do not count as occupied for this extra predicate. Phase20D asynchronous map publication, R3 recency rule, start-relative u_ref, R2, SP, alignment, fallback and recovery are reused. The20E wrapper binds the existing clean serialization helper missing in the inherited R2 logging globals; function bytecode and repair definition are unchanged.\n\n'
    text+='## Three primary outcomes and mechanism\n\n'+table(summary)+'\n\n## Frozen label\n\n'+table([v])+'\n\n'
    text+='Order: +2 goal successes → DETOUR_HELPS; no fewer goal successes or passages AND a strict majority of nonempty jointly-passed seed pairs faster → DETOUR_PASSES_FASTER; −2 goal successes → DETOUR_WORSE; otherwise DETOUR_MIXED. Technical failures remain in the12 attempts and provide no observed success/passage; valid N is explicit. No missing timing is imputed.\n\n'
    text+='## Same-seed paired outcomes\n\n'+table(pairs)+'\n\n'
    text+='## Run records\n\n'+table(records,['index','method','execution_git_sha','classification','goal_time_s','passed_box','box_passage_time_s','minimum_clearance_m','detour_triggers','detour_applied','detour_collision_count','trigger_stages','no_obstacle_ahead_count','blocked_stages','detour_applied_after_passage','snapshot_max_age_s'])+'\n\n'
    text+='NO_OBSTACLE_AHEAD counts eligible9Hz checks, not deduplicated stop episodes; rejecting the obstacle condition does not start a cooldown or alter commands. Pre/post classification uses first recorded footprint passage, for evaluation only. Runs that never pass retain all events in the before group. Oracle box geometry is used only for placement/rendering and evaluation. Simulator pose is exact (no odometry error).\n\n'
    text+='## Technical failures\n\n'+table([r for r in records if r.get('technical_validation')!='PASS'],['index','method','output','error'])+'\n\n## Visualization availability\n\n'
    for case in visual:
        if case['missing']:
            reason='; '.join(r['method']+': '+r['reason'] for r in case['missing']);text+=f"- L2/{case['index']}: {'Figures skipped; both runs unavailable' if case['skipped'] else 'Missing panels: TECHNICAL_FAILURE (no data)'}. {reason}\n"
    text+='\nSmall gray open diamonds mark NO_OBSTACLE_AHEAD; orange diamonds mark applied NO_PROGRESS triggers; orange dashed paths are applied detours. Gray thick trajectory segments mark publication gaps.\n\n'
    for i in range(89,95):
        if any(r['index']==i and r['skipped'] for r in visual):continue
        for ext in ('png','gif'):text+=f'![L2/{i}](../research/results/phase20e/drive_L2_{i}.{ext})\n\n'
    text+='![paired passage and goal times](../research/results/phase20e/passage_summary.png)\n\nThis six-seed pilot does not establish generalization. Successful box passage and goal arrival are distinct outcomes.\n'
    doc.parent.mkdir(exist_ok=True);doc.write_text(text);return v


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--publish',action='store_true');a=ap.parse_args();root=a.run_root.resolve();plan=json.loads((root/'plan.json').read_text());assert len(plan['jobs'])==12
    records=[json.loads((root/'metrics'/f"main_{j['key']}.json").read_text()) for j in plan['jobs']]
    for r in records:
        f=Path(r['output'])/'provenance.json'
        if f.exists():r['execution_git_sha']=json.loads(f.read_text())['git_sha']
    out=ROOT/'research/results/phase20e';doc=ROOT/'docs/PHASE20E_OBSTACLE_TRIGGER.md';v=render(records,out,doc)
    if a.publish:
        assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
        subprocess.run(['git','add','--',str(out.relative_to(ROOT)),str(doc.relative_to(ROOT))],cwd=ROOT,check=True)
        media=[*out.glob('*.png'),*out.glob('*.gif')]
        if media:subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in media]],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase20E obstacle-conditional pilot'],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
    print(json.dumps(v))
if __name__=='__main__':main()
