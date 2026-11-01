"""L2B-only replay of the frozen campaign; original L2/raw/report remain read-only."""
import argparse,inspect,json,subprocess,time,types
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from . import drive_campaign as frozen
from .drive_config import verify_sources as verify_original,METHODS
from .drive_preflight import env,write

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase22_l2b_preflight'
def registration():return json.loads((HERE/'l2b_protocol.json').read_text())
def protocol():
    p=verify_original();r=registration()
    return dict(p,phase='22-L2B-runtime-fix',planned_runs=12,main_order=[j for j in p['main_order'] if j['scene']=='L2B'],rerun_registration=r)
def verify_sources():
    p=protocol();r=p['rerun_registration'];assert r['status']=='FROZEN'
    assert sha256_file(HERE/'drive_protocol.json')==r['original_protocol_sha256']
    original=json.loads((ROOT/'research/results/phase22_preflight/readiness.json').read_text())
    for file,h in original['source_sha256'].items():
        expected=r['runtime_patch']['after_sha256'] if file==r['runtime_patch']['file'] else h
        assert sha256_file(ROOT/file)==expected,file
    for file,h in r['preserved_sha256'].items():assert sha256_file(file)==h,file
    return p

# Keep the exact retry, exclusion, lock/resume and launch logic. Only the job
# list, registration/readiness paths and post-run report module are substituted.
ns={**frozen.__dict__,'protocol':protocol,'verify_sources':verify_sources}
ns['jobs']=types.FunctionType(frozen.jobs.__code__,ns)
src=inspect.getsource(frozen.campaign)
for old,new in (
    ('research/results/phase22_preflight/readiness.json','research/results/phase22_l2b_preflight/readiness.json'),
    ("'drive_protocol.json'","'l2b_protocol.json'"),
    ('nomad_phase22.drive_report','nomad_phase22.l2b_report')):
    assert src.count(old)==1;src=src.replace(old,new)
exec(compile(src,__file__,'exec'),ns)
main_source=inspect.getsource(frozen.main).replace('nomad_phase22.drive_campaign','nomad_phase22.l2b_rerun')
exec(compile(main_source,__file__,'exec'),ns)

def launch_checks(root):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=False);results=[]
    for method,index in zip(METHODS,(901,902,903)):
        target=root/f'{method}_{index}';target.mkdir()
        command=['/home/gpuadmin/isaacsim/python.sh','-m','nomad_phase22.l2b_launch_check','--level','L2B','--method',method,'--index',str(index),'--delay','.75','--timeout','90','--socket','/tmp/unused-phase22-l2b-check.sock','--output',str(target),'--portable-root',str(target/'portable')]
        started=time.monotonic()
        with (target/'simulator.log').open('x') as stream:code=subprocess.run(command,cwd=ROOT,env=env(),stdout=stream,stderr=subprocess.STDOUT).returncode
        file=target/'launch_check.json';r=json.loads(file.read_text()) if file.exists() else dict(passed=False,method=method,index=index)
        r.update(output=str(target),exit_code=code,wall_s=time.monotonic()-started);r['passed']=r['passed'] and code==0
        results.append(r);write(OUT/'launch_checks.json',results);print(f'[spawn-only] {method} index{index} PASS={r["passed"]}',flush=True)
        assert r['passed'],f'Spawn-only check failed; preserved {target}'

if __name__=='__main__':
    import sys
    if '--launch-checks' in sys.argv:
        ap=argparse.ArgumentParser();ap.add_argument('--launch-checks',type=Path,required=True);a=ap.parse_args();launch_checks(a.launch_checks)
    else:ns['main']()
