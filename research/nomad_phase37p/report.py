"""Registered pilot decision and automatic saved-run figures; no inference."""
import argparse,json,subprocess
from pathlib import Path
from collections import Counter
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,verify

def read(p):return json.loads(Path(p).read_text())

def decide(rows):
    wanted={(s,i,m) for s in SCENES for i in INDICES for m in METHODS}
    valid=len(rows)==20 and {(r['scene'],r['index'],r['method']) for r in rows}==wanted and all(r.get('technical_validation')=='PASS' and r.get('collision') is not None for r in rows)
    counts={m:dict(goal=sum(bool(r.get('success')) for r in rows if r['method']==m and r.get('technical_validation')=='PASS'),
        collision=sum(bool(r.get('collision')) for r in rows if r['method']==m and r.get('technical_validation')=='PASS')) for m in METHODS}
    old,new=[counts[m] for m in METHODS];checks=dict(goal_strictly_more=new['goal']>old['goal'],collision_not_more=new['collision']<=old['collision'])
    return dict(label='PROMISING' if valid and all(checks.values()) else 'NOT_PROMISING',checks=checks,counts=counts,evidence_valid=valid,
        reason='registered ten-pair comparison' if valid else 'Incomplete/technically invalid evidence; no missing collision imputed safe')

def generate(root,output=OUT,document=None,make_figures=True):
    p=verify();root=Path(root);output=Path(output);rows=[read(f) for f in sorted((root/'metrics').glob('*.json'))];d=decide(rows);stats=[];trigger_rows=[];pairs=[]
    for m in METHODS:
        for scene in (*SCENES,'ALL'):
            group=[r for r in rows if r['method']==m and (scene=='ALL' or r['scene']==scene)];v=[r for r in group if r.get('technical_validation')=='PASS']
            stats.append(dict(method=m,scene=scene,n=len(group),valid=len(v),goal=sum(r['success'] for r in v),collision=sum(r['collision'] for r in v),
                goal_time_median_s=median([r['goal_time_s'] for r in v if r['success']]),mean_speed_m_s=median([r['mean_speed_m_s'] for r in v]),
                stopped_fraction=median([r['stopped_fraction'] for r in v]),trigger_A=sum(r.get('trigger_counts',{}).get('A',0) for r in v),
                trigger_B=sum(r.get('trigger_counts',{}).get('B',0) for r in v),detour_applied=sum(r.get('detour_applied_count',0) for r in v)))
            for kind in ('A','B'):
                counts=Counter()
                for r in v:counts.update(r.get('trigger_oracle_counts',{}).get(kind,{}))
                trigger_rows.append(dict(method=m,scene=scene,trigger=kind,**{k:counts[k] for k in ('BOX_AHEAD','STATIC_AHEAD','PASSED_BOX','NOTHING_AHEAD')}))
    for scene in SCENES:
        for index in INDICES:
            by={r['method']:r for r in rows if (r['scene'],r['index'])==(scene,index)};a=by.get('OURS',{});b=by.get('OURS+PROV',{})
            both=a.get('technical_validation')==b.get('technical_validation')=='PASS' and a.get('success') and b.get('success')
            pairs.append(dict(scene=scene,index=index,OURS_goal=a.get('success'),PROV_goal=b.get('success'),OURS_collision=a.get('collision'),PROV_collision=b.get('collision'),
                goal_time_delta_s=b['goal_time_s']-a['goal_time_s'] if both else None))
    output.mkdir(parents=True,exist_ok=True);save(output/'runs.json',rows);save(output/'decision.json',d);csvout(output/'summary.csv',stats);csvout(output/'triggers.csv',trigger_rows);csvout(output/'paired.csv',pairs)
    failures=[{k:r.get(k) for k in ('scene','index','method','primary_cause','classification','termination','minimum_goal_distance_m','output')} for r in rows if r.get('technical_validation')=='PASS' and not r['success']]
    technical=[{k:r.get(k) for k in ('scene','index','method','attempt_count','error','output')} for r in rows if r.get('technical_validation')!='PASS']
    save(output/'failures.json',failures);save(output/'technical_failures.json',technical)
    figures=[]
    if make_figures:
        from .figures import pair_plot
        for scene in SCENES:
            for index in INDICES:
                block=[r for r in rows if (r['scene'],r['index'])==(scene,index)]
                figures.append(pair_plot(block,scene,index,output/'figures'/f'trajectories_{scene}_{index}.png'))
    save(output/'figures.json',figures)
    from nomad_isaac.common import sha256_file
    text=f'''# Phase37-P — OURS / OURS+PROV 파일럿

**{d['label']}**. Protocol FROZEN SHA256 `{sha256_file(HERE/'protocol.json')}`.20 run,10개 scene×seed 짝을 대상으로 한다. 판정은 PROV 도착>OURS 도착 AND PROV 충돌≤OURS 충돌이다. 도착시간은 판정에 사용하지 않는다.

## 사용자 결정 / 사전등록 이탈

{p['user_decision']['date_kst']}: Phase37-B의 `PROV_NOT_ESTABLISHED_MISSING_HISTORY`를 보존한다(확인 이력 기준 BOX42/45, 비-BOX116→59). 보존되지 않은 과거 지도 때문에 오프라인 gate를 확정할 수 없어, 사용자가 라이브 이력을 모두 추적하는 주행 파일럿을 승인했다. 오프라인 라벨을 PASS로 바꾸지 않았다.

OURS는 Phase35 동결 코드 그대로다. OURS+PROV는 매 지도 발행 직전, 최종 V1/shadow 상태에서 `last_free_tick==frame_tick AND observed AND not occupied`이고 최초 occupied 이전인 셀의 플래그를 누적한다. B의 새 덩어리 집계에만 이 플래그를 추가한다. 기존 ID·t_new·u_ref, 트리거A, 유지/넘김, R2/R3, EC, PP/SP와>90° 정렬은 그대로다.10초 방향 보정과 TOPO-H는 사용하지 않는다. Oracle은 아래 사후 분류/그림에만 사용한다.

## 판정 및 방법×장면

{table([d])}

{table(stats)}

## 트리거 수 / Phase37 oracle4분류

{table(trigger_rows)}

실제 TRIGGER event를 A/B로 나눠 센다. 같은 u_ref 전방1.0×0.4m 사각형과 원 Phase37 기하 분류를 사용하며, 실제 spawn/passage 시각을 사용한다. 우회 적용 수는 APPLIED event 수다.

## 짝 도착시간 (PROV−OURS)

{table(pairs)}

둘 다 도착한 짝의 중앙값: {median([r['goal_time_delta_s'] for r in pairs if r['goal_time_delta_s'] is not None])}s.

## 실패 원인 / 기술 실패

{table(failures)}

Phase31-D의 첫 일치 순서(상자/구조벽 충돌→경계 정지→목표0.6m 접근 후 실패→상자 통과 후 실패→정적 마지막10초 진전<0.2m→상자 미통과→출현 전/초기 정체→기타)를 Phase35의 동결 분석 코드로 재사용했다. WALL_COLLISION 분해에는 margin 정지가 포함될 수 있지만 판정의 collision은 원 evaluator 값이다.

{table(technical)}

## 블록별 주행 궤적

Phase35와 같은150dpi/1:1 축 비율이다. OURS 파랑, PROV 주홍, 실제 궤적과 실제 R3 실행 구간(굵은 선), 회색 벽/고정 장애물, 보라색 실제 생성 상자를 표시한다. 종료 원=도착, X=충돌, 사각형=timeout이며 그 밖의 경계 정지는 별도 표시한다. 기술 실패/필수 로그 없음은 범례에 표시하고, 둘 다 없으면 그림을 생략하고 이유를 남긴다.
'''
    for f in figures:
        if f['skipped']:text+=f"\n- {f['scene']} {f['index']}: 생략 — {f['reason']}\n"
        else:text+=f"\n![{f['scene']} seed{f['index']}](../research/results/phase37p/figures/{Path(f['file']).name})\n"
    text+='\n저장 v2: values 생략 및 provenance flag/최초 확인 tick 보존. 같은 seed 기술 실패1회 재시도, run 종료 cache 정리, 매 attempt 전30GB 점검. 기존 Phase35/37/37-B 결과는 수정하지 않는다.\n'
    doc=Path(document) if document else ROOT/'docs/PHASE37P_RESULTS.md';doc.write_text(text);return doc,figures

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args();assert a.run_root.resolve()==RUN_ROOT.resolve()
    doc,figures=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        images=[f['file'] for f in figures if not f['skipped']]
        if images:subprocess.run(['git','add','-f','--',*images],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase37-P provenance pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
