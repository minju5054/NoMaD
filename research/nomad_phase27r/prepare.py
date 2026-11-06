"""Read saved PATH_APPLIED events; no navigation, inference, solve or rollout."""
import csv,json,math,shutil,subprocess
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase20.execution import SPAlignment
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase26 import campaign as original_campaign
from .config import HERE,OUT,RUN_ROOT,protocol,verify,registration,PATCH

def read(p):return json.loads(Path(p).read_text())
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def csv_write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def table(rows):
    keys=list(rows[0]);fmt=lambda x:'—' if x is None else f'{x:.3f}' if isinstance(x,float) else str(x)
    return '\n'.join(['| '+' | '.join(keys)+' |','|'+'|'.join(['---']*len(keys))+'|']+['| '+' | '.join(fmt(r[k]) for k in keys)+' |' for r in rows])
def wrapped(a):return (a+math.pi)%(2*math.pi)-math.pi
def summarize(rows,method):
    r=dict(method=method,events=len(rows))
    for when in ('before','after'):
        angles=[x[when+'_error_deg'] for x in rows if x[when+'_error_deg'] is not None]
        for lo,hi in ((0,20),(20,45),(45,90),(90,180.000001)):
            r[f'{when}_{lo}_{min(180,int(hi))}']=sum(lo<=a<hi for a in angles)
        r[when+'_no_target']=len(rows)-len(angles)
        active=[x for x in rows if x[when+'_trigger']]
        r[when+'_triggered']=len(active)
        r[when+'_stopped_triggered']=sum(x['previous_v']<.01 for x in active)
        r[when+'_moving_triggered']=sum(x['previous_v']>=.01 for x in active)
        r[when+'_ideal_rotation_seconds']=sum(x[when+'_ideal_rotation_s'] for x in active)
    return r

