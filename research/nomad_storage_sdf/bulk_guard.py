"""Read-only host process/lock exclusion for offline storage maintenance."""
import json,os,re,time
from pathlib import Path

ACTIVE={'RUNNING','STARTING','TRAINING','EVALUATING','RENDERING','ACTIVE'}

class ActiveRoot(RuntimeError):pass


def ancestors():
 result=set();pid=os.getpid()
 while pid>0 and pid not in result:
  result.add(pid)
  try:pid=int(Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[1])
  except (OSError,ValueError):break
 return result


def host_required():
 name=Path('/proc/1/comm').read_text().strip()
 if name not in ('systemd','init'):raise RuntimeError('Host PID visibility required, found '+name)


def kernel_locks():
 result=set()
 for line in Path('/proc/locks').read_text().splitlines():
  for token in line.split():
   if re.fullmatch(r'[0-9a-fA-F]+:[0-9a-fA-F]+:[0-9]+',token):
    major,minor,ino=token.split(':');result.add((os.makedev(int(major,16),int(minor,16)),int(ino)))
 return result


class Guard:
 def __init__(self,base):
  host_required();self.base=Path(base).resolve();self.ignore=ancestors();self.last=0.;self.process_roots={};self.locks=set();self.lock_paths={}
 def refresh(self,force=False):
  if not force and time.monotonic()-self.last<1.:return
  matched={};locks=kernel_locks()
  for p in Path('/proc').iterdir():
   if not p.name.isdigit() or int(p.name) in self.ignore:continue
   try:cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
   except (FileNotFoundError,ProcessLookupError,PermissionError):continue
   for name in re.findall(r'(?:^|[/ ])isaac6/([^/\s"\x27]+)',cmd):matched.setdefault(name,[]).append(dict(pid=int(p.name),kind='command',command=cmd[:1000]))
   # Orphaned spawned workers may not carry --output in argv; their open
   # log/data descriptors still identify the run. Ignore our own descriptors.
   try:
    if p.stat().st_uid!=os.getuid():continue
   except (FileNotFoundError,ProcessLookupError,PermissionError):continue
   try:files=list((p/'fd').iterdir())
   except (FileNotFoundError,ProcessLookupError,PermissionError):continue
   for fd in files:
    try:target=os.readlink(fd)
    except (FileNotFoundError,ProcessLookupError,PermissionError,OSError):continue
    prefix=str(self.base)+'/'
    if target.startswith(prefix):
     name=target[len(prefix):].split('/')[0]
     matched.setdefault(name,[]).append(dict(pid=int(p.name),kind='open_fd',target=target))
  self.process_roots=matched;self.locks=locks;self.last=time.monotonic()
 def reason(self,root,force=False):
  root=Path(root);self.refresh(force)
  if root.name=='phase32_01':return dict(reason='PROTECTED_PHASE32_ROOT')
  marker=[str(p) for p in root.iterdir() if p.name.lower() in ('lock','.lock','pid','.pid','campaign.pid') or p.name.lower().endswith('.lock')]
  if marker:return dict(reason='RUN_ROOT_LOCK_MARKER',files=marker)
  state=root/'state.json'
  if state.exists():
   try:s=json.loads(state.read_text())
   except (ValueError,UnicodeDecodeError):return dict(reason='UNREADABLE_STATE')
   if isinstance(s,dict):
    if str(s.get('status','')).upper() in ACTIVE:return dict(reason='ACTIVE_STATE',status=s.get('status'),pid=s.get('pid'))
    for key in ('pid','active_child_pid'):
     pid=s.get(key)
     if pid and Path(f'/proc/{pid}').exists():
      try:token=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[19]
      except (FileNotFoundError,ProcessLookupError):continue
      if key=='active_child_pid' or not s.get('process_token') or token==s['process_token']:return dict(reason='LIVE_STATE_PID',pid=pid)
  if self.process_roots.get(root.name):return dict(reason='LIVE_PROCESS_OR_OPEN_FD',processes=self.process_roots[root.name])
  if root.name not in self.lock_paths:
   self.lock_paths[root.name]=[p for p in root.rglob('*') if p.name.lower().endswith('.lock') or p.name.lower() in ('lock','.lock','campaign.pid')]
  residue=0
  for p in self.lock_paths[root.name]:
   try:st=p.stat()
   except FileNotFoundError:continue
   rel=p.relative_to(root)
   if not any(part in ('cache','portable','pycache') for part in rel.parts[:-1]):return dict(reason='EXECUTION_LOCK_MARKER',file=str(p))
   if (st.st_dev,st.st_ino) in self.locks:return dict(reason='HELD_CACHE_LOCK',file=str(p))
   residue+=1
  return None
 def assert_clear(self,root):
  reason=self.reason(root)
  if reason:raise ActiveRoot(json.dumps(dict(root=str(root),**reason)))
