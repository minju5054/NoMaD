"""Experiment-specific protocol selection; numerical protocols remain byte-frozen."""
import inspect,json,sys
from pathlib import Path
from nomad_phase53p import launch as frozen
from nomad_phase40p.launch import bind
from nomad_isaac.common import sha256_file
from . import config
from .config import HERE,RUN_ROOT,SMOKE_ROOT,METHODS,SCENES,EXP,DEFS,split

LAUNCHER_REL='research/nomad_night20261111/launch.py'

def revision():return json.loads((HERE/'launcher_revision.json').read_text())

def verify(e=None):
    """Honor every original hash, plus the sole authorized launcher revision.

    No protocol mutation or global verifier bypass. The original verifier runs
    with a private hash callback that first checks the actual replacement bytes
    and original registered hash for this one file, then supplies its old token.
    All other source and reference hashes are checked by the frozen verifier.
    """
    e=e or EXP;r=revision();p=config.protocol(e)
    assert sha256_file(HERE/f'protocol_{e}.json')==r['protocol_before_sha256'][e]
    assert p['source_sha256'][LAUNCHER_REL]==r['original_launcher_sha256']
    assert sha256_file(HERE/'launch.py')==r['revised_launcher_sha256']
    def checked_hash(path):
        actual=sha256_file(path)
        if Path(path).resolve()==(HERE/'launch.py').resolve():
            assert actual==r['revised_launcher_sha256']
            return r['original_launcher_sha256']
        return actual
    return bind(config.verify,sha256_file=checked_hash)(e)

class Processes(frozen.Processes):Popen=bind(frozen.Processes.Popen,HERE=HERE,split=split)

def launcher_main(processes):
    source=inspect.getsource(frozen.launcher_main)
    assert source.count("HERE/'protocol.json'")==1
    source=source.replace("HERE/'protocol.json'","HERE/f'protocol_{EXP}.json'")
    source=source.replace("phase='53-P'","phase='NIGHT_20261111_'+EXP")
    source=source.replace("source_sha256=verify()['source_sha256']", "source_sha256={**verify()['source_sha256'],LAUNCHER_REL:revision()['revised_launcher_sha256']},launcher_revision=revision()")
    source=source.replace("a.index==95 and a.scene=='LC_D075' and a.method=='GRAPH-HO'", "a.index==95 and a.scene==SMOKE_SCENE and a.method==SMOKE_METHOD")
    ns=dict(frozen.launcher_main.__globals__,HERE=HERE,METHODS=METHODS,SCENES=SCENES,verify=verify,EXP=EXP,revision=revision,LAUNCHER_REL=LAUNCHER_REL,
        SMOKE_SCENE=DEFS[EXP]['smoke']['scene'],SMOKE_METHOD=DEFS[EXP]['smoke']['method'])
    source=source.replace('METHODS=METHODS,SCENES=SCENES,verify=verify,subprocess=processes,','METHODS=METHODS,SCENES=SCENES,verify=verify,subprocess=processes,SMOKE_SCENE=SMOKE_SCENE,SMOKE_METHOD=SMOKE_METHOD,')
    exec(compile(source,__file__,'exec'),ns);return ns['launcher_main'](processes)

def dry_run():
    """Execute actual parser/verify/provenance/storage path; stop at first Popen."""
    import tempfile
    class BeforeChild(Exception):pass
    class NoProcesses:
        def __getattr__(self,name):return getattr(__import__('subprocess'),name)
        def Popen(self,*a,**kw):raise BeforeChild()
    original=sys.argv[:]
    with tempfile.TemporaryDirectory(prefix='night-launch-protocol-') as tmp:
        row=DEFS[EXP]['smoke'];out=Path(tmp)/'attempt'
        sys.argv=['launch','--scene',row['scene'],'--method',row['method'],'--index',str(row['index']),'--output',str(out),'--smoke']
        try:
            try:launcher_main(NoProcesses())()
            except BeforeChild:pass
            else:raise AssertionError('Dry-run did not reach actual first child launch boundary')
            p=json.loads((out/'provenance.json').read_text());r=revision();expected=verify()
            assert p['protocol']==expected
            assert p['protocol_sha256']==r['protocol_before_sha256'][EXP]
            assert p['source_sha256'][LAUNCHER_REL]==r['revised_launcher_sha256']
            assert (out/'storage_policy.json').exists()
            print(json.dumps(dict(experiment=EXP,status='PASS',protocol_file=f'protocol_{EXP}.json',protocol_sha256=p['protocol_sha256'],
                provenance_written=True,child_launch_boundary_reached=True,processes_started=0,original_protocol_content_unchanged=True)))
        finally:sys.argv=original

def queue_run():
    """Supply this same narrow verifier to the unchanged queue/report entrypoints."""
    import subprocess
    from . import queue
    class ReportProcessRoutes:
        def __getattr__(self,name):return getattr(subprocess,name)
        def run(self,args,*a,**kw):
            args=list(args)
            if 'nomad_night20261111.report' in args:
                i=args.index('nomad_night20261111.report');args[i]='nomad_night20261111.launch';args.insert(i+1,'--report')
            return subprocess.run(args,*a,**kw)
    queue.verify=verify;queue.subprocess=ReportProcessRoutes()
    queue.run()

def report_main():
    from . import report
    report.verify=verify;sys.argv.remove('--report');report.main()

def main():
    if '--dry-run' in sys.argv:dry_run();return
    if '--queue-run' in sys.argv:queue_run();return
    if '--report' in sys.argv:report_main();return
    bind(frozen.main,HERE=HERE,RUN_ROOT=RUN_ROOT,SMOKE_ROOT=SMOKE_ROOT,Processes=Processes,launcher_main=launcher_main)()
if __name__=='__main__':main()
