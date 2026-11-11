"""Phase18 process launcher; RAW method, protocol, simulator and provenance routing."""
import inspect,subprocess
from nomad_phase18 import launch as frozen
from nomad_phase40p.launch import bind
from .config import ROOT,HERE,METHODS,RTC,verify_sources
class Processes:
    def __getattr__(self,k):return getattr(subprocess,k)
    def Popen(self,args,*a,**kw):
        args=[str(HERE/'simulator.py') if str(x).endswith('/nomad_phase18/simulator.py') else x for x in args]
        return subprocess.Popen(args,*a,**kw)

def launcher_main(processes):
    source=inspect.getsource(frozen.main).replace('phase=18,','phase="18-RAW",')
    def write(path,value):
        if path.name=='provenance.json':
            from nomad_isaac.common import sha256_file
            value=dict(value,protocol_sha256=sha256_file(HERE/'protocol.json'),source_sha256=verify_sources()['source_sha256'])
        return frozen.write_json(path,value)
    ns=dict(frozen.main.__globals__,__file__=str(HERE/'launch.py'),METHODS=METHODS,RTC=RTC,verify_sources=verify_sources,subprocess=processes,write_json=write)
    exec(compile(source,__file__,'exec'),ns);return ns['main']
def main():
    import sys
    assert '--smoke' not in sys.argv
    return launcher_main(Processes())()
if __name__=='__main__':main()
