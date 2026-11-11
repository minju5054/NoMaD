"""After J0 exits: rerun only its four H2 jobs, preserve/merge the other 16."""
import argparse
import json
import subprocess
from pathlib import Path
from nomad_isaac.common import sha256_file
from nomad_phase26.storage import atomic_json
from .config import ROOT,HERE,OUT,RUN_ROOT,INDICES,DELAYS,verify
from .campaign import jobs,execute,status

RERUN_ROOT=ROOT.parent/'artifacts/isaac6/j0_h2_sdf_01'

def plan(root):
    selected=[j for j in jobs(root) if j['scene']=='H2']
    assert len(selected)==4 and {(j['delay'],j['index']) for j in selected}=={(d,i) for d in DELAYS for i in INDICES}
    return selected

def baseline(base):
    base=Path(base);state=status(base)
    assert state.get('status')=='COMPLETE' and state.get('stage')=='DONE','Wait for original J0 campaign/report to finish'
    old=HERE/'protocol_before_sdf_fix.json'
    assert state['protocol_sha256']==sha256_file(old),'Unexpected original J0 protocol'
    rr=[]
    for j in jobs(base):
        f=base/'metrics'/(j['key']+'.json')
        assert f.exists(),f
        r=json.loads(f.read_text())
        assert (r['scene'],r['index'],r['delay'])==(j['scene'],j['index'],j['delay'])
        rr.append((f,r))
    return rr

def combine(base,root):
    old=baseline(base);new=[]
    for j in plan(root):
        f=Path(root)/'metrics'/(j['key']+'.json')
        if f.exists():
            r=json.loads(f.read_text())
            assert (r['scene'],r['index'],r['delay'])==('H2',j['index'],j['delay'])
            new.append((f,r))
    kept=[(f,r) for f,r in old if r['scene']!='H2']
    assert len(kept)==16
    records=[r for _,r in kept+new]
    manifest=dict(original_root=str(Path(base).resolve()),rerun_root=str(Path(root).resolve()),
        retained_original_non_H2=[dict(file=str(f),sha256=sha256_file(f)) for f,_ in kept],
        preserved_superseded_original_H2=[dict(file=str(f),sha256=sha256_file(f)) for f,r in old if r['scene']=='H2'],
        replacement_H2=[dict(file=str(f),sha256=sha256_file(f)) for f,_ in new],
        original_protocol_sha256=sha256_file(HERE/'protocol_before_sdf_fix.json'),new_protocol_sha256=sha256_file(HERE/'protocol.json'),
        complete=len(new)==4,rule='Replace all four H2 jobs regardless of outcome; reuse all other 16 verbatim; never edit original artifacts')
    return records,manifest

def generate(base,root,publish=False):
    from .report import generate as frozen_report
    records,manifest=combine(base,root)
    doc=frozen_report(root,records=records)
    atomic_json(OUT/'h2_rerun_merge.json',manifest)
    doc.write_text(doc.read_text()+'\n## H2 SDF 등록 범위 배관 수정\n\n'+
        '원래 H2 네 attempt는 기술 실패 기록으로 원본에 보존한다. 고정 원점/해상도에서 +x 등록 상한만 확장한 네 재실행으로 교체하고, 나머지16개 metrics는 원본을 그대로 재사용했다. 방법·선별식·체크포인트·seed·지연은 동일하다. 이 보고서는 별도 수정 브랜치에서 생성되며 실행 중이던 작업 트리는 변경하지 않는다.\n')
    if publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))]
        subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet',
                '-m','Report J0 with four H2 SDF-registration reruns and sixteen original jobs','--',*paths],cwd=ROOT,check=True)
        branch=verify()['sdf_fix']['publish_branch']
        assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()==branch
        subprocess.run(['git','push','origin',f'HEAD:refs/heads/{branch}'],cwd=ROOT,check=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base-root',type=Path,default=RUN_ROOT)
    ap.add_argument('--run-root',type=Path,default=RERUN_ROOT);ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--report',action='store_true');ap.add_argument('--publish',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args()
    if a.status:print(json.dumps(status(a.run_root)));return
    verify();assert a.run_root.resolve()!=a.base_root.resolve()
    if a.dry_run:
        print(json.dumps(dict(planned=4,simulations_started=0,reused_original=16,base_root=str(a.base_root.resolve()),
                             jobs=plan(a.run_root.resolve()),original_finished_required_before_execution=True)));return
    if a.report:generate(a.base_root,a.run_root,a.publish);return
    baseline(a.base_root)
    execute(a.run_root.resolve(),plan(a.run_root.resolve()),report_argv=['/usr/bin/python3','-m','nomad_j0.h2_rerun',
        '--report','--publish','--base-root',str(a.base_root.resolve()),'--run-root',str(a.run_root.resolve())])

if __name__=='__main__':main()
