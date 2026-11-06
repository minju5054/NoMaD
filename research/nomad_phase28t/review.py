"""Generate smoke interpretation and the reusable saved-run comparison tables."""
import argparse,csv,shutil
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from .report import OUT,read,save,csv_write,table,smoke
from .analysis import analyze

CAMPAIGN='cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase28t.campaign --run-root ../artifacts/isaac6/phase28t_main_01 > ../artifacts/isaac6/phase28t_main_01.log 2>&1 < /dev/null &'
STATUS='cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase28t.campaign --run-root ../artifacts/isaac6/phase28t_main_01 --status'

def baselines(scene=None,index=None):
    rows=[]
    for phase,method in (('phase27r','C0'),('phase28','C0-NA')):
        rows.extend(dict(r,reused_phase=phase) for r in read(ROOT/f'research/results/{phase}/runs.json') if r['method']==method and (scene is None or r['scene']==scene) and (index is None or r['index']==index))
    return rows

def summarize_rows(rows,out):
    result=[];budgets=[]
    for r in rows:
        key=f"{r['scene']}_{r['index']}_{r['method']}"
        if r['technical_validation']!='PASS':continue
        analysis,budget,_,_=analyze(r['output'],out/key)
        assert abs(analysis['stop_fraction']-r['stopped_fraction'])<1e-10
        result.append(dict(scene=r['scene'],index=r['index'],method=r['method'],success=r['success'],collision=r['collision'],
            minimum_clearance_m=r['minimum_clearance_m'],goal_time_s=r['goal_time_s'],passage=r['box_passage'],
            passage_from_spawn_s=r['box_passage_from_spawn_s'],mean_speed_m_s=r['distance_m']/r['duration_s'],**analysis))
        budgets.extend(dict(scene=r['scene'],index=r['index'],method=r['method'],**b) for b in budget)
    csv_write(out/'run_analysis.csv',result);csv_write(out/'time_budget_all.csv',budgets)
    return result,budgets

