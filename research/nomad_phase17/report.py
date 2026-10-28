"""The preregistered offline readiness report; runtime report only if READY."""
from nomad_isaac.common import ROOT


def offline_report(out,s):
    def value(d):
        return '—' if not d['n'] else f"{d['median']:.6f} [{d['p10']:.6f}, {d['p90']:.6f}] (n={d['n']})"
    lines=['# Phase 17 — clearance preference 사전 오프라인 검증','',
        f"**{s['label']}** — 391개 입력에 CLR을 각각 한 번만 실행. 기존 Graph 결과는 저장값을 재사용했다.",'',
        '기존 DepthGraph의 제약, certificate, prior, solver 및 상수는 그대로 상속한다. 구간당 기존 9개 SDF 샘플에서 `max(0, 0.15 − d_depth)/0.05` residual과 해석적 Jacobian만 추가했다. oracle은 solve 이후 평가에만 사용했다.','',
        '| 방법 | 수락 / 전체 | 수락률 |','|---|---:|---:|',
        f"| 기존 GRAPH-depth (저장된 수치 수락) | {s['baseline_accepted']}/{s['jobs']} | {100*s['baseline_acceptance_lower']:.2f}–{100*s['baseline_acceptance_upper']:.2f}% |",
        f"| GRAPH-depth-CLR | {s['clr_accepted']}/{s['jobs']} | {100*s['clr_acceptance']:.2f}% |",'',
        f"기존 결과가 없는 terminal job {s['baseline_missing']}개는 미수락으로 단정하지 않고 수락률 상·하한을 기록했다. READY는 보수적인 상한 대비 감소 ≤10%p와 solve p95 ≤0.15s를 모두 만족해야 한다. 감소 검증값: {s['acceptance_change_conservative_pp']:.2f}%p. 수치 수락과 온라인 STALE/SUPERSEDED/실제 적용은 구분한다.",'',
        '| 시간 (초) | median | p95 |','|---|---:|---:|']
    for label,key in [('CLR 전체 시도 (초기화 거절 포함)','clr_attempt_wall_s'),('CLR solver 시작 시도만','clr_started_attempt_wall_s'),('CLR SLSQP만','clr_solver_s'),('기존 SLSQP 저장값','baseline_solver_s'),('기존 solve+certificate 저장값','baseline_solve_certificate_s')]:
        d=s[key];lines.append(f"| {label} | {d['median']:.6f} | {d['p95']:.6f} |")
    lines+=['','신규 시도 시간은 초기화·solve·certificate를 포함하며 depth 파일 읽기와 oracle 평가를 제외한다. 준비 판정은 전체 시도 및 실제 solver 시작 시도의 p95 중 큰 값을 사용한다. 기존 시간은 다른 실행 시점의 저장값이므로 계산시간 인과 비교가 아니다.','',
        '| 수락된 경로 지표: median [p10, p90] | 기존 | CLR |','|---|---|---|']
    for name,key in [('보정−원본 oracle clearance (m)','oracle_delta_m'),('oracle clearance (m)','oracle_clearance_m'),('고정 entry E와 B 거리 (m)','boundary_error_m'),('최대 |κ| (/m)','maximum_abs_curvature_m_inv'),('끝점 전방 진행량 (m)','endpoint_progress_m')]:
        lines.append(f"| {name} | {value(s['accepted_metrics']['baseline'][key])} | {value(s['accepted_metrics']['clr'][key])} |")
    lines+=['','Oracle clearance는 robot radius를 포함한 상자/외곽 벽 거리의 최솟값이다. 수락 집합이 달라 위 분포는 paired 성능 개선 증거가 아니다. 거절된 iterate와 초기화 실패도 CSV/JSON에 보존했다.','',
        '이는 offline mechanism validation이며 실제 PP 실행 안전성이나 closed-loop 회복 성공의 검증이 아니다.','',
        f"후속 처리: {s['next_step']}",'',f"최종 준비 판정: **{s['label']}**"]
    path=ROOT/'docs/PHASE17_RECOVERY_CLR.md'
    with path.open('x') as f:f.write('\n'.join(lines)+'\n')
