"""Inspection and explicit cleanup only; no bulk conversion starts here."""
import argparse,json,os,zipfile
from pathlib import Path
import numpy as np
from .pilot import ROOT,ISAAC,OUT as PILOT_OUT,save,read
from .convert import sha
from .loader import ORIGINAL_LOAD,load_npz,array_fingerprint,reconstruct,bit_equal
from .bulk_guard import Guard

OUT=ROOT/'research/results/storage_retrofit_bulk'

def health(path):
 with ORIGINAL_LOAD(path,allow_pickle=False) as z:data={k:z[k] for k in z.files}
 if not data:raise RuntimeError('Empty source archive')
 for k,v in data.items():
  if v.dtype.hasobject:raise RuntimeError('Unsafe object array in source')
  if v.dtype.kind in 'fc' and not np.isfinite(v).all():raise RuntimeError('Nonfinite source array '+k)
 if {'occupied','values'}.issubset(data):
  if data['occupied'].dtype!=np.bool_ or data['values'].shape!=data['occupied'].shape:raise RuntimeError('Malformed source SDF arrays')
 return dict(sha256=sha(path),arrays={k:array_fingerprint(v) for k,v in data.items()},np_load_ok=True,
             sdf_bit_equal=bit_equal(data['values'],reconstruct(data)) if {'values','occupied','origin','h','radius'}.issubset(data) else None)

def temps(base):
 result=[]
 for directory,dirs,files in os.walk(base,followlinks=False):
  for name in files:
   if 'sdf-strip' in name or 'sdf_strip' in name or ('.npz' in name and name.endswith('.tmp')):result.append(Path(directory)/name)
 return sorted(result)

def source_of_temp(path):
 s=str(path)
 if s.endswith('.npz.archive.tmp'):return Path(s.removesuffix('.archive.tmp'))
 if s.endswith('.npz.sdf-strip.tmp'):return path.with_name(path.name[1:].removesuffix('.sdf-strip.tmp'))
 if s.endswith('.npz.tmp'):return Path(s.removesuffix('.tmp'))
 raise RuntimeError('Unresolved temporary source: '+s)

def audit(clean=False):
 OUT.mkdir(parents=True,exist_ok=True);guard=Guard(ISAAC);found=temps(ISAAC);temp_rows=[]
 # Validate every corresponding source before deleting any temporary.
 for t in found:
  root=ISAAC/t.relative_to(ISAAC).parts[0];blocked=guard.reason(root,force=True)
  if blocked:temp_rows.append(dict(temporary=str(t),status='SKIPPED_ACTIVE_OR_LOCKED',**blocked));continue
  source=source_of_temp(t)
  if not source.exists():raise RuntimeError('Original missing: '+str(source))
  h=health(source);temp_rows.append(dict(temporary=str(t),source=str(source),temporary_bytes=t.stat().st_size,status='SOURCE_INTACT',**h))
 manifests=[PILOT_OUT/'manifest.json'];reconciled=[]
 for mf in manifests:
  for row in read(mf):
   path=Path(row['path']);guard.assert_clear(ISAAC/path.relative_to(ISAAC).parts[0]);current=sha(path)
   if current==row['new_sha256']:
    load_npz(path,row['original_arrays']);reconciled.append(dict(path=str(path),status='VERIFIED_CONVERTED',current_sha256=current,original_sha256=row['original_sha256'],manifest=str(mf)))
   elif current==row['original_sha256']:
    health(path);reconciled.append(dict(path=str(path),status='ORIGINAL_NOT_REPLACED',current_sha256=current,manifest=str(mf)))
   else:raise RuntimeError('Original/replacement does not match manifest: '+str(path))
 # Pilot journal is complete; reconcile PREPARED/CONVERTED records without
 # rewriting the frozen pilot evidence. Report an authoritative audit view.
 journal=PILOT_OUT/'conversion_journal.jsonl';last={}
 for line in journal.read_text().splitlines():
  r=json.loads(line);last[r['path']]=r
 for r in reconciled:
  j=last.get(r['path']);assert j and j['new_sha256']==r['current_sha256']
  r['journal_final_status']=j['status'];r['needs_manifest_repair']=j['status']!='CONVERTED' and r['status']=='VERIFIED_CONVERTED'
 if clean:
  for r in temp_rows:
   if r['status']!='SOURCE_INTACT':continue
   t=Path(r['temporary']);source=Path(r['source']);guard.assert_clear(ISAAC/source.relative_to(ISAAC).parts[0]);assert sha(source)==r['sha256'];t.unlink();assert sha(source)==r['sha256'];r['status']='TEMP_ONLY_REMOVED'
 result=dict(status='PASS',temporary_files=temp_rows,converted_files_checked=len(reconciled),reconciled=reconciled,manifest_repairs_required=sum(r['needs_manifest_repair'] for r in reconciled),original_damage_found=False,cleanup_performed=clean)
 save(OUT/'resume_audit.json',result);print(json.dumps(dict(status='PASS',temporaries=len(temp_rows),removed=sum(r['status']=='TEMP_ONLY_REMOVED' for r in temp_rows),converted_verified=len(reconciled),repairs_required=result['manifest_repairs_required'])))
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--clean',action='store_true');a=p.parse_args()
 try:audit(a.clean)
 except BaseException as exc:
  save(OUT/'resume_audit_failure.json',dict(status='STOPPED_AUDIT_ERROR',error=repr(exc)));raise
if __name__=='__main__':main()
