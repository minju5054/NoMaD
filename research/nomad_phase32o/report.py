"""Summarize completed saved-event EXEC-CERT evaluation; never run a simulator."""
import json,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT
from .evaluate import OUT,save,csvout,clean


def q(values,p=.5):
 a=[v for v in values if v is not None and np.isfinite(v)];return float(np.quantile(a,p)) if a else None

def gate(detected,false_rate,error_p95,time_p95):
 conditions=dict(detection=detected>=12,false_reject=false_rate is not None and false_rate<=.10,
                 model_error=error_p95 is not None and error_p95<=.03,compute=time_p95 is not None and time_p95<=.02)
 return ('OFFLINE_PASS' if all(conditions.values()) else 'OFFLINE_FAIL'),conditions

def table(rows):
 if not rows:return '해당 없음'
 keys=list(rows[0]);fmt=lambda v:'—' if v is None else f'{v:.5g}' if isinstance(v,float) else str(v).replace('|','/')
 return '\n'.join(['| '+' | '.join(keys)+' |','|'+'|'.join(['---']*len(keys))+'|']+['| '+' | '.join(fmt(r.get(k)) for k in keys)+' |' for r in rows])


def aggregate(events,name):
 exact=[r for r in events if r['exact_install_map']];benign=[r for r in exact if not r['collision_event']];rejected=[r for r in benign if not r['passed']]
 return dict(group=name,installations=len(events),exact_maps=len(exact),missing_latest_maps=len(events)-len(exact),noncollision_exact=len(benign),false_reject=len(rejected),
  false_reject_rate=len(rejected)/len(benign) if benign else None,noncollision_exposed=sum(r['observation_exposure_s']>0 for r in benign),
  compute_p50_s=q([r['compute_s'] for r in exact]),compute_p95_s=q([r['compute_s'] for r in exact],.95),
  event_error_p95_m=q([r['position_error_p95_m'] for r in events],.95),invalid_na_inputs=sum(not r.get('valid_na_input_path',True) for r in events))


