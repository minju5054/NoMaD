"""Resumable, fail-stop bulk retrofit. Full per-run tar backup precedes writes.

Workers only prepare/verify temporary files. The coordinator alone atomically
replaces originals, after an entire bounded batch has completed without error.
"""
import argparse,csv,fcntl,hashlib,io,json,os,platform,shutil,signal,stat,subprocess,tarfile,time,zipfile
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_EXCEPTION
import numpy as np
import scipy
from .pilot import ROOT,ISAAC,BACKUP_DIR,save,read
from .convert import sha
from .loader import ORIGINAL_LOAD,reconstruct,bit_equal,array_fingerprint,load_npz
from .versions import Registry,KNOWN_KEYS,MIN_KEYS
from .bulk_guard import Guard,ActiveRoot

OUT=ROOT/'research/results/storage_retrofit_bulk'
ROOT_OUT=OUT/'roots'
RESERVE=5_000_000_000
HEARTBEAT_SECONDS=180

class OperatorAbsent(Exception):pass

def heartbeat():
 (OUT/'agent_heartbeat').touch()

def require_heartbeat():
 if time.time()-(OUT/'agent_heartbeat').stat().st_mtime>HEARTBEAT_SECONDS:raise OperatorAbsent('No agent heartbeat; pause before next mutation batch')


def arrays_digest(data):
 desc={k:array_fingerprint(v) for k,v in data.items()}
 return hashlib.sha256(json.dumps(desc,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def known_digest(row):
 if row.get('arrays_sha256'):return row['arrays_sha256']
 return hashlib.sha256(json.dumps(row['original_arrays'],sort_keys=True,separators=(',',':')).encode()).hexdigest()

def write_jsonl(path,rows):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp')
 with tmp.open('w') as f:
  for r in rows:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n')
  f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)

def read_jsonl(path):
 if not Path(path).exists():return []
 return [json.loads(s) for s in Path(path).read_text().splitlines() if s]

def targets(root):
 found=[]
 for d,dirs,files in os.walk(root,followlinks=False):
  parent=Path(d)
  for name in files:
   if name.endswith('.npz') and ((parent.name=='depth' and name.startswith('snapshot_')) or (parent.name=='repair_jobs' and name.startswith('input_'))):
    p=parent/name
    if not p.is_symlink():found.append(p)
 return sorted(found)

def folder_bytes(root):return int(subprocess.check_output(['du','-sb',str(root)],text=True).split()[0])

def protected_sources():
 paths=[p for p in (ROOT/'research').glob('nomad_phase*') if p.is_dir()]
 files=[f for p in paths for f in p.glob('*.py')]+[f for p in paths for f in p.glob('*protocol*.json')]
 return {str(f.relative_to(ROOT)):sha(f) for f in files if not f.is_symlink()}

def make_plan():
 assert read(OUT/'resume_audit.json')['status']=='PASS'
 if (OUT/'plan.json').exists():raise FileExistsError('Existing bulk plan preserved; use --run/--status')
 guard=Guard(ISAAC);registry=Registry();roots=[];total_backups=0
 for root in sorted(ISAAC.iterdir()):
  if not root.is_dir() or root.is_symlink():continue
  reason=guard.reason(root,force=True)
  row=dict(name=root.name,path=str(root),before_bytes=folder_bytes(root),reason=reason,runs=[],target_files=0,target_before_bytes=0)
  if reason:row['status']='EXCLUDED_ACTIVE_OR_LOCKED'
  else:
   files=targets(root);row.update(target_files=len(files),target_before_bytes=sum(f.stat().st_size for f in files))
   groups=defaultdict(list)
   for f in files:groups[str(f.parent.parent)].append(f)
   for run,ff in groups.items():
    v=registry.resolve(run);size=folder_bytes(run)
    row['runs'].append(dict(path=run,before_bytes=size,version=v,files=[str(p) for p in ff]))
    if v['supported']:total_backups+=size
   row['runs'].sort(key=lambda r:(r['before_bytes'],r['path']));row['status']='READY' if files else 'NO_TARGET_FILES'
  roots.append(row);print('[plan]',root.name,row['status'],row['target_files'],flush=True)
 roots.sort(key=lambda r:(r['before_bytes'],r['name']))
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');backup=BACKUP_DIR/('bulk_'+stamp)
 plan=dict(created_utc=stamp,root_base=str(ISAAC),backup_directory=str(backup),roots=roots,
  input_patterns=['**/depth/snapshot_*.npz','**/repair_jobs/input_*.npz'],workers=4,reserve_external_bytes=RESERVE,
  full_run_backup_estimated_bytes=total_backups,external_free_bytes=shutil.disk_usage(BACKUP_DIR).free,
  unknown_versions='skip unchanged',different_formats='skip unchanged',exceptions='stop all immediately; no automatic retry',
  protected_sources=protected_sources(),protected_documents={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'docs').glob('*.md') if p.name!='STORAGE_RETROFIT.md'},numpy=np.__version__,scipy=scipy.__version__,python=platform.python_version(),
  known_versions=registry.records,tool_sources={str(p.relative_to(ROOT)):sha(p) for p in Path(__file__).parent.glob('*.py')},initial_df=subprocess.check_output(['df','-B1',str(ISAAC),str(BACKUP_DIR)],text=True))
 save(OUT/'plan.json',plan);save(OUT/'versions.json',registry.records)
 print(json.dumps(dict(roots=len(roots),with_targets=sum(r['target_files']>0 for r in roots),targets=sum(r['target_files'] for r in roots),known_runs=sum(v['version']['supported'] for r in roots for v in r['runs']),unknown_runs=sum(not v['version']['supported'] for r in roots for v in r['runs']),backup_estimated_GB=total_backups/1e9,external_free_GB=plan['external_free_bytes']/1e9)))


