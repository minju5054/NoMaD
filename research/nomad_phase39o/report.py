"""Registered paired numerical outcomes; no EC or online experiment."""
import argparse,json
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .inputs import ROOT,OUT,HERE
from .solver import VARIANTS

def gate(rows,expected):
    counts={v:[r for r in rows if r['variant']==v and r['scene']=='SLW'] for v in VARIANTS}
    wanted={c['case_id'] for c in expected if c['scene']=='SLW'}
    complete=bool(wanted) and all({r['case_id'] for r in counts[v]}==wanted for v in VARIANTS)
    base=sum(r['success'] for r in counts['V0'])/len(wanted) if complete else None
    decisions=[]
    for v in VARIANTS[1:]:
        group=counts[v];rate=sum(r['success'] for r in group)/len(wanted) if complete else None
        timing=float(np.quantile([r['job_wall_s'] for r in group],.95)) if group else None
        failures=sum(r['accepted_certificate_failures'] for r in group)
        checks=dict(success_plus_30pp=rate is not None and rate>=base+.30-1e-12,p95_le_1s=timing is not None and timing<=1.,certificate_failures_zero=failures==0)
        ok=complete and all(checks.values())
        decisions.append(dict(variant=v,label='GO_ONLINE' if ok else 'NO_GO' if complete else 'NOT_EVALUATED',checks=checks,
            slw_jobs=len(group),baseline_success_rate=base,success_rate=rate,p95_s=timing,accepted_certificate_failures=failures))
    selected=next((r['variant'] for r in decisions if r['label']=='GO_ONLINE'),None)
    return dict(label='GO_ONLINE' if selected else 'NO_GO' if complete else 'NOT_EVALUATED',selected_variant=selected,
        selection_order=['V1','V2','V3'],slw_complete=complete,variants=decisions)

def chosen_progress(case,numeric):
    i=numeric.get('selected_sample')
    if i is None:return None
    r=numeric['results'][i]
    if case['kind']=='R3':return r['progress_m']
    q=np.asarray(r['reference']);B=np.asarray(case['job']['B'])[:2];u=q[-1]-B;length=np.linalg.norm(u)
    return float((np.asarray(r['path'])[-1]-B)@(u/length)) if length>1e-12 else None

