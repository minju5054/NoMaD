"""Append verification/cause evidence without changing frozen gate code."""
import json
from pathlib import Path
from collections import Counter
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase32o.evaluate import save
from .config import OUT,HERE,verify
from .report import generate,table

def main():
    protocol=verify();decision=generate();rows=json.loads((OUT/'offline_rows.json').read_text())
    counts=Counter(r['initialization_error'] for r in rows if r['variant']=='G18X' and r.get('initialization_error'))
    tests=Path('/tmp/phase33_tests.log').read_text();process_tests=Path('/tmp/phase33_storage_process_tests.log').read_text()
    assert 'Ran 23 tests' in tests and '\nOK\n' in tests and 'Ran 7 tests' in process_tests and '\nOK\n' in process_tests
    frozen_changes=[f for f,h in protocol['frozen_sources'].items() if sha256_file(ROOT/f)!=h];assert not frozen_changes
    for x in json.loads((OUT/'input_manifest.json').read_text()):assert sha256_file(x['file'])==x['sha256'],x['file']
    verification=dict(unit_tests_passed=30,unit_log=tests,process_test_log=process_tests,frozen_source_changes=frozen_changes,
                      input_hashes_unchanged_after_evaluation=True,navigation_started=0,protocol_sha256=sha256_file(HERE/'protocol.json'),
                      gate_code_sha256=sha256_file(HERE/'report.py'),gate_definition_changed=False,
                      main_root_created=(ROOT.parent/'artifacts/isaac6/phase33p_01').exists())
    save(OUT/'verification.json',verification);save(OUT/'cause_breakdown.json',dict(G18X_normal_initialization_errors=dict(counts)))
    doc=ROOT/'docs/PHASE33P_PREP.md'
    boundary_rejected=sum(v for k,v in counts.items() if 'Previous curvature exceeds Phase33' in k)
    r2=[r for r in rows if r['variant']=='G18X' and r['state']=='R2'];r3=[r for r in rows if r['variant']=='G18X' and r['state']=='R3']
    with doc.open('a') as f:
        f.write('\n## 검증 및 주요 원인\n\n단위 테스트30개 통과. 세 Graph의 해석적 Jacobian, 변경하지 않은 목적함수·초기값·bounds, 시작 완화+e, storage v1/v2 모든 배열 비트 일치, 프로세스 오류 중단을 확인했다. 동결 source와 평가 입력 hash는 평가 후에도 일치한다. 실제 주행0.\n\n')
        f.write(table([{'G18X NORMAL 초기화 거부 사유':k,'건수':v} for k,v in counts.items()])+'\n\n')
        f.write(f"기존 이전 곡률 검사도 새 hard 상한2를 사용하므로 이전 ω/v가2를 넘는{boundary_rejected}건이 이 초기화 검사에서 거부됐다. 이 검사를 우회하거나 상수를 조정하지 않았다. G18X의 R2는{len(r2)}개 중{sum(r['solve_success'] for r in r2)}개, R3는{len(r3)}개 중{sum(r['solve_success'] for r in r3)}개에서 선택 가능한 해가 나왔다. 기존 전체 pool 시간 정의에 따른 G18 p95도{decision['baseline']['compute_p95_s']:.3f}초이며 G18X는{decision['variant']['compute_p95_s']:.3f}초다. 조건부 EC 통과율이 높은 것과 전체 사건에서 쓸 수 있는 해가 많은 것은 구분해야 한다.\n")
        f.write('\n재생성: `PYTHONPATH=research /usr/bin/python3 -m nomad_phase33p.finalize` (오프라인 결과만 사용, 주행 없음).\n')
    print(json.dumps(dict(label=decision['label'],tests=30,frozen_sources_unchanged=True,navigation_started=0)))

if __name__=='__main__':main()
