"""Four main-run results and requested top-down images, system Python only."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase31p.report import table
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,protocol,verify
from .figures import generate as make_figures

FIELDS=('classification','success','collision','wrong_stop','timeout_without_declaration','box_passage','passage_side','box_passage_from_spawn_s',
        'spawn_time_s','goal_time_s','stopped_s','align_rotate_s','minimum_clearance_m','ec_rejects','graph_adoption_rate','graph_rejection_reasons')

def generate(root=RUN_ROOT,output=OUT,document=None,figure_dir=None):
    p=verify();root=Path(root);output=Path(output);output.mkdir(exist_ok=True,parents=True)
    runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    expected={(j['scene'],j['index'],j['method']) for j in p['main_order']};keys=[(r['scene'],r['index'],r['method']) for r in runs]
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    for r in runs:r.setdefault('condition',r['scene'].rsplit('_',1)[1])
    by={(r['scene'],r['index'],r['method']):r for r in runs};summary=[]
    for j in p['main_order']:
        r=by.get((j['scene'],j['index'],j['method']));row=dict(scene=j['scene'],seed=j['index'],method=j['method'],technical=r['technical_validation'] if r else 'NOT_RUN')
        row.update({k:r.get(k) if r and r['technical_validation']=='PASS' else None for k in FIELDS});summary.append(row)
    plots=make_figures(runs,figure_dir)
    state=dict(status='COMPLETE' if len(runs)==4 else 'PARTIAL' if runs else 'PREPARED_NOT_RUN',completed=len(runs),planned=4,smoke=False,
        protocol_sha256=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest())
    save(output/'runs.json',runs);save(output/'status.json',state);csvout(output/'summary.csv',summary);save(output/'figure_manifest.json',plots)
    docs=Path(document) if document else ROOT/'docs/H1V2_TRIAL.md'
    rows=['# H1-v2 시험 주행',table([state]),'Phase53-P CUT·GRAPH-HO, EC 제동꼬리, 1초 만료 및 HMM·공식 도착 판정은 동결 그대로다. 장면만 H1-v2(y=1.10, 65556be)로 연결했다. Smoke는 없고 지정한4회가 본 실행이다.',
        table(summary),'분류·통과·최소 여유·EC·Graph 수치는 기존 평가/log에서 가져온다. 통과 쪽은 +y 진행 기준 +X(오른쪽)/−X(왼쪽), 출현→통과 시간은 실제 spawn 시각부터의 시간이다. Graph 채택률은 실제 Graph 설치/시도이며 실패 사유는 원 solver·certificate·EC 거절 로그명 그대로다.']
    if plots['files']:
        rows.extend(['![4 runs, top-down only](figures/h1v2_trial_all.png)',
            '\n'.join(f'- [{Path(f).stem}](figures/{Path(f).name})' for f in plots['files'] if Path(f).name!='h1v2_trial_all.png'),
            '위 그림은 시간축 없이 저장된 실제72Hz 궤적을 명령 상태 색으로 그린다. 회색 점선=CUT, 주황 파선=GRAPH 설치 경로. 아주 옅은 선은 controller에 도착한 각 chunk의 원 NoMaD8후보(저장 metric을 관측 pose로 world 변환)이며, 설치/채택되지 않은 후보도 표시한다. 빨간x는 저장 EC 거절 위치, 보라 마름모는 상자 출현 순간 로봇 위치다. 상자 미출현 시 계획 위치를 비어 있는 점선으로 구별한다.',table(plots['details'])])
    else:rows.append('아직 주행하지 않았다. 종료 후 run별 PNG4장과2×2 종합 PNG를 자동 생성한다.')
    docs.write_text('\n\n'.join(rows)+'\n');return docs,plots

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc,plots=generate()
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        images=[str(Path(f).relative_to(ROOT)) for f in plots['files']]
        if images:subprocess.run(['git','add','-f','--',*images],cwd=ROOT,check=True)
        tracked=paths+images
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*tracked],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report four H1-v2 CUT and GRAPH-HO trial runs','--',*tracked],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
