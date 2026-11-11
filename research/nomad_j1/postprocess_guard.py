"""One process scan, never waits/polls and never sends a signal."""
import fcntl
import os
from contextlib import contextmanager
from pathlib import Path

ORIGINAL=Path('/home/gpuadmin/Workspace/NoMaD/visualnav-transformer')
ARTIFACTS=ORIGINAL.parent/'artifacts/isaac6'

def is_live_command(argv):
    modules={'nomad_j1.campaign','nomad_j1.launch','nomad_j1.report'}
    if any(a in modules for a in argv):return True
    if any(a.endswith('/nomad_j1/simulator.py') for a in argv):return True
    if any(a in ('nomad_isaac.worker','nomad_phase8.worker') for a in argv):
        return any('/artifacts/isaac6/j1_01/' in a for a in argv)
    return False

def assert_stopped(proc_root=Path('/proc')):
    live=[]
    for directory in proc_root.iterdir():
        if not directory.name.isdigit() or int(directory.name)==os.getpid():continue
        try:argv=(directory/'cmdline').read_bytes().decode(errors='replace').strip('\0').split('\0')
        except (FileNotFoundError,PermissionError,ProcessLookupError):continue
        if is_live_command(argv):live.append(dict(pid=int(directory.name),argv=argv))
    if live:raise RuntimeError(f'J1 still running; nothing changed and no waiting: {live}')
    return dict(live_j1_processes=0,scan='one-shot /proc, no polling, no signal')

@contextmanager
def locked(root):
    root=Path(root);assert root.exists()
    with (root/'campaign.lock').open('a') as local,(ARTIFACTS/'.phase0d_s0_batch.lock').open('a') as global_lock:
        fcntl.flock(local,fcntl.LOCK_EX|fcntl.LOCK_NB)
        fcntl.flock(global_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
