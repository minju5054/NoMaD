"""Preparation/offline evidence now; descriptive three-method drive report later."""
import argparse,csv,json,subprocess
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase26.metrics import audit as original_audit
from .config import HERE,OUT,RUN_ROOT,SCENES,METHODS,verify,protocol

def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s] if Path(p).exists() else []
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def csv_write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def table(rows):
    keys=list(rows[0]);fmt=lambda x:'—' if x is None else f'{x:.4g}' if isinstance(x,float) else str(x).replace('|','/')
    return '\n'.join(['| '+' | '.join(keys)+' |','|'+'|'.join(['---']*len(keys))+'|']+['| '+' | '.join(fmt(r.get(k)) for k in keys)+' |' for r in rows])
def quant(rows,k,q=.5):
    v=[r[k] for r in rows if r.get(k) is not None];return float(np.quantile(v,q)) if v else None
def audit(run):
    r=original_audit(run);run=Path(run);config=read(run/'scenario.json');r['method']=config['phase28_method']
    trace=list(csv.DictReader((run/'agent_trajectory.csv').open()));t=np.array([float(q['simulation_time_s']) for q in trace]);dt=np.r_[0.,np.diff(t)];mid=t-dt/2
    commands=lines(run/'phase20_commands.jsonl');ct=[q['time_s'] for q in commands];idx=np.searchsorted(ct,mid+1e-10,side='right')-1
    rotate=np.array([i>=0 and commands[max(0,i)]['source']=='ALIGN_ROTATE' for i in idx]);brake=np.array([i>=0 and commands[max(0,i)]['source']=='ALIGN_BRAKE' for i in idx])
    h=lines(run/'phase28_handoff.jsonl');feedback=[q for q in h if q['event']=='COMMAND'];applied=[q for q in h if q['event']=='APPLIED'];fallback=Counter(q['reason'] for q in h if q['event']=='FALLBACK')
    r.update(mean_speed_m_s=r['distance_m']/r['duration_s'],alignment_rotation_fraction=float(dt[rotate].sum()/r['duration_s']),alignment_brake_fraction=float(dt[brake].sum()/r['duration_s']),
        handoff_calls=sum(q['event']=='DISPATCH' for q in h),handoff_applied=len(applied),handoff_fallback_reasons=dict(fallback),
        feedback_command_count=len(feedback),feedback_clip_fraction=float(np.mean([q['diag']['any_clipped'] for q in feedback])) if feedback else None,
        handoff_compute_p50_s=quant([q['result'] for q in applied],'wall_s'),handoff_compute_p95_s=quant([q['result'] for q in applied],'wall_s',.95))
    return r

