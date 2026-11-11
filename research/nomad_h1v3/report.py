"""Unchanged J0 screening criterion; own outputs and branch only."""
import argparse
import json
import subprocess
from pathlib import Path
from nomad_j0.report import selection as original_selection,stats,csv_write
from nomad_phase18.report import table
from nomad_phase26.storage import atomic_json
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,INDICES,DELAYS,verify,bind

def selection(records):
    result=bind(original_selection,SCENES=SCENES,INDICES=INDICES,DELAYS=DELAYS)(records)
    result['status']='COMPLETE' if len(records)==4 else 'PARTIAL' if records else 'PREPARED_NOT_RUN'
    return result

def generate(root=RUN_ROOT,out=OUT,document=None):
    p=verify();out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rr=[json.loads(f.read_text()) for f in sorted((Path(root)/'metrics').glob('*.json'))]
    keys=[(r['scene'],r['index'],r['delay']) for r in rr]
    assert len(keys)==len(set(keys)) and set(keys)<={(s,i,d) for s in SCENES for i in INDICES for d in DELAYS}
    decision=selection(rr);decision['protocol_sha256']=sha256_file(HERE/'protocol.json')
    summary=[]
    for delay in DELAYS:
        allrows=[r for r in rr if r['delay']==delay];valid=[r for r in allrows if r['technical_validation']=='PASS']
        cp=stats([r.get('checkpoint_time_s') for r in valid]);arr=stats([r.get('goal_time_s') for r in valid])
        summary.append(dict(scene='H1-v3',delay_s=delay,planned=2,completed=len(allrows),technical_failures=len(allrows)-len(valid),
            success=sum(r['success'] for r in valid),collision=sum(r['collision'] for r in valid),wall_intrusion=sum(r['wall_intrusion'] for r in valid),
            timeout=sum(r['timeout'] for r in valid),checkpoint_n=cp['n'],checkpoint_mean_s=cp['mean'],checkpoint_median_s=cp['median'],
            checkpoint_p95_s=cp['p95'],arrival_median_s=arr['median'],arrival_p95_s=arr['p95']))
    detail=[{k:r.get(k) for k in ('index','delay','classification','technical_validation','success','collision','wall_intrusion','timeout',
             'checkpoint_threshold_m','checkpoint_start_distance_m','checkpoint_time_s','goal_time_s','error')} for r in rr]
    atomic_json(out/'runs.json',rr);atomic_json(out/'decision.json',decision);csv_write(out/'summary.csv',summary);csv_write(out/'runs.csv',detail)
    doc=Path(document) if document else ROOT/'docs/H1V3_J0_RESULTS.md'
    doc.write_text('\n\n'.join(['# H1-v3 — J0 선별',table([dict(status=decision['status'],planned=4,completed=len(rr),
        eligible=bool(decision['selected_scenes']),protocol_sha256=decision['protocol_sha256'])]),
        '방법·판정은 J0와 동일한 OURS-noEC, Phase18 PP/CURV·1s 만료·공식 NoMaD subgoal·ENDPOINT latch다. 종료 판정은 Phase18과 동일(0.3m). EC·HMM/NET·회복·STOP_WAIT 특수처리 없음.',
        table([p['scenes']['H1-v3']['checkpoint']]),table(summary),table(decision['rows']),table(detail),
        '선별 기준: 0s 성공2/2 AND 0.75s checkpoint 평균>0s 평균. 두 조건 모두 seed221·222의 checkpoint가 있어야 하며 결측 대체 없음. 0s 두 run을 먼저 실행한다. 기존 H1-v2 코드·결과는 수정하지 않는다.',
        '![H1-v3 geometry](figures/h1v3_scene_preview.png)'])+'\n')
    return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))]
        subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report H1-v3 J0 scene screen','--',*paths],cwd=ROOT,check=True)
        branch=verify()['publish_branch'];assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()==branch
        subprocess.run(['git','push','origin',f'HEAD:refs/heads/{branch}'],cwd=ROOT,check=True)

if __name__=='__main__':main()
