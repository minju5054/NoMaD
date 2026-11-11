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
    r=bind(original_selection,SCENES=SCENES,INDICES=INDICES,DELAYS=DELAYS)(records)
    r['status']='COMPLETE' if len(records)==4 else 'PARTIAL' if records else 'PREPARED_NOT_RUN';return r

def generate(root=RUN_ROOT,out=OUT,document=None):
    p=verify();root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rr=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    keys=[(r['scene'],r['index'],r['delay']) for r in rr]
    assert len(keys)==len(set(keys)) and set(keys)<={(s,i,d) for s in SCENES for i in INDICES for d in DELAYS}
    decision=selection(rr);decision['protocol_sha256']=sha256_file(HERE/'protocol.json');summary=[]
    for d in DELAYS:
        allrows=[r for r in rr if r['delay']==d];valid=[r for r in allrows if r['technical_validation']=='PASS']
        cp=stats([r.get('checkpoint_time_s') for r in valid])
        summary.append(dict(scene='SLW-v2',delay_s=d,planned=2,completed=len(allrows),technical_failures=len(allrows)-len(valid),
            success=sum(r['success'] for r in valid),collision=sum(r['collision'] for r in valid),wall_intrusion=sum(r['wall_intrusion'] for r in valid),
            timeout=sum(r['timeout'] for r in valid),checkpoint_n=cp['n'],checkpoint_mean_s=cp['mean'],checkpoint_median_s=cp['median'],checkpoint_p95_s=cp['p95']))
    detail=[{k:r.get(k) for k in ('index','delay','classification','technical_validation','success','collision','wall_intrusion','timeout','checkpoint_time_s','goal_time_s','error')} for r in rr]
    from .figures import run_figures
    pictures=run_figures(rr,'slwv2_j0')
    atomic_json(out/'runs.json',rr);atomic_json(out/'decision.json',decision);atomic_json(out/'trajectory_figures.json',pictures)
    csv_write(out/'summary.csv',summary);csv_write(out/'runs.csv',detail)
    ref=root/'resolved_assets.json';resolved=json.loads(ref.read_text()) if ref.exists() else None
    state=root/'reference_state.json';ref_state=json.loads(state.read_text()) if state.exists() else dict(status='NOT_STARTED')
    if resolved:atomic_json(out/'reference_assets.json',resolved)
    doc=Path(document) if document else ROOT/'docs/SLWV2_J0_RESULTS.md'
    lines=['# SLW-v2 — J0 선별',table([dict(status=decision['status'],completed=len(rr),planned=4,eligible=bool(decision['selected_scenes']),protocol_sha256=decision['protocol_sha256'])]),
        '시작 x=-1.0m, 통로 시작벽 xmin=-2.0m, 상자색 빨강·파랑·노랑 외 장면 기하·목표·checkpoint는 SLW와 동일하다. 새 reference와2초 간격 Topomap은 동결 SLW 절차로 준비한 뒤에만 선별 주행한다.',
        table([ref_state]),table([p['scenes']['SLW-v2']['checkpoint']]),table(summary),table(decision['rows']),table(detail),
        '종료 판정은 Phase18과 동일(0.3m). J0 OURS-noEC 실행기·선별식 동결: 0s 성공2/2 AND 0.75s checkpoint 평균>0s 평균(각 조건 두 관측 필수, 결측 대체 없음). 0s 두 회 먼저 실행. 기존 SLW 코드·결과는 보존한다.']
    for pic in pictures:lines.append(f"![saved trajectory](figures/{Path(pic['file']).name})")
    doc.write_text('\n\n'.join(lines)+'\n');return doc,pictures

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc,pictures=generate()
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];images=[p['file'] for p in pictures]
        subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if images:subprocess.run(['git','add','-f','--',*images],cwd=ROOT,check=True)
        paths+=images
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report SLW-v2 J0 screen with saved trajectory figures','--',*paths],cwd=ROOT,check=True)
        branch=verify()['publish_branch'];assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()==branch
        subprocess.run(['git','push','origin',f'HEAD:refs/heads/{branch}'],cwd=ROOT,check=True)

if __name__=='__main__':main()
