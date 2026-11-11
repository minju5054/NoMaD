"""User-run, after natural exit only. Apply the prepared branch and report.

This entry point imports no project code until AFTER merging into the original
repository, so all analysis imports resolve to the newly installed code there.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

ORIGINAL=Path('/home/gpuadmin/Workspace/NoMaD/visualnav-transformer')
BRANCH='fix/j1-rtc-validation'

def main():
    assert Path.cwd().resolve()==ORIGINAL,'Run from the original repository'
    file=Path(__file__).resolve().with_name('postprocess_guard.py')
    spec=importlib.util.spec_from_file_location('j1_postprocess_guard_standalone',file)
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    guard.assert_stopped()  # One scan, fail immediately if still running.
    root=ORIGINAL.parent/'artifacts/isaac6/j1_01'
    with guard.locked(root):
        current=subprocess.check_output(['git','branch','--show-current'],cwd=ORIGINAL,text=True).strip()
        assert current=='research/phase0-infrastructure',current
        subprocess.run(['git','fetch','origin',f'refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}'],cwd=ORIGINAL,check=True)
        dirty=set(subprocess.check_output(['git','diff','--name-only'],cwd=ORIGINAL,text=True).splitlines())
        dirty.update(subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ORIGINAL,text=True).splitlines())
        affected=set(subprocess.check_output(['git','diff','--name-only',f'HEAD...origin/{BRANCH}'],cwd=ORIGINAL,text=True).splitlines())
        assert not dirty&affected,f'User edits overlap prepared patch: {sorted(dirty&affected)}'
        try:
            subprocess.run(['git','merge','--no-edit',f'origin/{BRANCH}'],cwd=ORIGINAL,check=True)
        except subprocess.CalledProcessError:
            # Restore the pre-merge tree on a real merge conflict; do not resolve
            # or discard unrelated user edits automatically.
            pending=subprocess.run(['git','rev-parse','--verify','-q','MERGE_HEAD'],cwd=ORIGINAL,capture_output=True)
            if pending.returncode==0:subprocess.run(['git','merge','--abort'],cwd=ORIGINAL,check=True)
            raise
        sys.path[0]=str(ORIGINAL/'research')
        from nomad_j1.config import ROOT,verify
        assert ROOT==ORIGINAL;verify()
        from nomad_j1.reassess import process
        process(root,publish=True)

if __name__=='__main__':main()
