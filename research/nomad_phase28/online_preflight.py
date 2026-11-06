"""Saved-case integration parity and dated user deviation. Never starts Isaac."""
import argparse,copy,csv,io,json,subprocess
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase20d.recent import RecentSnapshot
from .config import HERE,PARAMETERS,RUN_ROOT

OUT=ROOT/'research/results/phase28_r1_online'
R1=ROOT/'research/results/phase28_r1'
def read(p):return json.loads(Path(p).read_text())
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def csv_write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def freeze():
    assert not (HERE/'active_protocol.json').exists(),'Active registration already exists'
    assert not RUN_ROOT.exists(),'Preserve any existing campaign data; do not mix revisions'
    OUT.mkdir(parents=True,exist_ok=True)
    old=read(HERE/'protocol.json');frozen=read(HERE/'protocol_r1.json');gate=read(R1/'gate.json')
    assert gate['label']=='GATE_FAIL' and frozen['parameters']==PARAMETERS==old['parameters']
    manifest=read(R1/'sample_same.json');cases={c['event_key']:c for c in manifest['cases']};results=read(R1/'same/events.json');bykey={r['event_key']:r for r in results}
    warm={};warm_keys={}
    for c in sorted(manifest['cases'],key=lambda c:(c['output'],c['time_s'])):
        warm_keys[c['event_key']]=warm.get(c['output'])
        if bykey[c['event_key']]['accepted']:warm[c['output']]=c['event_key']
    selected=[]
    for kind,n in [('OPTIMIZED',8),('INIT_ONLY',6),('FALLBACK',6)]:
        # Functional branch coverage, not a performance sample. Deadline behavior
        # is unit-tested separately; wall-clock-sensitive TIMEOUT is excluded.
        groups=defaultdict(list)
        for r in results:
            if r['output_type']==kind and r['disposition']!='TIMEOUT':groups[r['scene']].append(r)
        for q in groups.values():q.sort(key=lambda r:r['event_key'])
        chosen=[]
        while len(chosen)<n:
            for scene in sorted(groups):
                if groups[scene] and len(chosen)<n:chosen.append(groups[scene].pop(0))
        for r in chosen:
            c=cases[r['event_key']]
            selected.append(dict(case=c,warm_predecessor=warm_keys[c['event_key']],expected_output=r['output_type'],
                expected_file=str(R1/'same'/(r['event_key']+'.json')),expected_sha256=sha256_file(R1/'same'/(r['event_key']+'.json'))))
    assert len(selected)==len({r['case']['event_key'] for r in selected})==20
    save(OUT/'parity_manifest.json',dict(selection='8OPTIMIZED/6INIT_ONLY/6non-timeoutFALLBACK; deterministic round-robin scenes then event_key, frozen before replays; timeout tested independently',
        scope='Functional integration equivalence, not a new acceptance-rate estimate',cases=selected))
    doc=ROOT/'docs/PHASE28_PREP_R1.md';(OUT/'original_gate_report.md').write_bytes(doc.read_bytes())
    stamp=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
    deviation=dict(user_authorized=True,date=stamp,original_gate_label='GATE_FAIL',original_gate=gate,
        user_rationale='FALLBACK uses frozen C0-NA, therefore user accepts the narrowly failed gate and elects to drive',
        caveat='Same fallback does not guarantee no worse outcome: waiting, state, accepted paths, and handover timing can differ.',
        action='Exception to eligibility gate only; R1 values, costs, limits and0.15s deadline unchanged; no navigation by agent')
    p=copy.deepcopy(old);p.update(runtime_revision='R1',original_protocol_sha256=sha256_file(HERE/'protocol.json'),
        frozen_r1_protocol_sha256=sha256_file(HERE/'protocol_r1.json'),gate_file=str((R1/'gate.json').relative_to(ROOT)),gate_sha256=sha256_file(R1/'gate.json'),deviation=deviation,
        parity_manifest=str((OUT/'parity_manifest.json').relative_to(ROOT)),parity_manifest_sha256=sha256_file(OUT/'parity_manifest.json'))
    p['implementation_definitions']=dict(frozen['changes'],online='Frozen R1 solver+R1Follower bound into unchanged H dispatch/apply lifecycle',
        telemetry='CASE_OUTCOME, COMMAND, CASE_SUMMARY; effective and numerical output types, reason, compute, clip counts; discarded cases separate by reason/applied')
    frozen_sources={f:h for f,h in old['source_sha256'].items() if f not in ('research/nomad_phase28/config.py','research/nomad_phase28/simulator.py','research/nomad_phase28/report.py')}
    frozen_sources.update(frozen['source_sha256'])
    for f,h in frozen_sources.items():assert sha256_file(ROOT/f)==h,f
    p['frozen_numerical_sources']=frozen_sources
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in sorted(HERE.glob('*.py'))}
    target=HERE/'protocol_online_r1.json';save(target,p);save(HERE/'active_protocol.json',dict(file=target.name,sha256=sha256_file(target)))
    save(OUT/'deviation.json',deviation)
    print(json.dumps(dict(date=stamp,protocol_sha256=sha256_file(target),cases=20,original_gate=gate['label'])))

