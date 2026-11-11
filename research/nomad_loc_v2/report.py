"""Evaluation metrics only; calibration is shown solely as fit/coverage metadata."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase42l.analyze import table,csvout
from nomad_phase26.storage import atomic_json
from .data import HERE,OUT,RUN_ROOT,SOURCES
from .filter import VARIANTS
from .replay import verify,fingerprint,cache_path

def stats(rr):
    return dict(inferences=len(rr),absolute_median=float(np.median([r['abs_error'] for r in rr])) if rr else None,
        absolute_p95=float(np.quantile([r['abs_error'] for r in rr],.95)) if rr else None,signed_mean=float(np.mean([r['signed_error'] for r in rr])) if rr else None,
        false_goal_count=sum(r['false_goal'] for r in rr),false_goal_runs=len({r['uid'] for r in rr if r['false_goal']}))

def delay_stats(rr):
    observed=[r['delay_after_true_inferences'] for r in rr if r['delay_after_true_inferences'] is not None]
    signed=[r['signed_first_MAP_delay'] for r in rr if r['signed_first_MAP_delay'] is not None]
    return dict(true_goal_runs=sum(r['true_goal_reached'] for r in rr),delay_median_inferences=float(np.median(observed)) if observed else None,
        right_censored_runs=sum(r['right_censored_after_true'] for r in rr),delay_observed_runs=len(observed),
        delay_p95_inferences=float(np.quantile(observed,.95)) if observed else None,negative_early_goal_runs=sum(r['early_negative_delay'] for r in rr),
        signed_first_MAP_median=float(np.median(signed)) if signed else None,no_true_goal_runs=sum(not r['true_goal_reached'] for r in rr))

def generate(root=RUN_ROOT,output=OUT,document=None):
    protocol=verify();root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    inv=json.loads((root/'inventory.json').read_text()) if (root/'inventory.json').exists() else dict(protocol_sha256=protocol,groups={'CAL':[],'EVAL':[]},coverage=[])
    assert inv['protocol_sha256']==protocol
    model=json.loads((root/'calibration.json').read_text()) if (root/'calibration.json').exists() else None
    model_hash=sha256_file(root/'calibration.json') if model else None
    results=[];parts=[]
    for item in inv['groups']['CAL']:
        f=cache_path(root/'cal_cache',item)
        if f.exists():
            part=json.loads(f.read_text());assert part['fingerprint']==fingerprint(item,protocol);parts.append(part)
    for item in inv['groups']['EVAL']:
        f=cache_path(root/'eval_cache',item)
        if f.exists():
            result=json.loads(f.read_text());assert result['fingerprint']==fingerprint(item,protocol,model_hash);results.append(result)
    events=[e for r in results for e in r['rows']];declarations=[e for r in results for e in r['declarations']];delays=[e for r in results for e in r['delays']]
    summary=[];by_phase=[];delay_table=[]
    for variant in VARIANTS:
        rr=[e for e in events if e['variant']==variant];decl=[e for e in declarations if e['variant']==variant]
        wrong=[e for e in decl if e['original_wrong_stop']];success=[e for e in decl if e['original_success']]
        summary.append(dict(variant=variant,**stats(rr),original_wrong_stop=len(wrong),wrong_stop_blocked=sum(e['would_declare'] is False for e in wrong),
            wrong_stop_unmeasured=sum(e['would_declare'] is None for e in wrong),original_success=len(success),success_declaration_retained=sum(e['would_declare'] is True for e in success),
            success_unmeasured=sum(e['would_declare'] is None for e in success)))
        delay_table.append(dict(variant=variant,**delay_stats([e for e in delays if e['variant']==variant])))
    for phase,scene in sorted({(e['phase'],e['scene']) for e in events}):
        for variant in VARIANTS:by_phase.append(dict(phase=phase,scene=scene,variant=variant,**stats([e for e in events if (e['phase'],e['scene'],e['variant'])==(phase,scene,variant)])))
    coverage=[]
    for split,phase,*unused in SOURCES:
        registered=[c for c in inv['coverage'] if c['split']==split and c['phase']==phase]
        used=[r for r in (parts if split=='CAL' else results) if r['phase']==phase]
        coverage.append(dict(split=split,phase=phase,registered_runs=len(registered) if registered else None,available_runs=sum(c['status']=='AVAILABLE' for c in registered),
            processed_runs=len(used),used_runs=sum((r['inference_count'] if split=='CAL' else r['input_events'])>0 for r in used),used_inferences=sum(r['inference_count'] if split=='CAL' else r['input_events'] for r in used),
            missing_inferences=sum(len(r['missing_events']) for r in used),used_adjacent_pairs=sum(len(r['residuals']) for r in used) if split=='CAL' else None))
    status=dict(status='PREPARED_NOT_RUN' if not results else 'COMPLETE' if len(parts)+len(results)==len(inv['coverage']) else 'PARTIAL_OR_AVAILABLE_ONLY',
        calibration_runs=len(parts),evaluation_runs=len(results),model_sha256=model_hash,protocol_sha256=protocol)
    atomic_json(output/'status.json',status);atomic_json(output/'calibration.json',model or dict(status='NOT_FITTED'));atomic_json(output/'coverage.json',inv['coverage'])
    for name,data in [('summary',summary),('phase_coverage',coverage),('by_scene',by_phase),('goal_delay',delay_table),('goal_delay_runs',delays),('declarations',declarations),('inferences',events)]:csvout(output/(name+'.csv'),data)
    inputs={f:h for item in [*inv['groups']['CAL'],*inv['groups']['EVAL']] for f,h in item['input_sha256'].items()};atomic_json(output/'input_sha256.json',inputs)
    doc=Path(document) if document else ROOT/'docs/LOC_V2_REPLAY.md'
    fit_meta=dict(status='NOT_FITTED') if model is None else {k:model[k] for k in ('sigma2','residual_mean','residual_count','candidate_distance_count','distance_bin_count','frozen_at_utc')}
    text=['# 위치추정 v2 오프라인 재생',table([status]),
        '성과 표는 평가 데이터 Phase57·58·59-P의 seed227·228 HMM run만 사용한다. 보정은 Phase47-C·52-P·53-P·NIGHT E1/E3의 HMM0 run만 사용하며 평가 결과로 보정값을 선택하거나 변경하지 않는다.',
        '## 데이터 범위와 보정 메타데이터',table(coverage),table([fit_meta]),
        'Phase47-C는 OURS-DETOUR+HMM, Phase57-P는 MIN/MIN+G18만 포함한다. 나머지 지정 phase는 HMM 사용 전 방법이며 보정 Phase52/53/NIGHT는 D075·D150을 모두 포함한다. 보정172개·평가48개가 예정 범위다. 미완료/파일 누락은 coverage.json에 표시하고, 사용 run·추론 수는 위 표로 공개한다. 보정·평가 폴더 및 seed 집합의 비중복을 검사한다. 보정 자료의 성능 수치는 이 문서에 보고하지 않는다.',
        '## 고정 정식화와 사용 가정',
        'Topomap 노드 pose와 오도메트리가 동일한 좌표계로 제공된다고 가정한다. 경로 접선은 내부 노드에서 p[j+1]−p[j−1]의 단위벡터,양 끝은 단방향 인접차다. 길이0이면 가장 가까운 유효 인접 선분을 쓴다. ℓ은 기존 양수 인접 노드 간격 중앙값이다.',
        '| 변형 | 방출 | 전이 |\n|---|---|---|\n| HMM0 | 기존 exp(−NoMaD 거리) | 기존 최소1+ceil 주행거리 폭 |\n| NET | 기존 | 동결 HMM_REPLAY NET |\n| OBS | 보정 히스토그램 곱 | HMM0 |\n| SIGN | 기존 | 부호 있는 Gaussian |\n| OBS+SIGN | 보정 히스토그램 곱 | SIGN |',
        'OBS에서 가설 노드 i의 방출은 ∏_j p(bin(d_j) | k=j−i)이다. k=−4..+4와 양쪽 범위 밖을 합친1행,거리 bin0.5,Laplace1이다. bin의 유한 범위는 보정 데이터의 min/max로만 정하고 양 끝 underflow/overflow bin을 따로 둔다. 평가 거리로 범위를 늘리지 않는다.',
        'SIGN 보정은 직전 추론의 로그 HMM0 MAP 접선에 현재−직전 odometry XY를 투영한 s를 쓰고, residual=(true_node_t−true_node_prev)−s/ℓ의 모집단 분산(ddof0)을 구한다. 평가 시에는 각 변형의 직전 MAP 접선을 쓴다. 전이 가중치는 정수 offset j−i에서 N(s/ℓ,σ²) 밀도를 평가해 전체 지도 노드 범위에서 행 정규화한다. 분산 floor·support cutoff·평가 튜닝은 없다.',
        '각 재생은 기록된 후보 창과 거리값에 조건부로 수행한다. 창 밖 거리는 생성하지 않고,창 안 도달 prior가0이면 기존 Phase42-L처럼 창 균등 prior로 재초기화한다. 첫 prior와 동률 규칙도 기존 그대로다. HMM0/NET 및 선언 시점 연결은 nomad_hmm_replay 코드를 재사용한다.',
        '## 평가 데이터 성과',table(summary),
        '오차는 관측 시점 MAP−true_node이며 거짓 목표는 MAP==goal AND true_node<goal−2다. 거짓 목표 run 수는 해당 추론이 하나 이상인 평가 run 수다. 기존 잘못된 도착/성공은 원래 선언을 발생시킨 추론 ID에서만 차단/유지 여부를 비교하며 주행 성공 수를 다시 정의하지 않는다.',
        '## 실제 목표 노드 도달 이후 지연',table(delay_table),
        '주 지연의0은 저장 추론에서 true_node가 처음 goal이 된 추론이다. 그 추론 이후 첫 MAP=goal까지의 추론 ID 간격을 센다. 끝까지 이후 확인이 없으면 우측 검열로 두고 지연 중앙값에서 제외하며,검열 수를 중앙값 바로 옆에 표시한다. 실제 목표 노드를 관측하지 않은 run은 별도로 표시한다.',
        '실제 도달 전에 MAP=goal이 있었으면 negative_early_goal_runs로 별도 집계한다. signed_first_MAP_median은 최초 MAP=goal ID−최초 true_node=goal ID의 부호 있는 보조 중앙값으로 음수를 포함한다. 조기 판정과 이후 검열은 동시에 성립할 수 있다(일찍 goal을 냈지만 실제 도달 뒤 다시 goal을 내지 못한 경우). 따라서 주 지연과 조기 판정을 합쳐 검열을 숨기지 않는다.',
        table(delays or [dict(status='NOT_RUN')]),'## 평가 phase·장면별',table(by_phase or [dict(status='NOT_RUN')]),
        '## 기존 선언 시점 비교',table(declarations or [dict(status='NOT_RUN')]),
        '## 한계',
        '1. OBS는 창 안 거리값들이 서로 독립이라는 가정의 곱이므로 과신할 수 있다.\n2. SIGN 분산은 로그의 HMM0 MAP 접선 기준으로 보정했으므로 MAP이 틀렸던 구간의 오차가 분산에 포함된다.']
    doc.write_text('\n\n'.join(text)+'\n');return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate()
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report held-out localization v2 OBS SIGN replay with frozen calibration','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
