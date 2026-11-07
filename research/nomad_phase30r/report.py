"""Paired Phase29 G18 dev comparison, original evaluator; no navigation."""
import argparse,csv,json,subprocess
from pathlib import Path
import numpy as np
from nomad_phase29.metrics import audit as original_audit
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,verify

def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines()] if Path(p).exists() else []
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def median(xs):return float(np.median(xs)) if xs else None
def table(rows):
    if not rows:return '자료 없음'
    keys=list(rows[0]);fmt=lambda x:'—' if x is None else f'{x:.5g}' if isinstance(x,float) else str(x).replace('|','/')
    return '\n'.join(['| '+' | '.join(keys)+' |','|'+'|'.join(['---']*len(keys))+'|']+['| '+' | '.join(fmt(r.get(k)) for k in keys)+' |' for r in rows])
def csv_write(p,rows):
    if not rows:p.write_text('');return
    with p.open('w',newline='') as f:w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)

def detour_metrics(root):
    root=Path(root);summary=read(root/'summary.json');end=summary['simulation_duration_s'];events=lines(root/'detour.jsonl')
    with (root/'agent_trajectory.csv').open() as f:trace=list(csv.DictReader(f))
    times=np.array([float(r['simulation_time_s']) for r in trace]);dt=np.r_[0.,np.diff(times)]
    xy=np.array([[float(r[k]) for k in ('x_m','y_m')] for r in trace]);distance=np.r_[0.,np.linalg.norm(np.diff(xy,axis=0),axis=1)]
    mask=np.zeros(len(times),bool);planned=[];durations=[];censored=0
    for a in (e for e in events if e['event']=='APPLIED'):
        stop=next((e for e in events if e['event']=='END' and e['job_id']==a['job_id'] and e['simulation_time_s']>=a['simulation_time_s']),None)
        b=stop['simulation_time_s'] if stop else end;censored+=stop is None
        durations.append(b-a['simulation_time_s']);path=np.asarray(a['path'])
        planned.append(float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum()))
        mid=times-dt/2;mask|=(mid>=a['simulation_time_s'])&(mid<b)
    repairs=[e for e in lines(root/'repair.jsonl') if e['event']=='PATH_APPLIED' and e['kind']=='REPAIR']
    commands=lines(root/'phase20_commands.jsonl');ct=[e['time_s'] for e in commands];idx=np.searchsorted(ct,times-dt/2,side='right')-1
    repair_mask=np.array([i>=0 and commands[max(0,i)]['repair_active'] and commands[max(0,i)]['source'] in ('REPAIR','ALIGN_ROTATE','ALIGN_BRAKE') for i in idx])
    return dict(detour_applied=len(planned),detour_execution_s=float(sum(durations)),detour_path_length_m=float(sum(planned)),
        detour_mean_path_length_m=float(np.mean(planned)) if planned else None,detour_actual_distance_m=float(distance[mask].sum()),detour_terminal_censored=censored,
        repair_execution_s=float(dt[repair_mask].sum()),repair_path_length_m=float(sum(np.linalg.norm(np.diff(np.asarray(e['path_world']),axis=0),axis=1).sum() for e in repairs)))

def audit(root):
    r=original_audit(root);r.update(detour_metrics(root));return r

def baseline():
    return [dict(r,reused=True) for r in read(ROOT/'research/results/phase29/runs.json') if r['stage']=='dev' and r['method']=='G18']

def decide(new,old):
    pairs=[]
    for n in new:
        b=next((r for r in old if (r['scene'],r['index'])==(n['scene'],n['index'])),None)
        if not b or n['technical_validation']!='PASS' or b['technical_validation']!='PASS':continue
        pairs.append(dict(scene=n['scene'],index=n['index'],new_goal=n['success'],old_goal=b['success'],new_collision=n['collision'],old_collision=b['collision'],
            **{k+'_difference':n[k]-b[k] if n.get(k) is not None and b.get(k) is not None else None for k in ('goal_time_s','mean_speed_m_s','detour_execution_s','detour_path_length_m','box_passage_from_spawn_s','minimum_clearance_m')},
            paired_goal_time_s=n['goal_time_s']-b['goal_time_s'] if n['success'] and b['success'] else None))
    valid=len(new)==len(old)==len(pairs)==10
    goal=sum(r.get('success',False) for r in new);old_goal=sum(r['success'] for r in old)
    collision=sum(bool(r.get('collision',False)) for r in new);old_collision=sum(r['collision'] for r in old)
    times=[r['paired_goal_time_s'] for r in pairs if r['paired_goal_time_s'] is not None];time_median=median(times)
    checks=dict(valid_evidence=valid,goal=goal>=old_goal,collision=valid and collision<=old_collision,time=time_median is not None and time_median<0)
    return dict(label='INCLUDE_TONIGHT' if all(checks.values()) else 'EXCLUDE',checks=checks,goal=goal,baseline_goal=old_goal,collision=collision if valid else None,
        baseline_collision=old_collision,successful_pairs=len(times),goal_time_difference_median_s=time_median,
        note='Missing/technical-invalid outcomes do not establish the safety condition; empty successful pairs do not establish negative median.'),pairs

def generate(root):
    p=verify();new=[read(f) for f in sorted((root/'metrics').glob('*.json'))];old=baseline()
    for r in old:r.update(detour_metrics(r['output']))
    decision,pairs=decide(new,old);rows=old+new;summary=[]
    for scene in (*SCENES,'ALL'):
        for method in ('G18','G18-R'):
            q=[r for r in rows if r['method']==method and (scene=='ALL' or r['scene']==scene) and r['technical_validation']=='PASS']
            summary.append(dict(scene=scene,method=method,n=len(q),goal=sum(r['success'] for r in q),collision=sum(r['collision'] for r in q),
                **{k:median([r[k] for r in q if r.get(k) is not None]) for k in ('goal_time_s','mean_speed_m_s','detour_execution_s','detour_path_length_m','detour_actual_distance_m','repair_execution_s','repair_path_length_m','box_passage_from_spawn_s','minimum_clearance_m')}))
    OUT.mkdir(parents=True,exist_ok=True);save(OUT/'runs.json',rows);save(OUT/'decision.json',decision);csv_write(OUT/'summary.csv',summary);csv_write(OUT/'paired.csv',pairs)
    doc=ROOT/'docs/PHASE30R_RESULTS.md';doc.write_text('# Phase30-R same-seed comparison\n\n'+decision['label']+'\n\n'+json.dumps(decision,ensure_ascii=False,indent=2)+'\n\n'+table(summary)+'\n\n'+table(pairs)+'\n\nG18 baseline reuses Phase29 dev seeds201/202; different execution dates. Only NORMAL CLR and R3 CLR preference targets change .15→.08m. R2 has no soft clearance factor and is unchanged.\n\nDetour execution is R3 APPLIED→END (includes its alignment), summed per run; terminal active intervals are censored at run end and flagged. Detour path length sums the polylines actually installed (not just solved). Actual travelled detour distance and R2 repair time/length are separate columns. Box passage time is from spawn; multi-box aggregation is the frozen evaluator value. Goal-time comparison uses both-success pairs only; other medians include all valid outcomes. Minimum clearance is descriptive, not part of INCLUDE_TONIGHT.\n')
    return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    root=a.run_root.resolve();assert root==RUN_ROOT.resolve();doc=generate(root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase30-R clearance-target pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
