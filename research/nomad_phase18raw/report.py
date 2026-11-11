"""Exploratory same-seed checkpoint bootstrap; existing Phase18 results untouched."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase18.report import stat,csv_write,table
from nomad_isaac.common import sha256_file
from nomad_phase26.storage import atomic_json
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,METHOD,BASELINES,protocol,verify_sources
from .statistics import paired
BASELINE_FILE=ROOT/'research/results/phase18/runs.json'

def generate(root=RUN_ROOT,output=OUT,document=None):
    verify_sources();p=protocol();root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('main_*.json'))]
    expected={(j['scene'],j['index'],j['method']) for j in p['main_order']};keys=[(r['scene'],r['index'],r['method']) for r in runs]
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    baseline=[r for r in json.loads(BASELINE_FILE.read_text()) if r['method'] in BASELINES]
    summary=[]
    for scene in (*SCENES,'ALL'):
        rr=[r for r in runs if scene=='ALL' or r['scene']==scene];valid=[r for r in rr if r['technical_validation']=='PASS']
        arrival=stat([r['goal_time_s'] for r in valid if r['success']])
        summary.append(dict(scene=scene,method=METHOD,planned=24 if scene=='ALL' else 8,attempted=len(rr),valid=len(valid),technical_failures=len(rr)-len(valid),
            success=sum(r['success'] for r in valid),safety_failures=sum(bool(r['collision'] or r['corridor']) for r in valid),timeout=sum(r['stuck'] for r in valid),
            other_termination=sum(not r['success'] and not(r['collision'] or r['corridor']) and not r['stuck'] for r in valid),
            arrival_n=arrival['n'],arrival_median_s=arrival['median'],arrival_p95_s=arrival['p95']))
    comparisons=[paired([*runs,*baseline],other,scene=None if scene=='ALL' else scene) for scene in ('ALL',*SCENES) for other in BASELINES]
    by={(r['scene'],r['index']):r for r in runs};details=[]
    for j in p['main_order']:
        r=by.get((j['scene'],j['index']),{});row=dict(j,status=r.get('technical_validation','NOT_RUN'),classification=r.get('classification'),
            success=r.get('success'),collision=r.get('collision'),corridor=r.get('corridor'),stuck=r.get('stuck'),goal_time_s=r.get('goal_time_s'),checkpoint_time_s=r.get('checkpoint_time_s'))
        for other,label in [(BASELINES[0],'OURS_CLR'),(BASELINES[1],'RTC_HARD')]:
            b=next((x for x in baseline if x['scene']==j['scene'] and x['index']==j['index'] and x['method']==other),{})
            row[label+'_checkpoint_s']=b.get('checkpoint_time_s')
            row['RAW_minus_'+label+'_checkpoint_s']=r['checkpoint_time_s']-b['checkpoint_time_s'] if r.get('technical_validation')=='PASS' and b.get('technical_validation')=='PASS' and r.get('checkpoint_time_s') is not None and b.get('checkpoint_time_s') is not None else None
        details.append(row)
    status=dict(status='COMPLETE' if len(runs)==24 else 'PARTIAL' if runs else 'PREPARED_NOT_RUN',planned=24,completed=len(runs),comparison='EXPLORATORY',
        raw_goal_rule=p['raw_goal_rule'],protocol_sha256=sha256_file(HERE/'protocol.json'),phase18_results_sha256=sha256_file(BASELINE_FILE))
    atomic_json(output/'runs.json',runs);atomic_json(output/'status.json',status)
    csv_write(output/'summary.csv',summary);csv_write(output/'paired.csv',comparisons);csv_write(output/'run_pairs.csv',details)
    doc=Path(document) if document else ROOT/'docs/PHASE18_RAW_RESULTS.md'
    rule='종료 판정은 Phase18과 동일(0.3m)'
    small=[{k:v for k,v in x.items() if k!='pairs'} for x in comparisons]
    doc.write_text('\n\n'.join(['# Phase18-RAW — 탐색적 추가 비교',table([status]),
        '기존 Phase18 실행·결과·raw는 수정하지 않는다. 새24개 RAW와 보존된 Phase18 GRAPH-depth-CLR(OURS)·RTC-hard를 같은(scene,seed)로만 연결한다. 실행일이 다르고 사후 추가한 기준선이므로 확인 실험 판정 라벨은 부여하지 않는다.',
        '실행기는 Phase18 PP lookahead0.25m+CURV(vmax0.3,|ω|≤0.4,기존 가속 규칙),72Hz/9Hz,1s 만료다. SP·출발 정렬·ENDPOINT latch·HMM·SAFE 필터·Graph·EC·회복은 적용하지 않는다. Depth 렌더/지도는 Phase18과 같은 부하·기록을 유지하지만 RAW 경로 선택에는 사용하지 않는다.',
        rule,table(summary),
        f"checkpoint는 Phase18의 저장72Hz 최초 axis>=threshold 시점 그대로다. 차이는 RAW−비교 방법(초),CI는{100*(1-p['raw_comparison_alpha']):.5f}%. seed 단위 장면 클러스터 bootstrap20,000회,seed20261030을 그대로 재사용한다. 두 방법 모두 기술 PASS이고 checkpoint가 있는 짝만 사용하며 결측은 대체하지 않는다. 도착시간은 성공 run만의 중앙값/p95다.",
        table(small),table(details)])+'\n');return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report exploratory Phase18 RAW baseline and paired checkpoint bootstrap','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
