"""Use the frozen Phase29 driver affinity/short socket/cleanup for both EC arms."""
import subprocess,sys
from pathlib import Path
from types import FunctionType
from nomad_phase29 import launch as old
from .config import HERE,verify,METHODS,SCENES,RUN_ROOT

class Processes(old.Processes):
 def Popen(self,args,*a,**kw):
  args=[str(HERE/'simulator.py') if str(x).endswith('/nomad_phase26/simulator.py') else x for x in args]
  child=subprocess.Popen(args,*a,**kw);self.children.append(child);return child

_main=FunctionType(old.main.__code__,dict(old.main.__globals__,HERE=HERE,verify=verify,METHODS=METHODS,SCENES=SCENES,RUN_ROOT=RUN_ROOT,Processes=Processes),old.main.__name__,old.main.__defaults__,old.main.__closure__)
def main():
 assert '--smoke' not in sys.argv
 out=Path(sys.argv[sys.argv.index('--output')+1]).resolve();assert out.is_relative_to(RUN_ROOT.resolve()/'main')
 base=old.base;writer=base.write_json
 def provenance(path,value):
  if path.name=='provenance.json':value=dict(value,phase='32',ec_method=value['method'],offline_deviation='2026-11-07 user-approved continuation; Phase32-O remains OFFLINE_FAIL')
  return writer(path,value)
 base.write_json=provenance
 try:return _main()
 finally:base.write_json=writer
if __name__=='__main__':main()
