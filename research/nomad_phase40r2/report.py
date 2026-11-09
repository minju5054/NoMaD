"""Frozen Phase40-P calculations with the new label and tables-only document."""
import argparse,inspect,json,subprocess
from pathlib import Path
from nomad_phase40p import report as frozen
from nomad_phase31p.report import table
from .config import ROOT,HERE,OUT,RUN_ROOT,verify


def analyze(rows):
    return frozen.analyze([dict(r,method='OURS-N') if r['method']=='OURS-R2' else r for r in rows])


def generate(root=RUN_ROOT,output=OUT,document=None,baseline=None):
    source=inspect.getsource(frozen.generate).replace('OURS-N','OURS-R2').replace('PHASE40P_RESULTS','PHASE40R2_RESULTS')
    ns=dict(frozen.generate.__globals__,verify=verify,ROOT=ROOT,OUT=OUT,RUN_ROOT=RUN_ROOT,analyze=analyze)
    exec(compile(source,str(HERE/'report.py'),'exec'),ns)
    doc=ns['generate'](root,output,document,baseline)
    decision=json.loads((Path(output)/'decision.json').read_text())
    blocks=[block for block in doc.read_text().split('\n\n') if block.lstrip().startswith('|')]
    doc.write_text(table([decision])+'\n\n'+'\n\n'.join(blocks)+'\n')
    return doc


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    assert a.run_root.resolve()==RUN_ROOT.resolve();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))]
        subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase40-R2 pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)


if __name__=='__main__':main()