def generate(output=OUT,document=None):
    output=Path(output);protocol=json.loads((HERE/'protocol.json').read_text());cases=json.loads((OUT/'preparation/inputs.json').read_text());by={c['case_id']:c for c in cases}
    jobs=[];solutions=[];messages=Counter();reproductions=[];escape=[]
    for f in sorted((output/'jobs').glob('*.json')):
        result=json.loads(f.read_text());case=by[result['case_id']];v=result['variant'];numeric=result['numeric'];audit=result['certificate_audit']
        bad=sum(not r['certificate_pass'] for r in audit)
        jobs.append(dict(case_id=case['case_id'],scene=case['scene'],kind=case['kind'],variant=v,success=any(r.get('accepted') for r in numeric['results']),
            selected_index=numeric['selected_sample'],job_wall_s=numeric['pool_wall_s'],progress_m=chosen_progress(case,numeric),accepted_certificate_failures=bad,
            accepted_solutions=len(audit),negative_B_accepted=sum(r['negative_B_escape'] for r in audit)))
        for i,r in enumerate(numeric['results']):
            message=r.get('message',r.get('error',r.get('disposition','UNKNOWN')));messages[(case['scene'],case['kind'],v,message)]+=1
            solutions.append(dict(case_id=case['case_id'],scene=case['scene'],kind=case['kind'],variant=v,index=i,
                disposition=r['disposition'],accepted=r['accepted'],message=message,iterations=r.get('iterations'),xi_max=r.get('xi_max'),
                cB=r.get('cB',r.get('cB_depth_clearance_m')),fixed_B_constraint_m=r.get('fixed_B_constraint_m'),
                constraint_violation=r.get('constraint_violation'),certificate_pass=r.get('certificate_pass'),depth_clearance_m=r.get('depth_clearance_m')))
        for a in audit:
            if a['escape_schedule']:escape.append(dict(case_id=case['case_id'],scene=case['scene'],kind=case['kind'],variant=v,**a))
        if result.get('reproduction'):reproductions.append(dict(case_id=case['case_id'],scene=case['scene'],kind=case['kind'],**result['reproduction']))
    summary=[]
    for scene in (*sorted({c['scene'] for c in cases}),'ALL'):
        for kind in ('R2','R3','ALL'):
            for v in VARIANTS:
                group=[r for r in jobs if (scene=='ALL' or r['scene']==scene) and (kind=='ALL' or r['kind']==kind) and r['variant']==v]
                if not group:continue
                ts=[r['job_wall_s'] for r in group]
                summary.append(dict(scene=scene,kind=kind,variant=v,n=len(group),accepted_jobs=sum(r['success'] for r in group),
                    job_success_rate=sum(r['success'] for r in group)/len(group),job_p50_s=median(ts),job_p95_s=float(np.quantile(ts,.95)),
                    selected_progress_median_m=median([r['progress_m'] for r in group if r['progress_m'] is not None]),
                    accepted_certificate_failures=sum(r['accepted_certificate_failures'] for r in group),negative_B_accepted=sum(r['negative_B_accepted'] for r in group),
                    negative_B_successful_jobs=sum(r['negative_B_accepted']>0 for r in group)))
    d=gate(jobs,cases);d['all_variants_complete']=len(jobs)==len(cases)*4
    # Even a complete SLW subset cannot close an interrupted registered run.
    if not d['all_variants_complete']:d.update(label='NOT_EVALUATED',selected_variant=None)
    save(output/'decision.json',d);csvout(output/'jobs.csv',jobs);csvout(output/'solutions.csv',solutions);csvout(output/'summary.csv',summary)
    message_rows=[dict(scene=s,kind=k,variant=v,message=m,count=n) for (s,k,v,m),n in sorted(messages.items())]
    csvout(output/'messages.csv',message_rows);csvout(output/'reproduction.csv',reproductions);csvout(output/'escape.csv',escape)
    before=json.loads((OUT/'preparation/inventory.json').read_text());comparable=[r for r in reproductions if r.get('available')]
    matches=sum(r['disposition_matches'] for r in comparable);n=sum(r['sample_comparisons'] for r in comparable)
    doc=Path(document) if document else ROOT/'docs/PHASE39O_RESOLVE.md'
    text=preparation_text(protocol)
    job_matches=sum(r['all_dispositions_match'] and r['selected_index_match'] for r in comparable)
    text+=f"\n## 재풀이 결과\n\n**{d['label']}**, 선택 {d['selected_variant']}. 완료 {len(jobs)}/{len(cases)*4} job×변형. V0 수치 disposition 일치 {matches}/{n}, 모든 disposition과 선택 index가 일치한 job {job_matches}/{len(comparable)}.\n\n{table(d['variants'])}\n\n{table(summary)}\n\nSLSQP 메시지 분포는 `messages.csv`, 수락해별 탈출 거리(1mm 호길이 표본의 최초 exact point clearance≥0.025)는 `escape.csv`, 재현성/원 온라인 disposition은 `reproduction.csv`에 저장했다. 거리 표본은 연속 certificate를 대체하지 않는다.\n"
    doc.write_text(text);return d

