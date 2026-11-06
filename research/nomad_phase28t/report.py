"""Saved-log diagnosis and post-smoke timing report. No navigation is invoked."""
import argparse,csv,json,platform
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from .config import HERE,OUT,protocol,SMOKE_ROOT
from nomad_phase28.report import audit as frozen_audit

def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s] if Path(p).exists() else []
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def csv_write(p,rows):
    if not rows:p.write_text('');return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,keys,lineterminator='\n');w.writeheader();w.writerows(rows)
def quant(values,q=.5):
    v=[x for x in values if x is not None];return float(np.quantile(v,q)) if v else None
def table(rows):
    if not rows:return '없음'
    keys=list(rows[0]);fmt=lambda x:'—' if x is None else f'{x:.5g}' if isinstance(x,float) else str(x).replace('|','/')
    return '\n'.join(['| '+' | '.join(keys)+' |','|'+'|'.join(['---']*len(keys))+'|']+['| '+' | '.join(fmt(r.get(k)) for k in keys)+' |' for r in rows])
def duration(t,a,b):return (t[b]-t[a])/1e9 if t.get(a) is not None and t.get(b) is not None else None

def stage_values(result):
    t=result.get('timing',{});stages=defaultdict(float)
    for r in t.get('stages',[]):stages[r['name']]+=(r['end_ns']-r['start_ns'])/1e9
    entries=dict(total=result.get('wall_s'),worker_inclusive=result.get('worker_inclusive_wall_s'),
        B_prediction=duration(t,'B_prediction_start_ns','B_prediction_end_ns'),
        transport_thread_queue=duration(t,'submit_ns','transport_thread_start_ns'),
        SDF_copy=duration(t,'sdf_copy_start_ns','sdf_copy_end_ns'),
        send_to_worker_receive=duration(t,'parent_send_start_ns','worker_receive_ns'),
        field_attach=duration(t,'field_attach_start_ns','field_attach_end_ns'),
        submit_to_solver_enter=duration(t,'submit_ns','worker_solver_enter_ns'),
        worker_result_to_parent_receive=duration(t,'worker_send_start_ns','parent_receive_ns'),
        parent_decode=duration(t,'parent_receive_ns','parent_decode_end_ns'),**stages)
    return entries

def application_counts(cases):
    rows=list(cases)
    excluded=[r for r in rows if r.get('reason')=='DETOUR_STARTED']
    assert not any(r.get('applied',False) for r in excluded),'DETOUR_STARTED must be a discarded case'
    applied=sum(bool(r.get('applied')) and r['output_type'] in ('OPTIMIZED','INIT_ONLY') for r in rows)
    return dict(total=len(rows),detour_started_excluded=len(excluded),eligible=len(rows)-len(excluded),applied=applied)

def smoke_gate(case_count,numerical_accepted,applied,times,detour_started_excluded=0):
    assert 0<=detour_started_excluded<=case_count
    den=case_count-detour_started_excluded
    assert 0<=applied<=den
    fraction=applied/den if den else None;p95=quant(times,.95)
    passed=den>0 and fraction>=.7 and p95 is not None and p95<=.30
    return dict(label='GATE_PASS' if passed else 'GATE_FAIL',denominator='ALL_H_CASES_EXCEPT_DETOUR_STARTED',total_h_cases=case_count,detour_started_excluded=detour_started_excluded,denominator_n=den,applied=applied,application_fraction=fraction,compute_p95_s=p95,compute_samples=len(times),
        applied_among_all=applied/case_count if case_count else None,applied_among_numerically_accepted=applied/numerical_accepted if numerical_accepted else None)

def smoke_destinations(root):
    # Keep the existing smoke_01 technical-failure report and tables intact.
    suffix='_02' if Path(root).name=='phase28t_smoke_02' else ''
    return OUT/('smoke'+suffix),ROOT/('docs/PHASE28T_SMOKE'+suffix+'.md')

