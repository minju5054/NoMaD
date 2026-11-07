"""Frozen Phase32 evaluator plus Phase34 routing telemetry and paired report."""
import argparse,json,subprocess
from pathlib import Path
from collections import Counter
from nomad_phase32.report import audit as frozen_audit,lines
from nomad_phase31p.report import table,csv_write,save,median
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,verify

def collision_state(root,summary,collision):
    if not collision:return None
    contacts=[]
    def visit(value):
        if isinstance(value,dict):
            c=value.get('first_contact')
            if isinstance(c,dict):contacts.append(c)
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(summary.get('obstacle_evaluation'));visit(summary.get('dynamic_obstacle'))
    contacts=[c for c in contacts if c.get('detected_sim_s') is not None]
    if contacts:
        contact=min(contacts,key=lambda c:c['detected_sim_s']);t=contact.get('interval_start_s',contact['detected_sim_s']);detected=contact['detected_sim_s'];basis='FROZEN_FIRST_CONTACT_INTERVAL'
    else:
        bad=[c for c in lines(root/'clearance.jsonl') if c.get('geometric_overlap') or c.get('corridor_lower_m',0)<0]
        first=min(bad,key=lambda x:x['start_sim_s']) if bad else None
        t=first['start_sim_s'] if first else summary['simulation_duration_s'];detected=first['end_sim_s'] if first else t;basis='FROZEN_CLEARANCE_INTERVAL' if first else 'TERMINAL_TIME_ONLY'
    commands=[c for c in lines(root/'phase20_commands.jsonl') if c['time_s']<=t+1e-9];detours=[c for c in lines(root/'phase20d_commands.jsonl') if c['time_s']<=t+1e-9]
    c=commands[-1] if commands else {};d=detours[-1] if detours else {};source=c.get('source','UNKNOWN')
    if d.get('detour_state')=='WAIT':state='R3_WAIT'
    elif d.get('detour_state')=='ACTIVE':state='R3_'+source
    elif c.get('repair_active'):state='R2_'+source
    elif source=='REPAIR_WAIT':state='R2_WAIT'
    else:state=source
    return dict(state=state,command_source=source,detour_state=d.get('detour_state'),repair_active=c.get('repair_active'),
                interval_start_s=t,detected_s=detected,time_basis=basis,command=c.get('command'),path_source_id=c.get('path_source_id'),pending_job=c.get('pending_job'))

def audit(root):
    root=Path(root);r=frozen_audit(root);cfg=json.loads((root/'scenario.json').read_text());events=lines(root/'events.jsonl');detours=lines(root/'detour.jsonl');ec=lines(root/'exec_cert.jsonl')
    a={x['job_id']:x for x in detours if x['event']=='TRIGGER' and x.get('trigger')=='A'}
    result={x['job_id']:x for x in detours if x['event']=='RESULT' and x['job_id'] in a};applied={x['job_id'] for x in detours if x['event']=='APPLIED' and x['job_id'] in a}
    filters=[x for x in ec if x['event']=='SOLVER_FILTER' and x['state']=='R3' and x['job_id'] in a]
    active={};seconds=0.
    for x in detours:
        if x['event']=='APPLIED':active[x['job_id']]=x['simulation_time_s']
        elif x['event']=='END' and x['job_id'] in active:seconds+=x['simulation_time_s']-active.pop(x['job_id'])
    seconds+=sum(r['duration_s']-t for t in active.values())
    summary=json.loads((root/'summary.json').read_text())
    r.update(method=cfg['phase34_method'],trigger_A_count=sum(bool(e.get('phase16',{}).get('selection',{}).get('all_unsafe')) for e in events),
             R2_calls=sum(x['event']=='SUBMIT' for x in lines(root/'repair.jsonl')),A_R3_attempts=len(a),A_R3_success=len(applied),A_R3_failure=len(a)-len(applied),
             A_R3_dispositions=dict(Counter(result[i]['disposition'] if i in result else 'TERMINAL_NO_RESULT' for i in a)),
             A_R3_EC_reject_jobs=sum(not any(c['passed'] for c in f['checks']) for f in filters),
             A_R3_EC_reject_candidates=sum(not c['passed'] for f in filters for c in f['checks']),
             detour_execution_s=seconds,collision_execution_state=collision_state(root,summary,r['collision']))
    if cfg['phase34_method']==METHODS[1]:
        assert r['R2_calls']==0,'The -R2 arm must never dispatch R2'
        assert all(x['kind']=='R3' for x in lines(root/'repair_pool_jobs.jsonl')),'The -R2 worker must receive only R3 jobs'
    return r

def decide(rows):
    keys={(s,i,m) for s in SCENES for i in INDICES for m in METHODS};have=[(r['scene'],r['index'],r['method']) for r in rows]
    valid=len(rows)==20 and set(have)==keys and all(r.get('technical_validation')=='PASS' and r.get('collision') is not None for r in rows)
    stats={m:dict(goal=sum(bool(r.get('success')) for r in rows if r['method']==m),collision=sum(bool(r.get('collision')) for r in rows if r['method']==m)) for m in METHODS}
    a,b=(stats[m] for m in METHODS);checks=dict(goal_not_lower=b['goal']>=a['goal'],collision_not_higher=b['collision']<=a['collision'])
    return dict(label='PROMISING' if valid and all(checks.values()) else 'NOT_PROMISING',evidence_valid=valid,checks=checks,counts=stats,
                reason='registered ten-pair comparison' if valid else 'incomplete/technically invalid evidence; unknown collision is not treated as safe')

