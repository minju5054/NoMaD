"""Automatic run tables/plots and frozen same-seed Phase57 baseline columns."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,verify
FIELDS=('classification','success','collision','wrong_stop','timeout_without_declaration','box_passage','box_passage_from_spawn_s','goal_time_s','stopped_s',
        'left_right_switches','backward_reference_selections','backward_robot_selections','graph_adoption_rate','graph_solve_p50_s','graph_solve_p95_s')
BASELINE=ROOT/'research/results/phase57p/runs.json'

def generate(root=RUN_ROOT,output=OUT,document=None):
    p=verify();root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    expected={(r['scene'],r['index'],r['method']) for r in p['main_order']};keys=[(r['scene'],r['index'],r['method']) for r in runs]
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    baselines=json.loads(BASELINE.read_text()) if BASELINE.exists() else [];baseline_sha=sha256_file(BASELINE) if BASELINE.exists() else None
    baselines=[r for r in baselines if r['method'] in ('NOMAD_RAW','MIN')]
    summary=[]
    for m in METHODS:
        for s in (*SCENES,'ALL'):
            rr=[r for r in runs if r['method']==m and (s=='ALL' or r['scene']==s)];good=[r for r in rr if r['technical_validation']=='PASS']
            attempts=sum(r.get('graph_attempts',0) for r in good);applied=sum(r.get('graph_applied',0) for r in good)
            summary.append(dict(method=m,scene=s,n=len(rr),valid=len(good),**{k:sum(bool(r.get(k)) for r in good) for k in FIELDS[1:6]},
                goal_time_s=median([r['goal_time_s'] for r in good if r.get('goal_time_s') is not None]),stopped_s=median([r['stopped_s'] for r in good if r.get('stopped_s') is not None]),
                left_right_switches=sum(r.get('left_right_switches',0) for r in good),backward_reference_selections=sum(r.get('backward_reference_selections',0) for r in good),
                backward_robot_selections=sum(r.get('backward_robot_selections',0) for r in good),graph_attempts=attempts,graph_applied=applied,graph_adoption_rate=applied/attempts if attempts else None))
    by={(r['scene'],r['index'],r['method']):r for r in runs};details=[]
    for j in p['main_order']:
        r=by.get((j['scene'],j['index'],j['method']));row=dict(j,status=r['technical_validation'] if r else 'NOT_RUN')
        row.update({k:r.get(k) if r else None for k in FIELDS})
        for method in ('NOMAD_RAW','MIN'):
            b=next((x for x in baselines if x['scene']==j['scene'] and x['index']==j['index'] and x['method']==method),{})
            row['P57_'+method+'_status']=b.get('technical_validation','NOT_AVAILABLE')
            row.update({'P57_'+method+'_'+k:b.get(k) for k in FIELDS})
        details.append(row)
    status=dict(status='COMPLETE' if len(runs)==18 else 'PARTIAL' if runs else 'PREPARED_NOT_RUN',planned=18,completed=len(runs),
        protocol_sha256=sha256_file(HERE/'protocol.json'),phase57_results_sha256=baseline_sha,phase57_baseline_records=len(baselines))
    save(output/'runs.json',runs);save(output/'status.json',status);csvout(output/'summary.csv',summary);csvout(output/'paired.csv',details)
    from .figures import generate as figures
    files=figures(runs,output/'figures')
    doc=Path(document) if document else ROOT/'docs/PHASE58P_RESULTS.md'
    lines=['# Phase58-P',table([status]),
        '세 방법 모두 Phase53 CUT의 depth 필터·RECOVER·정렬·전속도→0.1→STOP fallback·HMM·1s 만료·공식 도착 판정을 유지하고 ENDPOINT latch를 사용한다. CONS만 후보 순서를 기준 방향과 각도 최소/잔여 길이 최대 순으로 바꾼다. G18은 기존 E2 경계 곡률 조건부 제외 구현을 재사용한다.',
        '좌우 전환은 선택된 NoMaD 후보 끝점 방향의 실제 로봇 heading 기준 부호가 연속 비중립 설치 사이에 바뀐 횟수다. 뒤 선택의 주 집계는 CONS 기준 방향과의 각도 >90°이며, 실제 로봇 heading 대비 >90°도 구분해 표시한다. Graph가 보정된 경우 다음 기준은 보정된 실제 설치 끝점이다.',
        'Phase57 비교는 같은 scene·seed의 이미 발표된 NOMAD_RAW/MIN만 읽는다. 실행 날짜와 정책이 다르며 누락 필드는 —다. 진행 중인 Phase57 로그는 읽거나 변경하지 않는다. 비교 파일 hash는 이 report 생성 시점의 값이다.',
        table(summary),table([{k:('—' if v is None else v) for k,v in r.items()} for r in details])]
    for file in files:
        f=Path(file);lines.append(f'![{f.stem}](../{f.relative_to(ROOT)})' if f.is_relative_to(ROOT) else f'![{f.stem}]({f})')
    doc.write_text('\n\n'.join(lines)+'\n');return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate()
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase58-P consistency selection pilot and saved-run plots','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