def run_inventory(run):
 entries=[]
 for p in sorted(Path(run).rglob('*')):
  s=p.lstat();kind='symlink' if p.is_symlink() else 'file' if p.is_file() else 'dir' if p.is_dir() else 'special'
  if kind=='special':raise RuntimeError('Unsupported special entry in original run: '+str(p))
  r=dict(relative=str(p.relative_to(run)),kind=kind,size=s.st_size,mode=stat.S_IMODE(s.st_mode),mtime_ns=s.st_mtime_ns)
  if kind=='file':r['sha256']=sha(p)
  if kind=='symlink':r['target']=os.readlink(p)
  entries.append(r)
 return entries


def verify_backup(path,run,inv):
 prefix=str(Path(run).relative_to(ISAAC));expected={prefix+'/'+r['relative']:r for r in inv};seen=set()
 with tarfile.open(path,'r:') as tf:
  for m in tf:
   if m.name==prefix:continue
   if m.name not in expected:raise RuntimeError('Unexpected tar member '+m.name)
   r=expected[m.name];seen.add(m.name)
   if r['kind']=='file':
    if not (m.isfile() or m.islnk()):raise RuntimeError('Backup member type mismatch')
    stream=tf.extractfile(m);h=hashlib.sha256()
    for b in iter(lambda:stream.read(4*1024*1024),b''):h.update(b)
    if h.hexdigest()!=r['sha256']:raise RuntimeError('Backup SHA mismatch '+m.name)
   elif r['kind']=='symlink':
    if not (m.issym() and m.linkname==r['target']):raise RuntimeError('Backup symlink mismatch')
   elif not m.isdir():raise RuntimeError('Backup directory mismatch')
 if seen!=set(expected):raise RuntimeError('Incomplete backup')