def preparation_text(p):
    inventory=json.loads((OUT/'preparation/inventory.json').read_text())
    from nomad_isaac.common import sha256_file
    return f'''# Phase39-O — R2/R3 재풀이 준비

준비 단계에서 데이터셋 재풀이·시뮬레이션 실행0회. 입력 {inventory['saved_jobs']} job, 입력 누락 {inventory['missing_jobs']}건(재구성 안 함). 저장 입력이 있는 NEGATIVE_DEPTH_AT_B job {inventory['saved_negative_depth_jobs']}건. 평가 범위 {p['selected_jobs']}건. SDF는 STORAGE_RETROFIT 로더로만 복원하며 raw/동결 코드는 수정하지 않는다.

Protocol FROZEN_OFFLINE SHA256: `{sha256_file(HERE/'protocol.json')}`.

대용량 입력 사본 `preparation/all_inputs.json`, `inputs.json`은 SSD 로컬에만 보존하고 Git에서 제외한다. 원격에는 코드·문서·검증 요약·입력 hash만 둔다. 사본이 없는 checkout에서는 `PYTHONPATH=research /usr/bin/python3 -m nomad_phase39o.prepare --refresh-inputs --validate`로 같은 보존 로그에서 다시 준비한다(재풀이 없음).

V3 추가 초기값 점검: {inventory.get('extra_initializations',{})}. ADDED가0이면 이번 입력에서 V3의 실제 초기값 집합은 V2와 같다. NoMaD/직전 경로가 짧다는 이유로 연장하거나 점을 반복하지 않는다.

| 변형 | 변경 |
|---|---|
| V0 | 동결 코드 그대로, pre-EC 수치 disposition·선택 index·경로를 기록값과 비교 |
| V1 | 검사점별 ξ≥0, 목적함수에1000Σξ; ξmax≤1e−6 및 원 제약 위반≤1e−7·certificate 등 기존 수락 조건 |
| V2 | V1 + c_B<0.025일 때만 c(s)=min(0.025,c_B−0.005+0.5s),0.3m 이후0.025; 음수 c_B 사전거부 제거 |
| V3 | V2 + 저장 NoMaD8 suffix/직전 설치 경로 초기값. B+10점,0.1~0.2m; 짧거나 간격 불충족인 추가 초기값만 제외 |

V0 재현성은 `repair_pool_jobs.jsonl`의 pre-EC 수치 disposition을 비교한다. 온라인 TIMEOUT/SUPERSEDED 등은 당시 제어/시간에 의존하므로 재현했다고 주장하지 않고 별도 열로 보존한다.

certificate는 기존 인접 waypoint 선분을0.3m에서 나누고, 각 닫힌 구간의 끝점 c(s_b)로 **동일한 exact segment-to-occupied-site 거리**를 판정한다. 구간을 더 잘게 쪼개 유리하게 만들지 않는다. c_B≥0.025이면 동결 certificate 그대로다. EC는 실행하지 않는다. **온라인 시 EC도 같은 c(s) 기준 필요**: 동결 EC(궤적 여유≥0.025)는 탈출 경로를 거절한다.

동결 c_B=d(B)−h/√2를 유지한다. 따라서 탈출 R3의 B점 제약은0.005−첫 구간 길이/16이며 최소 간격0.1m에서≤−0.00125m다. 최종 ξ 허용치와의 구조적 충돌을 별도 기록하고 상수는 바꾸지 않는다. R2 진전은 원 reference 끝점 방향, R3 진전은 저장 u_ref 방향이다.

SLW 전체 R2/R3 job 합산에서 V0보다 성공률≥30%p 증가 AND 전체 job p95≤1s AND 수락 해 재certificate 실패0이면 변형별 GO_ONLINE. 하나라도 통과하면 전체 GO_ONLINE이며 V1→V2→V3 순의 가장 단순한 통과 변형을 선택한다. 미완료 자료는 판정하지 않는다. 온라인 준비/실행은 하지 않는다.

동결과 같은 warmed4-process pool, BLAS1, SLSQP maxiter100/ftol1e−8,재시도0. 시간은 원 pool_wall_s(지도 복원·R3 cache·IPC·선택 포함,독립 audit 제외). 추정 {p['estimated_minutes']:.1f}분: 저장 job 시간에 변형별8배 보수적 계수와 추가 초기값 수,25% 여유·120s 고정 여유를 적용한 **계획 가정**이며 신규 실측이 아니다.55분에서 새 변형 job을 시작하지 않고 현재 job을 마친 뒤 PARTIAL로 저장한다. 같은 명령으로 미완료 부분만 재개한다.

```bash
cd {ROOT} && nohup env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase39o.run > ../artifacts/isaac6/phase39o_01.log 2>&1 < /dev/null &
```

진행 확인: `PYTHONPATH=research /usr/bin/python3 -m nomad_phase39o.run --status`. 산출물은 `research/results/phase39o/`, 완료/부분 종료 후 이 문서와 표가 자동 갱신된다. 이전 입력·결과를 덮어쓰지 않는다.
'''

if __name__=='__main__':generate()
