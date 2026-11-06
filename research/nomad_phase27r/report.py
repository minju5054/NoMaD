"""Preparation now; later reuse the unmodified Phase26 evaluator in a new folder."""
import argparse,json,subprocess
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from .config import OUT,verify,check_run_root,HERE

DOC=ROOT/'docs/PHASE27R_RESULTS.md'

def generate(root,out=OUT,doc=DOC):
    from nomad_phase26.report import generate as phase26_report
    result=phase26_report(root,out,doc)
    text=doc.read_text().replace('# Phase26 preregistered pilot','# Phase27-R — Phase26 suffix-alignment bug-fix rerun',1)
    text=text.replace('Protocol SHA256','Unchanged Phase26 protocol SHA256',1)
    text+='\nPhase27-R registration SHA256 `'+sha256_file(HERE/'protocol.json')+'`. The sole controller change is SPAlignment.replace_path: project B, then use the first stored suffix waypoint at arclength >=s_B+0.05m; no alignment if unavailable. All Phase26 decisions, seeds, scenes, method ordering and technical-retry rules are reused. Original Phase26 results are preserved.\n'
    doc.write_text(text);return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--run-root',type=Path);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    if a.prepare:
        assert not a.run_root and not a.publish
        from .prepare import generate as prepare
        print(json.dumps(prepare(),ensure_ascii=False));return
    assert a.run_root;verify();print(json.dumps(generate(check_run_root(a.run_root))))
    if a.publish:
        paths=[str(DOC.relative_to(ROOT)),str(OUT.relative_to(ROOT))]
        subprocess.run(['git','add','-f','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase27-R registered alignment-fix rerun','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

if __name__=='__main__':main()
