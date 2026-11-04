"""Operational-only disk checks and durable metadata; no planner dependencies."""
import errno,json,os,shutil,tempfile,time
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file

HERE=Path(__file__).parent
RESERVE_BYTES=1024*1024
HEADROOM_BYTES=20_000_000_000
PATCHABLE={'campaign.py','online_launch.py','online_execution.py','online_config.py','online_simulator.py','online_report.py'}

def read(path,default=None):
    path=Path(path);return json.loads(path.read_text()) if path.exists() else default

def atomic_json(path,value,backup=False):
    """Never open the committed JSON for writing; failed writes leave it intact."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    payload=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode();fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent);tmp=Path(name)
    try:
        with os.fdopen(fd,'wb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
        if backup and path.exists():
            read(path)  # Never promote malformed current data to the backup.
            link=tmp.with_suffix('.backup')
            try:os.link(path,link);os.replace(link,path.with_name(path.name+'.bak'))
            finally:link.unlink(missing_ok=True)
        os.replace(tmp,path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:tmp.unlink(missing_ok=True)

def ensure_reserve(root):
    file=Path(root)/'.metadata_reserve'
    if file.exists():return
    with file.open('xb') as stream:os.posix_fallocate(stream.fileno(),0,RESERVE_BYTES);os.fsync(stream.fileno())

def disk_full_state(root,state,error):
    """Release a preallocated1MiB so failure metadata can still be committed."""
    root=Path(root);(root/'.metadata_reserve').unlink(missing_ok=True)
    state.update(status='DISK_FULL_STOP',pid=None,current=None,error=repr(error),stopped_ns=time.time_ns())
    try:atomic_json(root/'state.json',state,backup=True)
    except OSError:
        # The previous complete state remains available if even metadata fails.
        print('[disk] cannot persist failure; previous atomic state preserved',flush=True)

def operational_hash(path,original):
    patch=read(HERE/'storage_protocol.json',{});entry=patch.get('changed_sources',{}).get(path)
    if entry is None:return original
    assert Path(path).parent==Path('research/nomad_phase24') and Path(path).name in PATCHABLE,path
    assert entry['original_sha256']==original,path
    return entry['sha256']

def verify_storage_sources():
    patch=read(HERE/'storage_protocol.json')
    if patch is None:return
    assert patch['status']=='FROZEN' and patch['scope']=='OPERATIONAL_STORAGE_ONLY'
    assert patch['method_protocol_sha256']==sha256_file(HERE/'online_protocol.json')
    for path,value in patch['new_sources'].items():assert sha256_file(ROOT/path)==value,path

def retain_full_frames(index,smoke=False):return smoke or int(index)==131

def iter_files(directory):
    for base,_,files in os.walk(directory):
        for name in files:
            f=Path(base)/name
            if f.is_file():yield f

def retention_frames(run):
    """1Hz visualization maps plus immutable snapshots at native FRESHs."""
    keep={-1};buckets=set()
    for line in (run/'depth/updates.jsonl').read_text().splitlines():
        r=json.loads(line);bucket=int(r['sim_s'])
        if bucket not in buckets:keep.add(r['frame_id']);buckets.add(bucket)
    for line in (run/'events.jsonl').read_text().splitlines():
        r=json.loads(line);snap=r.get('depth_snapshot') or {}
        if 'frame_id' in snap:keep.add(snap['frame_id'])
    return keep

def measure_run(run,full=True):
    run=Path(run);keep=retention_frames(run) if full else set();total=thin=raw=maps=0
    for f in iter_files(run):
        rel=f.relative_to(run);size=f.stat().st_size;total+=size;drop=False
        if rel.parts[0]=='observations' or (len(rel.parts)==1 and (f.name.startswith('observation_') or f.name in ('goal.png','observation_start.png')) and f.suffix=='.png'):
            raw+=size;drop=True
        if rel.parts[0]=='depth':
            if f.name.startswith('depth_') and f.suffix=='.npz':raw+=size;drop=True
            elif full and f.name.startswith('snapshot_') and f.name!='snapshot_initial.npz':
                frame=int(f.stem.split('_')[-1])
                if frame not in keep:maps+=size;drop=True
        if not drop:thin+=size
    # Before/after FRESH can observe adjacent publications. Allow20% of maps
    # that a retrospective single-frame projection would otherwise omit.
    return dict(output=str(run),bytes=total,thin_projected_bytes=thin+round(.20*maps) if full else total,raw_frame_bytes=raw,unneeded_map_bytes=maps)

def capacity(root,plan,free_bytes=None):
    root=Path(root);done=[];pending=[]
    for job in plan:
        metric=read(root/'metrics'/(job['key']+'.json'))
        if metric is not None:
            if metric.get('technical_validation')=='PASS':done.append(job)
        else:pending.append(job)
    full=[];compact=[];details=[]
    for job in done:
        run=Path(job['output']);policy=read(run/'storage_policy.json',{});is_full=policy.get('full_frames',True)
        m=measure_run(run,is_full);details.append(dict(key=job['key'],full_frames=is_full,**m))
        if is_full:full.append(m['bytes']);compact.append(m['thin_projected_bytes'])
        else:compact.append(m['bytes'])
    assert full or compact,'No completed-run size evidence'
    full_mean=sum(full)/len(full) if full else sum(compact)/len(compact)
    compact_mean=sum(compact)/len(compact)
    expected=sum(full_mean if retain_full_frames(j['index']) else compact_mean for j in pending)
    free=shutil.disk_usage(root).free if free_bytes is None else free_bytes
    return dict(remaining_runs=len(pending),completed_valid_runs=len(done),completed_full_mean_bytes=full_mean,compact_mean_bytes=compact_mean,
        old_remaining_bytes=full_mean*len(pending),expected_remaining_bytes=expected,headroom_bytes=HEADROOM_BYTES,required_free_bytes=expected+HEADROOM_BYTES,
        free_bytes=free,enough=free>=expected+HEADROOM_BYTES,details=details,checked_ns=time.time_ns())

def has_disk_error(run,log=None):
    files=[Path(run)/n for n in ('FAILED.json','launch_failure.json','simulator.log','worker.log','async_thread_failure.txt')]
    if log:files.append(Path(log))
    for f in files:
        if f.exists():
            with f.open('rb') as stream:
                stream.seek(max(0,f.stat().st_size-2_000_000));text=stream.read().decode(errors='replace')
            if 'No space left on device' in text or '[Errno 28]' in text:return True
    return False
