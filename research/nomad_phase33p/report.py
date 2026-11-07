"""Offline gate report. A failed gate cannot produce a campaign command."""
import argparse,json,shutil
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase32o.evaluate import save,csvout
from .config import OUT,HERE

def summarize(rows):
    result=[]
    for scope in ('ALL','NORMAL','R2','R3'):
        for variant in ('G18','G18X'):
            group=[r for r in rows if r['variant']==variant and (scope=='ALL' or r['state']==scope)]
            n=len(group);solved=sum(r['solve_success'] for r in group);passed=sum(r['solve_and_ec'] for r in group)
            result.append(dict(scope=scope,variant=variant,n=n,solve_successes=solved,solve_success_rate=solved/n if n else None,
                ec_pass_given_solution=passed/solved if solved else None,solve_and_ec_count=passed,solve_and_ec_rate=passed/n if n else None,
                compute_p50_s=float(np.median([r['compute_s'] for r in group])) if n else None,
                compute_p95_s=float(np.quantile([r['compute_s'] for r in group],.95)) if n else None,
                installed_ec_count=sum(r['installed_ec_pass'] for r in group),
                failure_reasons=dict(Counter(r['failure_reason'] for r in group if not r['solve_success']))))
    return result

def decide(summary):
    old=next(r for r in summary if r['scope']=='ALL' and r['variant']=='G18');new=next(r for r in summary if r['scope']=='ALL' and r['variant']=='G18X')
    assert old['n']==new['n']==247
    checks=dict(solve_success_at_least_80_percent=new['solve_success_rate']>=.8,
                compute_p95_at_most_150ms=new['compute_p95_s']<=.15,
                overall_solve_and_ec_strictly_better=new['solve_and_ec_rate']>old['solve_and_ec_rate'])
    return dict(label='OFFLINE_OK' if all(checks.values()) else 'OFFLINE_FAIL',checks=checks,failed_checks=[k for k,v in checks.items() if not v],
                population=247,baseline=old,variant=new,navigation_started=0,main_prepared=False)

def table(rows):
    if not rows:return '없음'
    keys=list(rows[0]);return '\n'.join(['| '+' | '.join(keys)+' |','| '+' | '.join('---' for _ in keys)+' |',*['| '+' | '.join(str(r.get(k,'')).replace('|','/') for k in keys)+' |' for r in rows]])

