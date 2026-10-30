"""Geometry bookkeeping and six sequential excluded L2 smokes; never main navigation."""
import argparse,json,os,subprocess,time
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from .config import protocol,verify_sources,METHODS

def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def env():
    e=os.environ.copy()
    for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):e.pop(k,None)
    e.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/phase21-mpl');return e

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--geometry-root',type=Path);ap.add_argument('--smoke-root',type=Path);ap.add_argument('--finalize',action='store_true');a=ap.parse_args();p=verify_sources();out=ROOT/'research/results/phase21_preflight'
    if a.geometry_root:
        data=[json.loads((a.geometry_root/k/'geometry.json').read_text()) for k in ('odd','even')];assert all(r['passed'] for r in data)
        write(out/'geometry.json',dict(passed=True,checks=data,files={str(a.geometry_root/k/'geometry.json'):sha256_file(a.geometry_root/k/'geometry.json') for k in ('odd','even')}))
        p['status']='GEOMETRY_PASS';p['geometry']['passed_offset_m']=p['scenes']['L2A']['offset_m'];write(Path(__file__).with_name('protocol.json'),p);print('[geometry] both parities PASS; offset unchanged',flush=True)
    if a.smoke_root:
        assert p['status']=='GEOMETRY_PASS';root=a.smoke_root.resolve();root.mkdir(parents=True,exist_ok=False);results=[]
        for method in METHODS:
            output=root/method;log=root/f'{method}.log';start=time.monotonic()
            argv=['/usr/bin/python3','-u','-m','nomad_phase21.launch','--mode','navigation','--scene','L2','--method',method,'--index','95','--delay','.75','--timeout','90','--smoke','--topomap',p['SO']['topomap'],'--output',str(output)]
            with log.open('x') as stream:code=subprocess.run(argv,cwd=ROOT,env=env(),stdout=stream,stderr=subprocess.STDOUT).returncode
            result=dict(method=method,output=str(output),exit_code=code,technical_validation='FAIL',excluded=True)
            if code==0:
                try:
                    from .metrics import audit
                    result.update(audit(output))
                except Exception as exc:result['audit_error']=repr(exc)
            result['total_wall_s']=time.monotonic()-start;results.append(result);write(out/'smokes.json',results);print(f"[smoke] {method} {result['technical_validation']} {result['total_wall_s']:.1f}s",flush=True)
        estimate=sum(r['total_wall_s'] for r in results)/6*60
        p['smoke']['measured_wall_s']={r['method']:r['total_wall_s'] for r in results};p['smoke']['estimated_60_s']=estimate
        if estimate>9000:p['indices']=list(range(111,115))
        p['main_order']=[j for j in p['main_order'] if j['index'] in p['indices']];p['planned_runs']=len(p['main_order']);p['estimated_main_s']=estimate*p['planned_runs']/60
        p['status']='SMOKE_PASSED' if all(r['technical_validation']=='PASS' for r in results) else 'SMOKE_TECHNICAL_FAILURE';write(Path(__file__).with_name('protocol.json'),p)
        print(json.dumps(dict(status=p['status'],planned=p['planned_runs'],estimated_s=p['estimated_main_s'])),flush=True)
    if a.finalize:
        assert p['status'] in ('SMOKE_PASSED','FROZEN');p['status']='FROZEN';write(Path(__file__).with_name('protocol.json'),p)
        package=Path(__file__).parent;write(out/'readiness.json',dict(passed=True,protocol_sha256=sha256_file(package/'protocol.json'),source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in package.glob('*') if f.is_file()},main_navigation_started=0))
        print('[preflight] frozen; main not executed')
if __name__=='__main__':main()