def preparation():
    p=verify();manifest=read(OUT/'preparation/sample_manifest.json');events=read(OUT/'offline/events.json');rows=[];cost=[]
    for stratum in ('C0_SAFE_RANDOM','ACTUAL_ALIGNMENT'):
        q=[r for r in events if r['stratum']==stratum];con=[r for r in q if r['solver_success']];accepted=[r for r in q if r['accepted']];measured=[r for r in con if 'cost_fractions' in r]
        row=dict(stratum=stratum,n=len(q),solver_success=len(con),solver_success_fraction=len(con)/len(q),accepted=len(accepted),acceptance_fraction=len(accepted)/len(q),
            wall_p50_s=quant(q,'wall_s'),wall_p95_s=quant(q,'wall_s',.95),over_015_fraction=sum(r['over_deadline'] for r in q)/len(q),
            accepted_max_w=max((r['max_abs_w'] for r in accepted),default=None),accepted_max_a=max((r['max_abs_a'] for r in accepted),default=None),accepted_max_angular_acceleration=max((r['max_abs_angular_acceleration'] for r in accepted),default=None),
            accepted_max_start_pose_error=max((r['start_pose_error'] for r in accepted),default=None),accepted_max_start_v_error=max((r['start_speed_error'] for r in accepted),default=None),accepted_max_start_w_error=max((r['start_omega_error'] for r in accepted),default=None),
            expected_time_difference_median_s=quant(accepted,'expected_time_difference_s'),expected_time_difference_p95_s=quant(accepted,'expected_time_difference_s',.95),planned_zero_error_clip_fraction_median=quant(accepted,'planned_knot_clip_fraction'))
        row.update(**{'converged_'+k:max((r[k] for r in con if k in r),default=None) for k in ('max_abs_w','max_abs_a','max_abs_angular_acceleration','start_pose_error','start_speed_error','start_omega_error')},converged_time_difference_median_s=quant(con,'expected_time_difference_s'))
        rows.append(row)
        cost.append(dict(stratum=stratum,converged=len(con),terms_available=len(measured),**{k:float(np.median([r['cost_fractions'][k] for r in measured])) if measured else None for k in ('tracking','nonholonomic','smoothing','clearance','time')}))
    csv_write(OUT/'offline_summary.csv',rows);csv_write(OUT/'cost_contributions.csv',cost)
    dispositions=[dict(stratum=s,reason=k,count=v) for s in ('C0_SAFE_RANDOM','ACTUAL_ALIGNMENT') for k,v in Counter(r['disposition'] for r in events if r['stratum']==s).items()];csv_write(OUT/'offline_dispositions.csv',dispositions)
    flat=[]
    for r in events:
        flat.append({k:r.get(k) for k in ('event_key','stratum','scene','index','source_method','solver_success','accepted','disposition','wall_s','over_deadline','max_abs_w','max_abs_a','max_abs_angular_acceleration','start_pose_error','start_speed_error','start_omega_error','trajectory_time_s','expected_time_difference_s','planned_knot_clip_fraction')})
    csv_write(OUT/'offline_events.csv',flat)
    from nomad_phase26.campaign import jobs
    import nomad_phase26.campaign as campaign
    old=campaign.protocol;campaign.protocol=protocol
    try:plan=jobs(RUN_ROOT)
    finally:campaign.protocol=old
    from nomad_phase26.storage import capacity
    disk=capacity(RUN_ROOT,[dict(j,method='C0') for j in plan]);save(OUT/'preparation/capacity.json',disk)
    tests=read(OUT/'preparation/tests.json')
    command='cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase28.campaign --run-root ../artifacts/isaac6/phase28_pilot_01 > ../artifacts/isaac6/phase28_pilot_01.log 2>&1 < /dev/null &'
    status='cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase28.campaign --run-root ../artifacts/isaac6/phase28_pilot_01 --status'
    text=f'''# Phase28 준비 — C0-NA / C0-H

**Isaac·smoke·본 주행은 실행하지 않았다.** 단위테스트, 고정200개 저장 사건의 단일 SLSQP 풀이, B 예측을 위한 짧은 기존 실행기72Hz 전방 적분만 수행했다. NoMaD 추론·새 depth 렌더·튜닝 없음. 기준은 Phase27-R 수정 실행기이며 C0 결과60개 중 C0 10개를 비교행으로 재사용한다.

등록 protocol SHA256 `{sha256_file(HERE/'protocol.json')}`; 표본 manifest SHA256 `{sha256_file(OUT/'preparation/sample_manifest.json')}`. 수치·표본·source hash를 첫 실제 저장 사건 solve 전에 고정했다. 단위테스트 {tests['tests_run']}개 통과. 기존 결정 계층·R2/R3·depth 필터·지도·평가기 source는 변경하지 않았다.

## 방법과 plant 확인

| 방법 | 평소 주행 | 실패·우회 | 제자리 출발 정렬 |
|---|---|---|---|
| C0(재사용) | Phase27-R PP+SP | 기존 R2/R3·회복 | 정지20°/이동45° |
| C0-NA | 동일 PP+SP | 동일 R2/R3·회복 | B 이후 호길이5cm 목표 방향이 엄격히90° 초과일 때만 |
| C0-H | SAFE FRESH마다 시간 SE(2) Graph, feedforward+feedback | H 실패 시 C0-NA; R2/R3 계획·결정·회복은 동결 | H의 제자리 회전도 기준 방향90° 초과일 때만 |

실제 Phase26/27-R config의 `plant_alpha='inf'`와 AngularPlant 코드를 확인했다. **기존 유한 각가속도 한계가 없어 H 계획·추종 한계를2.0rad/s²로 고정**했다. 유한 plant가 있는 config에는 그 값을 쓰는 분기가 있다. 물리 plant 설정과 기존 R2/R3/RECOVER 코드는 바꾸지 않았다. H 시간 궤적 추종 이후 최종 명령을0≤v≤0.3, |ω|≤0.4, |Δv|≤0.5/9, |Δω|≤2/9로 다시 clip한다. fallback C0-NA·기존 우회/회복은 그 동결 실행 규칙이며 H feedback 통계와 분리한다.

## H의 고정 수식·시간 규칙

B는 dispatch 후0.15s를 지난 첫9Hz tick의 예측 상태다(정상 controller dispatch에서2/9s). 현재 실행기의 상태를 복사해 PP/SP 또는 H 추종, 기존 plant, 정확72Hz `integrate_se2`로 그 tick까지 적분한다. 별도 등속 근사나 미래 저장 pose를 B로 쓰지 않는다. 계산 동안 OLD 실행기를 유지하고, 지정 tick에서만 적용한다. 최신 FRESH나 R2/R3/회복 전환이 생기면 해당 H job은 버린다.

변수는 B 고정 pose x0와 별개인 미래10pose x1..x10,10개 dt(0.1–1.0s), 총40개다. 초기 v0·ω0는 B 예측값이다. 첫 구간은 `integrate_se2(B,v0,ω0,dt0)`와 hard equality로 연결한다. 따라서 초기 pose뿐 아니라 첫 구간 속도·yaw rate도 고정한다. 경로 chord길이 l과 Δθ에 대해 v=l/(dt·sinc(Δθ/2)), ω=Δθ/dt; 이웃 구간 중심시간 차이로 a·각가속도를 계산한다. v≤0.3, |ω|≤0.4, |a|≤0.5, |angular_accel|≤2는 hard다. 기준이 뒤쪽이 아니면 추가 `|ω|≤40v`로 v=0에서 새 회전을 허용하지 않는다.

목적함수는 다음5항의 합이다. ①참조10점 XY 제곱오차/0.05² ②TEB 방향-heading 비홀로노믹 및 역방향 hinge residual/0.03² ③2차 XY 차분/0.03² ④node+midpoint에서 max(0,0.15−d)²/0.05² ⑤0.1Σdt. d는 몸체 반경이 차감된 기존 depth SDF 값이다. node+midpoint hard d≥0.025이며, 출력 certificate는 구간당9점의 `d−h/√2−L/16≥0.025`와 정확 점유 site 거리≥0.025를 모두 검사한다. NORMAL H는 원래 선택과 같은 base depth 지도(unknown 비점유)를 쓴다. R3의 보수적 지도는 바꾸지 않는다.

SLSQP(maxiter100, ftol1e−8), 해석적 목적·제약 Jacobian, 단일 시작점, 직전 실제 적용 H 해의 잔여를 warm start로 쓴다. 0.15s에는 B 예측·초기화·풀이·certificate를 포함하며 npz 로딩은 제외한다. 해가 수렴해도 제약/certificate/시간한도를 통과하지 못하면 수락하지 않는다. 실패 사유별 로그를 남기고 같은 선택 경로를 C0-NA로 적용한다. 새로운 파라미터 탐색·재시도는 없다.

추종은 시간 축으로 pose와 구간 중심 속도를 보간한다. body 좌표 오차로 Δv=0.5e_x, Δω=1.0e_y+0.5e_θ를 더한 뒤 최종 제한을 적용하고 clip 비율을 기록한다. 목표 경과 후에는 같은 제한 안에서 정지한다. 미래 reference pose의 선형 보간과 feedforward의 속도 보간은 근사 정합이며, 실행 오차는 feedback과 최종 제한으로 제어한다. 이번 오프라인 수치는 주행 안전/성공 보장이 아니다.

Phase12–18에서 사용한 PurePursuit/XYPath, depth Snapshot·SDF 인터페이스, v4 norm/구간 certificate 식을 재사용했다. frozen Phase18D SP는 NA 및 OLD 예측에 재사용한다. 기존 graph/solver 파일은 수정하지 않았다.

## 두 층의 표본과 결과

seed20261106으로 첫100개는 C0 SAFE FRESH 전체에서 무작위 추출했다. 둘째100개는 전체 Phase27-R depth 사용 방법의 **실제 정렬=True인 SAFE FRESH** 중 첫 층과 중복되지 않게 추출했다. B0는 depth를 저장하지 않아 H 입력을 구성할 수 없으므로 제외하며, R2/R3 적용은 FRESH handoff가 아니므로 제외했다. 원래 사건 인덱스와 SDF hash를 먼저 저장했다. 각 층100개, 총200개를 한 번씩만 풀었다. 두 번째 층은 정렬 사건을 풍부하게 포함한 진단 층이므로 전체 run으로 외삽하지 않는다.

표본 구성: `{dict(Counter((c['stratum'],c['source_method']) for c in manifest['cases']))}`. 각 run 안에서 시간순으로 계산하고, 선택된 사건 중 직전 수락 결과만 warm start로 썼다. 선택되지 않은 중간 사건은 풀지 않았으므로 온라인 warm-start 이력과 같지 않다. TE의 OLD 예측은 저장된 chunk 추가/KEEP 기록·progress를 복원해 원래 TE 조향 코드를 쓴다.

{table(rows)}

최대ω·a·각가속도와 시작 불연속은 **수락 해** 기준이다. 사건 단위 CSV에는 수렴했으나 거절된 해의 값도 보존했다. 성공률은 solver 수렴률과 certificate까지 통과한 수락률을 분리한다. p50/p95·초과율의 분모는 각 층 전체100개다. NA 대비 시간 차이는 같은 예측 B에서 H의Σdt − NA의SP 호길이/속도 적분(+90°초과 정렬의 이상적 회전·감속시간)이다. 계산 대기2/9s, 실제 PP 추종 오차·앞으로의 FRESH·목표 도착은 포함하지 않는다. NA 초기 가속 transient도 완전한 rollout으로 재현한 값이 아니므로 **궤적 일정의 기대시간 비교**일 뿐이다.

offline clip 비율은 수락 궤적의 계획 pose에서 추종기를 조회한 **오차0 조건**이다. 로봇 궤적은 적분하지 않았다. 실제 feedback clip 비율은 본 주행 후 보고한다.

### 수렴 해 비용 기여 비율 중앙값

{table(cost)}

각 값은 해당 해의5항 합 대비 비율의 중앙값이다. 항별 중앙값의 합은1일 필요가 없다. `terms_available`은 timeout 전에 비용 분해가 확보된 수렴 해 수다.

### 실패·수락 사유

{table(dispositions)}

##20회 실행 준비·report 틀

C0-NA/C0-H × SLW/LC/L2/H1/H2 × seed201/202 =20회. C0는 Phase27-R의10개 결과만 재사용한다. 순서는 기존 Phase26 순서에서 C0의 scene×seed 순서를 취하고 각 위치에서 NA→H로 고정했다. 기술 실패 동일 seed1회 재시도, 최종 실패 scene×seed는 paired 분석에서 제외하고 원 기록을 남긴다. 기존 평가기·장면·벽 검증·checkpoint·Topomap·NoMaD seed·depth 설정은 동결이다.

완료 후 report 틀: scene×방법의 n/도착/충돌/도착시간/평균속도/정지비율/정렬 회전·감속비율/최소 여유 표, 같은 seed의 C0 대비 연속 지표 차이, H 수락·사유별fallback·계산시간·최종 feedback clip 비율. 이번 요청에는 성능 판정 임계값이 없으므로 새 승패 라벨이나 통계 판정을 만들지 않는다. C0 재사용 run과 새 두 방법의 실행 시점이 다름을 표기한다.

run-root `../artifacts/isaac6/phase28_pilot_01`, 결과 `research/results/phase28/`, 실행 후 문서 `docs/PHASE28_RESULTS.md`. simulator/worker가 모두 끝난 뒤 정확한 allowlist `portable/cache`, `pycache`만 삭제하는 옵션을 켰다. RGB/depth·로그·snapshot·평가 자료는 삭제하지 않는다. 기존 원본 보관 정책(seed201 전체/202 축소)과 run 전 용량 검사는 유지한다.

디스크: 여유 {disk['free_bytes']/1e9:.2f}GB, 삭제 효과를 미리 빼지 않은 보수적 필요량 {disk['required_free_bytes']/1e9:.2f}GB(20GB reserve 포함), 충분 여부 `{disk['enough']}`. 새 주행 시간은 측정하지 않았으며 이전 C0 launcher 시간으로 약1.3시간 규모다. smoke를 실행했다고 주장하지 않는다.

사용자 실행 명령(실행하지 않음):

```bash
{command}
```

진행 확인:

```bash
{status}
```

report는 `/usr/bin/python3`, `PYTHONPATH=research`를 사용하며 campaign 마지막 단계에서 결과 commit·push까지 수행한다. venv 설치 없음.
'''
    (ROOT/'docs/PHASE28_PREP.md').write_text(text);save(OUT/'preparation/commands.json',dict(campaign=command,status=status,executed=False))
    return rows

