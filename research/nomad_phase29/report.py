"""Registered gates and final artifact; read saved results only."""
import argparse,json,subprocess
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from .config import HERE,OUT,RUN_ROOT,SCENES,protocol
def read(p,default=None):return json.loads(Path(p).read_text()) if Path(p).exists() else default
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def median(x):return float(np.median(x)) if x else None
def table(rows):
    if not rows:return '자료 없음'
    keys=list(rows[0]);fmt=lambda x:'—' if x is None else f'{x:.4g}' if isinstance(x,float) else str(x).replace('|','/')
    return '\n'.join(['| '+' | '.join(keys)+' |','|'+'|'.join(['---']*len(keys))+'|']+['| '+' | '.join(fmt(r.get(k)) for k in keys)+' |' for r in rows])
def baselines():
    return [dict(r,stage='reused') for phase,method in [('phase27r','C0'),('phase28','C0-NA')] for r in read(ROOT/f'research/results/{phase}/runs.json',[]) if r['method']==method]
def dev_gate(rows,old):
    g=[r for r in rows if r['method']=='G18'];na=[r for r in old if r['method']=='C0-NA'];calls=sum(r.get('path_jobs',0) for r in g);applied=sum(r.get('path_applied',0) for r in g)
    checks=dict(complete=len(rows)==20 and len(g)==len(na)==10,collision=sum(r.get('collision',False) for r in g)<=sum(r['collision'] for r in na),goal=sum(r.get('success',False) for r in g)>=sum(r['success'] for r in na)-1,
        application=calls>0 and applied/calls>=.7,technical=all(r['technical_validation']=='PASS' for r in rows))
    return dict(passed=all(checks.values()),checks=checks,g18_goal=sum(r.get('success',False) for r in g),na_goal=sum(r['success'] for r in na),g18_collision=sum(r.get('collision',False) for r in g),na_collision=sum(r['collision'] for r in na),g18_calls=calls,g18_applied=applied,application_rate=applied/calls if calls else None)
def confirm_decision(rows):
    groups={m:{(r['scene'],r['index']):r for r in rows if r['method']==m and r['technical_validation']=='PASS'} for m in ('C0','C0-NA','SM','G18')}
    if any(len(v)!=15 for v in groups.values()):return dict(label='PARTIAL',reason='Confirmation requires all15 valid scene×seed pairs',pairs=[])
    pairs=[]
    for other in ('C0','C0-NA','SM'):
        for key,g in groups['G18'].items():
            b=groups[other][key];pairs.append(dict(scene=key[0],index=key[1],comparison='G18-'+other,clearance_difference_m=g['minimum_clearance_m']-b['minimum_clearance_m'],goal_time_difference_s=g['goal_time_s']-b['goal_time_s'] if g['success'] and b['success'] else None))
    n=lambda m,k:sum(r[k] for r in groups[m].values())
    sm=median([r['clearance_difference_m'] for r in pairs if r['comparison']=='G18-SM']);sm_time=median([r['goal_time_difference_s'] for r in pairs if r['comparison']=='G18-SM' and r['goal_time_difference_s'] is not None]);c_time=median([r['goal_time_difference_s'] for r in pairs if r['comparison']=='G18-C0' and r['goal_time_difference_s'] is not None])
    a=n('G18','collision')<n('C0-NA','collision') and n('G18','success')>=n('C0-NA','success')
    b=sm>0 and n('G18','collision')<=n('SM','collision') and sm_time is not None and sm_time<=3
    c=c_time is not None and c_time<0 and n('G18','collision')<=n('C0','collision')
    return dict(label='G18_SUPPORTED' if a and b and c else 'G18_PARTIAL' if a and b else 'G18_NOT_SUPPORTED',checks=dict(a=a,b=b,c=c),sm_clearance_median_m=sm,sm_goal_time_median_s=sm_time,c0_goal_time_median_s=c_time,pairs=pairs)