def fixture(case,expected,warm,field,pool,cache):
    from .online_r1 import R1Execution
    from .offline import previous_controller
    obj=object.__new__(R1Execution);obj.init_telemetry();obj.alpha=expected['alpha'];obj.pending_h=None;obj.warm_h=warm;obj.h_future=None;obj.h_id=0;obj.h_pool=pool
    obj.h_log=io.StringIO();obj.sp=previous_controller(case,cache);obj.follower=obj.sp.follower if obj.sp else None
    obj.last_command=list(case['previous_vw']);obj.plant=SimpleNamespace(actual_w=case['previous_vw'][1],alpha=float(read(Path(case['output'])/'scenario.json')['plant_alpha']))
    obj.snapshot=field;obj.depth_maps=SimpleNamespace(snapshot=lambda:field);obj.detour=None;obj.recovery=SimpleNamespace(state='NORMAL')
    obj.path_source_id=None;obj.path_kind=None;obj.mode='NORMAL';obj.repair_active=False;obj.last_application_ns=0
    obj.rlog=lambda *a,**kw:None
    core=SimpleNamespace(pose=np.asarray(case['B'],float),v=case['previous_vw'][0],w=case['previous_vw'][1])
    refresh=dict(simulation_time_s=case['time_s'],monotonic_ns=case['application_monotonic_ns'],valid=True)
    return obj,core,refresh

def parity():
    from .config import verify
    from .runtime import NAExecution
    from .alignment import NoAlignment
    from .graph_r1 import R1Follower
    verify();assert not (OUT/'parity_results.json').exists(),'No automatic test-case re-solves'
    spec=read(OUT/'parity_manifest.json');stored={r['event_key']:r for r in read(R1/'same/events.json')};cache={};rows=[]
    (OUT/'case_logs').mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=1,thread_name_prefix='online-r1-parity') as pool:
        for i,item in enumerate(spec['cases']):
            c=item['case'];expected=stored[c['event_key']];warm=copy.deepcopy(stored.get(item['warm_predecessor']))
            assert sha256_file(Path(item['expected_file']))==item['expected_sha256'];assert sha256_file(Path(c['snapshot']['file']))==c['snapshot_sha256']
            field=RecentSnapshot.load(c['snapshot']['file']);obj,core,refresh=fixture(c,expected,warm,field,pool,cache)
            obj.new_path(c['selected_path'],core,refresh,c['native_id'],'SAFE')
            result=obj.h_future.result(timeout=5);job=obj.pending_h;prediction=job['prediction']
            np.testing.assert_allclose(prediction['pose'],expected['prediction']['pose'],atol=1e-12,rtol=0);np.testing.assert_allclose(prediction['vw'],expected['prediction']['vw'],atol=1e-12,rtol=0)
            before_tick=prediction['apply_tick']-8;obj.collect_h(core,dict(refresh,simulation_time_s=before_tick/72),None);assert obj.pending_h is not None
            core.pose=np.asarray(prediction['pose']);core.v,core.w=prediction['vw'];obj.last_command=list(prediction['vw']);obj.plant.actual_w=core.w
            refresh=dict(refresh,simulation_time_s=prediction['apply_tick']/72,monotonic_ns=refresh['monotonic_ns']+round(prediction['delay_s']*1e9));obj.r1_now_s=refresh['simulation_time_s']
            obj.collect_h(core,refresh,None)
            same_type=result['output_type']==expected['output_type'];pose_error=dt_error=None
            if result['accepted'] and expected['accepted']:
                pose_error=float(np.max(np.abs(np.asarray(result['poses'])-expected['poses'])));dt_error=float(np.max(np.abs(np.asarray(result['dt'])-expected['dt'])))
                reference=R1Follower(expected,refresh['simulation_time_s'],obj.alpha)
            else:
                reference=NoAlignment();reference.replace_path(c['selected_path'],core.pose,core.v)
            actual_cmd,diag=obj.sp.control(core.pose,core.v);expected_cmd,_=reference.control(core.pose,core.v);command_error=float(np.max(np.abs(np.asarray(actual_cmd)-expected_cmd)))
            core.v,core.w=actual_cmd
            # The numerical/live H write path is real; only unrelated parent
            # simulator bookkeeping is mocked in this saved-input fixture.
            with patch.object(NAExecution,'write_command',autospec=True):obj.write_command(core,refresh,None,prediction['vw'],prediction['vw'],'HANDOFF' if result['accepted'] else 'NORMAL',diag)
            obj.finalize_telemetry();logs=[json.loads(s) for s in obj.h_log.getvalue().splitlines()];obj.h_log.close()
            outcomes=[r for r in logs if r['event']=='CASE_OUTCOME'];summaries=[r for r in logs if r['event']=='CASE_SUMMARY'];assert len(outcomes)==len(summaries)==1
            effective=outcomes[0]['output_type'];matches=same_type and effective==expected['output_type'] and (pose_error is None or pose_error<=1e-6) and (dt_error is None or dt_error<=1e-6) and command_error<=1e-6
            row=dict(event_key=c['event_key'],expected=expected['output_type'],online_solver=result['output_type'],online_applied=effective,
                match=matches,pose_max_error_m_or_rad=pose_error,dt_max_error_s=dt_error,first_command_max_error=command_error,
                original_wall_s=expected['wall_s'],online_wall_s=result['wall_s'],feedback_clip=summaries[0]['feedback_clip_any'],reason=outcomes[0]['reason'])
            rows.append(row);save(OUT/'case_logs'/(c['event_key']+'.json'),dict(comparison=row,events=logs,numerical_result=result))
            print('[parity]',i+1,'/20',matches,flush=True)
    save(OUT/'parity_results.json',rows);csv_write(OUT/'parity_results.csv',rows)
    print(json.dumps(dict(cases=20,matches=sum(r['match'] for r in rows),types=dict(Counter(r['online_applied'] for r in rows)))))