def smoke(root):
    p=protocol();out,doc=smoke_destinations(root);out.mkdir(parents=True,exist_ok=True)
    events=lines(root/'phase28_handoff.jsonl');cases={e['case_id']:e for e in events if e['event']=='CASE_OUTCOME'};cases.update({e['case_id']:e for e in events if e['event']=='CASE_SUMMARY'})
    results={e['job_id']:e['result'] for e in events if e['event']=='TIMING_RESULT' and e.get('result')};counts=application_counts(cases.values());applied=counts['applied']
    numerical=sum(r['output_type'] in ('OPTIMIZED','INIT_ONLY') for r in results.values());times=[r['wall_s'] for r in results.values()]
    assert p['gate']['denominator']=='ALL_H_CASES_EXCEPT_DETOUR_STARTED' and p['gate']['excluded_reasons']==['DETOUR_STARTED']
    gate=smoke_gate(len(cases),numerical,applied,times,counts['detour_started_excluded'])
    technical=(root/'launch_complete.json').exists() and not (root/'FAILED.json').exists()
    audit_result=None;technical_error=None
    if technical:
        try:audit_result=frozen_audit(root)
        except Exception as exc:technical=False;technical_error=repr(exc)
    if not technical:gate.update(label='GATE_FAIL',technical_failure=True)
    typed=[dict(scope='effective_case',type=k,count=v) for k,v in Counter(e['output_type'] for e in cases.values()).items()]
    typed += [dict(scope='ready_future',type=k,count=v) for k,v in Counter(r['output_type'] for r in results.values()).items()]
    typed += [dict(scope='worker_before_transport_deadline',type=k,count=v) for k,v in Counter(r.get('worker_output_type',r['output_type']) for r in results.values()).items()]
    stages=defaultdict(list);cpu_stages=defaultdict(list);rows=[]
    for job,r in sorted(results.items()):
        values=stage_values(r)
        for k,v in values.items():
            if v is not None:stages[k].append(v)
        t=r.get('timing',{});intervals=[i['interval_ns']/1e9 for i in t.get('iterations',[])]
        for item in t.get('stages',[]):cpu_stages[item['name']].append(item['cpu_ns']/1e9)
        case=next((c for c in cases.values() if c.get('job_id')==job),{})
        rows.append(dict(job_id=job,case_id=case.get('case_id'),case_type=case.get('output_type'),reason=case.get('reason'),numerical_type=r['output_type'],worker_type=r.get('worker_output_type'),
            applied=case.get('applied',False),compute_s=r.get('wall_s'),major_iterations_completed=t.get('completed_major_iterations'),iterations_at_timeout=t.get('iterations_at_timeout'),
            returned_nit=t.get('returned_nit'),timeout_stage=t.get('timeout_stage'),iteration_interval_p50_s=quant(intervals),iteration_interval_p95_s=quant(intervals,.95),
            mean_solver_s_per_completed_major=values.get('slsqp')/len(intervals) if intervals and values.get('slsqp') is not None else None,
            worker_cpu=t.get('worker_affinity'),**values))
    for e in events:
        cert=e.get('latest_certificate') if e['event']=='APPLIED' else (e.get('result') or {}).get('certificate') if e['event']=='FALLBACK' and isinstance(e.get('result'),dict) else None
        if cert and cert.get('timing'):
            d=duration(cert['timing'],'application_certificate_start_ns','application_certificate_end_ns')
            if d is not None:stages['application_certificate'].append(d)
    stage_rows=[dict(stage=k,n=len(v),p50_s=quant(v),p95_s=quant(v,.95),max_s=max(v),cpu_p50_s=quant(cpu_stages[k]),cpu_p95_s=quant(cpu_stages[k],.95)) for k,v in stages.items()]
    command_count=sum(e.get('feedback_commands',0) for e in cases.values());clip_count=sum(e.get('feedback_clipped_commands',0) for e in cases.values())
    summary=dict(cases=len(cases),detour_started_excluded=counts['detour_started_excluded'],gate_eligible_cases=counts['eligible'],case_reasons=dict(Counter(c['reason'] for c in cases.values())),jobs=len(results),actually_applied=applied,numerically_accepted=numerical,feedback_commands=command_count,feedback_clipped=clip_count,feedback_clip_fraction=clip_count/command_count if command_count else None,
        technical_validation='PASS' if technical else 'FAIL',technical_error=technical_error,original_evaluator=audit_result,
        compute_p50_s=quant(times),compute_p95_s=quant(times,.95),compute_max_s=max(times) if times else None,gate=gate)
    save(out/'summary.json',summary);save(out/'events.json',events);csv_write(out/'case_timing.csv',rows);csv_write(out/'stages.csv',stage_rows);csv_write(out/'outcome_types.csv',typed)
    csv_write(out/'gate_cases.csv',[dict(case_id=c['case_id'],job_id=c.get('job_id'),output_type=c['output_type'],reason=c['reason'],applied=c.get('applied',False),excluded_from_application_denominator=c['reason']=='DETOUR_STARTED') for c in cases.values()])
    affinity=read(root/'phase28t_affinity.json') if (root/'phase28t_affinity.json').exists() else {};worker=read(root/'phase28t_worker_provenance.json') if (root/'phase28t_worker_provenance.json').exists() else {}
    save(out/'affinity.json',dict(launch=affinity,worker=worker))
    doc.write_text('# Phase28-T single smoke\n\nExcluded H1/C0-H/seed201 run only; no campaign results.\n\nGate application ratio = actually applied OPTIMIZED/INIT_ONLY cases / (all H cases minus discarded DETOUR_STARTED cases). Only DETOUR_STARTED is excluded; SUPERSEDED, WORKER_BUSY and other reasons remain. The excluded count and per-case audit are in summary.json and gate_cases.csv.\n\n'+table([summary])+'\n\n'+table(typed)+'\n\n'+table(stage_rows)+'\n\n'+table(rows)+'\n\nIteration timestamps are completed major callbacks; internal SLSQP line searches/minor iterations are not exposed. Initialization total includes NA integration; submit-to-solver includes transport/copy/attach, so nested stages must not be summed. Application certificate is reported separately from compute budget. All dispatched completed-job times, including DETOUR_STARTED, timeout and other discarded jobs, enter compute p95; WORKER_BUSY has no dispatched job.\n\nAffinity: '+json.dumps(dict(launch=affinity,worker=worker),ensure_ascii=False)+'\n')
    return summary