def generate(root=RUN_ROOT,label=None,reason=None):
    OUT.mkdir(parents=True,exist_ok=True);state=read(root/'state.json',{});rows=[read(f) for f in sorted((root/'metrics').glob('*.json'))];old=baselines()
    dev=[r for r in rows if r['stage']=='dev'];conf=[r for r in rows if r['stage']=='confirm'];gate=dev_gate(dev,old)
    result=confirm_decision(conf) if len(conf)==60 else dict(label=label or state.get('label','PARTIAL'),reason=reason or state.get('reason','Preparation/incomplete'),pairs=[])
    if label:result['label']=label
    result.update(dev_gate=gate,stopped_stage=state.get('stage','implementation'),stop_reason=reason or state.get('reason',''),completed_by_stage=dict(Counter(r['stage'] for r in rows)),protocol_sha256=sha256_file(HERE/'protocol.json'))
    save(OUT/'decision.json',result);save(OUT/'runs.json',rows+old);save(OUT/'paired.json',result.pop('pairs',[]))
    summaries=[]
    for stage,group in [('dev',dev+old),('confirm',conf),('smoke',[r for r in rows if r['stage']=='smoke'])]:
        for scene in SCENES:
            for method in ('C0','C0-NA','SM','G18'):
                rr=[r for r in group if r['scene']==scene and r['method']==method];valid=[r for r in rr if r['technical_validation']=='PASS']
                if not rr:continue
                summaries.append(dict(stage=stage,scene=scene,method=method,n=len(rr),valid=len(valid),goal=sum(r['success'] for r in valid),collision=sum(r['collision'] for r in valid),
                    goal_time_s=median([r['goal_time_s'] for r in valid if r['success']]),mean_speed_m_s=median([r.get('mean_speed_m_s',r['distance_m']/r['duration_s']) for r in valid]),stop_fraction=median([r['stopped_fraction'] for r in valid]),minimum_clearance_m=median([r['minimum_clearance_m'] for r in valid]),omega_saturation=median([r['omega_saturation_fraction'] for r in valid])))
    save(OUT/'summary.json',summaries)
    graph=[dict(stage=r['stage'],scene=r['scene'],index=r['index'],calls=r.get('path_jobs',0),applied=r.get('path_applied',0),reasons=r.get('path_reasons',{}),compute_p50_s=r.get('compute_p50_s'),compute_p95_s=r.get('compute_p95_s')) for r in rows if r['method']=='G18'];save(OUT/'graph_statistics.json',graph)
    first=[f"최종 라벨: {result['label']}",f"완료: {result['completed_by_stage']} (본 실행 순차, smoke 제외)",f"dev G18/NA 도착 {gate['g18_goal']}/{gate['na_goal']}, 충돌 {gate['g18_collision']}/{gate['na_collision']}, G18 적용 {gate['g18_applied']}/{gate['g18_calls']}",f"멈춘 단계: {result['stopped_stage']} — {result['stop_reason'] or '진행/완료 상태는 decision.json 참조'}",'수치·정책·평가기·이전 결과 보존; 확인 실험은 dev gate 통과한 경우에만 실행.']
    doc='\n'.join(first)+'\n\n# Phase29 경로–속도 분해\n\n'+table(summaries)+'\n\n## Dev gate\n\n'+json.dumps(gate,ensure_ascii=False,indent=2)+'\n\n## G18 적용/거절/계산\n\n'+table(graph)+'\n\n## 짝 차이\n\n'+table(read(OUT/'paired.json',[]))+'\n\nSM: Phase22 P3 geometry(.5 strength, three halvings,11-point resampling) on B suffix. R3-only advance/spacing/disk restrictions do not apply to normal chunks; both use Phase18 output depth-site certificate. G18: unchanged ClearanceGraph/FlagGraphV4+depth hard+CLR soft(.15/.05), previous correction prior; original 0.5s STALE and latest-id SUPERSEDED decision. RAW selected path runs until a valid correction arrives, and remains on rejection. Output XY goes to frozen NA PP/SP and >90° alignment, not CURV or timed H follower. G18 process uses parent NumPy/SciPy and CPU7, immutable shared SDF arrays. C0 confirm remains original C0; C0-NA/SM/G18 share NA.\n\nDev denominator: all G18 SAFE FRESH submissions including initialization failures, expired, superseded, stale and terminal-unapplied. Technical failures are final run outcomes after at most one retry; failed attempts are preserved separately. Confirmation paired goal-time medians use both-success pairs; no such pair makes that condition false. Incomplete stages yield PARTIAL, not imputed failures. Deadlines are checked between runs; an active run is allowed to finish. Previous C0/NA results are copied as descriptive rows only. No tuning or package install.\n'
    (ROOT/'docs/PHASE29_GOAL_REPORT.md').write_text(doc);return result
def publish(stage):
    paths=['research/nomad_phase29','research/results/phase29','docs/PHASE29_GOAL_REPORT.md']
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Phase29 '+stage,'--',*paths],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();print(json.dumps(generate(),ensure_ascii=False))
    if a.publish:publish('report')
if __name__=='__main__':main()