def document():
    from .config import verify
    from nomad_phase26 import campaign as base
    p=verify();results=read(OUT/'parity_results.json');tests=read(OUT/'tests.json');assert all(r['match'] for r in results)
    archive=OUT/'original_gate_report.md';original=archive.read_text();gate=read(R1/'gate.json')
    assert gate==p['deviation']['original_gate'];assert p['main_order']==read(HERE/'protocol.json')['main_order']
    old=base.protocol;base.protocol=lambda:p
    try:jobs=base.jobs(RUN_ROOT)
    finally:base.protocol=old
    disk=base.capacity(RUN_ROOT,[dict(j,method='C0') for j in jobs]);save(OUT/'capacity.json',disk)
    command=read(ROOT/'research/results/phase28/preparation/commands.json')['campaign'];status=read(ROOT/'research/results/phase28/preparation/commands.json')['status']
    addition=f'''\n\n## 사전등록 이탈 — 사용자 승인에 따른 R1 주행 진행

**승인 기록 날짜: {p['deviation']['date']} (Asia/Seoul).** 원 게이트와 수치는 위와 같이 **GATE_FAIL**로 유지한다. 사용자 요청에 따라 이 eligibility gate를 예외적으로 넘어서 주행 준비를 진행한다. GATE_PASS로 재분류하거나 수락률 기준을 낮추지 않는다.

사용자가 제시한 근거는 “FALLBACK 때 동결 C0-NA 실행기를 적용하므로 C0-H가 C0-NA보다 불리해질 수 없다”는 것이다. 이는 **진행을 승인한 사용자 판단의 근거**로 기록한다. 동일 fallback만으로 비열등성이 보장되지는 않는다. H 계산 중 대기·OLD 진행, 적용 시점과 로봇 상태, 수락된 궤적, 추후 관측/전환이 달라질 수 있다. 따라서 결과는 실측으로 판단하며 사전에 우월성/비열등성을 가정하지 않는다.

### 활성 protocol과 변경 범위

활성 파일: `research/nomad_phase28/protocol_online_r1.json`, SHA256 `{sha256_file(HERE/'protocol_online_r1.json')}`. `active_protocol.json`이 이 hash를 검증한다. 원 Phase28 protocol과 R1 수치 동결 protocol은 별도 파일로 보존했고 R1 gate.json hash도 검증한다. 예외 승인 날짜·원 수치·검증 manifest·source hash가 활성 protocol에 포함된다.

C0-H만 **R1 solver + R1Follower**로 연결했다. C0-NA, 결정 계층, R2/R3, depth 지도/필터, 평가기, R1 비용/수치/제약/0.15s 한도는 변경하지 않았다. 기존 H의 dispatch→예측B→제어 tick 적용→최신지도 certificate→fallback lifecycle의 함수 본체를 그대로 바인딩하며 solver/follower 참조만 R1으로 교체했다. 원 H 구현도 보존한다.

### 온라인 로그와 보고 지표

`phase28_handoff.jsonl`에 사건당 `CASE_OUTCOME`과 종료 시 `CASE_SUMMARY`를 기록한다: OPTIMIZED/INIT_ONLY/FALLBACK, 사유, numerical solver 유형, 실제 적용 여부, 계산시간, feedback 명령·clip 수/비율. 분모는 H 대상인 NORMAL SAFE FRESH 사건이며 R2/R3 우회 사건은 포함하지 않는다. H 실행 명령마다 `COMMAND`에 case_id·출력 유형·clip flag를 기록한다. superseded/다른 모드/종료로 버린 사건은 실제 H 사용이 없으므로 effective FALLBACK으로 분류하되, 이것이 명시적 NA 경로 설치였는지는 별도 flag와 사유로 구분한다. 늦게 끝난 solver 시간은 최종 summary에서 보충하며, 알 수 없는 계산시간은0으로 만들지 않는다. WORKER_BUSY는 새 풀이를 시작하지 않았으므로 계산시간0으로 따로 구분한다.

report 틀은 도착·충돌, 도착시간(성공 조건부), 평균속도, 정지비율, 정렬 회전/감속비율, 최소 여유를 방법×장면별로 포함한다. Phase27-R 재사용 C0와 같은 scene×seed의 연속 지표 차이를 계산한다. H 사건 유형 비율은 사건 수로 가중 집계하고 solver 유형과 실제 적용 유형을 분리한다. feedback clip 비율도 명령 수로 가중 집계한다. 원 평가 함수와 기술 실패 제외 규칙은 그대로이며 새로운 성능 판정 기준은 추가하지 않는다.

### 검증 — 새 시뮬레이션 없음

단위테스트 **{tests['tests_run']}개 통과**. 기존 저장 사건20개를 branch coverage 목적으로 사전에 고정했다(OPTIMIZED8 / INIT_ONLY6 / 비-timeout FALLBACK6; scene 순환 후 event_key 순). 성능률 추정용 재표본이 아니다. 시간 경계는 별도 deterministic 단위테스트로 확인한다.

온라인의 실제 dispatch 함수·단일 worker·R1 solver·적용 함수·추종기·로그를 호출해 **20/20 사건이 저장 오프라인 R1 결과와 일치**했다. 원200개 이력의 정확한 직전 수락 warm 상태와 같은 snapshot을 사용했고, 새 FRESH/지도 변경이나 Isaac 폐루프는 만들지 않았다. 예상 pose/속도는1e−12, 경로·dt·첫 명령은1e−6 허용오차로 검증했다. nominal 적용 tick 이전에는 적용되지 않는지도 확인했다. 입력 로딩/인공 제어 tick fixture와 무관한 부모 simulator bookkeeping만 mock했으며, solve 결과나 시간을 mock하지 않았다. 상세는 `research/results/phase28_r1_online/parity_results.csv`와 사건 로그에 있다.

현재 본 run-root 존재: `{RUN_ROOT.exists()}`. 본 실험·smoke는 실행하지 않았다. 현재 여유 {disk['free_bytes']/1e9:.2f}GB, 보수적 필요량 {disk['required_free_bytes']/1e9:.2f}GB(20GB reserve 포함), 여유충족 `{disk['enough']}`. 종료 후 `portable/cache`·`pycache` 정리 옵션과 원본 보관 정책은 유지한다.

### 사용자 실행 명령 — 기존20회, 실행하지 않음

C0-NA/C0-H × SLW/LC/L2/H1/H2 × seed201/202 =20회. C0는 Phase27-R에서 재사용한다.

```bash
{command}
```

진행 확인:

```bash
{status}
```

report는 `/usr/bin/python3`와 `PYTHONPATH=research`로 자동 생성하며 결과 commit·push까지 수행한다. venv pip 설치 없음.
'''
    (ROOT/'docs/PHASE28_PREP_R1.md').write_text(original+addition)
    save(OUT/'verification.json',dict(original_gate_unchanged=True,original_report_prefix_sha256=sha256_file(archive),parity_matches=sum(r['match'] for r in results),
        unit_tests=tests['tests_run'],registered_runs=len(jobs),navigation_started=0,protocol_sha256=sha256_file(HERE/'protocol_online_r1.json')))
    print(json.dumps(dict(matches=20,tests=tests['tests_run'],planned=len(jobs),navigation_started=0,disk_enough=disk['enough'])))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--parity',action='store_true');ap.add_argument('--document',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    elif a.parity:parity()
    elif a.document:document()
    else:ap.error('Select a stage')

if __name__=='__main__':main()
