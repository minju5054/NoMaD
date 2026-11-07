"""Explicitly authorized Phase32 retrofit. No backups, simulation or retries."""
import argparse,json,os,time
from pathlib import Path
from collections import defaultdict,Counter
from nomad_storage_sdf import bulk as b,parallel as p
from nomad_storage_sdf.bulk_guard import Guard
from nomad_storage_sdf.versions import Registry

OUT=b.ROOT/'research/results/phase33p/storage'
TARGET=b.ISAAC/'phase32_01'

def setup():
    b.OUT=OUT;b.ROOT_OUT=OUT/'roots';OUT.mkdir(parents=True,exist_ok=True);b.ROOT_OUT.mkdir(exist_ok=True)

def plan():
    setup();guard=Guard(b.ISAAC,protected_roots=());guard.assert_clear(TARGET)
    state=b.read(TARGET/'state.json');assert state['status']=='COMPLETE' and not state.get('pid')
    if (OUT/'plan.json').exists():return b.read(OUT/'plan.json')
    files=b.targets(TARGET);registry=Registry();groups=defaultdict(list)
    for file in files:groups[str(file.parent.parent)].append(str(file))
    runs=[dict(path=run,before_bytes=b.folder_bytes(run),version=registry.resolve(run),files=ff) for run,ff in groups.items()]
    runs.sort(key=lambda r:(r['before_bytes'],r['path']))
    entry=dict(name=TARGET.name,path=str(TARGET),status='READY',target_files=len(files),before_bytes=b.folder_bytes(TARGET),runs=runs)
    spec=dict(roots=[entry],workers=8,protected_roots=[],backup_policy='DISABLED_BY_USER',backup_directory=str(b.ISAAC),
              benchmark_id='phase33_storage',frozen_runtime_sources=b.protected_sources(),versions=registry.records,
              authorization='Phase33-P explicit user instruction permits phase32_01 only after inactive/lock check')
    b.save(OUT/'plan.json',spec);print(json.dumps(dict(files=len(files),runs=len(runs),unknown_versions=sum(not r['version']['supported'] for r in runs),bytes=sum(f.stat().st_size for f in files))))
    return spec

def run():
    spec=plan()
    if (OUT/'state.json').exists():
        old=b.read(OUT/'state.json')
        if old['status']=='COMPLETE':print('Already complete');return
        if old['status']=='STOPPED_ERROR':raise RuntimeError('Previous conversion error; no automatic retry')
    import fcntl
    lock=(OUT/'conversion.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    rows=p.merged_rows(b.ROOT_OUT/TARGET.name);remaining=spec['roots'][0]['target_files']-len(rows)
    b.heartbeat()
    if os.getpriority(os.PRIO_PROCESS,0)<10:os.nice(10-os.getpriority(os.PRIO_PROCESS,0))
    runner=p.Runner(spec,dict(remaining_candidates=remaining),len(rows),8);runner.run()
    if runner.state['status']=='COMPLETE':
        summary=b.read(b.ROOT_OUT/TARGET.name/'summary.json');rows=b.read_jsonl(b.ROOT_OUT/TARGET.name/'manifest.jsonl')
        assert len({r['path'] for r in rows})==spec['roots'][0]['target_files']
        assert all(Path(r['path']).stat().st_size==r['after_bytes'] for r in rows)
        assert all(r['restored_arrays_bit_equal'] for r in rows if r['status']=='CONVERTED')
        assert not list(TARGET.rglob('*.sdf-strip.tmp'))
        summary['verification']='all-array byte check before replace; post-replace SHA; final manifest coverage/size; no temporary files'
        summary['backups_created']=0;b.save(OUT/'summary.json',summary)
        print(json.dumps({k:summary[k] for k in ('files','converted','skipped','skip_reasons','saved_bytes')}))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args();setup()
    if a.status:
        b.heartbeat();s=b.read(OUT/'state.json') if (OUT/'state.json').exists() else {};print(json.dumps({k:s.get(k) for k in ('status','stage','files_complete','root_target_files','error')}))
    elif a.run:run()
    else:plan()
if __name__=='__main__':main()
