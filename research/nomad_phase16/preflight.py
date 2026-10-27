"""Explicit developer preflight only: three scene captures and three excluded smokes."""
import argparse,json,subprocess,time
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase0.s0_batch import exclusive_batch
from .config import protocol,verify_sources
from .campaign import clean_env,write

def inspection_plot(folder,destination):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    with np.load(folder/'start_depth.npz') as z:depth=z['depth']
    with np.load(folder/'start_occupancy.npz') as z:occupied=z['occupied'];observed=z['observed'];origin=z['origin'];h=float(z['h'])
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    image=axes[0].imshow(np.where(np.isfinite(depth),depth,np.nan),vmin=0,vmax=3,cmap='viridis');fig.colorbar(image,ax=axes[0],label='Axial depth (m)');axes[0].set_title('First start-pose depth frame')
    grid=np.where(occupied,1.,np.where(observed,.5,0.));axes[1].imshow(grid,origin='lower',extent=[origin[0],origin[0]+occupied.shape[1]*h,origin[1],origin[1]+occupied.shape[0]*h],cmap='gray_r',vmin=0,vmax=1);axes[1].set_title('V1 occupancy after 3 stationary frames')
    axes[1].set_xlabel('World x (m)');axes[1].set_ylabel('World y (m)');fig.tight_layout();fig.savefig(destination,dpi=150);plt.close(fig)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);a=ap.parse_args();root=a.run_root.resolve();p=verify_sources()
    assert p['status']=='FROZEN','Awaiting reference-distance and TE KEEP_ACTIVE choices'
    assert not root.exists(),'Preflight never retries or overwrites'
    with exclusive_batch():
        root.mkdir();env=clean_env();evidence=[];out=ROOT/'research/results/phase16_preflight';out.mkdir(exist_ok=False)
        for sc in ('SL','LC','CL'):
            folder=root/'prepare'/sc;mode='reference' if sc=='SL' else 'inspect'
            argv=['/usr/bin/python3','-m','nomad_phase16.launch','--scene',sc,'--mode',mode,'--output',str(folder)]
            start=time.perf_counter()
            with (root/f'prepare_{sc}.log').open('x') as f:code=subprocess.run(argv,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
            row=dict(stage='prepare',scene=sc,exit_code=code,wall_s=time.perf_counter()-start,output=str(folder));evidence.append(row);write(root/'validation.json',evidence)
            if code:raise RuntimeError(f'{sc} preflight failed; no retries')
            inspection_plot(folder,out/f'start_{sc}.png');print(f'[inspect] {sc} PASS',flush=True)
        manifest=root/'prepare/SL/topomap/manifest.json'
        from .metrics import audit
        for method in p['smoke']['methods']:
            folder=root/'smoke'/f'SL_901_D750_{method}';start=time.perf_counter()
            argv=['/usr/bin/python3','-m','nomad_phase16.launch','--scene','SL','--mode','navigation','--method',method,'--index','901','--delay','.75','--timeout','30','--smoke','--topomap',str(manifest),'--output',str(folder)]
            with (root/f'smoke_{method}.log').open('x') as f:code=subprocess.run(argv,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
            result=dict(stage='smoke',method=method,exit_code=code,wall_s=time.perf_counter()-start,output=str(folder),excluded=True)
            if code==0:
                try:result.update(audit(folder))
                except Exception as exc:result.update(technical_validation='FAIL',error=repr(exc))
            else:result['technical_validation']='FAIL'
            evidence.append(result);write(root/'validation.json',evidence);print(f"[smoke] {method} {result['technical_validation']}",flush=True)
        verify_sources()
        result=dict(passed=all(r['exit_code']==0 and r.get('technical_validation','PASS')=='PASS' for r in evidence),evidence=evidence,
            actual_navigation_attempts=3,main_navigation_attempts=0,temporary_topomap_sha256=sha256_file(manifest),scope='TECHNICAL_PREFLIGHT_EXCLUDED_FROM_MAIN')
        write(out/'validation.json',result);write(root/'complete.json',result)
        if not result['passed']:raise RuntimeError('Smoke technical validation failed; no retries or main execution')
if __name__=='__main__':main()
