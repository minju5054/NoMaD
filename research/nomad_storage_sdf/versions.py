"""Resolve each run's recorded SDF source, accepting only known AST semantics."""
import ast,hashlib,json,subprocess
from pathlib import Path
from nomad_isaac.common import ROOT

OCC='research/nomad_phase15/occupancy.py'
DEPTH='research/nomad_phase15/depth_sdf.py'
KNOWN_KEYS={'values','occupied','observed','origin','h','radius','metadata','last_free_tick','first_free_tick','first_occupied_tick','new_component_ids','component_births'}
MIN_KEYS={'values','occupied','observed','origin','h','radius','metadata'}


def method(source,klass,name):
 t=ast.parse(source)
 c=next(n for n in t.body if isinstance(n,ast.ClassDef) and n.name==klass)
 n=next(n for n in c.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
 return ast.dump(n,include_attributes=False),ast.get_source_segment(source,n)


class Registry:
 def __init__(self):self.runs={};self.sources={};self.records={}
 def source(self,commit,path,expected=None):
  key=(commit,path,expected)
  if key in self.sources:return self.sources[key]
  current=(ROOT/path).read_text();current_hash=hashlib.sha256(current.encode()).hexdigest()
  if expected and expected==current_hash:answer=(current,'recorded SHA matches frozen file')
  else:
   r=subprocess.run(['git','show',f'{commit}:{path}'],cwd=ROOT,capture_output=True,text=True)
   if r.returncode:answer=(None,'historical source unavailable')
   elif expected and hashlib.sha256(r.stdout.encode()).hexdigest()!=expected:answer=(None,'recorded source SHA differs from available commit')
   else:answer=(r.stdout,'historical git source')
  self.sources[key]=answer;return answer
 def resolve(self,run):
  run=Path(run).resolve()
  if str(run) in self.runs:return self.runs[str(run)]
  p=run/'provenance.json';c=run/'scenario.json'
  if not p.exists() or not c.exists():result=dict(supported=False,reason='UNKNOWN_VERSION_NO_RUN_PROVENANCE')
  else:
   try:prov=json.loads(p.read_text());cfg=json.loads(c.read_text())
   except (ValueError,UnicodeDecodeError):result=dict(supported=False,reason='UNKNOWN_VERSION_UNREADABLE_PROVENANCE')
   else:
    commit=prov.get('git_sha') or prov.get('execution_git_sha')
    if not commit or not cfg.get('depth_camera'):result=dict(supported=False,reason='UNKNOWN_RUNTIME_DEPTH_VERSION')
    else:
     hashes={}
     for source in (prov,prov.get('protocol',{})):
      for key in ('frozen_sources','source_sha256','source_hashes'):
       value=source.get(key,{})
       if isinstance(value,dict):hashes.update(value)
     hashes={k.replace(str(ROOT)+'/',''):v for k,v in hashes.items()}
     dirty=prov.get('git_status','') or ''
     if not isinstance(dirty,str):dirty=''
     hashes={k:v for k,v in hashes.items() if isinstance(v,str)}
     if any(path in dirty and path not in hashes for path in (OCC,DEPTH)):result=dict(supported=False,reason='UNKNOWN_VERSION_DIRTY_SOURCE',commit=commit)
     else:
      sources={};how={}
      for path in (OCC,DEPTH):sources[path],how[path]=self.source(commit,path,hashes.get(path))
      if any(s is None for s in sources.values()):result=dict(supported=False,reason='UNKNOWN_VERSION_MISSING_SOURCE',commit=commit,details=how)
      else:
       try:
        signatures={OCC:method(sources[OCC],'LogOddsSDF','update'),DEPTH:method(sources[DEPTH],'DepthSDF','__init__')}
        matching=all(signatures[path][0]==method((ROOT/path).read_text(),'LogOddsSDF' if path==OCC else 'DepthSDF','update' if path==OCC else '__init__')[0] for path in (OCC,DEPTH))
       except (SyntaxError,StopIteration):matching=False
       result=dict(supported=matching,reason='KNOWN_LOG_ODDS_EDT_VERSION' if matching else 'UNKNOWN_VERSION_DIFFERENT_SDF_FUNCTION',commit=commit,source_resolution=how,
          source_sha256={p:hashlib.sha256(s.encode()).hexdigest() for p,s in sources.items()})
       if matching:
        result['function_sha256']={p:hashlib.sha256(signatures[p][1].encode()).hexdigest() for p in signatures}
        result['reconstruction']='Frozen LogOddsSDF.update EDT expression + matching DepthSDF empty initialization; file bit check still mandatory'
  ident=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()[:20];result=dict(result,version_id=ident)
  self.runs[str(run)]=result;self.records[ident]=result;return result
