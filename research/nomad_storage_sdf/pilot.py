"""One-run lossless SDF storage pilot. Other runs are read-only estimates."""
import argparse,csv,hashlib,io,json,os,platform,stat,tarfile,time,zipfile,zlib
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import numpy as np
import scipy
from nomad_isaac.common import ROOT
from .convert import inspect_file,compact_one,sha
from .loader import ORIGINAL_LOAD,bit_equal,array_fingerprint,load_npz,restoring_numpy_load,resolve_original_hash

ISAAC=ROOT.parent/'artifacts/isaac6'
PILOT=ISAAC/'phase29_01/dev/H1_201_G18/attempt1'
OUT=ROOT/'research/results/storage_retrofit'
BACKUP_DIR=Path('/media/gpuadmin/One Touch/nomad_archive/backup_before_sdf_strip')
PREFIXES=('phase26_smoke','phase27r','phase28','phase29','phase30r','phase31p')
PATTERNS=('depth/snapshot_*.npz','repair_jobs/input_*.npz')

def save(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp')
 with tmp.open('w') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
def read(path):return json.loads(Path(path).read_text())
def target_files():return sorted(p for pat in PATTERNS for p in PILOT.glob(pat))
def categories(root):
 result={}
 for key,pat in [('depth_raw','depth/depth_*.npz'),('snapshots','depth/snapshot_*.npz'),('repair_inputs','repair_jobs/input_*.npz')]:
  fs=list(root.glob(pat));result[key]=dict(count=len(fs),bytes=sum(f.stat().st_size for f in fs),allocated_bytes=sum(f.stat().st_blocks*512 for f in fs))
 return result

def inventory(root):
 out=[]
 for p in sorted(root.rglob('*')):
  s=p.lstat();kind='symlink' if p.is_symlink() else 'file' if p.is_file() else 'dir' if p.is_dir() else 'SPECIAL'
  if kind=='SPECIAL':raise ValueError('Unexpected special file: '+str(p))
  r=dict(relative=str(p.relative_to(root)),kind=kind,size=s.st_size,mode=stat.S_IMODE(s.st_mode),mtime_ns=s.st_mtime_ns)
  if kind=='file':r['sha256']=sha(p)
  if kind=='symlink':r['target']=os.readlink(p)
  out.append(r)
 return out

def phase31e_check():
 from . import phase31e_reference as old
 from nomad_phase15.evaluate import suffix
 old.INPUTS.clear();old.CACHE.clear();old.LOG.clear()
 case=next(v for v in read(ROOT/'research/results/phase31e/box_collision_details.json').values() if v['row']['uid']=='phase29_dev_H1_201_G18')
 row=case['row'];app=case['application'];s=old.read(PILOT/'summary.json');cfg=old.read(PILOT/'scenario.json');tr=old.trace(PILOT);tc=row['contact_s'];ta=row['install_s'];box=next(b for b in old.boxes_at(s,cfg,tc) if b['id']==row['obstacle']);tail,_=suffix(np.asarray(app['path_world']),app['pose'])
 with restoring_numpy_load():
  field=old.cached_field(row['planning_snapshot_file']);hist=old.box_history(PILOT,tr,box,tc,ta,row['spawn_s']);gap=float(field.exact_clearance(tail))
  oracle,_=old.oracle_path(tail,cfg,old.boxes_at(s,cfg,ta))
 expected={k:row[k] for k in hist};assert hist==expected,(hist,expected)
 assert np.asarray(gap).tobytes()==np.asarray(row['planning_base_exact_clearance_m']).tobytes()
 assert np.asarray(oracle).tobytes()==np.asarray(row['plan_oracle_suffix_m']).tobytes()
 return dict(passed=True,box_history_exactly_equal=True,plan_depth_clearance_bit_equal=True,oracle_plan_clearance_bit_equal=True,
             planning_base_exact_clearance_m=gap,oracle_plan_suffix_m=oracle,box_history=hist,
             original_analysis_sha256=read(ROOT/'research/results/phase31e/verification.json')['script_sha256'],reference_functions_sha256=sha(Path(__file__).with_name('phase31e_reference.py')))

def dry_run():
 assert (PILOT/'launch_complete.json').exists() and (PILOT/'summary.json').exists()
 if (OUT/'manifest.json').exists():raise RuntimeError('Pilot already converted; use verify/report, never overwrite original dry-run')
 OUT.mkdir(parents=True,exist_ok=True);rows=[]
 for i,f in enumerate(target_files()):
  r,_=inspect_file(f);rows.append(r)
  if (i+1)%20==0:print('[dry-run]',i+1,flush=True)
 inv=inventory(PILOT);save(OUT/'run_inventory_before.json',inv);save(OUT/'dry_run.json',dict(run=str(PILOT),files=rows,categories_before=categories(PILOT),
  target_bytes_before=sum(r['original_bytes'] for r in rows),proposed_target_bytes=sum(r['proposed_bytes'] for r in rows),
  bit_equal=sum(r['values_bit_equal'] for r in rows),file_count=len(rows),numpy=np.__version__,scipy=scipy.__version__,python=platform.python_version(),zlib=zlib.ZLIB_VERSION,
  runtime_formula='nomad_phase15.occupancy.distance_transform_edt(~occupied,sampling=h)-radius; empty allocation via DepthSDF',
  runtime_sources={f:sha(ROOT/f) for f in ['research/nomad_phase15/occupancy.py','research/nomad_phase15/depth_sdf.py','research/nomad_phase15b/depth.py','research/nomad_phase20d/recent.py','research/nomad_phase20f/history.py']}))
 save(OUT/'phase31e_before.json',phase31e_check());print('[dry-run] complete',len(rows),'files',sum(r['values_bit_equal'] for r in rows),'equal',flush=True)

def verify_tar(file,inv):
 prefix=str(PILOT.relative_to(ISAAC));expected={prefix+'/'+r['relative']:r for r in inv};seen=set()
 with tarfile.open(file,'r:') as tf:
  for m in tf:
   if m.name==prefix:continue
   if m.name not in expected:raise ValueError('Unexpected backup member '+m.name)
   row=expected[m.name];seen.add(m.name)
   if row['kind']=='file':
    assert m.isfile() and m.size==row['size'];h=hashlib.sha256();stream=tf.extractfile(m)
    for b in iter(lambda:stream.read(4*1024*1024),b''):h.update(b)
    assert h.hexdigest()==row['sha256'],m.name
   elif row['kind']=='symlink':assert m.issym() and m.linkname==row['target']
   else:assert m.isdir()
 assert seen==set(expected)
 return dict(verified_members=len(seen),verified_regular_files=sum(r['kind']=='file' for r in inv),all_file_sha256_match=True)

def backup():
 plan=read(OUT/'dry_run.json');inv=read(OUT/'run_inventory_before.json')
 assert inventory(PILOT)==inv,'Run changed after dry-run'
 if (OUT/'backup.json').exists():raise FileExistsError('Backup receipt already exists; do not create duplicates')
 assert Path('/media/gpuadmin/One Touch').is_mount(),'External drive must be mounted'
 BACKUP_DIR.mkdir(parents=True,exist_ok=True);stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');name='phase29_01_dev_H1_201_G18_attempt1_'+stamp+'.tar';dest=BACKUP_DIR/name;tmp=dest.with_suffix('.tar.partial')
 assert not dest.exists() and not tmp.exists()
 import shutil
 size=sum(r['size'] for r in inv if r['kind']=='file');assert shutil.disk_usage(BACKUP_DIR).free>size+1024**3
 print('[backup] writing',dest,flush=True)
 with tarfile.open(tmp,'w',format=tarfile.PAX_FORMAT,dereference=False) as tf:tf.add(PILOT,arcname=str(PILOT.relative_to(ISAAC)),recursive=True)
 with tmp.open('rb') as f:os.fsync(f.fileno())
 checked=verify_tar(tmp,inv);os.replace(tmp,dest)
 receipt=dict(archive=str(dest),archive_sha256=sha(dest),archive_bytes=dest.stat().st_size,source=str(PILOT),source_inventory_sha256=sha(OUT/'run_inventory_before.json'),verified=True,**checked)
 save(BACKUP_DIR/(name+'.inventory.json'),dict(receipt=receipt,files=inv));save(OUT/'backup.json',receipt)
 assert inventory(PILOT)==inv;print('[backup] verified',checked['verified_regular_files'],'files',flush=True)

def convert():
 plan=read(OUT/'dry_run.json');bk=read(OUT/'backup.json');assert bk['verified'] and sha(bk['archive'])==bk['archive_sha256']
 inv=read(OUT/'run_inventory_before.json');assert sha(OUT/'run_inventory_before.json')==bk['source_inventory_sha256']
 journal_path=OUT/'conversion_journal.jsonl';previous={}
 if journal_path.exists():
  for line in journal_path.read_text().splitlines():
   r=json.loads(line);previous[r['path']]=r
 rows=[]
 with journal_path.open('a') as journal:
  def record(r):journal.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n');journal.flush();os.fsync(journal.fileno())
  for i,expected in enumerate(plan['files']):
   f=Path(expected['path']);assert f in target_files()
   old=previous.get(str(f));member=str(f.relative_to(ISAAC))
   if old and old['status'] in ('CONVERTED','PREPARED') and sha(f)==old['new_sha256']:
    load_npz(f,old['original_arrays']);row=dict(old,status='CONVERTED',new_allocated_bytes=f.stat().st_blocks*512);record(row)
   else:row=compact_one(f,expected,bk['archive'],member,record)
   rows.append(row)
   if (i+1)%20==0:print('[convert]',i+1,flush=True)
 save(OUT/'manifest.json',rows);verify()


def verify():
 rows=read(OUT/'manifest.json');inv=read(OUT/'run_inventory_before.json');bk=read(OUT/'backup.json')
 assert sha(bk['archive'])==bk['archive_sha256']
 direct_arrays=0
 with tarfile.open(bk['archive'],'r:') as tf:
  for r in rows:
   blob=tf.extractfile(r['backup_member']).read();assert hashlib.sha256(blob).hexdigest()==r['original_sha256']
   with ORIGINAL_LOAD(io.BytesIO(blob),allow_pickle=False) as z:original={k:z[k] for k in z.files}
   restored=load_npz(r['path'],r['original_arrays']);assert set(original)==set(restored)
   for k in original:assert bit_equal(original[k],restored[k]),(r['path'],k)
   direct_arrays+=len(original);r['literal_backup_array_bits_equal']=True
 save(OUT/'manifest.json',rows)
 index={str(Path(r['path']).relative_to(PILOT)):r for r in rows};checked=0
 for r in rows:
  assert sha(r['path'])==r['new_sha256'];load_npz(r['path'],r['original_arrays']);checked+=1
 for item in inv:
  p=PILOT/item['relative']
  if item['kind']=='file' and item['relative'] not in index:assert sha(p)==item['sha256'],str(p)
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
 # New/removed entries would also invalidate the untouched-run guarantee.
 assert {x['relative'] for x in inventory(PILOT)}=={x['relative'] for x in inv}
 after=phase31e_check();before=read(OUT/'phase31e_before.json');assert after==before;save(OUT/'phase31e_after.json',after)
 refs=[]
 for name in ('phase31d','phase31e','phase32o'):
  mf=ROOT/'research/results'/name/'input_manifest.json'
  for r in read(mf):
   if str(Path(r['file']).resolve()) not in {x['path'] for x in rows}:continue
   result=resolve_original_hash(r['file'],r['sha256'],OUT/'manifest.json');refs.append(dict(report_manifest=str(mf.relative_to(ROOT)),file=r['file'],expected_original_sha256=r['sha256'],**result))
 save(OUT/'report_hash_lineage.json',refs)
 save(OUT/'verification.json',dict(restored_files_bit_equal=checked,literal_backup_arrays_compared=direct_arrays,other_arrays_bit_equal=True,non_target_run_files_sha256_unchanged=True,phase31e_equal=True,report_hash_references=len(refs),report_hash_lineage_verified=True,categories_after=categories(PILOT),only_converted_run=str(PILOT),simulation_started=0))
 print('[verify] full arrays',checked,'old-report hash links',len(refs),'Phase31-E unchanged',flush=True)


def estimate():
 """Read-only whole-SSD inventory, stratified fixed sample for compression."""
 roots=sorted(p for p in ISAAC.iterdir() if p.is_dir() and p.name.startswith(PREFIXES));records=[];raw=[];groups=defaultdict(list)
 for root in roots:
  for directory,dirs,files in os.walk(root,followlinks=False):
   for name in files:
    p=Path(directory)/name
    if p.is_symlink() or p.suffix!='.npz':continue
    if p.parent.name=='depth' and name.startswith('depth_'):raw.append(dict(root=root.name,path=str(p),bytes=p.stat().st_size));continue
    kind='snapshot' if p.parent.name=='depth' and name.startswith('snapshot_') else 'repair_input' if p.parent.name=='repair_jobs' and name.startswith('input_') else None
    if kind is None:continue
    with zipfile.ZipFile(p) as z:
     methods={i.compress_type for i in z.infolist()};has_values='values.npy' in z.namelist()
    fmt='stored' if methods=={0} else 'deflated' if methods=={8} else 'mixed'
    r=dict(root=root.name,path=str(p),kind=kind,archive_format=fmt,has_values=has_values,bytes=p.stat().st_size);records.append(r);groups[(root.name,kind,fmt)].append(r)
  print('[inventory]',root.name,flush=True)
 # Existing pilot dry-run supplies exact sizes for its93 files. No repeat write.
 pilot={r['path']:r for r in read(OUT/'dry_run.json')['files']};rng=np.random.default_rng(20261107);estimates=[];samples=[]
 for key,items in sorted(groups.items()):
  items=sorted(items,key=lambda r:r['path']);chosen=rng.choice(len(items),min(3,len(items)),replace=False);ratios=[];matches=[];sample_before=[];sample_after=[]
  for j in sorted(chosen.tolist()):
   r=items[j]
   if not r['has_values']:ratio=1.;match=True;size=r['bytes'];status='ALREADY_COMPACT'
   else:
    detail=pilot.get(r['path'])
    if detail is None:detail,_=inspect_file(r['path'])
    size=detail['proposed_bytes'];ratio=size/detail['original_bytes'];match=detail['values_bit_equal'];status='BIT_EQUAL' if match else 'UNCHANGED_MISMATCH'
   ratios.append(ratio);matches.append(match);sample_before.append(r['bytes']);sample_after.append(size);samples.append(dict(r,new_bytes_sample=size,new_old_ratio=ratio,bit_equal=match,status=status))
  # Compression ratios are extrapolated, not an eligibility guarantee. Show
  # a min/max sensitivity range; this is not a confidence interval.
  total=sum(r['bytes'] for r in items);ratio=float(sum(sample_after)/sum(sample_before));estimates.append(dict(root=key[0],kind=key[1],archive_format=key[2],files=len(items),before_bytes=total,sample_count=len(ratios),sample_equal_count=sum(matches),
   estimated_after_bytes=round(total*ratio),estimated_saved_bytes=round(total*(1-ratio)),saved_sensitivity_low_bytes=round(total*(1-max(ratios))),saved_sensitivity_high_bytes=round(total*(1-min(ratios)))))
  print('[estimate]',key,len(items),'sample',len(ratios),flush=True)
 save(OUT/'ssd_inventory.json',records);save(OUT/'ssd_raw_depth_inventory.json',raw);save(OUT/'ssd_compression_samples.json',samples);save(OUT/'ssd_estimates.json',estimates)


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=('dry-run','estimate','backup','convert','verify'),required=True);a=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
 {'dry-run':dry_run,'estimate':estimate,'backup':backup,'convert':convert,'verify':verify}[a.stage]()
if __name__=='__main__':main()