def generate():
    p=verify();r=registration();dest=OUT/'preparation';dest.mkdir(parents=True,exist_ok=True)
    tests=read(dest/'tests.json');assert tests['failures']==tests['errors']==0
    prior=ROOT/'research/results/phase27f';f=prior/'alignment_events.json'
    cases=[x for x in read(f) if x['scope']=='SP_START'];assert len(cases)==5012
    with (ROOT/'research/results/phase27d/runs.csv').open() as stream:runs={x['run_id']:x for x in csv.DictReader(stream)}
    grouped=defaultdict(list)
    for e in cases:grouped[e['run_id']].append(e)
    events=[];hashes={str(f):sha256_file(f)};max_error=0.
    for uid,group in grouped.items():
        log=Path(runs[uid]['output'])/'repair.jsonl';hashes[str(log)]=sha256_file(log)
        apps=[q for line in log.read_text().splitlines() if (q:=json.loads(line))['event']=='PATH_APPLIED']
        for e in group:
            q=apps[e['event_id']];assert q['id']==e['native_id'] and abs(q['simulation_time_s']-e['time_s'])<1e-9 and q['alignment']
            B=np.asarray(q['pose']);v=q['previous_vw'][0];path=XYPath(q['path_world'])
            old=next(x for x in path.points if np.linalg.norm(x-B[:2])>=.05)
            before=float(abs(wrapped(math.atan2(*(old-B[:2])[::-1])-B[2]))*180/math.pi)
            err=abs(before-e['logged_error_deg']);max_error=max(err,max_error);assert err<1e-6
            s,_=path.project(B[:2]);indices=np.flatnonzero(path.s>=s+.05);after_target=path.points[indices[0]].tolist() if len(indices) else None
            controller=SPAlignment();controller.replace_path(q['path_world'],B,v)
            after=controller.initial_heading_error_deg;threshold=20. if v<.01 else 45.
            assert controller.alignment_threshold_deg==q['threshold_deg']==threshold
            assert (after is not None)==bool(len(indices))
            if after is not None:
                exact=abs(wrapped(math.atan2(*(np.array(after_target)-B[:2])[::-1])-B[2]))*180/math.pi
                assert abs(exact-after)<1e-8
            events.append(dict(run_id=uid,phase=e['phase'],scene=e['scene'],method=e['method'],event_id=e['event_id'],native_id=e['native_id'],time_s=e['time_s'],kind=e['kind'],
                B_x=float(B[0]),B_y=float(B[1]),B_yaw=float(B[2]),previous_v=v,projected_s_m=s,remaining_s_m=float(path.s[-1]-s),threshold_deg=threshold,
                before_target=json.dumps(old.tolist()),after_target=json.dumps(after_target),after_target_s_m=float(path.s[indices[0]]) if len(indices) else None,
                before_error_deg=before,after_error_deg=after,before_trigger=True,after_trigger=bool(controller.trigger_S),
                before_ideal_rotation_s=math.radians(before)/.4,after_ideal_rotation_s=math.radians(after)/.4 if controller.trigger_S else 0.,
                observed_old_rotation_s=e['rotation_s'],observed_old_braking_s=e['braking_s']))
    summaries=[summarize(events,'ALL')]+[summarize([e for e in events if e['method']==m],m) for m in sorted({e['method'] for e in events})]
    csv_write(dest/'alignment_events.csv',events);csv_write(dest/'alignment_summary.csv',summaries)
    phase26=[e for e in events if e['phase']=='phase26'];csv_write(dest/'phase26_alignment_summary.csv',[summarize(phase26,'ALL')]+[summarize([e for e in phase26 if e['method']==m],m) for m in sorted({e['method'] for e in phase26})])
    plan=original_campaign.jobs(RUN_ROOT);assert len(plan)==60 and [dict(scene=j['scene'],index=j['index'],method=j['method']) for j in plan]==p['main_order']
    disk=original_campaign.capacity(RUN_ROOT,plan);save(dest/'capacity.json',dict(measured_at_utc=datetime.now(timezone.utc).isoformat(),**disk))
    from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
    max_socket=max(validate_socket_path(socket_path_for_run(Path(o))) for j in plan for o in j['outputs']);assert max_socket<100
    audit=[dict(source='research/nomad_phase19s/srg.py',line=82,finding='SAME_PREFIX_SCAN_UNCHANGED',note='Offline SRG trigger S scans full.points by Euclidean distance; no edit. Phase26 does not call this rollout (SP imports wrap/evaluate only).'),
        dict(source='research/nomad_phase24r/follower.py',line=24,finding='CHORD_DIRECTION_NOT_PREFIX_POINT',note='Uses segment chord, not B-to-old-waypoint. first_pending also checks segment0 before projected segment: a different potential stale-segment direction; investigated only, unchanged.'),
        dict(source='research/nomad_phase17/recovery.py',line=9,finding='NO_PATH_PREFIX_INPUT',note='Depth free rays at current heading +/-30deg determine recovery sign. No chunk-prefix target.'),
        dict(source='research/nomad_phase23/rollout.py',line=16,finding='PLANNED_HEADING_SEGMENTS',note='Native graph rotation uses planned segment theta/omega; does not scan original prefix for a point5cm from B. Unchanged.'),
        dict(source='research/nomad_phase21/execution.py',line=30,finding='INHERITS_CORRECTED_SP',note='SAFE_TE latest selected chunk uses SPAlignment; no independent prefix selector. Ensemble steering and KEEP rules unchanged.'),
        dict(source='research/nomad_phase23/prediction.py',line=1,finding='INHERITED_SP_WITH_SAVED_STATE',note='Existing prediction reuses SPAlignment and restores saved alignment state when available; not separately edited or used to simulate here.')]
    for a in audit:a['sha256']=sha256_file(ROOT/a['source'])
    save(dest/'alignment_code_audit.json',audit)
    old_doc=read(ROOT/'research/results/phase26/preflight.json');hours=old_doc['estimated_hours']
    command='cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase27r.campaign --run-root ../artifacts/isaac6/phase27r_pilot_01 > ../artifacts/isaac6/phase27r_pilot_01.log 2>&1 < /dev/null &'
    status='cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase27r.campaign --run-root ../artifacts/isaac6/phase27r_pilot_01 --status'
    save(dest/'commands.json',dict(campaign=command,status=status,executed=False))
    summary=summaries[0]
    def distribution(which):
        return table([dict(방법=q['method'],사건=q['events'],**{label:q[f'{which}_{lo}_{hi}'] for label,lo,hi in [('0–20°',0,20),('20–45°',20,45),('45–90°',45,90),('90°+',90,180)]},목표없음=q[which+'_no_target']) for q in summaries])
    md=f'''# Phase27-R 준비 — SP 출발 정렬 suffix 수정

**Isaac·smoke·본 실험은 실행하지 않았다.** 단위테스트와 Phase27F의 저장 SP 정렬5012건에 대한 목표 방향 재계산만 했다. 기존 주행·결과·Phase26 등록 protocol은 보존했다.

## 1. 허용된 수정 하나

`SPAlignment.replace_path`에서 동일한 `XYPath.project(B[:2])`로 `s_B`를 구하고, 저장된 waypoint 중 **호길이 s≥s_B+0.05m인 첫 점**을 정렬 목표로 선택한다. 5cm는 B와의 직선거리가 아니라 투영점 이후 호길이 기준이다. s_B+0.05m에 새 점을 삽입하지 않는다. 잔여 길이가5cm 미만이면 목표 없음으로 정렬하지 않는다. 경로 끝을 지난 B는 끝점으로 투영되어 같은 처리를 받는다.

정지20°/이동45° 기준, 실제 v<0.01 구분, ω한계0.4rad/s, 가속0.5m/s², SP·PP·TE·RTC·선택·fallback·회복·트리거·우회·certificate·평가 함수는 그대로다. 동작 파일 변경은 [execution.py](../research/nomad_phase20/execution.py#L13)의3줄뿐이다.

- 수정 전 SHA256: `{r['allowed_source_change']['before_sha256']}`
- 수정 후 SHA256: `{r['allowed_source_change']['after_sha256']}`
- 원래 Phase26 protocol SHA256: `{r['phase26_protocol_sha256']}` (변경 없음)
- Phase27-R delta 등록: [protocol.json](../research/nomad_phase27r/protocol.json), SHA256 `{sha256_file(HERE/'protocol.json')}`

Phase26의 엄격한 source hash 검사를 우회하지 않는다. Phase27-R wrapper에서 이 한 파일의 새 hash만 명시적으로 허용하고 나머지 모든 frozen source·scene·Topomap·checkpoint hash는 그대로 검증한다. 기존 `nomad_phase26.campaign` 직접 실행은 원래 hash와 달라 거부되며, 아래 새 wrapper만 사용한다. wrapper 변경은 검증 예외·프로세스 모듈 경로·결과 저장 경로·provenance 표기뿐이다. 주행 구현은 원래 Phase26 launcher/simulator/실행기를 재사용한다.

## 2. 단위테스트와 무변경 조사

**{tests['tests_run']}개 통과 / {tests['tests_run']}개**, 실패0·오류0. B가 경로 중간,5cm 미만 suffix, 끝점 이후, 곡선 경로(호길이와 직선거리 구별), 정확5cm 경계, 임계각·회전 명령을 확인했다. 재실행 wrapper의60개 순서·한 파일 hash 예외·이전 raw 경로 거부·결과 파일 byte 동등성도 검증했다. 기존 Phase26 장면·판정 테스트와 Phase20의 SP/정렬 관련 단위테스트를 포함한다. 기존 `test_moving_alignment_brakes_before_rotation` 한 개는 합성 직각 경로108tick 수치 적분으로 감속 후 회전 명령을 검증한다. Isaac·NoMaD·기존 run 재주행은 없으며, 저장5012사건 검산에서는 궤적 rollout 없이 방향만 계산했다.

{table([dict(코드=f"[{a['source']}](../{a['source']}#L{a['line']})",조사결과=a['finding'],근거=a['note']) for a in audit])}

Phase19-S의 offline SRG에는 같은 full-prefix 검색이 남아 있지만 요청대로 고치지 않았다. G chord 정렬은 B에서 과거 점을 향하는 동일 계산이 아니다. 다만 `first_pending` 때0번 chord를 별도로 보는 동작은 그대로 남는다. RECOVER_ROTATE는 depth ray 기준으로 경로 prefix를 읽지 않는다. 이들 조사에서 새 주행이나 성능 검증을 하지 않았다.

## 3. 5012개 저장 사건의 오프라인 검산

Phase27F의 `SP_START` 사건만 사용했다(G 정렬 제외). 각 원래 `PATH_APPLIED`의 B·실제 직전 속도·설치 경로를 그대로 넣었다. 수리/우회/HERMITE 경로가 설치됐던 사건도 그 **실제 설치 경로**를 사용한다. 새 FRESHEST 선택이나 NoMaD 재생성은 하지 않았다. 원래 목표각의 재계산과 Phase27F 로그 값의 최대 차이는 {max_error:.3g}°다.

범위는 하한 포함/상한 제외,90°+는180° 포함. 수정 후 목표가 없는 사건은0°로 대체하지 않고 별도 열로 센다. 아래 표는 **원래 정렬이 발동했던5012건에 조건부인 재계산**이다. 원래 정렬하지 않은 사건에서 새로 발동할 수 있는 수나 폐루프에서의 사건 수 변화는 측정하지 않았다.

### 수정 전 방향 오차

{distribution('before')}

### 수정 후 방향 오차

{distribution('after')}

### 정렬 발동 수와 이상적 회전 시간

추정 회전 시간은 발동 사건에 한해 `|wrap(목표방향−B heading)|/0.4rad/s`를 합한 값이다. 감속·제어 이산화·경로 만료·새 chunk 교체를 포함하지 않는다. 수정 전후 모두 같은 식을 사용했다. Phase27F에서 관측한 잘린 회전 시간과 이 이상적 정렬 완수 시간을 혼동해서는 안 된다.

{table([dict(방법=q['method'],사건=q['events'],전_발동=q['before_triggered'],후_발동=q['after_triggered'],후_정지20도=q['after_stopped_triggered'],후_이동45도=q['after_moving_triggered'],전_추정회전_s=q['before_ideal_rotation_seconds'],후_추정회전_s=q['after_ideal_rotation_seconds']) for q in summaries])}

수정 후 발동은 **{summary['after_triggered']}/5012건**, 이상적 회전 시간 합은 **{summary['before_ideal_rotation_seconds']:.3f}→{summary['after_ideal_rotation_seconds']:.3f}s**다. 실제 시간 절약·성공률 개선을 의미하지 않는다. 전체 사건별 수치 및 Phase26 subset 표는 [preparation](../research/results/phase27r/preparation/)에 별도로 보존했다.

## 4. 재실행 준비 — 실행하지 않음

원래 Phase26 그대로 B0/B1/B2/B3/B4/C0 × SLW/LC/L2/H1/H2 × seed201,202 =60회다. 원래 `main_order`·등록 판정·기술 실패1회 동일 seed 재시도와 그룹 제외·잠금·재개·socket 사전 검사·벽 검증·저장량 정책을 재사용한다. 모든 가능한120개 attempt의 socket 길이는100bytes 미만(최대 {max_socket}bytes)이다. 원래 smoke 자료는 기술적 선행 자료로만 재사용하며, 이번 수정 후 smoke를 실행했다고 주장하지 않는다.

raw run-root: `../artifacts/isaac6/phase27r_pilot_01` (새 경로). 최종 결과: `research/results/phase27r/`. 준비 자료는 그 아래 `preparation/`, 완료 후 결과 문서는 `docs/PHASE27R_RESULTS.md`다. Phase26의 기존 report 함수·판정 함수를 다른 out/doc 인수로 호출하며 기존 결과를 덮어쓰지 않는다. 가짜60행 입력으로 기존 결과와 새 경로 결과의 runs/summary/paired/decision/exclusions가 byte 단위로 일치함을 확인했다.

### 디스크·시간

- 현재 여유 **{disk['free_bytes']/1e9:.2f}GB ({disk['free_bytes']/2**30:.2f}GiB)**.
- 원래 Phase26 용량 계산 그대로 남은60run 예상 **{disk['expected_remaining_bytes']/1e9:.2f}GB**,20GB여유 포함 필요 **{disk['required_free_bytes']/1e9:.2f}GB**.
- 현재 상태: **{'DISK_READY' if disk['enough'] else 'DISK_NOT_READY'}**. 부족분 **{max(0,disk['required_free_bytes']-disk['free_bytes'])/1e9:.2f}GB**. 자동 삭제나 보관 정책 변경을 하지 않았다. 공간이 부족한 채 아래 명령을 실행하면 기존 사전 점검이 첫 run 이전에 LOW_DISK_STOP으로 정지한다.
- seed201은 scene별 원본 RGB/depth 전체 보존, seed202는 기존 축소 보관 규칙 그대로다. 매 run/재시도 직전에 남은 추정량+20GB를 재검사한다.
- 과거 Phase26 smoke 기반 예상 약 **{hours:.2f}시간**. 이번 버그 수정 후 주행을 측정하지 않아 소요시간은 검증되지 않았다. 회복·주행 변화에 따라 달라질 수 있다.

공간 확보 후 사용자가 한 번 실행할 명령(이번 준비에서는 실행하지 않음):

```bash
{command}
```

진행 확인(한 줄):

```bash
{status}
```

준비 보고서 재생성(주행 없음): `PYTHONPATH=research /usr/bin/python3 -m nomad_phase27r.report --prepare`. 본 campaign 완료 시 새 경로에 report를 생성하고 결과 commit·push하는 구조는 Phase26과 같다. venv 패키지를 설치하거나 환경을 변경하지 않았다.
'''
    (ROOT/'docs/PHASE27R_PREP.md').write_text(md)
    assert all(sha256_file(Path(k))==v for k,v in hashes.items())
    result=dict(status='PREPARED_NOT_EXECUTED',tests=tests,events=len(events),summary=summary,source_hash_exception_only=PATCH,old_inputs_unchanged=True,
        original_angle_max_error_deg=max_error,planned=len(plan),max_socket_bytes=max_socket,navigation_started=0,raw_run_root_exists=RUN_ROOT.exists(),
        disk_enough=disk['enough'],free_bytes=disk['free_bytes'],required_free_bytes=disk['required_free_bytes'])
    save(dest/'verification.json',result);save(dest/'input_hashes.json',hashes);return result
