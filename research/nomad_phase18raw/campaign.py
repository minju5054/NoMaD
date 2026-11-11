"""Phase18 resumable stage engine, 24 RAW runs, same no-retry rule."""
import argparse,inspect,json,shutil,subprocess
from pathlib import Path
from nomad_phase18 import campaign as frozen
from nomad_phase0.s0_batch import exclusive_batch
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from nomad_phase26.storage import atomic_json
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,protocol,verify_sources

def write(path,value):atomic_json(path,value,backup=Path(path).name=='state.json')
def plan_jobs(root):
    jobs=[]
    for item in protocol()['main_order']:
        j=dict(item);j['key']=f"{j['scene']}_{j['index']:03d}_D750_{j['method']}";j['output']=str(root/'main'/j['key']);j['delay']=.75
        j['seed_offset']=10000*j['index'];j['run_id']=f"{j['scene']}_{j['index']}"
        sock=socket_path_for_run(j['output']);j.update(socket_path=str(sock),socket_bytes=validate_socket_path(sock));jobs.append(j)
    assert len(jobs)==24 and len({j['socket_path'] for j in jobs})==24
    return jobs

source=inspect.getsource(frozen.campaign)
changes=[("ROOT/'research/results/phase18_preflight/readiness.json'","OUT/'preparation/validation.json'"),
         ('Stored RTC replay and one excluded RTC smoke must pass before campaign','RAW plumbing dry-run must pass before campaign'),
         ("    assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).strip(),'Tracked edits must be committed'", "    verify_sources()  # exact frozen-source hashes, unrelated report edits allowed"),
         ('nomad_phase18.launch','nomad_phase18raw.launch'),('nomad_phase18.report','nomad_phase18raw.report'),
         ("state['main_planned']=144","state['main_planned']=24")]
for old,new in changes:assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new)
# A resource stop before a new job preserves the no-retry experiment plan.
old="            for j in jobs:\n                assert j['scene'] in passed"
new="            for j in jobs:\n                if shutil.disk_usage(ROOT).free<30_000_000_000:raise OSError('Disk reserve below30GB; no new run started')\n                assert j['scene'] in passed"
assert source.count(old)==1;source=source.replace(old,new)
ns=dict(frozen.campaign.__globals__,__package__=__package__,__file__=__file__,OUT=OUT,protocol=protocol,verify_sources=verify_sources,plan_jobs=plan_jobs,write=write,shutil=shutil)
exec(compile(source,__file__,'exec'),ns);campaign=ns['campaign']

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args();root=a.run_root.resolve()
    if a.status:print(json.dumps(frozen.status(root)));return
    verify_sources()
    if a.dry_run:
        jobs=plan_jobs(root);print(json.dumps(dict(planned=24,navigation_started=0,new_gate_runs=0,new_reference_runs=0,socket_max_bytes=max(j['socket_bytes'] for j in jobs),jobs=jobs)));return
    with exclusive_batch():campaign(root)
if __name__=='__main__':main()