def ensure_backup(plan,root,run,guard,folder):
 run=Path(run);key=hashlib.sha256(str(run.relative_to(ISAAC)).encode()).hexdigest()[:20];receipt_file=folder/'backups'/(key+'.json')
 if receipt_file.exists():
  receipt=read(receipt_file)
  if not receipt['verified'] or not Path(receipt['tar']).exists():raise RuntimeError('Missing verified backup')
  side=read(receipt['inventory_file']);return receipt,side['files']
 guard.assert_clear(root);inv=run_inventory(run);target=Path(plan['backup_directory']);target.mkdir(parents=True,exist_ok=True)
 estimate=sum(((r['size']+511)//512)*512 if r['kind']=='file' else 0 for r in inv)+8192*(len(inv)+1)+10240
 if shutil.disk_usage(target).free<estimate+RESERVE:raise OSError(28,'Insufficient external backup space before run '+str(run))
 dest=target/(root.name+'__'+key+'.tar');tmp=dest.with_suffix('.tar.partial')
 if dest.exists() or tmp.exists():raise FileExistsError('Unreconciled backup exists: '+str(dest))
 def check_member(member):guard.assert_clear(root);return member
 with tarfile.open(tmp,'w',format=tarfile.PAX_FORMAT,dereference=False) as tf:tf.add(run,arcname=str(run.relative_to(ISAAC)),recursive=True,filter=check_member)
 with tmp.open('rb') as f:os.fsync(f.fileno())
 verify_backup(tmp,run,inv);guard.assert_clear(root);os.replace(tmp,dest)
 # Tar member content is verified before any original replacement.
 receipt=dict(run=str(run),tar=str(dest),tar_sha256=sha(dest),bytes=dest.stat().st_size,verified=True,regular_files=sum(r['kind']=='file' for r in inv),inventory_file=str(dest)+'.inventory.json')
 save(receipt['inventory_file'],dict(receipt=receipt,files=inv));save(receipt_file,receipt)
 return receipt,inv


def prepare_file(path,backup,version,original_entry,prior=None):
 path=Path(path);st=path.stat();raw=path.read_bytes();original_sha=hashlib.sha256(raw).hexdigest()
 if original_sha!=original_entry['sha256']:raise RuntimeError('Original changed since verified backup: '+str(path))
 base=dict(path=str(path),runtime_version_id=version['version_id'],original_sha256=original_sha,new_sha256=original_sha,before_bytes=st.st_size,after_bytes=st.st_size,
  backup_tar=backup['tar'],backup_member=str(path.relative_to(ISAAC)),values_bit_equal=None,restored_arrays_bit_equal=None,array_count=None,
  mtime_ns=st.st_mtime_ns,mode=stat.S_IMODE(st.st_mode))
 with ORIGINAL_LOAD(io.BytesIO(raw),allow_pickle=False) as z:
  keys=set(z.files)
  if 'values' not in keys:
   if prior is None:raise RuntimeError('Compact input has no manifest lineage: '+str(path))
   if original_sha!=prior['new_sha256']:raise RuntimeError('Prior compact SHA mismatch')
   data=load_npz(path,prior.get('original_arrays'))
   digest=arrays_digest(data)
   if digest!=known_digest(prior):raise RuntimeError('Prior compact arrays mismatch')
   base.update(status='ALREADY_COMPACT',original_sha256=prior['original_sha256'],arrays_sha256=digest,array_count=len(data),values_bit_equal=True,restored_arrays_bit_equal=True,
    backup_tar=prior['backup_tar'],backup_member=prior['backup_member'],prior_manifest='research/results/storage_retrofit/manifest.json',current_format_backup=backup['tar'])
   return base
  if not MIN_KEYS.issubset(keys) or not keys.issubset(KNOWN_KEYS):base.update(status='SKIPPED_DIFFERENT_FORMAT',keys=sorted(keys));return base
  # Object-backed legacy metadata is a different format, never unpickle it.
  with zipfile.ZipFile(io.BytesIO(raw)) as archive:
   for key in z.files:
    with archive.open(key+'.npy') as stream:
     version_number=np.lib.format.read_magic(stream)
     if version_number not in ((1,0),(2,0)):
      base.update(status='SKIPPED_DIFFERENT_FORMAT',reason='unsupported NPY header');return base
     shape,order,dtype=(np.lib.format.read_array_header_1_0(stream) if version_number==(1,0) else np.lib.format.read_array_header_2_0(stream))
     if dtype.hasobject:
      base.update(status='SKIPPED_DIFFERENT_FORMAT',reason='object array');return base
  data={k:z[k] for k in z.files}
 for k,a in data.items():
  if a.dtype.hasobject:raise RuntimeError('Object array in recognized SDF')
  if a.dtype.kind in 'fc' and not np.isfinite(a).all():raise RuntimeError('Nonfinite original array '+str(path)+':'+k)
 if data['occupied'].dtype!=np.bool_ or data['occupied'].ndim!=2 or data['values'].shape!=data['occupied'].shape:
  base.update(status='SKIPPED_DIFFERENT_FORMAT',reason='unsupported grid dtype/dimensions');return base
 computed=reconstruct(data);base.update(values_bit_equal=bit_equal(data['values'],computed),arrays_sha256=arrays_digest(data),array_count=len(data))
 if not base['values_bit_equal']:
  base.update(status='SKIPPED_SDF_MISMATCH',max_abs_difference=float(np.max(np.abs(computed-data['values']))));return base
 tmp=path.with_name('.'+path.name+'.sdf-strip.tmp')
 if tmp.exists():raise FileExistsError('Unreconciled temporary '+str(tmp))
 try:
  with tmp.open('xb') as f:
   np.savez_compressed(f,**{k:v for k,v in data.items() if k!='values'});f.flush();os.fsync(f.fileno())
  restored=load_npz(tmp)
  if set(restored)!=set(data) or not all(bit_equal(v,restored[k]) for k,v in data.items()):raise RuntimeError('Temporary restoration differs from original '+str(path))
  os.chmod(tmp,base['mode']);os.utime(tmp,ns=(st.st_atime_ns,st.st_mtime_ns))
  base.update(status='VERIFIED_TEMP',temp_path=str(tmp),new_sha256=sha(tmp),after_bytes=tmp.stat().st_size,restored_arrays_bit_equal=True)
  return base
 except BaseException:
  # Keep the original and leave any partial temp for the explicit resume audit.
  raise


def validate_compact(row):
 if sha(row['path'])!=row['new_sha256']:raise RuntimeError('Committed SHA differs '+row['path'])
 if row['status'] in ('CONVERTED','ALREADY_COMPACT','PREPARED'):
  data=load_npz(row['path'])
  if arrays_digest(data)!=row['arrays_sha256']:raise RuntimeError('Restored arrays differ '+row['path'])


def journal_writer(file):
 def write(row):file.write(json.dumps(row,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n');file.flush();os.fsync(file.fileno())
 return write


def commit_file(row,guard,root,record):
 if row['status']!='VERIFIED_TEMP':record(row);return row
 path=Path(row['path']);tmp=Path(row['temp_path']);guard.assert_clear(root)
 if sha(path)!=row['original_sha256']:raise RuntimeError('Original changed before atomic replace '+str(path))
 if sha(tmp)!=row['new_sha256']:raise RuntimeError('Verified temporary changed')
 record(dict(row,status='PREPARED'));os.replace(tmp,path);fd=os.open(path.parent,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
 if sha(path)!=row['new_sha256']:raise RuntimeError('Atomic replacement SHA failure')
 result=dict(row,status='CONVERTED');result.pop('temp_path',None);record(result);return result


def existing_rows(folder):
 final=folder/'manifest.jsonl';rows={r['path']:r for r in read_jsonl(final)}
 for r in read_jsonl(folder/'journal.jsonl'):
  if r.get('status') in ('CONVERTED','ALREADY_COMPACT','SKIPPED_SDF_MISMATCH','SKIPPED_DIFFERENT_FORMAT','SKIPPED_UNKNOWN_VERSION'):rows[r['path']]=r
  elif r.get('status')=='PREPARED':
   if sha(r['path'])==r['new_sha256']:
    validate_compact(r);rows[r['path']]=dict(r,status='CONVERTED')
   elif sha(r['path'])!=r['original_sha256']:raise RuntimeError('Interrupted replacement cannot be reconciled')
 return rows


def prepare_batch(pool,jobs):
 futures=[pool.submit(prepare_file,*args) for args in jobs]
 done,pending=wait(futures,return_when=FIRST_EXCEPTION)
 error=next((f.exception() for f in done if f.exception() is not None),None)
 if error:
  for f in pending:f.cancel()
  wait(futures);raise error
 return [f.result() for f in futures]


def process_root(plan,entry,guard,pool,state):
 root=Path(entry['path']);folder=ROOT_OUT/root.name;folder.mkdir(parents=True,exist_ok=True)
 if (folder/'summary.json').exists() and read(folder/'summary.json').get('status')=='COMPLETE':return read(folder/'summary.json')
 reason=guard.reason(root,force=True)
 if reason:return dict(root=root.name,status='EXCLUDED_ACTIVE_OR_LOCKED',reason=reason,converted=0)
 prior={r['path']:r for r in read(ROOT/'research/results/storage_retrofit/manifest.json')};rows=existing_rows(folder)
 with (folder/'journal.jsonl').open('a') as journal:
  record=journal_writer(journal)
  for run in entry['runs']:
   require_heartbeat();guard.assert_clear(root);remaining=[Path(p) for p in run['files'] if p not in rows]
   if not remaining:continue
   state.update(stage='backup',root=root.name,run=run['path'],files_complete=len(rows),root_target_files=entry['target_files'],saved_bytes=sum(r['before_bytes']-r['after_bytes'] for r in rows.values()),backup=None);save(OUT/'state.json',state)
   if not run['version']['supported']:
    for p in remaining:
     st=p.stat();r=dict(path=str(p),status='SKIPPED_UNKNOWN_VERSION',reason=run['version']['reason'],runtime_version_id=run['version']['version_id'],before_bytes=st.st_size,after_bytes=st.st_size,original_sha256=sha(p),new_sha256=sha(p),values_bit_equal=None,restored_arrays_bit_equal=None)
     record(r);rows[str(p)]=r
    continue
   backup,inv=ensure_backup(plan,root,run['path'],guard,folder);byfile={str(Path(run['path'])/r['relative']):r for r in inv if r['kind']=='file'}
   state.update(stage='convert',backup=backup['tar']);save(OUT/'state.json',state)
   for start in range(0,len(remaining),plan['workers']):
    require_heartbeat();guard.assert_clear(root);batch=remaining[start:start+plan['workers']]
    for p in batch:
     if str(p) not in byfile:raise RuntimeError('Missing original backup entry '+str(p))
    prepared=prepare_batch(pool,[(p,backup,run['version'],byfile[str(p)],prior.get(str(p))) for p in batch])
    # No replacements from this batch occur until every temp has verified.
    for row in prepared:rows[row['path']]=commit_file(row,guard,root,record)
    state.update(files_complete=len(rows),root_target_files=entry['target_files'],saved_bytes=sum(r['before_bytes']-r['after_bytes'] for r in rows.values()),last_file=str(batch[-1]),updated_utc=datetime.now(timezone.utc).isoformat())
    save(OUT/'state.json',state)
    if len(rows)%100<plan['workers']:print('[convert]',root.name,len(rows),'/',entry['target_files'],flush=True)
   write_jsonl(folder/'manifest.jsonl',list(rows.values()))
 write_jsonl(folder/'manifest.jsonl',list(rows.values()))
 counts=Counter(r['status'] for r in rows.values());tested=[r for r in rows.values() if r.get('values_bit_equal') is not None]
 result=dict(root=root.name,status='COMPLETE',files=len(rows),converted=counts['CONVERTED'],bit_checked=len(tested),bit_equal=sum(r['values_bit_equal'] for r in tested),bit_match_fraction=sum(r['values_bit_equal'] for r in tested)/len(tested) if tested else None,
  skipped=len(rows)-counts['CONVERTED'],skip_reasons={k:v for k,v in counts.items() if k!='CONVERTED'},before_bytes=entry['before_bytes'],after_bytes=folder_bytes(root),
  target_before_bytes=sum(r['before_bytes'] for r in rows.values()),target_after_bytes=sum(r['after_bytes'] for r in rows.values()),saved_bytes=sum(r['before_bytes']-r['after_bytes'] for r in rows.values()),manifest=str(folder/'manifest.jsonl'),manifest_sha256=sha(folder/'manifest.jsonl'),df=subprocess.check_output(['df','-B1',str(ISAAC),plan['backup_directory']],text=True))
 save(folder/'summary.json',result);print('[root done]',root.name,'converted',result['converted'],'saved GB',round(result['saved_bytes']/1e9,3),flush=True);return result


def execute():
 if (OUT/'state.json').exists() and read(OUT/'state.json').get('status')=='STOPPED_ERROR':raise RuntimeError('Prior exception requires user review; automatic retry prohibited')
 audit=read(OUT/'resume_audit.json');assert audit['status']=='PASS' and not audit['original_damage_found']
 plan=read(OUT/'plan.json');heartbeat();assert Path('/media/gpuadmin/One Touch').is_mount()
 if plan.get('backup_policy')=='DISABLED_BY_USER':raise RuntimeError('Backups disabled: use nomad_storage_sdf.parallel; legacy backup runner prohibited')
 for file,h in {**plan['protected_sources'],**plan.get('tool_sources',{})}.items():
  if sha(ROOT/file)!=h:raise RuntimeError('Frozen source changed '+file)
 guard=Guard(ISAAC);ROOT_OUT.mkdir(parents=True,exist_ok=True);lock=(OUT/'bulk.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 def stop(*_):raise KeyboardInterrupt('User/system requested stop')
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 affinity=sorted(os.sched_getaffinity(0));cpus=[c for c in affinity if c!=7][:plan['workers']]
 if cpus:os.sched_setaffinity(0,set(cpus))
 state=dict(status='RUNNING',pid=os.getpid(),start_utc=datetime.now(timezone.utc).isoformat(),worker_cores=cpus,stage='starting',completed_roots=[]);save(OUT/'state.json',state)
 pool=ThreadPoolExecutor(max_workers=plan['workers'],thread_name_prefix='sdf-verify')
 try:
  for entry in plan['roots']:
   if entry['status']=='NO_TARGET_FILES':continue
   if entry['status']=='EXCLUDED_ACTIVE_OR_LOCKED':continue
   summary=process_root(plan,entry,guard,pool,state);state['completed_roots'].append(summary);save(OUT/'state.json',state)
  state.update(status='COMPLETE',stage='finished',end_utc=datetime.now(timezone.utc).isoformat(),pid=None)
 except OperatorAbsent as exc:
  state.update(status='PAUSED_NO_HEARTBEAT',stage='paused',reason=str(exc),pid=None)
 except BaseException as exc:
  state.update(status='STOPPED_ERROR',stage='halted',error=repr(exc),end_utc=datetime.now(timezone.utc).isoformat(),pid=None)
  if state.get('root'):
   folder=ROOT_OUT/state['root']
   try:write_jsonl(folder/'partial_manifest.jsonl',list(existing_rows(folder).values()))
   except Exception as audit_error:state['partial_manifest_error']=repr(audit_error)
  raise
 finally:
  pool.shutdown(wait=True,cancel_futures=True);save(OUT/'state.json',state);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',action='store_true');ap.add_argument('--run',action='store_true');ap.add_argument('--status',action='store_true');ap.add_argument('--heartbeat',action='store_true');a=ap.parse_args()
 if a.heartbeat:heartbeat()
 if a.status:
  s=read(OUT/'state.json') if (OUT/'state.json').exists() else {'status':'NOT_STARTED'};print(json.dumps({k:s.get(k) for k in ('status','stage','root','run','files_complete','root_target_files','saved_bytes','last_file','error')}));return
 if a.plan:make_plan()
 elif a.run:execute()
 else:ap.error('Choose --plan, --run or --status')
if __name__=='__main__':main()
