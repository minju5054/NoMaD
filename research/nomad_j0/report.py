"""Frozen descriptive scene selection, never tunes any run or parameter."""
import argparse
import csv
import json
import subprocess
from pathlib import Path
import numpy as np
from nomad_phase18.report import table
from nomad_phase26.storage import atomic_json
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,INDICES,DELAYS,verify

def stats(values):
    a=np.array([v for v in values if v is not None],float)
    return dict(n=len(a),mean=float(a.mean()) if len(a) else None,median=float(np.median(a)) if len(a) else None,
                p95=float(np.quantile(a,.95)) if len(a) else None)

def selection(records):
    by={(r['scene'],r['index'],r['delay']):r for r in records};rows=[]
    for scene in SCENES:
        groups=[[by.get((scene,i,d)) for i in INDICES] for d in DELAYS]
        complete=all(r and r.get('technical_validation')=='PASS' for group in groups for r in group)
        observed=bool(complete and all(r.get('checkpoint_time_s') is not None for group in groups for r in group))
        success0=sum(bool(r and r.get('technical_validation')=='PASS' and r.get('success')) for r in groups[0])
        means=[float(np.mean([r['checkpoint_time_s'] for r in g])) for g in groups] if observed else [None,None]
        passed=bool(success0==2 and observed and means[1]>means[0])
        rows.append(dict(scene=scene,zero_success=success0,required_success=2,complete=bool(complete),all_checkpoints_observed=observed,
            zero_checkpoint_mean_s=means[0],delayed_checkpoint_mean_s=means[1],difference_s=means[1]-means[0] if observed else None,
            passed=passed,reason='PASS' if passed else 'INCOMPLETE_OR_MISSING_CHECKPOINT' if not observed else 'ZERO_DELAY_NOT_2_OF_2' if success0!=2 else 'NO_DELAY_INCREASE'))
    ranked=sorted((r for r in rows if r['passed']),key=lambda r:(r['zero_checkpoint_mean_s'],SCENES.index(r['scene'])))
    return dict(status='COMPLETE' if len(records)==20 else 'PARTIAL' if records else 'PREPARED_NOT_RUN',
        selected_scenes=[r['scene'] for r in ranked[:3]],eligible_scenes=len(ranked),rows=rows,
        missing_policy='Require both checkpoint observations in both conditions; no censoring or imputation',
        tie_rule='Frozen SCENES order',criteria='zero-delay success 2/2 AND delayed checkpoint mean strictly greater; rank zero-delay mean ascending')

def csv_write(path,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)

def generate(root=RUN_ROOT,out=OUT,doc=None,records=None):
    p=verify();root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    records=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))] if records is None else records
    expected={(j['scene'],j['index'],j['delay']) for j in p['main_order']}
    keys=[(r['scene'],r['index'],r['delay']) for r in records]
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    summaries=[]
    for scene in SCENES:
        for delay in DELAYS:
            rr=[r for r in records if r['scene']==scene and r['delay']==delay];vv=[r for r in rr if r['technical_validation']=='PASS']
            cp=stats([r.get('checkpoint_time_s') for r in vv]);arrival=stats([r.get('goal_time_s') for r in vv])
            summaries.append(dict(scene=scene,delay_s=delay,planned=2,completed=len(rr),technical_failures=len(rr)-len(vv),
                success=sum(r['success'] for r in vv),collision=sum(r['collision'] for r in vv),wall_intrusion=sum(r['wall_intrusion'] for r in vv),
                timeout=sum(r['timeout'] for r in vv),checkpoint_n=cp['n'],checkpoint_mean_s=cp['mean'],checkpoint_median_s=cp['median'],
                checkpoint_p95_s=cp['p95'],arrival_median_s=arrival['median'],arrival_p95_s=arrival['p95']))
    decision=selection(records);decision['protocol_sha256']=sha256_file(HERE/'protocol.json')
    detail=[{k:r.get(k) for k in ('scene','index','method','delay','technical_validation','classification','success','collision','wall_intrusion','timeout',
             'checkpoint_axis','checkpoint_threshold_m','checkpoint_start_distance_m','checkpoint_time_s','checkpoint_status','goal_time_s','error')} for r in records]
    coordinate=[]
    for scene in SCENES:
        for index in INDICES:
            rr=[r for r in records if r['scene']==scene and r['index']==index and r.get('checkpoint_threshold_m') is not None]
            values=[r['checkpoint_threshold_m'] for r in rr]
            coordinate.append(dict(scene=scene,index=index,threshold_observations=len(values),methods=len({r['method'] for r in rr}),
                max_same_seed_between_methods_m=0. if values else None,between_methods_scope='N/A: one method only',
                max_same_seed_between_delays_m=max(values)-min(values) if len(values)>1 else None))
    atomic_json(out/'runs.json',records);atomic_json(out/'decision.json',decision)
    csv_write(out/'summary.csv',summaries);csv_write(out/'runs.csv',detail);csv_write(out/'checkpoint_coordinates.csv',coordinate)
    doc=Path(doc) if doc else ROOT/'docs/J0_RESULTS.md'
    checkpoints=[dict(scene=s,**p['scenes'][s]['checkpoint']) for s in SCENES]
    doc.write_text('\n\n'.join(['# J0 장면 선별',table([dict(status=decision['status'],completed=len(records),planned=20,selected_J1_scenes=', '.join(decision['selected_scenes']) or '—',protocol_sha256=decision['protocol_sha256'])]),
        '종료 판정은 Phase18과 동일(0.3m). 실제 목표 반경 진입이며 closest_node 기반 종료는 쓰지 않는다.',
        'OURS-noEC: Phase18 최장 SAFE + GRAPH-depth-CLR + PP/CURV와 ENDPOINT latch. EC·회복·STOP_WAIT 특수처리·HMM/NET 없음. 0s 10회가 먼저, 0.75s 10회가 뒤다. seed221·222 공통.',
        '체크포인트는 로봇 중심이 마지막 상자 먼 면+0.30m를 진행축으로 처음 넘는 저장72Hz 시점이다. H1-v2의 대상은 새 돌발 상자이며, H2는 실제 마지막 spawn 상자의 +x 투영 반폭을 사용한다. H2 마지막 상자 미생성 시 미측정이다.',
        table(checkpoints),table(summaries),table(decision['rows']),
        '선별: 0s 성공2/2 AND 0.75s 체크포인트 평균>0s 평균. 조건마다 두 checkpoint가 모두 관측된 장면만 비교하며 결측을 대체하지 않는다. 통과 장면을 0s 평균 오름차순으로 최대3개 선택한다. 동률은 동결 장면 순서. 기술 실패·미완료는 선별하지 않는다.',
        table(detail),'동일seed 방법 간 임계좌표 최대차: J0는 방법1개라 비교 불가(관측값 존재 시 범위0). 지연 조건 간 차이는 별도 열이며 장면별 지연 비교 해석 시 함께 확인한다.',table(coordinate),
        '새 시뮬레이션을 하지 않은 PREP 단계에서는 결과·장면 선택을 주장하지 않는다. 누적 결과는 같은run-root에서 재개하며 과거 실험 결과를 덮어쓰지 않는다.'])+'\n')
    return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))]
        subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report J0 delay-based scene screening','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

if __name__=='__main__':main()