def generate():
    rows=json.loads((OUT/'offline_rows.json').read_text());assert len(rows)==494
    summary=summarize(rows);decision=decide(summary);save(OUT/'decision.json',decision);csvout(OUT/'summary.csv',summary)
    failures=[]
    for file in sorted((OUT/'cases').glob('*.json')):
        case=json.loads(file.read_text())
        for variant,data in case['numerical'].items():
            result=data['result'];details=result.get('details',{})
            if 'results' in details:
                for candidate in details['results']:
                    if not candidate.get('accepted'):
                        failures.append(dict(case_id=case['case_id'],variant=variant,state=details['kind'],reason=candidate.get('disposition'),status=candidate.get('solver_status'),message=candidate.get('message',candidate.get('error'))))
            elif not result['solve_success']:
                failures.append(dict(case_id=case['case_id'],variant=variant,state='NORMAL',reason=result['reason'],status=details.get('status'),message=result.get('error',details.get('message'))))
    csvout(OUT/'failure_details.csv',failures)
    failure_table=[dict(variant=v,state=s,reason=r,count=n) for (v,s,r),n in Counter((r['variant'],r['state'],r['reason']) for r in failures).items()]
    storage=json.loads((OUT/'storage/summary.json').read_text());sampling=json.loads((OUT/'sampling.json').read_text());p=json.loads((HERE/'protocol.json').read_text())
    shown=[]
    for r in summary:
        shown.append({'대상':r['scope'],'방법':r['variant'],'n':r['n'],'(a) solve 성공':f"{r['solve_successes']}/{r['n']} ({r['solve_success_rate']:.1%})",'(b) 해 존재 시 EC PASS':'없음' if r['ec_pass_given_solution'] is None else f"{r['ec_pass_given_solution']:.1%}",
                      '(c) 전체 solve+EC':f"{r['solve_and_ec_count']}/{r['n']} ({r['solve_and_ec_rate']:.1%})",'계산 p50/p95 (s)':f"{r['compute_p50_s']:.6f} / {r['compute_p95_s']:.6f}",'실제 설치 경로 EC(참고)':f"{r['installed_ec_count']}/{r['n']}"})
    text=f'''# Phase33-P 준비: G18X + EC

**{decision['label']}** — 실제 주행/Isaac/NoMaD 추론 실행0. 게이트는247개 전체로 계산했다. 원래300개 요청은 사전 답변에 따라 NORMAL200 + R2전체7 + R3전체40의 고유 사건247개로 고정했다.

Protocol SHA256: `{sha256_file(HERE/'protocol.json')}` (`FROZEN_OFFLINE`). 입력 cohort SHA256: `{p['cohort_sha256']}`.

## 고정한 변경

| 항목 | Phase32 G18+EC | G18X |
| --- | --- | --- |
| NORMAL / R2 / R3 곡률 hard 상한 | 각각 기존 상한 | 모두2.0 m⁻¹ |
| SDF hard 기준 | 기존 .025m 및 기존 R2/R3 시작 완화 | 기존 기준 + e(κ) |
| e(κ) | 없음 | R−√(R²−.25²), R=1/abs(κ), κ=0이면0 |
| 검사점 곡률 | — | 해당 선분 양 끝 Menger 곡률의 큰 절댓값. 경로 양 끝은 가까운 내부 곡률 |
| 시작 .30m | 기존 완화 | 같은 완화 기준에 e 추가 |
| soft 여유 / 목적함수 / solver / 초기화 | 동결 | 그대로 재사용 |
| EC·결정 계층·지도·필터·C0-NA·평가기 | 동결 | 변경 없음 |

기존 h/√2 + 선분 길이/16 보수적 여유와 exact certificate 알고리즘/허용오차도 유지한다. 기존 NORMAL의 이전 ω/v 초기화 검사는 새 hard 상한2에 맞춘다. e의 Jacobian은 Menger 해석적 미분을 재사용한다. 비허용 반복점 abs(κ)>2에서는 경계의 접선 연장으로 유한값을 제공한다. 허용 해 영역에서는 주어진 수식 그대로다. abs/max의 동점은 왼쪽, κ=0은0 subgradient를 사용한다. 가중치·상수 튜닝은 없다.

## 저장 정책 v2와 Phase32 변환

새 snapshot/repair input은 `savez_compressed`로 values를 저장하지 않는다. occupied·observed·origin·h·radius·기존 tick 배열과 트리거에 필수인 component ID/birth metadata를 보존한다. 복원은 STORAGE_RETROFIT 로더를 사용한다. 빈 지도의 원래 상수와 dtype/order, 원래 metadata 문자열은 저장 metadata에만 보존해 반올림 오차 없이 복원한다. 라이브 지도 update/EDT 계산은 변경하지 않는다. 기존 R3의 일시적 derived cache 전송은 동결 구현을 유지하며 오프라인 cache는 사례별 계산 후 삭제한다.

Phase32 변환: {storage['files']:,}개 검사, {storage['converted']:,}개 변환, 건너뜀 {storage['skipped']}개; **{storage['saved_bytes']/1e9:.3f}GB 절감**. 백업 생성0. 모든 배열을 임시 파일 복원 결과와 비트 비교한 후 원자 교체했다. 원래/새 SHA와 배열 digest는 [storage manifest](../research/results/phase33p/storage/roots/phase32_01/manifest.jsonl)에 있다. 기존 Phase32 코드·결과 문서는 수정하지 않았다.

## 표본·평가 정의

- seed20261108, NORMAL은 전체1,419개 중200개를 비복원 추출. R2전체7, R3전체40. 고유 사건247개이며 일부 사건은 같은 원래 Graph job의 다른 설치 시점이다. 원래 입력은 모두 저장 SUBMIT/transport에서 확보했다. NORMAL previous_xy는 이전의 실제 적용 Graph RESULT 순서로 복원했다.
- **R2 n=7**은 기술적·서술적 자료이며 독립적인 신뢰성 결론을 내리기에 작다. 상태별 표는 참고이고 게이트는247개 전체만 사용한다.
- 기준은 EC로 선별된 설치 경로가 아니라 **각 알고리즘이 같은 입력에서 내는 수치 해**다. NORMAL은 단일 해, R2/R3는 전체 후보 job이 기존 규칙으로 EC 전에 선택한 해를 검사한다. 실패/해 없음은 EC 불통과다.
- (a)는 기존 accepted/feasible 정의(optimizer 성공 + hard 제약 + certificate)를 만족해 선택 가능한 해의 비율이다. (b)는 이 해가 있을 때의 EC PASS, (c)는 전체247개 대비 solve 성공 AND EC PASS다. 게이트 비교는(c)다.
- EC에는 양쪽 모두 같은 저장 설치 시점의 CHECK pose·실제(v,ω)·depth snapshot·속도 상한을 쓴다. 실제 PATH_APPLIED 경로는 참고 열로 별도 재검사했다. 이는 고정 저장 입력에 대한 반사실이며 새 계산시간에 따른 폐루프 상태 변화·미래 FRESH·supersession을 재현하지 않는다.
- NORMAL 계산시간은 CPU7의 constructor+solve+certificate. R2(8 sample)/R3(7 초기값)는 기존4-process pool 전체 job 시간이며 SDF load/cache/I/O를 포함한다. 프로세스 시작·오프라인 cache 삭제·후속 EC 시간은 제외한다. baseline-first/X-first를 사건마다 교대하고 각 방법을1회씩 계산했다.

## 오프라인 결과

{table(shown)}

{table([{'게이트 조건':k,'충족':v} for k,v in decision['checks'].items()])}

기준: solve 성공≥80%, 계산 p95≤0.15s, (c)가 G18보다 엄격히 큼. 판정: **{decision['label']}**.

## 실패 사유

아래 R2/R3 수는 job 내부의 sample/초기값별 실패 수이며, 위 사건 분모와 다르다.

{table(failure_table)}

## 실행 준비 상태

'''
    if decision['label']=='OFFLINE_FAIL':
        text+='게이트 미충족이므로 사용자 지시에 따라 **실행 준비를 중단**한다. 본 campaign/20-run launcher/dry-run/nohup 명령을 생성하거나 실행하지 않았다. 조건부20개 블록 순열·판정은 protocol에 명시돼 있지만 실행 승인은 없다. 실패한 조건: '+', '.join(decision['failed_checks'])+'.\n'
    else:text+='OFFLINE_OK: 다음 단계는 조건부20-run 실행기 연결·단위테스트·dry-run 준비다. 본 주행은 실행하지 않는다. 준비가 끝나기 전에는 실행 명령을 제공하지 않는다.\n'
    text+='\n결과 원자료: [offline.csv](../research/results/phase33p/offline.csv), [summary.csv](../research/results/phase33p/summary.csv), [decision.json](../research/results/phase33p/decision.json).\n'
    (ROOT/'docs/PHASE33P_PREP.md').write_text(text)
    print(json.dumps(decision))
    return decision

if __name__=='__main__':generate()
