"""Held-out geometry first, then three excluded L2 smokes; no main campaign."""
import argparse,json,os,subprocess,time
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from .drive_config import protocol,verify_sources,METHODS

def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def env():
    e=os.environ.copy()
    for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):e.pop(k,None)
    e.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/phase22-drive-mpl');return e

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--geometry-root',type=Path);ap.add_argument('--smoke-root',type=Path);ap.add_argument('--finalize',action='store_true');a=ap.parse_args();p=verify_sources();out=ROOT/'research/results/phase22_preflight'
    if a.geometry_root:
        root=a.geometry_root.resolve();root.mkdir(parents=True,exist_ok=False);results=[]
        for attempt in (1,2):
            current=[]
            for index in (121,122):
                target=root/f'offset_{p["scenes"]["L2B"]["offset_m"]}_{index}';target.mkdir()
                command=['/home/gpuadmin/isaacsim/python.sh',str(ROOT/'research/nomad_phase22/drive_simulator.py'),'--geometry-only','--level','L2B','--method','P0_ASTAR','--index',str(index),'--delay','0','--timeout','90','--socket','/tmp/unused22geom.sock','--output',str(target),'--portable-root',str(target/'portable')]
                with (target/'launcher.log').open('x') as log:code=subprocess.run(command,cwd=ROOT,env=env(),stdout=log,stderr=subprocess.STDOUT).returncode
                if code:raise RuntimeError(f'Geometry renderer error:{target}; preserve data, no placement adjustment for technical errors')
                r=json.loads((target/'geometry.json').read_text());r['output']=str(target);current.append(r);results.append(r);print(f'[geometry] index{index} PASS={r["passed"]}',flush=True)
            if all(r['passed'] for r in current):break
            if attempt==1:
                p['scenes']['L2B']['offset_m']=.2;write(Path(__file__).with_name('drive_protocol.json'),p);print('[geometry] one allowed offset adjustment to0.2',flush=True)
        passed=all(r['passed'] for r in current);write(out/'geometry.json',dict(passed=passed,attempts=results));assert passed,'Geometry failed; no method execution'
        p['geometry_passed']=True
        if p['status']=='REGISTERED':p['status']='GEOMETRY_PASS'
        write(Path(__file__).with_name('drive_protocol.json'),p)
    if a.smoke_root:
        assert p['status']=='GEOMETRY_PASS';root=a.smoke_root.resolve();root.mkdir(parents=True,exist_ok=False);results=[]
        for method in METHODS:
            target=root/method;start=time.monotonic();command=['/usr/bin/python3','-u','-m','nomad_phase22.drive_launch','--mode','navigation','--scene','L2','--method',method,'--index','95','--delay','.75','--timeout','90','--smoke','--topomap',p['SO']['topomap'],'--output',str(target)]
            with (root/f'{method}.log').open('x') as log:code=subprocess.run(command,cwd=ROOT,env=env(),stdout=log,stderr=subprocess.STDOUT).returncode
            r=dict(method=method,output=str(target),excluded=True,technical_validation='FAIL',exit_code=code)
            if code==0:
                try:
                    from .drive_metrics import audit
                    r.update(audit(target))
                except Exception as exc:r['audit_error']=repr(exc)
            r['total_wall_s']=time.monotonic()-start;results.append(r);write(out/'smokes.json',results);print(f'[smoke] {method} {r["technical_validation"]} {r["total_wall_s"]:.1f}s',flush=True)
        estimate=sum(r['total_wall_s'] for r in results)/3*24;p['smoke']['estimated_24_s']=estimate;p['smoke']['measured_wall_s']={r['method']:r['total_wall_s'] for r in results}
        if estimate>7200:p['indices']=[121,122,123]
        p['main_order']=[j for j in p['main_order'] if j['index'] in p['indices']];p['planned_runs']=len(p['main_order']);p['estimated_main_s']=estimate*len(p['main_order'])/24
        p['status']='SMOKE_PASSED' if all(r['technical_validation']=='PASS' for r in results) else 'SMOKE_TECHNICAL_FAILURE';write(Path(__file__).with_name('drive_protocol.json'),p)
    if a.finalize:
        assert p['status'] in ('SMOKE_PASSED','FROZEN');p['status']='FROZEN';write(Path(__file__).with_name('drive_protocol.json'),p)
        files=[*Path(__file__).parent.glob('drive*.py'),Path(__file__).with_name('drive_protocol.json'),Path(__file__).with_name('test_drive.py')]
        write(out/'readiness.json',dict(passed=True,protocol_sha256=sha256_file(Path(__file__).with_name('drive_protocol.json')),source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in files},main_navigation_started=0))
if __name__=='__main__':main()