def generate(root):
    new=[read(p) for p in sorted((root/'metrics').glob('*.json'))];assert len(new)==20
    old=[r for r in read(ROOT/'research/results/phase27r/runs.json') if r['method']=='C0'];prior=list(csv.DictReader((ROOT/'research/results/phase27r/time_budget_runs.csv').open()))
    for r in old:
        t=next(x for x in prior if x['phase']=='phase27r' and x['method']=='C0' and x['scene']==r['scene'] and int(x['index'])==r['index'])
        r.update(reused=True,mean_speed_m_s=r['distance_m']/r['duration_s'],alignment_rotation_fraction=float(t['ALIGN_ROTATE_s'])/r['duration_s'],alignment_brake_fraction=float(t['ALIGN_BRAKE_s'])/r['duration_s'])
    excluded=sorted({(r['scene'],r['index']) for r in new if r['technical_validation']!='PASS'});rows=old+new;summary=[];pairs=[]
    for scene in (*SCENES,'ALL'):
        for method in ('C0',*METHODS):
            q=[r for r in rows if r['method']==method and (scene=='ALL' or r['scene']==scene) and r['technical_validation']=='PASS' and (r['scene'],r['index']) not in excluded]
            summary.append(dict(scene=scene,method=method,n=len(q),goal=sum(r['success'] for r in q),collision=sum(r['collision'] for r in q),
                **{k:quant(q,k) for k in ('goal_time_s','mean_speed_m_s','stopped_fraction','alignment_rotation_fraction','alignment_brake_fraction','minimum_clearance_m','feedback_clip_fraction')},
                handoff_calls=sum(r.get('handoff_calls',0) for r in q),handoff_applied=sum(r.get('handoff_applied',0) for r in q)))
    for scene in SCENES:
        for index in (201,202):
            if (scene,index) in excluded:continue
            c=next(r for r in old if (r['scene'],r['index'])==(scene,index))
            for method in METHODS:
                r=next(r for r in new if (r['scene'],r['index'],r['method'])==(scene,index,method))
                pairs.append(dict(scene=scene,index=index,method=method,goal=r['success'],baseline_goal=c['success'],collision=r['collision'],baseline_collision=c['collision'],
                    **{k+'_difference':r[k]-c[k] if r.get(k) is not None and c.get(k) is not None else None for k in ('goal_time_s','mean_speed_m_s','stopped_fraction','alignment_rotation_fraction','minimum_clearance_m')}))
    save(OUT/'runs.json',rows);save(OUT/'exclusions.json',excluded);csv_write(OUT/'summary.csv',summary);csv_write(OUT/'paired.csv',pairs)
    fallback=[dict(scene=r['scene'],index=r['index'],method=r['method'],reasons=r.get('handoff_fallback_reasons',{}),compute_p50=r.get('handoff_compute_p50_s'),compute_p95=r.get('handoff_compute_p95_s')) for r in new];save(OUT/'handoff_statistics.json',fallback)
    doc=ROOT/'docs/PHASE28_RESULTS.md';doc.write_text('# Phase28 results\n\nC0 rows reuse Phase27-R; new NA/H runs occurred later. Descriptive continuous outcomes; no new performance label. Goal time uses successes only; other metrics include valid failures. Medians per method/scene. Technical paired exclusions: '+str(excluded)+'\n\n'+table(summary)+'\n\n'+table(pairs)+'\n\nH fallback counts and timing: `handoff_statistics.json`. Clip fractions count actual H feedforward+feedback controller queries. Frozen planner, selector and evaluator unchanged.\n')
    return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    if a.prepare:print(json.dumps(preparation()));return
    verify();doc=generate(a.run_root.resolve())
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','-f','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase28 executor comparison','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

if __name__=='__main__':main()