def main():
 status=json.loads((OUT/'status.json').read_text());assert status['status']=='COMPLETE',status
 events=[];alternatives=[];errors=[];same=[];examples=[]
 for p in sorted((OUT/'per_run').glob('*.json')):
  data=json.loads(p.read_text());events+=data['events'];alternatives+=data['alternatives'];examples+=data['examples']
  with np.load(p.with_name(p.stem+'_errors.npz')) as z:errors.extend(z['all_errors'].tolist());same.extend(z['same_executor_errors'].tolist())
 for r in events:r.setdefault('valid_na_input_path',True)
 assert len(events)==8937 and len({r['uid'] for r in events})==160
 positive=[r for r in events if r['box_positive']];assert len(positive)==17
 known=[r for r in positive if r['exact_install_map']];detected=sum(not r['passed'] for r in known)
 exact=[r for r in events if r['exact_install_map']];benign=[r for r in exact if not r['collision_event']];population_benign=[r for r in events if not r['collision_event']]
 false_count=sum(not r['passed'] for r in benign);fpr=false_count/len(benign);err=q(errors,.95);tim=q([r['compute_s'] for r in exact],.95);label,conditions=gate(detected,fpr,err,tim)
 missing_benign=len(population_benign)-len(benign);proxy_fpr=sum(not r['passed'] for r in population_benign)/len(population_benign)
 decision=dict(label=label,conditions=conditions,box_detection=dict(known_detected=detected,total=17,exact_map_cases=len(known),missing_cases=17-len(known),lower_bound=detected/17,upper_bound=(detected+17-len(known))/17,
  with_older_map_proxy_detected=sum(not r['passed'] for r in positive)),
  false_reject=dict(reject=false_count,denominator=len(benign),rate=fpr,total_noncollision_population=len(population_benign),missing_latest_maps=missing_benign,
   population_rate_lower_bound=false_count/len(population_benign),population_rate_upper_bound=(false_count+missing_benign)/len(population_benign),older_map_proxy_rate=proxy_fpr),
  validation=dict(position_samples=len(errors),position_p50_m=q(errors),position_p95_m=err,same_executor_samples=len(same),same_executor_p50_m=q(same),same_executor_p95_m=q(same,.95),
   no_comparable_interval_events=sum(r['valid_actual_ticks']==0 for r in events),definition='Inclusive actual-path prefix, censored at external override/replacement; C0/H policy differences retained. Same executor subgroup descriptive only.'),
  timing=dict(p50_s=q([r['compute_s'] for r in exact]),p95_s=tim,rollout_p50_s=q([r.get('rollout_s') for r in exact]),rollout_p95_s=q([r.get('rollout_s') for r in exact],.95),sweep_p50_s=q([r.get('sweep_s') for r in exact]),sweep_p95_s=q([r.get('sweep_s') for r in exact],.95),over_20ms=sum(r['compute_s']>.02 for r in exact),
   all_including_proxies_p95_s=q([r['compute_s'] for r in events],.95),io_excluded=True),
  coverage=dict(events=8937,runs=160,exact_maps=len(exact),missing_latest_maps=len(events)-len(exact),invalid_na_inputs=sum(not r.get('valid_na_input_path',True) for r in events)),
  no_new_navigation=True,oracle_in_certificate=False,r3_new_solves=0)
 save(OUT/'decision.json',decision);csvout(OUT/'events.csv',events);csvout(OUT/'collision_detection.csv',positive);csvout(OUT/'alternatives.csv',alternatives)
 groups=[aggregate(events,'ALL')]+[aggregate([r for r in events if r['state']==s],s) for s in ('NORMAL','R2','R3')]
 methods=sorted({r['method'] for r in events});groups += [aggregate([r for r in events if r['method']==m],m) for m in methods]
 groups += [aggregate([r for r in events if r['method']==m and r['state']==s],m+':'+s) for m in methods for s in ('NORMAL','R2','R3')]
 csvout(OUT/'summary.csv',groups)
 alt_summary=[]
 for group,rs in [('ALL',alternatives)]+[(s,[r for r in alternatives if r['state']==s]) for s in ('NORMAL','R2','R3')]+[(m,[r for r in alternatives if r['method']==m]) for m in methods]:
  n=len(rs);r3=[r for r in rs if r['r3_pass'] is not None]
  alt_summary.append(dict(group=group,rejected_noncollision=n,other_safe_input_available=sum(r['other_safe_available_input'] for r in rs),other_safe_pass=sum(r['other_safe_pass'] for r in rs),other_safe_fraction=sum(r['other_safe_pass'] for r in rs)/n if n else None,
   slowdown_pass=sum(r['slowdown_pass'] for r in rs),slowdown_fraction=sum(r['slowdown_pass'] for r in rs)/n if n else None,
   r3_assessed=len(r3),r3_unassessed=n-len(r3),r3_pass=sum(r['r3_pass'] for r in r3),r3_fraction_among_assessed=sum(r['r3_pass'] for r in r3)/len(r3) if r3 else None,
   any_measured_pass=sum(r['any_measured_alternative_pass'] for r in rs),any_measured_fraction_lower_bound=sum(r['any_measured_alternative_pass'] for r in rs)/n if n else None))
 csvout(OUT/'alternative_summary.csv',alt_summary)
 validation=[]
 for name,subset in [('ALL',events),('SAME_NA_EXECUTOR',[r for r in events if r['same_executor']])]+[(m,[r for r in events if r['method']==m]) for m in methods]:
  validation.append(dict(group=name,events=len(subset),comparable_events=sum(r['valid_actual_ticks']>0 for r in subset),compared_seconds=sum(r['compared_actual_s'] for r in subset),event_median_error_m=q([r['position_error_p50_m'] for r in subset]),event_p95_error_m=q([r['position_error_p95_m'] for r in subset],.95),max_error_m=max((r['position_error_max_m'] for r in subset if r['position_error_max_m'] is not None),default=None)))
 csvout(OUT/'validation.csv',validation)
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axes=plt.subplots(1,2,figsize=(11,4));srows=groups[1:4]
 axes[0].bar([r['group'] for r in srows],[r['false_reject_rate']*100 for r in srows]);axes[0].axhline(10,c='red',ls='--');axes[0].set_ylabel('Noncollision REJECT (%)')
 axes[1].hist(np.array([r['compute_s'] for r in exact])*1000,bins=50);axes[1].axvline(20,c='red',ls='--');axes[1].set_xlabel('Certificate compute time (ms)');fig.tight_layout();fig.savefig(OUT/'certificate_rates_timing.png',dpi=160);plt.close(fig)
 fig,ax=plt.subplots(figsize=(10,4));ax.hist(np.minimum(errors,.3),bins=np.linspace(0,.3,61),alpha=.6,label='all original executors');ax.hist(np.minimum(same,.3),bins=np.linspace(0,.3,61),alpha=.6,label='original NA executor');ax.axvline(.03,c='red',ls='--');ax.set_xlabel('Position error (m), plot clipped at .30m');ax.set_yscale('log');ax.set_xlim(0,.3);ax.legend();fig.tight_layout();fig.savefig(OUT/'model_error.png',dpi=160);plt.close(fig)
 # Frozen collision example selection: the first four BOX cases in input order.
 order=[r['uid'] for r in json.loads((ROOT/'research/results/phase31d/runs.json').read_text()) if r['primary_cause']=='BOX_COLLISION'][:4]
 ex_by={x['event_key']:x for x in examples};fig,axes=plt.subplots(2,2,figsize=(10,8))
 for ax,uid in zip(axes.flat,order):
  r=next(r for r in positive if r['uid']==uid);e=ex_by[r['event_key']];pred=np.array(e['predicted_poses']);actual=np.array(e['actual_poses']);path=np.array(e['path']);ax.plot(path[:,0],path[:,1],'--',c='gray',label='installed path');ax.plot(pred[:,0],pred[:,1],label='NA prediction');ax.plot(actual[:,0],actual[:,1],label='saved actual prefix');ax.scatter(pred[0,0],pred[0,1],marker='o',s=20);ax.set_aspect('equal');ax.set_title(uid+'\n'+r['disposition'],fontsize=8)
  combined=np.vstack([path,pred[:,:2],actual[:,:2]]);center=(combined.min(axis=0)+combined.max(axis=0))/2;span=max(.4,float(np.ptp(combined,axis=0).max())*1.25);ax.set_xlim(center[0]-span/2,center[0]+span/2);ax.set_ylim(center[1]-span/2,center[1]+span/2)
 handles,labels=axes.flat[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=3,fontsize=8);fig.tight_layout(rect=[0,.05,1,1]);fig.savefig(OUT/'collision_rollouts.png',dpi=160);plt.close(fig)
 for item in json.loads((OUT/'input_manifest.json').read_text()):assert hashlib.sha256(Path(item['file']).read_bytes()).hexdigest()==item['sha256'],item['file']
 source=json.loads(Path(__file__).with_name('protocol.json').read_text())
 for f,h in source['source_hashes'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,f
 save(OUT/'verification.json',dict(source_hashes_unchanged=True,raw_input_hashes_unchanged=True,tests=13,events=8937,unique_runs=160,simulation=0,new_graph_solves=0,
  commands=['PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m nomad_phase32o.evaluate','PYTHONPATH=research /usr/bin/python3 -m nomad_phase32o.report'],source_hashes=source['source_hashes']))
 cv=[{k:r[k] for k in ('uid','state','install_s','collision_delay_s','exact_install_map','disposition','proxy_disposition','clearance_m','snapshot_age_s','valid_actual_ticks','position_error_p95_m')} for r in positive]
 gate_table=[dict(condition=k,passed=v) for k,v in conditions.items()]
 text=f'''# Phase32-O EXEC-CERT 오프라인 평가

**{label}** — 충돌 검출 확정 **{detected}/17**, 비충돌 설치사건 REJECT **{false_count}/{len(benign)} ({fpr:.2%})**, 위치 오차 p95 **{err:.5f}m**, 계산 p95 **{tim*1000:.2f}ms**.

기존160run의 PATH_APPLIED **8,937건 전체**를 목록화하고 보존된 입력으로 평가했다. 최신 snapshot 확보 {len(exact)}건, 최신 파일 결측 {len(events)-len(exact)}건이다. 결측은 이전 보존 지도를 사용한 **proxy**와 분리했으며 원래 최신 지도 결과로 대체하지 않았다. 새 Isaac 실행·렌더·NoMaD 추론·Graph 풀이0. 기존 코드/결과 수정 없음.

## 구현·측정 규칙

- 입력: 설치 tick의 저장 실제 pose/v/ω, 설치 XY, 설치 control refresh 시각 이전에 발행된 최신 V1 snapshot. oracle/목표좌표/박스 위치는 checker API에 없다. 저장 input 복사본의 동일 frame도 허용했다.
- `nomad_phase28.alignment.NoAlignment`와 동결 PP/SP를 직접 재사용한다. lookahead0.25m, >90°일 때만 정렬, 9Hz 제어/72Hz `integrate_se2`, v≤0.3/|ω|≤0.4/|Δv|≤0.5/9이다. 모든 원 run의 plant α=∞여서 초기 실제ω는 입력 provenance에 보존하지만 첫9Hz 명령 이후 별도 각가속도 제한을 만들지 않는다.
- 종료는 동결 follower가 기존1cm endpoint 도달을 선언한 제어 tick 또는2s다. 투영점만 끝에 닿았다고 새 종료 규칙을 추가하지 않았다. 경로 끝을 지나쳤는데 endpoint 허용 원을 놓친 경우도 동결 동작 그대로2s까지 적분한다.
- 지도는 공통 **V1 base, unknown=free**. R3의 unknown/recency-blocked 계획 certificate를 새 실행 검사에 섞지 않았다. 정적 footprint 반경0.09m의 **각72Hz 원호 swept 영역과 점유 셀 중심의 정확 최소 거리**를 구해0.025m 이상이면 PASS다. 기존 V1 cell-center 거리 정의를 사용하며 셀 사각형으로 팽창하거나 새 safety margin을 더하지 않았다. SDF의 h/√2는 후보 셀 검색 범위에만 사용했다. 거의 직선인 원호의 chord 보수 오차는1e−10m 미만이다. 검색 범위 안에 점유 셀이 없는 NO_SITE_WITHIN_SEARCH_BOUND는 정확 최소값 대신 안전이 보장된 하한을 반환하며 lower_bound_only로 표시한다.
- frozen NA가 구성할 수 없는 XY 길이0의 timed H 회전 경로는 `INVALID_INPUT`으로 명시적 REJECT한다. 정지 경로를 임의로 만들어 PASS하지 않았고, 모델 위치 오차는 비교 불가로 남겼다.
- ‘비충돌’은 해당 설치 경로가 직접 실행되던 구간에 원 evaluator 충돌이 없다는 뜻이다. 같은 run이 이후 다른 설치 경로로 충돌해도 앞선 사건은 비충돌 분모에 포함한다. 원래 collision 플래그26건(BOX17+wall9)을 사용한다.
- **오거절은 운영상 명칭**이다. 원 run에서는 다음 FRESH/우회 종료/재계획으로2s 전에 경로를 바꿀 수 있다. 고정 경로2s 반사실을 REJECT했다는 사실만으로 실제 잘못된 안전 판정이라고 단정할 수 없다.
- 계산시간은 설치된 경로의 profile 생성+전방 적분+depth swept 검사 모두 포함, NPZ 디스크 읽기/분석표 작성/대안 탐색은 제외한다. import/NumPy 초기화는 합성 입력10회로 warm-up했고 기존 사건 성적을 보고 상수는 바꾸지 않았다.

## 1. 충돌17건 검출

{table(cv)}

확정 검출 {detected}/17; 최신 지도 결측을 모두 미검출/검출로 놓은 검출률 범위는 **{decision['box_detection']['lower_bound']:.2%}~{decision['box_detection']['upper_bound']:.2%}**다. 이전 지도 proxy까지 포함한 검출 수는 {decision['box_detection']['with_older_map_proxy_detected']}/17이며 주 수치와 분리한다. 원래 충돌 결과는 checker 입력으로 전달하지 않았고 검출률 집계에만 사용했다.

![고정된 첫4개 충돌 사례](../research/results/phase32o/collision_rollouts.png)

## 2. 비충돌 설치사건 REJECT

{table(groups[:4])}

{table(groups[4:4+len(methods)])}

방법×상태 상세 행은 [summary.csv](../research/results/phase32o/summary.csv), 모든 설치별 판정·snapshot·오차·시간은 [events.csv](../research/results/phase32o/events.csv)에 있다. NORMAL에는 원/SM 경로와 GRAPH18/HANDOFF가 모두 들어가며 kind를 별도 보존한다.

최신 지도 결측의 비충돌 {missing_benign}건을 모두 PASS/REJECT로 가정하면 전체 모집단 오거절률 범위는 **{decision['false_reject']['population_rate_lower_bound']:.2%}~{decision['false_reject']['population_rate_upper_bound']:.2%}**다. 이전 지도 proxy 포함 값은 {proxy_fpr:.2%}. 결측을 조용히 PASS/REJECT로 채우지 않았다.

![상태별 REJECT와 시간](../research/results/phase32o/certificate_rates_timing.png)

## 3. 실행기 모델 검증

고정 경로의 예측과 실제72Hz pose를 설치 직후부터 비교하되 다음 PATH_APPLIED, 실제 run 종료, endpoint/2s, 외부 WAIT/회복/만료 명령 중 먼저 오는 시각까지만 사용했다. 최초 pose의 자명한0 오차는 분포에서 제외했다. 비교 가능한 시간이 없는 사건은0 오차로 채우지 않았다({decision['validation']['no_comparable_interval_events']}건).

전체 유효 {len(errors)}개의72Hz 위치 샘플: **p50 {q(errors):.6f}m / p95 {err:.6f}m**.
원 실행기도 동일 NA였던 구간: {len(same)}샘플, **p50 {q(same):.6f}m / p95 {q(same,.95):.6f}m**.

C0는20°/45° 정렬이고 C0-H HANDOFF는 timed follower라 이번 고정 NA 모델과 정책적으로 다르다. 이 사건을 전체 주 검증/게이트에서 숨기지 않고, 동일 실행기 부분집합만 별도로 표시했다. 전체 오차가 크면서 동일 실행기 오차가 작다면 그것을 단순 수치 적분 버그와 혼동하면 안 된다. 반대로 동일 실행기에도 제어 경계/실행 상태 차이가 남을 수 있다.

아래 event_error 열은 사건별 오차 분위의 분포이며, 위의 pooled72Hz p95와 다른 통계다.

{table(validation)}

![위치 오차 분포](../research/results/phase32o/model_error.png)

## 4. 계산시간

{table([decision['timing']])}

latest snapshot 결측의 proxy까지 포함한 p95는 {decision['timing']['all_including_proxies_p95_s']*1000:.2f}ms다. affinity와 소스 hash는 protocol에 기록했다. 여러 run을 병렬 실행하거나 simulator를 띄우지 않았으며 NumPy/BLAS thread 수는1로 실행했다.

## 5. REJECT된 비충돌 사건의 대안

{table(alt_summary)}

같은 실제 pose/v/ω와 같은 snapshot으로만 검사했다. 다른 SAFE 후보는 동일 저장 NoMaD 세트에서 원 선택 index를 제외하고 원 안전 필터를 다시 통과한 후보다. 0.1m/s 감속 대안은 기존 PP 곡률/SP에 목표 상한만0.1로 둔 반사실이고, 초기 속도가 더 높으면0.5m/s² 제한으로 내려간다. 순간 감속·즉시 정지를 가정하지 않았다.

R3는 설치 시점까지 이미 계산되어 저장된 동일 경계 pose의 R3 job만 검사했다. 다른 수락 초기값이 있으면 EXEC-CERT를 다시 적용했다. **저장 job이 없으면 R3 실패가 아니라 UNASSESSED**다. 새 R3 풀이/trigger 생성은 하지 않았다. 따라서 ‘어느 대안이든 PASS’는 확인된 존재 비율의 하한이며, 미평가 R3를 포함한 완전한 존재율은 아니다. 상세는 [alternatives.csv](../research/results/phase32o/alternatives.csv).

## 게이트·한계

{table(gate_table)}

주 게이트는 검출 확정 수를17로 나누고, 오거절/계산시간은 정확한 최신 지도 확보 사건으로, 위치 오차는 모든 비교 가능한 원 실행기 구간으로 계산했다. 결측으로 인한 모집단 범위와 동일 NA 부분집합 검증은 보조이며, 게이트를 통과시키기 위해 분모나 임계값을 바꾸지 않았다. 최종 **{label}**. 결측 및 R3 미평가 범위를 고려하지 않고 전체8,937건이 완전히 관측됐다고 해석하면 안 된다.

이 평가는 고정 경로·고정 snapshot에서2s 이내의 실행 반사실이다. 향후 FRESH·depth 변화·NoMaD 반응·회복 결과를 재현하지 않으며 온라인 주행 효과의 증거가 아니다. 확인된 기술 결함은 새 evaluator의0-XY H 입력 처리와 재개 기록에만 반영했고, 동결 실행기/검사 임계값은 변경하지 않았다.

재현: `PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m nomad_phase32o.evaluate` → `PYTHONPATH=research /usr/bin/python3 -m nomad_phase32o.report`. 기존 per_run이 있으면 재적분하지 않고 이어서 집계한다. [verification.json](../research/results/phase32o/verification.json)에13개 테스트 및 기존 코드·입력 hash 검산을 기록했다. 패키지 설치 없음.
'''
 (ROOT/'docs/PHASE32O_EXEC_CERT.md').write_text(text)
 print(json.dumps(clean(dict(label=label,conditions=conditions,detection=detected,false_reject=fpr,error_p95=err,compute_p95=tim,coverage=decision['coverage']))))

if __name__=='__main__':main()
