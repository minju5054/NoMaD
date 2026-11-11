"""Phase59 NET outcomes and same-key Phase58 comparison; saved-log plots only."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,verify
FIELDS=('classification','success','collision','wrong_stop','timeout_without_declaration','stop_distance_m',
        'declaration_estimated_node','declaration_true_node','goal_node','reached_goal_0p7','arrived_without_declaration',
        'reached_goal_0p5','arrived_0p5_without_declaration','false_goal_count','minimum_actual_goal_distance_m',
        'goal_time_s','stopped_s','box_passage','graph_adoption_rate')
BASELINE=ROOT/'research/results/phase58p/runs.json'

def generate(root=RUN_ROOT,output=OUT,document=None,prepare_only=False):
    p=verify();root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    expected={(j['scene'],j['index'],j['method']) for j in p['main_order']};keys=[(r['scene'],r['index'],r['method']) for r in runs]
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    old=json.loads(BASELINE.read_text());baselines=[]
    from .metrics import localization_metrics
    for b in old:
        b=dict(b)
        if not prepare_only and b['technical_validation']=='PASS':
            b.update(localization_metrics(b['output'],b));b['supplementary_metrics_status']='SAVED_LOG_ONLY'
        else:b['supplementary_metrics_status']='NOT_COMPUTED_IN_PREPARATION' if prepare_only else 'TECHNICAL_FAILURE'
        baselines.append(b)
    summary=[]
    for phase,source in [('Phase59 NET',runs),('Phase58 HMM0',baselines)]:
        for method in METHODS:
            for scene in (*SCENES,'ALL'):
                rr=[r for r in source if r['method']==method and (scene=='ALL' or r['scene']==scene)];good=[r for r in rr if r['technical_validation']=='PASS']
                row=dict(phase=phase,method=method,scene=scene,n=len(rr),valid=len(good))
                for k in ('success','collision','wrong_stop','timeout_without_declaration','reached_goal_0p7','arrived_without_declaration','arrived_0p5_without_declaration'):
                    row[k]=sum(bool(r[k]) for r in good) if good and all(k in r for r in good) else None
                row['false_goal_count']=sum(r['false_goal_count'] for r in good) if good and all('false_goal_count' in r for r in good) else None
                row['false_goal_runs']=sum(r['false_goal_count']>0 for r in good) if row['false_goal_count'] is not None else None
                for k in ('stop_distance_m','goal_time_s','stopped_s'):
                    row[k+'_median']=median([r[k] for r in good if r.get(k) is not None])
                summary.append(row)
    by={(r['scene'],r['index'],r['method']):r for r in runs};oldby={(r['scene'],r['index'],r['method']):r for r in baselines};pairs=[]
    for j in p['main_order']:
        key=(j['scene'],j['index'],j['method']);r=by.get(key,{});b=oldby.get(key,{})
        row=dict(j,status=r.get('technical_validation','NOT_RUN'),Phase58_status=b.get('technical_validation','NOT_AVAILABLE'))
        row.update({k:r.get(k) for k in FIELDS});row.update({'Phase58_'+k:b.get(k) for k in FIELDS});pairs.append(row)
    status=dict(status='COMPLETE' if len(runs)==18 else 'PARTIAL' if runs else 'PREPARED_NOT_RUN',planned=18,completed=len(runs),
        protocol_sha256=sha256_file(HERE/'protocol.json'),phase58_results_sha256=sha256_file(BASELINE),baseline_enriched_from_saved_logs=not prepare_only)
    save(output/'runs.json',runs);save(output/'status.json',status);csvout(output/'summary.csv',summary);csvout(output/'paired.csv',pairs)
    save(output/'baseline_fields.json',[{k:r.get(k) for k in ('scene','index','method','output','supplementary_metrics_status',*FIELDS)} for r in baselines])
    from .figures import generate as figures
    files=figures(runs,output/'figures')
    doc=Path(document) if document else ROOT/'docs/PHASE59P_RESULTS.md'
    shown=lambda rr:table([{k:('—' if v is None else v) for k,v in r.items()} for r in rr])
    text=['# Phase59-P NET 전이 파일럿',table([status]),
        'Phase58-P와 방법·장면·seed·jitter·블록 순서·실행기·EC·Graph·latch·만료·공식 도착 기준이 같다. 변경은 NET 전이뿐이다. HMM_REPLAY Replay(NET)를 그대로 사용하고, 영상 observation tick의 odometry XY로 현재 MAP 진입 후 순변위를 계산한다. ℓ은 기존 중앙 노드 간격,round는 Python ties-to-even,최소1 없음,자기 전이 포함이다. MEM은 사용하지 않는다.',
        '후보 창은 기존 radius4 규칙으로 온라인 NET MAP을 중심으로 갱신한다. 방출·부목표 threshold3·closest==goal 선언 규칙은 동결이다. 이는 저장된 창을 고정한 오프라인 HMM_REPLAY와 달리 실제 후속 관측 창도 변할 수 있는 주행 비교다.',
        '성공은 기존대로 선언 시 거리≤0.5m AND 충돌 없음이다. reached_goal_0p7은 선언과 무관한72Hz 저장 목표거리 최소≤0.7m이며, arrived_without_declaration은 그 조건을 만족하고 run 종료까지 선언 파일이 없는 경우다. 기존0.5m 기준의 미선언 수도 보조 열로 구분한다. 실제 도착 여부를 새로운 성공으로 바꾸지 않는다.',
        '거짓 목표 판정은 HMM_REPLAY와 동일하게 추론 MAP==goal AND 관측 시점 true_node<goal−2인 건수(종료 후 저장 추론 포함)다. 실제 거리>0.5m의 잘못된 도착과는 다른 지표다. 선언 시 true_node는 선언 순간 실제 pose에 최근접인 Topomap 노드이며 관측 시점 true_node와 구분한다.',
        'Phase58 값은 같은(scene,seed,method) 결과의 옆 열이다. 추가 거리·노드 항목은 report 단계에서 저장 로그로만 읽어 새 표에 계산하고, 기존 Phase58 결과는 수정하지 않는다. 준비 단계에서는 이 보조 재계산을 하지 않아 일부 비교 열이 —다.',shown(summary),shown(pairs)]
    for file in files:
        f=Path(file);text.append(f'![{f.stem}](../{f.relative_to(ROOT)})' if f.is_relative_to(ROOT) else f'![{f.stem}]({f})')
    doc.write_text('\n\n'.join(text)+'\n');return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate()
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase59-P online NET transition pilot versus Phase58','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