def preparation():
    p=protocol();rows=read(OUT/'preparation/legacy_replay/results.json');manifest=read(OUT/'preparation/legacy_manifest.json')
    matched=[r for r in rows if r.get('offline_prediction_reproduced')];kernel=[r for r in rows if r.get('offline_scope')=='SOLVER_ONLY_SAVED_B']
    legacy=[]
    for name,key in [('dispatch→worker completion(total)','online_compute_s'),('before diagnostics(composite)','online_planning_s'),('diagnostic bookkeeping','online_diagnostic_s'),('dispatch→decision(wait, not compute)','online_wait_s')]:
        v=[r[key] for r in rows if r.get(key) is not None];legacy.append(dict(stage=name,n=len(v),p50_s=quant(v),p95_s=quant(v,.95),max_s=max(v) if v else None))
    pairs=[]
    for label,q in [('prediction reproduced',matched),('saved B solver-only',kernel)]:
        pairs.append(dict(scope=label,n=len(q),online_p50_s=quant([r['online_compute_s'] for r in q]),online_p95_s=quant([r['online_compute_s'] for r in q],.95),
            offline_p50_s=quant([r['offline_wall_s'] for r in q]),offline_p95_s=quant([r['offline_wall_s'] for r in q],.95),
            paired_online_minus_offline_median_s=quant([r['online_minus_offline_s'] for r in q]),paired_online_minus_offline_p95_s=quant([r['online_minus_offline_s'] for r in q],.95)))
    csv_write(OUT/'preparation/legacy_stage_summary.csv',legacy);csv_write(OUT/'preparation/paired_offline_summary.csv',pairs)
    stats=dict(cases=368,reasons=dict(Counter(r['online_reason'] for r in rows)),numeric_payloads=sum(r['numeric_details_available'] for r in rows),
        prediction_matches=len(matched),kernel_only=len(kernel),offline_types=dict(Counter(r.get('offline_type') for r in rows)),last_iterate_changed=sum(r['last_iterate_changed'] for r in rows))
    save(OUT/'preparation/diagnosis_summary.json',stats)
    tests=read(OUT/'preparation/tests.json');affinity=p['affinity_plan']
    command='cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase28t.smoke --output ../artifacts/isaac6/phase28t_smoke_01 > ../artifacts/isaac6/phase28t_smoke_01.log 2>&1 < /dev/null &'
    text=f'''# Phase28-T 준비 — 시간 구성 진단과 단일 smoke

**본 campaign·smoke·Isaac는 실행하지 않았다.** 저장368개 사건의 로그 분석과 동결0.15s R1 오프라인 재측정, 합성 단위테스트만 수행했다. 기존 주행 결과와 C0-NA·결정·R2/R3·필터·평가기·R1 비용/제약은 보존했다.

## 1. 기존368사건 진단

실제 H 적용0/368. 사건 이유는 `{stats['reasons']}`다. 완전한 numerical result가 남은 것은 {stats['numeric_payloads']}건이고 나머지는 CASE_SUMMARY의 총 시간만 있다.

{table(legacy)}

worker 시작·큐 진입, B 예측 시작/끝, NA 초기 적분 시작/끝, SLSQP 시작/끝, certificate 시작/끝은 **기존 로그에 없다**. planning_wall_s는 이들을 합친 값이므로 역으로 분해하거나 queue 시간으로 간주하지 않는다. initialization 메타데이터는 경로 적분이 끝났다는 사실만 알려주며 시간은 알려주지 않는다.

358개 TIMEOUT payload의 iterations=0은 정상 solver 반환 전 예외가 나면 그대로 남는 기본값이다. 초기 x와 마지막 x가 다른 {stats['last_iterate_changed']}건에서 solver가 진행된 흔적은 있지만 **TIMEOUT의 정확한 반복 번호는 복원 불가**다. 이번에는 완료 major callback마다 timestamp와 CPU 시간을 기록하고 timeout 시 완료 callback 수를 남긴다. 내부 line-search/minor iteration 수는 SciPy가 공개하지 않으므로 주장하지 않는다.

### 같은 실제 입력의 오프라인 비교

이전 R1 표본은 Phase27-R 자료라 이번 Phase28-C0-H368건과 단순히 seed/id로 짝지을 수 없다. 이번 실제 DISPATCH의 선택 경로·snapshot·예측B/vw를 동결 R1로 한 번씩 다시 풀었다(한도0.15s 유지). 이전 H 적용이0이라 실제 warm state는 모두None이다. 가능하면 저장 OLD NA 상태를 복원하고 같은72Hz 예측을 수행해 B/vw가1e−10 이내로 일치하는지 확인했다.

{table(pairs)}

prediction reproduced {len(matched)}건은 예측+풀이를 포함한 오프라인 시간이다. 나머지 {len(kernel)}건은 저장 B를 직접 쓴 solver-only 비교이며 B 예측 시간이 빠져 있어 전체 dispatch 시간의 동등 비교가 아니다. 두 범위를 섞어 순수 SLSQP speedup으로 주장하지 않는다. 온라인은 Isaac·NoMaD와 동시 실행된 값, 오프라인은 `/usr/bin/python3`에서 계측한 값이다. 원 온라인 NumPy/SciPy 버전과 thread CPU/GIL 대기는 기록되지 않아 계산 지연을 CPU 경쟁 하나로 단정할 수 없다. 오프라인 출력 분포: `{stats['offline_types']}`. 기존 결과는 재분류하지 않는다.

## 2. 사전 고정 시간·자원 정책

- 적용: dispatch 후 **세 번째9Hz tick**, 즉24개의72Hz tick 뒤(0.333333s). B는 원 실행기와 원 plant 적분 함수로 그 tick까지 예측한다. 비용·제약·초기화·fallback 선택 규칙·controller·지도는 같다.
- 계산 예산: **0.30s**, dispatch에서 B 예측·대기·전송·worker·certificate·결과 수신까지 포함한다. 넘으면 FALLBACK. worker 계산이 성공했어도 전송 포함 시간이 넘으면 수락하지 않고 원 numerical type을 별도 보존한다.
- 기존 R1.solve의 세0.15시간 비교만0.30으로 치환하고 원 함수·factor·Jacobian을 재사용한다. AST 검사와 수치 동등성 테스트로 다른 상수/식을 바꾸지 않았음을 확인한다.
- 기존 thread는 Isaac와 PID/GIL을 공유하므로 H 수치 worker만 별도 프로세스로 옮긴다. 실제 Isaac 부모의 Python executable, NumPy/SciPy 파일 경로·버전을 그대로 넘기고 일치를 검사한다. 새 venv나 패키지는 설치하지 않는다. R2/R3 worker는 변경하지 않는다.
- 선택 core 계획: `{affinity}`. worker는 CPU {affinity.get('worker_cpu')}에, Isaac/NoMaD 등 이 launcher의 자식들은 나머지 driver CPU에 고정한다. SMT sibling도 driver에서 제외한다. `os.sched_setaffinity` 실패/지원 불가 시 사유와 실제 mask를 기록하며 분리 성공을 허위로 표시하지 않는다. 다른 사용자 프로세스의 affinity는 바꾸지 않는다.

SDF는 immutable array를 공유 메모리로 복사해 전송하며 값/점유/관측 배열은 바꾸지 않는다. 큐·복사·IPC·attach·worker·반복별·certificate·반환 timestamp를 남기고, 계산 p95에 전송 overhead도 포함한다. solver cost/constraints나 선택·우회 정책을 수정하는 추가 최적화는 없다.

## 3. 계측 및 smoke report

새 로그: `phase28_handoff.jsonl`의 TIMING_RESULT에 모든 dispatched job의 최종 계측(폐기/timeout 포함), WORKER_READY에 PID·core·library 정보를 남긴다. 원 CASE_OUTCOME/CASE_SUMMARY/COMMAND 로그도 유지한다. 단계는 B prediction, client queue, SDF copy, send→receive, attach, NA72Hz 초기 적분, SLSQP, 초기/최종 certificate, application certificate, result receive/decode/cleanup으로 나눈다. nested 구간(예: initialization_total 안의 NA 적분)을 합산하지 않는다.

smoke report는 사건별 시간 분포 CSV, OPTIMIZED/INIT_ONLY/FALLBACK(실제 case·future·worker 원출력별), 실제 적용 수, feedback clip 비율, 단계별 p50/p95/max, 완료 major 반복 수·간격·반복당 시간을 출력한다. application certificate는 계산 예산과 별도로 표시한다. 알 수 없는 값은NA로 남긴다.

게이트는 사용자 확정대로 다음을 모두 만족해야 한다.

- **실제 적용된 OPTIMIZED 또는 INIT_ONLY 사건 수 / (전체 H 사건 수 − 버려진 DETOUR_STARTED 사건 수) ≥70%.** R2/R3 우회 시작으로 버려진 DETOUR_STARTED만 분모에서 제외하고 그 수를 별도 보고한다. SUPERSEDED, WORKER_BUSY, TIMEOUT, TERMINAL 등 다른 사유는 모두 분모에 포함한다. 사건별 포함·제외는 `gate_cases.csv`에 남긴다.
- **전체 dispatched job 계산 p95≤0.30s**는 그대로 유지한다. DETOUR_STARTED가 적용 비율 분모에서 제외되어도 해당 job의 측정 계산시간은 p95에 포함한다. 시간초과·다른 폐기 job도 제외하지 않는다. WORKER_BUSY는 계산을 시작한 job이 없으므로 사건 수에는 포함하되 계산 p95에는 넣지 않는다.

전체 H 사건 대비 원 비율과 numerical OPTIMIZED/INIT_ONLY 대비 적용률도 참고로 보고하지만 게이트에는 사용하지 않는다. 기술 실패나 유효 분모0은 통과로 처리하지 않는다.

## 4. 준비 검증·명령(실행하지 않음)

단위테스트 {tests['tests_run']}개 통과. 적용 tick, 예측 적분, budget-only AST, factor/제약 수치 보존, timeout 반복 계측, 프로세스 전달·affinity 선택, report/gate를 검증했다. 실제 H1 렌더/NoMaD/주행 smoke는 실행하지 않았다. Protocol SHA256 `{sha256_file(HERE/'protocol.json')}`.

H1 × C0-H × seed201 **한 번만**, 기존90초 주행 상한을 유지한다. 본 campaign 호출이나 자동 재시도는 없다. 기존 smoke 폴더가 있으면 덮어쓰거나 재실행하지 않는다. 결과는 본 실험에서 제외한다. 완료 후 `docs/PHASE28T_SMOKE.md`, `research/results/phase28t/smoke/`를 생성한다.

```bash
{command}
```

로그 확인: `tail -n 20 /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase28t_smoke_01.log`

report 재생성: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase28t.report --smoke-root ../artifacts/isaac6/phase28t_smoke_01`
'''
    (ROOT/'docs/PHASE28T_PREP.md').write_text(text)
    return stats

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--smoke-root',type=Path,default=SMOKE_ROOT);a=ap.parse_args()
    print(json.dumps(preparation() if a.prepare else smoke(a.smoke_root.resolve()),ensure_ascii=False))

if __name__=='__main__':main()
