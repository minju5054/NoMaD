import argparse
import json
import subprocess
from pathlib import Path
from nomad_j0.report import stats,csv_write
from nomad_phase18.report import table
from nomad_phase26.storage import atomic_json
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,METHODS,verify
from .statistics import primary

def generate(root=RUN_ROOT,out=OUT,document=None):
    p=verify();root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rr=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    expected={(j['scene'],j['index'],j['method']) for j in p['main_order']};keys=[(r['scene'],r['index'],r['method']) for r in rr]
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    result=primary(rr);result.update(protocol_sha256=sha256_file(HERE/'protocol.json'),completed_runs=len(rr),planned_runs=195)
    summary=[]
    for scene in (*SCENES,'ALL'):
        for method in METHODS:
            allrows=[r for r in rr if r['method']==method and (scene=='ALL' or r['scene']==scene)];valid=[r for r in allrows if r['technical_validation']=='PASS']
            arrival=stats([r.get('goal_time_s') for r in valid]);cp=stats([r.get('checkpoint_time_s') for r in valid]);solve=stats([v for r in valid for v in r.get('solve_times_s',[])])
            summary.append(dict(scene=scene,method=method,planned=39 if scene=='ALL' else 13,completed=len(allrows),technical_failures=len(allrows)-len(valid),
                success=sum(r['success'] for r in valid),collision=sum(r['collision'] for r in valid),wall_intrusion=sum(r['wall_intrusion'] for r in valid),
                timeout=sum(r['timeout'] for r in valid),arrival_n=arrival['n'],arrival_median_s=arrival['median'],arrival_p95_s=arrival['p95'],
                checkpoint_n=cp['n'],checkpoint_median_s=cp['median'],checkpoint_p95_s=cp['p95'],
                graph_applied=sum(r['graph_applied'] for r in valid),ec_checks=sum(r.get('ec_checks',0) for r in valid),ec_rejected=sum(r.get('ec_rejected',0) for r in valid),
                solve_median_s=solve['median'],solve_p95_s=solve['p95']))
    atomic_json(out/'runs.json',rr);atomic_json(out/'decision.json',result);csv_write(out/'summary.csv',summary)
    csv_write(out/'paired.csv',result['checkpoint_pairs']);csv_write(out/'primary.csv',result['primary'])
    doc=Path(document) if document else ROOT/'docs/J1_REPORT.md'
    doc.write_text('\n\n'.join(['# J1',f"**{result['label']}**",table([{k:v for k,v in result.items() if k not in ('primary','checkpoint_pairs')}]),
        '종료 판정은 Phase18과 동일(0.3m). 공식 NoMaD argmin closest/subgoal,1s 만료,관측pose world고정/현재B 투영,PP+CURV,depth V1,SDF 등록fix,ENDPOINT latch를 공통 사용한다. 회복·STOP_WAIT 특수처리·HMM/NET 없음.',
        'J0 선별에서 LC는 통과했고 H1-v3·SLW-v2는 미달했지만 각각 돌발 장애물·좁은 통로 평가를 위해 사용자 사전 결정으로 포함했다. seed231–243,195회,seed별15회 고정RNG 섞기. 5.5h가 지난 뒤 새seed블록은 시작하지 않고 완료된 블록까지 중간 보고하며 동일 명령으로 재개한다.',
        '52-P 대비: 제동꼬리 적분·swept certificate·설치/36tick 검사는 동일하며, controller만 공통 Phase18 PP/CURV를 전달하고 사용자 지시대로 다음후보/0.1/STOP_WAIT 대체를 제거해 설치거절은 KEEP,주기거절은 같은 경로+stop_command 감속으로 처리한다.',
        'OURS-noEC는 J0 실행 객체를 그대로 사용한다. RAW는 Phase18-RAW에 공통 ENDPOINT latch만 추가한다. RTC-hard는 Phase18 생성/SAFE 규칙이며 공통 제거사항을 적용한다. OURS는 SAFE 원경로 설치와 비동기Graph 보정을 각각EC로 인증한다. 원경로EC거절도 SAFE후보의Graph 시도를 막지 않으며 새chunk/STALE/만료 폐기는 동결 규칙이다.',
        table(summary),table(result['primary']),
        '주 비교는 완료seed블록의 기술PASS·관측된 짝만 사용한다. checkpoint 결측은 대체하지 않으며 n을 표시한다. 차이=OURS−RTC,seed cluster bootstrap20,000회(seed20261030),양측95% CI,귀무가설 중심화 bootstrap p=(1+|boot−mean|≥|mean| 횟수)/(B+1). 안전실패=충돌OR벽침범,정확McNemar 양측검정. 두 p의 가족에Holm α=.05. 중간값은 탐색적으로 제시하며 전체13seed 완료 전 판정은 보류한다.',
        table([dict(scene=s,**p['scenes'][s]['checkpoint']) for s in SCENES])])+'\n');return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report J1 completed seed blocks and preregistered comparisons','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

if __name__=='__main__':main()
