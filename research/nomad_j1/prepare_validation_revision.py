"""Prepare correction in worktree only; never updates live artifacts or waits."""
import json
import os
import re
import subprocess
from datetime import datetime,timezone
from nomad_isaac.common import sha256_file
from nomad_phase26.storage import atomic_json
from .config import ROOT,HERE,protocol
from .validation_revision import ALLOWED,REVISION
from .postprocess_guard import ORIGINAL

ADDED=('validation_revision.py','postprocess_guard.py','interim_analysis.py','reassess.py','apply_after_exit.py',
       'test_validation_revision.py','prepare_validation_revision.py')

def main():
    assert ROOT!=ORIGINAL,'Preparation must not edit the live original worktree'
    p=protocol();h=sha256_file(HERE/'protocol.json')
    assert h=='2dbe6817a6751d04971453222baeccb971a4a0f24db6fc40ed1e4a71ec701586'
    revision=dict(revision=REVISION,created_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=h,
        scope='evaluation/verification/report plumbing only; no method,solver,control,scene,seed,schedule,threshold or primary-statistics change',
        replaced_source_sha256={f:dict(frozen=p['source_sha256'][f],revised=sha256_file(ROOT/f)) for f in sorted(ALLOWED)},
        added_source_sha256={str((HERE/name).relative_to(ROOT)):sha256_file(HERE/name) for name in ADDED})
    atomic_json(HERE/'validation_revision.json',revision)
    out=ROOT/'research/results/j1_validation_preparation';out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/j1-audit-mpl')
    result=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_j1.test_validation_revision','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (out/'tests.txt').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stderr[-7000:]
    record=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',result.stderr).group(1)),saved_run_regression='LC_231_D750_RTC-hard/attempt1',
        protocol_sha256=h,protocol_unchanged=sha256_file(HERE/'protocol.json')==h,original_worktree_written=False,
        simulations_started=0,solver_runs=0,real_metric_files_replaced=0,exploratory_dataset_executed=False,real_figures_generated=0,
        validation_revision_sha256=sha256_file(HERE/'validation_revision.json'))
    atomic_json(out/'validation.json',record)
    command=f'cd {ORIGINAL} && env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 {HERE}/apply_after_exit.py'
    atomic_json(out/'commands.json',dict(after_campaign_exit=command,executed=False))
    from nomad_phase18.report import table
    text=['# J1 검증 수정·중간 분석 준비',table([record]),
        '캠페인은 중지하지 않았고 종료를 폴링하지 않는다. 별도 worktree/branch fix/j1-rtc-validation에 코드만 준비했다. 저장된 LC/231 RTC 한 run 회귀 테스트 외 전체 재판정·탐색 분석·그림 생성은 종료 후 명령으로만 수행한다.',
        'RTC target은 H_old개 OLD suffix를 기록하지만 hard mask는 앞 d개만 적용한다. 검증의 출력 metric[:,:d]와 목표 target[:d]를 비교하도록 수정했다. d=0 prefix 오차는 N/A다. 공통 geometric outcome/checkpoint audit의 바이트코드와 주요 상수는 동일함을 테스트한다.',
        'protocol.json은 변경하지 않는다. 기존 hash 검증에서 auditor/config의검증부분/report/campaign의report-tail 네 파일만 별도 validation_revision.json으로 새 SHA를 확인한다. runtime/EC/Graph/worker/장면/seed/실행순서/5.5h블록예산/주검정 함수는 원 hash 그대로다. 이 예외는 보고·검증 수정만 허용하며 방법 코드에는 적용되지 않는다.',
        '처음 요청 시 실제 캠페인은5.5h전 seed239를 주행 중이어서 report 미생성만으로 예산 종료 실패라고 판단할 수 없었다. 종료 후 state/로그를 보존해 실제report완료 여부를 기록한다. 보고 단계가 실패하면 이제report.log·REPORT_FAILED·오류 원인을 명시한다. 블록 실행·예산 로직은 변경하지 않는다.',
        '종료 후 명령: 프로세스1회검사(남아 있으면 즉시 거부,대기·중지없음) → root/global lock → 수정branch를 원래폴더에merge(겹치는 사용자변경이면거부) → 완료seed블록 전체 RTC 저장artifacts 재판정 → 다른방법 canonical metrics 및 모든 attempt_metrics SHA 불변확인 → 중간report/그림 재생성·commit·push. 본 주행 재개/시뮬레이션 호출은 없다.',
        'RTC 원 실패 canonical JSON은 artifacts의 audit_revisions/RTC_PREFIX_D_AND_INTERIM_REPORT_V1/original_metrics에 바이트 그대로 보존하며 기존 attempt_metrics는 손대지 않는다. 수정 재판정에는 원 SHA·기술실패·사유·일시를 남긴다. 재실행 시 이미 처리한 metric은 재사용한다.',
        '보고는 실제 완료된 seed블록 전체이며 전체13개가 아니면「중간 결과, 판정 보류」를 유지한다. 원 주 비교2개의 현재 값·CI·Holm p와 안전실패 discordant 수를 모두 표시한다. 탐색 표는 checkpoint까지 평균속도/곡률감속/정지/거리 및 전체주행 대응값,OURS 대noGRAPH·RAW의짝 비교,OURS EC거절과H1-v3 timeout정지위치다. 주 판정과 분리한다.',
        '탐색 속도=저장궤적 거리/경과시간(정지포함),곡률감속=활성PP 중0<v_target<0.3(가속만/EC브레이크제외),정지=|v|<1e−12. run별값의중앙값을표시하며checkpoint미도달은N/A. 그림은요청한H1-v3·seed231–238·OURS/OURS-noGRAPH/NOMAD_RAW의24장만(추가완료seed의수치보고와분리).',
        '원래 폴더에서 실행할 종료 후 명령:', '`'+command+'`']
    (ROOT/'docs/J1_VALIDATION_FIX_PREP.md').write_text('\n\n'.join(text)+'\n')
    print(json.dumps(record))

if __name__=='__main__':main()
