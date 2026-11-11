"""Oracle analysis-condition outcomes, paired success differences and PNG publication."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from nomad_isaac.common import sha256_file
from nomad_phase60p.report import stage_report
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,verify
COMPARISONS=(('CONS','CUT'),('CONS+G18','CUT'),('CONS+G18','CONS'))
FIELDS=('classification','success','collision','wrong_stop','timeout_without_declaration','box_passage','box_passage_from_spawn_s',
        'goal_time_s','stopped_s','left_right_switches','backward_reference_selections','backward_robot_selections','graph_adoption_rate','graph_solve_p50_s','graph_solve_p95_s')

def paired(rows):
    by={(r['scene'],r['index'],r['method']):r for r in rows};details=[];summary=[]
    for left,right in COMPARISONS:
        valid=[]
        for scene in SCENES:
            for seed in INDICES:
                a=by.get((scene,seed,left));b=by.get((scene,seed,right));ok=bool(a and b and a['technical_validation']==b['technical_validation']=='PASS')
                row=dict(comparison=left+' minus '+right,scene=scene,seed=seed,left_status=a['technical_validation'] if a else 'NOT_RUN',
                    right_status=b['technical_validation'] if b else 'NOT_RUN',left_success=a.get('success') if a else None,
                    right_success=b.get('success') if b else None,success_difference=int(a['success'])-int(b['success']) if ok else None)
                details.append(row)
                if ok:valid.append(row)
        summary.append(dict(comparison=left+' minus '+right,valid_pairs=len(valid),planned_pairs=6,
            left_success=sum(r['left_success'] for r in valid),right_success=sum(r['right_success'] for r in valid),
            success_difference=sum(r['success_difference'] for r in valid) if valid else None,left_only=sum(r['success_difference']==1 for r in valid),
            right_only=sum(r['success_difference']==-1 for r in valid),both_success=sum(r['left_success'] and r['right_success'] for r in valid),
            both_failure=sum(not r['left_success'] and not r['right_success'] for r in valid)))
    return details,summary

def generate(root=RUN_ROOT,output=OUT,document=None):
    p=verify();root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    expected={(j['scene'],j['index'],j['method']) for j in p['main_order']};keys=[(r['scene'],r['index'],r['method']) for r in runs]
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    summary=[]
    for method in METHODS:
        for scene in (*SCENES,'ALL'):
            rr=[r for r in runs if r['method']==method and (scene=='ALL' or r['scene']==scene)];good=[r for r in rr if r['technical_validation']=='PASS']
            row=dict(method=method,scene=scene,n=len(rr),valid=len(good))
            for k in ('success','collision','wrong_stop','timeout_without_declaration','box_passage'):
                row[k]=sum(bool(r[k]) for r in good) if good else None
            for k in ('goal_time_s','stopped_s','box_passage_from_spawn_s'):
                row[k+'_median']=median([r[k] for r in good if r.get(k) is not None])
            for k in ('left_right_switches','backward_reference_selections','backward_robot_selections'):
                row[k]=sum(r[k] for r in good) if good else None
            attempts=sum(r.get('graph_attempts',0) for r in good);applied=sum(r.get('graph_applied',0) for r in good)
            row.update(graph_attempts=attempts,graph_applied=applied,graph_adoption_rate=applied/attempts if attempts else None);summary.append(row)
    by={(r['scene'],r['index'],r['method']):r for r in runs};details=[]
    for j in p['main_order']:
        r=by.get((j['scene'],j['index'],j['method']),{});details.append(dict(j,status=r.get('technical_validation','NOT_RUN'),**{k:r.get(k) for k in FIELDS}))
    pairs,pair_summary=paired(runs)
    status=dict(status='COMPLETE' if len(runs)==18 else 'PARTIAL' if runs else 'PREPARED_NOT_RUN',planned=18,completed=len(runs),
        oracle_localization_analysis_only=True,pose_clock='observation_pose',delivery_delay_s=.75,protocol_sha256=sha256_file(HERE/'protocol.json'))
    save(output/'runs.json',runs);save(output/'status.json',status)
    for name,rr in [('summary',summary),('runs',details),('paired',pairs),('paired_summary',pair_summary)]:csvout(output/(name+'.csv'),rr)
    from .figures import generate as figures
    files=figures(runs,output/'figures');save(output/'figures.json',dict(files=files,count=len(files),force_stage_png=True))
    doc=Path(document) if document else ROOT/'docs/PHASE61P_RESULTS.md'
    shown=lambda rr:table([{k:('—' if v is None else v) for k,v in r.items()} for r in rr])
    text=['# Phase61-P — oracle 위치추정 분석용 조건',
        '**실용 위치추정 성능 실험이 아니다.** 영상 관측 시점 시뮬레이터 실제 robot pose와 Topomap 노드 pose를 사용해 XY 최근접 노드를 선택한다. HMM은 사용하지 않는다. 이 oracle 정보는 위치추정에만 쓰며 장애물·EC·Graph에는 새 oracle 정보를 제공하지 않는다.',
        table([status]),'관측 시점 최근접 노드를 먼저 계산한 뒤 기존 candidate_range(radius4) 창과 subgoal 규칙을 그 노드에 적용한다. NoMaD 거리의 threshold3와 창 끝 clamp,closest==goal 선언은 그대로다. D075 전달 지연도 유지하므로 선언은 적용 시점의 실제 위치가 아니라 관측 시점 oracle 노드에 기반한다.',
        'Phase58-P의 CUT/CONS/CONS+G18·EC-tail·ENDPOINT latch·depth 필터·회복·정렬·0.1 fallback·1s 만료·도착 평가를 그대로 유지한다. 새 seed229·230은 기존 jitter 생성 규칙에 입력하며 H1-v2 고정 상자는 그대로다.',
        shown(summary),shown(details),'## 쌍별 성공 차이',
        '동일(scene,seed)의 두 run이 모두 기술 PASS인 경우만 성공 차이(left−right)를 계산한다. 미실행·기술 실패는 —이며 실패0으로 대체하지 않는다. 통계 검정이나 새 성과 판정 기준은 추가하지 않았다.',shown(pair_summary),shown(pairs)]
    for file in files:
        f=Path(file);text.append(f'![{f.stem}](../{f.relative_to(ROOT)})' if f.is_relative_to(ROOT) else f'![{f.stem}]({f})')
    doc.write_text('\n\n'.join(text)+'\n');return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate()
    if a.publish:
        paths=stage_report(doc,OUT)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase61-P oracle-localization analysis pilot with paired outcomes and figures','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
