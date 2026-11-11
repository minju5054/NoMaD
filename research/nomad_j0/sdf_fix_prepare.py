"""Isolated, offline-only revision validation; no original-root writes."""
import json
import os
import re
import subprocess
from pathlib import Path
from nomad_isaac.common import sha256_file
from nomad_phase26.storage import atomic_json
from .config import ROOT,HERE,OUT,SCENES,verify
from .prepare import freeze

def main():
    freeze(sdf_fix=True);p=verify();folder=OUT/'preparation/sdf_fix';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    tests=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_j0.test_j0','nomad_j0.test_sdf_fix','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(tests.stdout+tests.stderr)
    assert tests.returncode==0,tests.stderr[-7000:]
    from .test_sdf_fix import saved_depth_equivalence
    equivalence=saved_depth_equivalence();atomic_json(folder/'overlap_bit_equivalence.json',equivalence)
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_j0.h2_rerun','--dry-run'],cwd=ROOT,env=env,text=True))
    launches=[json.loads(subprocess.check_output([*j['argv'],'--dry-run'],cwd=ROOT,env=env,text=True)) for j in dry['jobs']]
    atomic_json(folder/'dry_run.json',dict(rerun=dry,launches=launches))
    validation=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',tests.stderr).group(1)),rerun_launcher_dry_runs=len(launches),
        simulations_started=0,saved_depth_comparisons=len(equivalence),bit_equal_count=sum(all(r['bit_equal'].values()) for r in equivalence),
        query_outside_rule_unchanged=True,protocol_sha256=sha256_file(HERE/'protocol.json'),
        original_protocol_sha256=sha256_file(HERE/'protocol_before_sdf_fix.json'),branch=p['sdf_fix']['publish_branch'])
    atomic_json(folder/'validation.json',validation)
    command=f'cd {ROOT} && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_j0.h2_rerun > ../artifacts/isaac6/j0_h2_sdf_01.log 2>&1 < /dev/null &'
    status=f'cd {ROOT} && PYTHONPATH=research /usr/bin/python3 -m nomad_j0.h2_rerun --status'
    atomic_json(folder/'commands.json',dict(campaign=command,status=status,executed=False))
    from nomad_phase18.report import table
    ranges=[dict(scene=s,origin=p['scenes'][s]['sdf_registration']['origin_m'],h=.01,
                 geometry_with_walls=p['scenes'][s]['sdf_registration']['scene_bbox_with_walls_m'],
                 padded=p['scenes'][s]['sdf_registration']['padded_bbox_m'],
                 registered=p['scenes'][s]['sdf_registration']['registered_bounds_m']) for s in SCENES]
    summary=[dict(scene=s,saved_depth_frames=3,overlap_bit_equal='3/3',query_value_gradient='3/3',initial_empty_map='bit-identical') for s in ('SLW','LC','CL','H1-v2')]
    lines=['# J0 H2 SDF 등록 범위 수정',table([validation]),
        '별도 worktree/브랜치 fix/j0-scene-sdf-bounds에서만 수정했다. 실행 중인 원래 작업 트리·protocol·run-root를 수정하지 않았으며 시뮬레이션은 실행하지 않았다.',
        '원인: H2 장면의 끝벽 내면은 x=9.0m인데 기존 depth 격자 등록 상한은 x=8.0m다. H2 후보 SDF 조회가 등록 밖으로 나가 frozen query의 ValueError로 실행 스레드가 종료됐다. 범위 밖을 free/occupied로 대신 처리하는 규칙은 추가하지 않았다.',
        '장면 벽 외곽(벽 두께0.10m)·정적 물체·고정된 돌발 물체 AABB에0.50m를 더하고, 기존 등록 영역과 합집합을 취한다. 원점(-4,-3.5)·해상도0.01m·기존 셀 인덱스는 보존하며 상한만 원 격자에 맞춰 올림한다. H2의 x상한만9.60m로 확장되고 다른4장면은 기존 배열 크기와 값이 동일하다. 빈 지도 sentinel도 기존 값을 유지한다.',
        table(ranges),table(summary),
        '검증은 각 장면의 보존된 depth3프레임을 원래/새 V1에 같은 noise seed로 입력했다. values·occupied·observed·log-odds·hit-count와 bilinear query값/gradient를 바이트 단위로 비교했다. H2 초기 겹침 영역도 동일하며 기존에 예외였던 x=8.1/9.1/9.59 조회가 가능하고 x=9.7은 계속 예외다. 새로 등록된 H2 영역에서 실제 장애물이 관측되면 그 관측에 따른 거리값 변화는 정상이며, 관측을 숨겨 기존 값을 강제 보존하지 않는다.',
        '방법·Graph 비용/제약·판정·체크포인트·seed·지연·실행 순서는 원 protocol과 동일함을 테스트했다. J1 공통 runtime_config와 depth factory도 동일 등록을 사용한다. depth 업데이트·EDT·query·발행 함수는 동결 소스 그대로다.',
        '원 J0가 COMPLETE/DONE이 된 뒤 H2×{0,0.75}s×{221,222} 네 run만 새 root j0_h2_sdf_01에서 실행한다. 기존 H2 네 기록은 보존하고 결과와 무관하게 모두 새 네 기록으로 대체한다. 다른16개 metrics는 원본 그대로 재사용하며 SHA를 merge manifest에 기록한다. 재시도 없이 단계별 재개·전역 잠금·디스크30GB하한·cache정리 유지. 완료 후 J0 report를 같은 선별식으로 재생성하고 이 수정 브랜치로만 자동 commit·push한다.',
        '원래 브랜치로 merge/cherry-pick하지 않았다. 아래 명령은 별도 worktree에서 실행하며 원 캠페인 종료 전에는 실행을 거부한다.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/j0_h2_sdf_01.log`','J0 종료 후 H2 재실행(미실행):','`'+command+'`']
    (ROOT/'docs/J0_SDF_FIX.md').write_text('\n\n'.join(lines)+'\n')
    prep=ROOT/'docs/J0_PREP.md';before=prep.read_text();marker='\n## 별도 worktree의 H2 등록 범위 수정\n'
    before=before.split(marker)[0]
    prep.write_text(before+marker+'\n원래20회 명령은 최초 J0 준비 기록이다. 현재 수정 브랜치에서는 원 J0 종료 후 H2 네 개만 새 root에서 실행하고 나머지16개와 합쳐 보고한다. [수정·동등성 검증](J0_SDF_FIX.md). 실행 중인 원 작업 트리는 변경하지 않는다.\n\n`'+command+'`\n')
    print(json.dumps(validation))

if __name__=='__main__':main()
