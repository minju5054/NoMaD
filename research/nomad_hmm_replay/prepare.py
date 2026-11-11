"""Freeze approved equations and validate synthetic replay plumbing only."""
import argparse,json,os,re,subprocess
from datetime import datetime,timezone
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase26.storage import atomic_json
from .data import HERE,OUT,RUN_ROOT,SOURCES

def freeze():
    assert not (RUN_ROOT/'cache').exists()
    p=dict(status='FROZEN',phase='HMM_REPLAY',frozen_at_utc=datetime.now(timezone.utc).isoformat(),variants=['HMM0','NET','NET+MEM'],
        parameters=dict(ell='median positive adjacent Topomap node XY spacing (Phase42-L)',round='Python nearest integer,ties-to-even',
            net_width='min(N-1,round(norm(odometry_xy-MAP_entry_xy)/ell)),no minimum1,selftransition included',
            entry_anchor='reset after each MAP change,including revisits/window resets',visited_memory='record first MAP visit position once;never overwrite',
            emission='exp(-(NoMaD distance-min(window distances))),unit temperature',memory='multiply exp(-squared XY distance/(2ell²));unvisited1',
            initial='Phase42-L uniform prior in recorded window',window_reset='Phase42-L uniform reset if logged window has zero reachable mass;explicitly counted',
            no_tuning=True),
        input=dict(cohorts=[list(x) for x in SOURCES],delay_s=.75,hmm_only=True,expected_runs=86,
            run_selection='Final run metrics selected attempt;never open an unfinished attempt. Dynamic discovery at script start/resume,missing inputs reported.',
            odometry='saved observation XY at hmm_odometry_tick;current exact simulator odometry assumption',truth='saved node_errors,validated with Phase42-L nearest;fallback nearest only if absent'),
        reports=dict(primary_error='observation-time MAP-true_node,all logged measurements;delivered/declaration subset separate',false_goal='MAP==goal AND true_node<goal-2',
            declarations='exact saved declaration inference ID;report would/would-not declare on old wrong and success cases,not new driving outcomes',
            outside_window='previous MAP outside,prediction MAP outside,zero-reachable forced reset,posterior outside(0 by construction)',
            replay_limit='logged candidate windows fixed,none synthesized,not an online counterfactual'),
        source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')},
        frozen_sources={f:sha256_file(ROOT/f) for f in ('research/nomad_phase42l/filter.py','research/nomad_phase42l/analyze.py','research/nomad_phase43p/localization.py')},
        reference_hashes={f:sha256_file(ROOT/f) for _,f,_ in SOURCES})
    atomic_json(HERE/'protocol.json',p)

def validate():
    folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    result=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_hmm_replay.test_replay','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stderr[-6000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_hmm_replay.replay','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['expected']==86 and dry['replayed_runs']==0 and dry['simulations']==0
    atomic_json(folder/'dry_run.json',dry)
    from .report import generate
    generate()
    v=dict(passed=True,synthetic_tests=int(re.search(r'Ran (\d+) tests',result.stderr).group(1)),real_replays=0,simulations=0,protocol_sha256=sha256_file(HERE/'protocol.json'))
    atomic_json(folder/'validation.json',v)
    prefix=f'cd {ROOT} && '
    command=prefix+'nohup env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_hmm_replay.replay > ../artifacts/isaac6/hmm_replay_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_hmm_replay.replay --status'
    atomic_json(folder/'commands.json',dict(command=command,status=status,executed=False))
    (ROOT/'docs/HMM_REPLAY_PREP.md').write_text('# HMM 재생 준비\n\n'+
        f"동결 protocol SHA256: `{v['protocol_sha256']}`. 합성 테스트 {v['synthetic_tests']}개 PASS. 기존 run 재생과 시뮬레이션은 실행하지 않았다.\n\n"+
        'HMM0는 Phase42-L 함수 그대로 재사용한다. NET은 현재 MAP 진입 후 XY 순변위/노드 간격을 round하고 최소1을 제거한다. 자기 전이를 포함한다. MAP이 바뀌면 진입 위치를 새로 저장한다. NET+MEM의 ℓ은 기존 중앙 노드 간격이며 p_j는 최초 방문 위치를 유지한다(사용자 확정). 튜닝은 없다.\n\n'+
        f"입력 예정86 run 중 준비 시점 완료·가용 입력은 {dry['available']}개다. 실행/재개 때 완료 metrics를 다시 스캔하므로 Phase57/58에서 이후 완료되는 run도 추가된다. 미완료/누락은 report 가용률에 표시하며 기다리거나 실행 중 파일을 읽지 않는다. 전체 데이터가 필요하면 해당 주행 종료 후 실행한다.\n\n"+
        '캐시는 run 단위이며 입력·프로토콜 hash가 같을 때만 재사용한다. 원자적 저장,실행 잠금,최대1분 간격 진행률,예외/중단 상태 기록을 지원한다. 완료 후 docs/HMM_REPLAY.md와 research/results/hmm_replay/를 생성하고 자동 commit·push한다. 같은 명령으로 새로 완료된 run을 추가하거나 중단 지점부터 재개한다.\n\n'+
        '기록 창만 사용하므로 최종 MAP의 창 밖 여부는 구조상0이다. 대신 이전 MAP 이탈/창 조건 전 전이 예측 MAP 이탈/강제 재초기화를 각각 보고한다. 거짓 목표는 노드 기준,기존 잘못된 도착은 거리 기준이라 별도 표로 구분한다.\n\n'+
        '진행 확인: `'+status+'`\n\n로그: `../artifacts/isaac6/hmm_replay_01.log`\n\n실행 명령(미실행):\n\n`'+command+'`\n')
    print(json.dumps(dict(v,available=dry['available'],expected=dry['expected'])))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
if __name__=='__main__':main()