def generate(root):
    p=verify();rows=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))];decision=decide(rows);stats=[]
    for m in METHODS:
        for scene in (*SCENES,'ALL'):
            group=[r for r in rows if r['method']==m and (scene=='ALL' or r['scene']==scene)];valid=[r for r in group if r.get('technical_validation')=='PASS']
            stats.append(dict(method=m,scene=scene,n=len(group),valid=len(valid),goal=sum(r['success'] for r in valid),collision=sum(r['collision'] for r in valid),
                goal_time_median_s=median([r['goal_time_s'] for r in valid if r['success']]),stop_fraction_median=median([r['stopped_fraction'] for r in valid]),
                trigger_A=sum(r['trigger_A_count'] for r in valid),R2_calls=sum(r['R2_calls'] for r in valid),A_R3_attempts=sum(r['A_R3_attempts'] for r in valid),
                A_R3_success=sum(r['A_R3_success'] for r in valid),A_R3_failure=sum(r['A_R3_failure'] for r in valid),
                A_R3_EC_reject_jobs=sum(r['A_R3_EC_reject_jobs'] for r in valid),A_R3_EC_reject_candidates=sum(r['A_R3_EC_reject_candidates'] for r in valid),
                detour_execution_s=sum(r['detour_execution_s'] for r in valid)))
    pairs=[]
    for scene in SCENES:
        for index in INDICES:
            pair={r['method']:r for r in rows if r['scene']==scene and r['index']==index};a=pair.get(METHODS[0],{});b=pair.get(METHODS[1],{})
            both=a.get('technical_validation')==b.get('technical_validation')=='PASS' and a.get('success') and b.get('success')
            pairs.append(dict(scene=scene,index=index,baseline_goal=a.get('success'),without_R2_goal=b.get('success'),baseline_collision=a.get('collision'),without_R2_collision=b.get('collision'),goal_time_delta_s=b['goal_time_s']-a['goal_time_s'] if both else None))
    OUT.mkdir(parents=True,exist_ok=True);save(OUT/'runs.json',rows);save(OUT/'decision.json',decision);csv_write(OUT/'summary.csv',stats);csv_write(OUT/'paired.csv',pairs)
    collisions=[dict(scene=r['scene'],index=r['index'],method=r['method'],**r['collision_execution_state']) for r in rows if r.get('collision_execution_state')]
    save(OUT/'collision_states.json',collisions);technical=[r for r in rows if r.get('technical_validation')!='PASS'];save(OUT/'technical_failures.json',technical)
    from nomad_isaac.common import sha256_file
    text='# Phase34-P: R2 생략 파일럿\n\n**'+decision['label']+'**. Protocol SHA256 `'+sha256_file(HERE/'protocol.json')+'`.\n\n'+table([decision])+'\n\n## 방법×장면\n\n'+table(stats)+'\n\n## 같은 scene×seed 짝\n\n'+table(pairs)
    text+='\n\n도착시간 차이는 두 방법 모두 도착한 짝에서 −R2 − baseline이다. 중앙값: '+str(median([x['goal_time_delta_s'] for x in pairs if x['goal_time_delta_s'] is not None]))+'s. 판정에는 도착·충돌 수만 사용한다.\n'
    text+='\n트리거 A 횟수는 정상 선택에서 ALL_UNSAFE가 확인된 FRESH 사건 수다. R3 성공은 실제 APPLIED 수이며 실패에는 solver/EC/certificate/timeout/종료 전 미적용을 포함한다. EC 거절 job 수와 후보별 거절 수를 분리한다. R2 생략 arm의 R2 호출0을 기술 검사한다. B 경로·R3 선택·EC·fallback·제어·평가기는 동결 구현이다.\n'
    text+='\n## 충돌 순간 실행 상태\n\n'+(table(collisions) if collisions else '충돌 없음.')+'\n\n기존 평가기의 first_contact 구간 시작 시점에 유효했던 명령/우회 상태를 사용한다. 이 표를 만들기 위해 충돌 판정을 다시 계산하거나 바꾸지 않는다.\n'
    text+='\n## 기술 실패\n\n'+(table([{k:r.get(k) for k in ('scene','index','method','attempt_count','error')} for r in technical]) if technical else '없음.')+'\n'
    text+='\nPhase32의44개 R2 호출을 사용한 오프라인 확인은 참고 자료이며 이 판정에 포함하지 않는다. 저장 v2는 디스크 표현만 바꾸고 라이브 지도/제어 계산을 바꾸지 않는다.\n'
    doc=ROOT/'docs/PHASE34P_RESULTS.md';doc.write_text(text);return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args();assert a.run_root.resolve()==RUN_ROOT.resolve();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase34-P R2 bypass pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

if __name__=='__main__':main()