def generate(root):
    # Archive the original canonical smoke_01 technical failure verbatim first.
    canonical=OUT/'smoke';old=OUT/'smoke_01';doc=ROOT/'docs/PHASE28T_SMOKE.md'
    if canonical.exists() and read(canonical/'summary.json')['technical_validation']=='FAIL':
        if not old.exists():shutil.copytree(canonical,old)
        for f in canonical.rglob('*'):
            if f.is_file():assert sha256_file(f)==sha256_file(old/f.relative_to(canonical))
        if doc.exists() and not (ROOT/'docs/PHASE28T_SMOKE_01.md').exists():shutil.copyfile(doc,ROOT/'docs/PHASE28T_SMOKE_01.md')
    summary=smoke(root);source=OUT/'smoke_02'
    assert root.name=='phase28t_smoke_02' and summary['technical_validation']=='PASS'
    canonical.mkdir(parents=True,exist_ok=True)
    for f in source.iterdir():
        if f.is_file():shutil.copyfile(f,canonical/f.name)
    rows=baselines('H1',201)+[summary['original_evaluator']]
    details,budgets=summarize_rows(rows,canonical)
    view=[{k:r[k] for k in ('method','success','collision','minimum_clearance_m','goal_time_s','passage_from_spawn_s','mean_speed_m_s','stop_fraction','alignment_rotation_s','alignment_brake_s','detour_execution_s','detour_wait_s')} for r in details]
    h=next(r for r in details if r['method']=='C0-H');na=next(r for r in details if r['method']=='C0-NA')
    clips=list(csv.DictReader((canonical/'H1_201_C0-H/clip_causes.csv').open()))
    combos=list(csv.DictReader((canonical/'H1_201_C0-H/clip_combinations.csv').open()))
    stages=[dict(stage=r['stage'],n=int(r['n']),p50_ms=1000*float(r['p50_s']),p95_ms=1000*float(r['p95_s'])) for r in csv.DictReader((canonical/'stages.csv').open())]
    affinity=read(canonical/'affinity.json');worker=affinity['worker']['affinity']
    budget_table=[]
    for state in sorted({r['state'] for r in budgets}):
        values={m:sum(r['seconds'] for r in budgets if r['method']==m and r['state']==state) for m in ('C0','C0-NA','C0-H')}
        budget_table.append(dict(state=state,**values,H_minus_NA_s=values['C0-H']-values['C0-NA']))
    csv_write(canonical/'time_budget_comparison.csv',budget_table)
    segments=[]
    for r in rows:
        b=r['boxes'][0];segments.append(dict(method=r['method'],before_spawn_s=b['spawn_time_s'],spawn_to_passage_s=b['passage_time_s'],passage_to_goal_s=r['duration_s']-b['passage_at_s']))
    csv_write(canonical/'passage_phases.csv',segments)
    plans=[]
    for r in details:
        path=canonical/f"H1_201_{r['method']}"/'path_schedules.csv'
        schedules=list(csv.DictReader(path.open()))
        plans.append(dict(method=r['method'],paths=len(schedules),completed=sum(x['completed']=='True' for x in schedules),
            sum_full_plan_s=sum(float(x['planned_sum_dt_s'] or x['na_ideal_full_schedule_s']) for x in schedules if x['planned_sum_dt_s'] or x['na_ideal_full_schedule_s']),
            sum_active_execution_s=sum(float(x['active_execution_s']) for x in schedules)))
    gate=summary['gate']
    main_note=''
    registration=ROOT/'research/nomad_phase28t/protocol_main.json'
    if registration.exists():
        preparation=OUT/'main_preparation'
        if (preparation/'validation.json').exists():
            v=read(preparation/'validation.json');disk=read(preparation/'capacity.json')
            main_note=f"FROZEN main protocol SHA256 `{sha256_file(registration)}`. 단위테스트 {v['tests_passed']}개와 실제 base launcher 10개 조합 인자 검증/dry-run 통과, 새 run 시작 0. 여유 공간 {disk['free_bytes']/1e9:.2f}GB, 보수적 필요량 {disk['required_free_bytes']/1e9:.2f}GB(20GB reserve 포함). 과거 launcher 시간 기반 예상 {v['estimated_wall_s']/60:.1f}분, 30% 여유 포함 약 {v['estimated_wall_s']*1.3/60:.1f}분; 기술 재시도는 추가. 매 run 전 여유 공간을 다시 검사한다."
    text=f'''# Phase28-T smoke_02 검토

**{gate['label']} · 기술 PASS. 실제 H 적용 {gate['applied']}/{gate['denominator_n']} = {100*gate['application_fraction']:.2f}%** (DETOUR_STARTED 제외 {gate['detour_started_excluded']}건). 전체 계산 p50/p95 **{1000*summary['compute_p50_s']:.2f}/{1000*summary['compute_p95_s']:.2f} ms**, 최대 {1000*summary['compute_max_s']:.2f} ms. worker core 고정 `{worker['passed']}`, 실제 `{worker['actual']}`; driver는 CPU 7 및 SMT sibling 15를 제외했다. H1 seed201은 도착 성공·충돌 0, 최소 여유 {h['minimum_clearance_m']:.4f}m, 도착 {h['goal_time_s']:.3f}s, 상자 생성→통과 {h['passage_from_spawn_s']:.3f}s다. 아래는 같은 seed의 재사용 C0(Phase27-R)·C0-NA(Phase28) 비교다.

{table(view)}

단계별 시간(ms, 각 단계의 관측값 기준; 중첩 단계를 더하지 않는다):

{table(stages)}

smoke_01 기술 실패는 `docs/PHASE28T_SMOKE_01.md`, `research/results/phase28t/smoke_01/` 및 원 raw에 보존했다. 이 문서와 canonical `smoke/`는 완료된 smoke_02를 가리킨다. smoke는 본 비교에서 제외하며, 같은 seed라도 실행 시점/실시간 inference·snapshot 이력이 달라 아래 차이는 단일 run의 서술이다. evaluator·수치·정책·게이트 변경 없음.

## Feedback clip 133건

H COMMAND {h['h_commands']}개 중 {h['clip_count']}개({100*h['clip_fraction']:.2f}%). 기록된 raw command와 직전 실제 v/ω로 최종 clip을 재계산해 모든 명령과 1e−9 이내 일치를 확인했다. 각 행은 raw가 해당 제한을 위반하면서 해당 축이 실제 clip된 경우다. 하나의 명령에서 여러 제한이 겹치므로 원인별 합은 133보다 클 수 있다. 가속도는 ±0.5/9 m/s, 각가속도는 ±2/9 rad/s의 tick당 변화다.

{table(clips)}

중복 없는 원인 조합(합계 133):

{table(combos)}

clip 시 feedforward 계획 속도가 이미 상한인 경우는 **{h['clipped_with_planned_v_at_upper']}/133**이다(상한 판정 0.3−1e−7, solver 수치오차 고려; 제어 한계 변경 아님). `clip_commands.csv`에 모든 명령의 계획·raw·최종 속도와 원인 플래그가 있다. 정지/곡선에서 가속도·각속도 제한에 걸리는 clip도 있으므로 전부 vmax feedback 포화로 해석하지 않는다.

## 계획 대비 실제 추종

H 실행 구간 72Hz {h['tracking_samples']}개 pose를 해당 APPLIED의 시간 매개 궤적과 비교했다. target XY는 knot 시간 선형 보간, heading은 unwrap 후 보간하고 오차는 wrap한다(실제 follower와 동일). 정지/우회 모드 등 H controller가 호출되지 않은 구간은 제외한다. 위치 오차 p50/p95 **{h['position_error_p50_m']:.5f}/{h['position_error_p95_m']:.5f}m**, heading **{h['heading_error_p50_deg']:.3f}/{h['heading_error_p95_deg']:.3f}°**. 미래 계획 전체의 off-policy rollout 수치가 아니다. C0-NA는 pose·dt 계획을 출력하지 않아 동일한 시간축 heading/위치 오차는 정의되지 않는다.

## 시간 손실 분해

C0-H − C0-NA 도착시간은 **{h['goal_time_s']-na['goal_time_s']:.3f}s**. 정지(|v|<0.01m/s, 기존 evaluator 정의)는 {h['stop_s']:.3f}s({100*h['stop_fraction']:.2f}%) vs {na['stop_s']:.3f}s({100*na['stop_fraction']:.2f}%). 정렬 회전은 {h['alignment_rotation_s']:.3f} vs {na['alignment_rotation_s']:.3f}s, 감속은 {h['alignment_brake_s']:.3f} vs {na['alignment_brake_s']:.3f}s다. STOP 비율은 아래 상태 분류와 겹치는 별도 속도 기준이다.

{table(budget_table)}

위 표는 72Hz 시간 구간을 우선순위(최초 대기→정렬/회복→계산대기/STOP_WAIT→우회→H→NA)로 배타 분류하므로 각 방법 열은 총 주행시간과 일치한다. H는 평소 이동 구간에서 H_MOVING과 NA_MOVING을 합쳐 비교해야 한다. 새 H 계산 중에는 OLD를 계속 실행하므로 H 계산시간 합을 정지시간에 가산하지 않는다.

{table(segments)}

손실의 대부분은 상자 생성→통과 구간 차이(8.000s)에 나타난다. H의 실제 수락 우회 실행은 더 짧고 정렬 회전 차이는 작다. 추가 STOP_WAIT/계산 대기와 평소 경로 추종 시간 증가가 함께 관측된다. clip·경로 차이·새 관측 이력 중 하나를 독립 원인으로 단정할 수 없다.

{table(plans)}

H 적용 계획 32개의 전체 Σdt 합은 {h['h_sum_full_plan_s']:.3f}s, 그 controller가 실제 호출된 구간 합은 {h['h_sum_active_s']:.3f}s다. {h['h_ended_before_plan']}/32는 전체 계획시간보다 일찍 교체/중단됐고, completed=True로 끝난 H 계획은 {h['h_completed_paths']}개다. 따라서 Σdt 합과 실제 도착시간을 빼서 추종 지연이라고 부를 수 없다. `path_schedules.csv`에는 계획별 Σdt, 실제 보유/추종 시간, 교체 검열 여부를 기록했다. NA의 비교 계획시간은 동결 SP 호길이/속도 적분+이상적 정렬시간이며 실제 가감속/미래 FRESH를 완전히 표현하지 않는다.

## 게이트 통과 후 10회 준비

C0-H만 SLW/LC/L2/H1/H2 × seed201/202 = 10회, 새 root `../artifacts/isaac6/phase28t_main_01`. C0 10개는 Phase27-R, C0-NA 10개는 Phase28에서 재사용한다. smoke_02는 이 10회에 포함하지 않는다. 기존 Phase28 순서에서 H만 취하고, 재개·잠금·short socket 검사·디스크 검사·기술실패 1회 재시도·재실패 scene×seed 제외를 그대로 사용한다. seed201 원본/seed202 축소 저장과 run 종료 cache cleanup 유지. 새 성능 라벨은 만들지 않는다. gate는 준비 자격 기준이며 성능 우위를 뜻하지 않는다.

본 report는 방법별 연속 지표와 같은 seed 차이, clip 원인·추종 오차·시간예산·계획시간 비교를 자동 생성한다. 명령은 문서에만 기록했으며 실행하지 않았다.

{main_note}

```bash
{CAMPAIGN}
```

```bash
{STATUS}
```

보고서 재생성: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase28t.review --smoke-root ../artifacts/isaac6/phase28t_smoke_02`
'''
    doc.write_text(text);return summary

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--smoke-root',type=Path,default=ROOT.parent/'artifacts/isaac6/phase28t_smoke_02');a=ap.parse_args()
    result=generate(a.smoke_root.resolve());print(result['gate']['label'])

if __name__=='__main__':main()
