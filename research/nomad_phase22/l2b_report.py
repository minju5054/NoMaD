"""Merge unchanged L2 metrics with new L2B; call frozen decision functions."""
import argparse,json,subprocess
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase19r.evaluate import clean
from . import drive_report as frozen
from .l2b_rerun import registration,verify_sources

def merged_records(root):
    r=registration();records=[]
    for entry in r['reuse_L2']:
        file=Path(entry['metrics_file']);assert sha256_file(file)==entry['metrics_sha256']
        row=json.loads(file.read_text());row.update(reused_L2=True,reused_metrics_file=str(file),reused_metrics_sha256=entry['metrics_sha256'])
        records.append(row)
    plan=json.loads((root/'plan.json').read_text());assert len(plan['jobs'])==12
    for job in plan['jobs']:
        assert job['scene']=='L2B';row=json.loads((root/'metrics'/f"{job['key']}.json").read_text());row['reused_L2']=False;records.append(row)
    assert len(records)==24 and len({(r['scene'],r['index'],r['method']) for r in records})==24
    for row in records:
        file=Path(row['output'])/'provenance.json'
        if file.exists():row['execution_git_sha']=json.loads(file.read_text())['git_sha']
    return records

def history_note():
    r=registration();patch=r['runtime_patch']
    text='## L2B execution defect and authorized rerun\n\n'
    text+='Original L2B: **TECHNICAL_INVALID** (12 logical runs, 24 attempts). All attempts failed during rotated-box monitor construction before the spawn was published; no L2B navigation outcome was observed. The original report and raw data are retained unchanged. This was an execution-defect repair before observing L2B outcomes, authorized before rerunning the same preregistered seeds.\n\n'
    text+='The parent ObstacleMonitor created `obstacle_geometry.json` with exclusive creation; OrientedMonitor tried to exclusively create the same file a second time. FileExistsError stopped the kinematic thread; the worker EOF was secondary. The only production-path change stores supplemental OBB metadata under a distinct filename. Placement, rigid-transformed swept collision, planners, weights, triggers, controller, seeds and decisions are unchanged.\n\n'
    text+='```diff\n'+patch['diff'].rstrip()+'\n```\n\n'
    text+=f"Patch `{patch['file']}`: `{patch['before_sha256']}` → `{patch['after_sha256']}`. Amendment protocol SHA256 `{sha256_file(Path(__file__).with_name('l2b_protocol.json'))}`.\n\n"
    text+='Original report: [PHASE22_REFINE_DRIVE.md](PHASE22_REFINE_DRIVE.md). Original L2 metrics are reused bit-for-bit from recorded hashes; only L2B is newly executed in a separate root. Same-seed one technical retry and full scene×seed group exclusion remain unchanged.\n\n'
    text+='Spawn-only launch checks use unused indices901/902/903 at the trigger plane: method/backend startup, production SuddenObstacleMonitor, rotated collision model and actual depth capture. No inference, navigation, planner solve or performance outcome is recorded by these diagnostic fixtures.\n\n'
    return text

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--publish',action='store_true');a=ap.parse_args();verify_sources()
    out=ROOT/'research/results/phase22_l2b_rerun';doc=ROOT/'docs/PHASE22_REFINE_DRIVE_L2B_RERUN.md'
    verdict=frozen.render(merged_records(a.run_root.resolve()),out,doc)
    original=json.loads((ROOT/'research/results/phase22/decisions.json').read_text())
    assert verdict['scenes'][0]==original['scenes'][0],'Reused L2 judgement must remain identical'
    text=doc.read_text().replace('../research/results/phase22/','../research/results/phase22_l2b_rerun/')
    first,rest=text.split('\n',1);doc.write_text(first+' — L2B runtime-fix rerun\n\n'+history_note()+rest)
    (out/'rerun_provenance.json').write_text(json.dumps(clean(registration()),indent=2)+'\n')
    if a.publish:
        assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
        subprocess.run(['git','add','--',str(doc.relative_to(ROOT)),str(out.relative_to(ROOT))],cwd=ROOT,check=True)
        subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in out.glob('*.png')]],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase22 unchanged L2 plus repaired L2B execution'],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
    print(json.dumps(verdict,ensure_ascii=False))
if __name__=='__main__':main()
