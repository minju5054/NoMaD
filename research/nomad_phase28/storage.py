"""Optional post-process ephemeral cache cleanup; never removes experiment logs."""
import json,shutil
from pathlib import Path

def cleanup(run,processes_finished,enabled=True):
    run=Path(run).resolve()
    if not processes_finished:raise RuntimeError('Cleanup requires simulator and worker termination')
    result=dict(enabled=bool(enabled),processes_finished=True,removed=[],skipped=[])
    if enabled:
        # Exact allowlist: original RGB/depth retention policy is untouched.
        for relative in ('portable/cache','pycache'):
            p=run/relative
            if not p.exists():continue
            if p.is_symlink() or run not in p.resolve().parents:
                result['skipped'].append(dict(path=relative,reason='OUTSIDE_RUN_OR_SYMLINK'));continue
            shutil.rmtree(p);result['removed'].append(relative)
    (run/'phase28_cleanup.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
