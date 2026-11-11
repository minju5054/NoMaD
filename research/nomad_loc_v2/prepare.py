"""Preregister fixed OBS/SIGN definitions and validate synthetic plumbing only."""
import argparse,json,os,re,subprocess
from datetime import datetime,timezone
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase26.storage import atomic_json
from nomad_phase42l.analyze import table
from .data import HERE,OUT,RUN_ROOT,SOURCES

def freeze():
    assert not (RUN_ROOT/'calibration.json').exists()
    p=dict(status='FROZEN',phase='LOC_V2_REPLAY',registered_at_utc=datetime.now(timezone.utc).isoformat(),
        variants=['HMM0','NET','OBS','SIGN','OBS+SIGN'],sources=[list(s) for s in SOURCES],expected_calibration_runs=172,expected_evaluation_runs=48,
        data_rule='HMM-use runs only;CAL Phase47-C only OURS-DETOUR+HMM,EVAL Phase57 only MIN/MIN+G18;all methods in remaining specified phases;EVAL seeds227,228;CAL/EVAL dirs and seeds disjoint',
        obs=dict(k='candidate node minus hypothesis node',offset_rows=[-4,-3,-2,-1,0,1,2,3,4,'OUTSIDE_BOTH_SIDES'],distance_bin_width=.5,laplace=1,
            emission='product across ALL logged window candidate distances,computed in log space',range='calibration min/max floor(distance/.5) plus fixed underflow and overflow bins;never evaluation values'),
        sign=dict(calibration_tangent='previous inference logged HMM0 MAP',evaluation_tangent='variant previous MAP',
            tangent='unit central adjacent-node difference;one-sided ends;zero vector uses nearest nonzero oriented adjacent edge',
            progress='current minus previous observed odometry XY projected onto tangent',ell='existing median positive adjacent node spacing',
            sigma2='population variance(ddof0) of true_node_delta - progress/ell,consecutive saved inference IDs only',
            transition='Gaussian density sampled at integer node offsets and row-normalized over global node range;mean=progress/ell;no cutoff/floor',
            variance_zero='fail explicitly;no tuned epsilon'),
        inheritance='OBS uses HMM0 transition;SIGN uses original emission;OBS+SIGN uses both. HMM0 and NET delegate to frozen nomad_hmm_replay.Replay.',
        goal_delay=dict(origin='first saved inference with true_node==goal',primary='first MAP==goal at/after origin;delay is inference ID difference',
            censor='no MAP==goal at/after origin through log end -> right censored;exclude from primary median and print count beside median',
            negative='first MAP==goal before origin -> separate negative count,signed first-MAP minus origin delay;can overlap later censor',
            no_truth_goal='no true_node goal observed -> separate,not delay0'),
        reporting='EVAL performance only;CAL and EVAL used run/inference counts by phase;CAL parameter/coverage metadata allowed,no CAL accuracy table',
        assumptions='Topomap node poses and observation-time exact odometry available in shared world frame;recorded candidate windows fixed;no missing distance synthesis',
        limitations=['OBS product assumes conditional independence of window distances and may be overconfident','SIGN variance uses logged HMM0 MAP tangent and includes error from incorrectly localized segments'],
        execution='Cache calibration contributions perrun;fit/save immutable model before any EVAL;resume requires same CAL fingerprint. Per-EVAL cache with input/model/protocol hash;1min progress;automatic report commit/push.',
        source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')},
        frozen_sources={f:sha256_file(ROOT/f) for f in ('research/nomad_hmm_replay/filter.py','research/nomad_hmm_replay/data.py','research/nomad_hmm_replay/replay.py','research/nomad_phase42l/filter.py','research/nomad_phase42l/analyze.py')},
        reference_hashes={f:sha256_file(ROOT/f) for _,_,f,_,_ in SOURCES})
    atomic_json(HERE/'protocol.json',p)

def validate():
    folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True);env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_loc_v2.test_loc_v2','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-6500:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_loc_v2.replay','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['calibration_expected']==172 and dry['evaluation_expected']==48 and dry['calibration_fits']==0 and dry['real_replays']==0
    atomic_json(folder/'dry_run.json',dry)
    from .report import generate
    generate()
    v=dict(passed=True,synthetic_tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),real_calibration_fits=0,real_replays=0,simulations=0,protocol_sha256=sha256_file(HERE/'protocol.json'))
    atomic_json(folder/'validation.json',v)
    prefix=f'cd {ROOT} && ';command=prefix+'nohup env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_loc_v2.replay > ../artifacts/isaac6/loc_v2_replay_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_loc_v2.replay --status'
    atomic_json(folder/'commands.json',dict(command=command,status=status,executed=False))
    lines=['# LOC v2 재생 준비',table([v]),table([dry]),
        '실제 보정·평가 재생과 시뮬레이션은 실행하지 않았다. 합성 테스트와 입력 가용성 dry-run만 수행했다. 기존 모듈은 수정하지 않고 nomad_hmm_replay의 입력 정렬·HMM0/NET·선언 연결을 재사용한다.',
        'HMM 사용 run만 포함한다. 보정: Phase47-C OURS-DETOUR+HMM,Phase52/53 전 방법,NIGHT E1/E3. 평가: Phase57 MIN/MIN+G18,Phase58/59 전 방법(seed227,228). 예정172/48개 중 실제 가용 수는 위 표다. 본 report에는 phase별 실제 사용 run·추론 수를 표기한다.',
        'OBS는 k=후보−가설 노드,거리 bin0.5,Laplace1의 조건부 히스토그램을 보정 자료로만 만든다. SIGN은 로그의 직전 HMM0 MAP 접선에서 계산한 true node change−s/ℓ의 분산(ddof0)을 사용한다. 평가에서는 각 변형의 MAP 접선을 사용한다. 보정값과 입력 hash를 먼저 저장·동결한 뒤 평가를 시작하며 평가 데이터로 재보정하지 않는다.',
        '목표 지연은 true_node가 처음 goal인 추론 이후 첫 MAP=goal까지의 추론 간격이다. 미확인 run은 우측 검열 수를 중앙값 옆에 표기한다. 이전에 MAP=goal을 냈다면 음수 선행 지연을 별도 집계하며 부호 있는 최초 지연 보조 중앙값도 병기한다. 실제 목표 노드가 기록상 도달하지 않은 run은 따로 표시한다.',
        'Topomap 노드 pose가 같은 오도메트리 좌표계에 주어진다는 가정을 명시한다. report 한계 항목은 OBS 독립성 곱에 따른 과신 가능성과 로그 HMM0 MAP 오류의 SIGN 분산 혼입 두 항목만 둔다.',
        'run별 원자적 cache,실행 잠금,중단/실패 상태,1분 진행 로그를 지원한다. 같은 명령으로 재개한다. 보정 corpus가 바뀌면 동결 모델을 자동 갱신하지 않고 중단한다. 종료 후 docs/LOC_V2_REPLAY.md 및 research/results/loc_v2_replay/를 자동 생성·commit·push한다.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/loc_v2_replay_01.log`','실행 명령(미실행):','`'+command+'`']
    (ROOT/'docs/LOC_V2_REPLAY_PREP.md').write_text('\n\n'.join(lines)+'\n');print(json.dumps(dict(v,calibration_available=dry['calibration_available'],evaluation_available=dry['evaluation_available'])))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
if __name__=='__main__':main()
