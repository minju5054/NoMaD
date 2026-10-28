"""One SLW depth inspection and exactly two excluded CL 30s smoke attempts."""
import argparse,json,subprocess,time
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase0.s0_batch import exclusive_batch
from nomad_phase16.preflight import inspection_plot
from .config import verify_sources,METHODS
from .campaign import clean_env,read,write


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);a=ap.parse_args()
    root=a.run_root.resolve();p=verify_sources()
    assert read(ROOT/'research/results/phase17/offline_complete.json')['label']=='READY'
    assert not root.exists(),'Preflight never retries or overwrites'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).strip()
    out=ROOT/'research/results/phase17_preflight';assert not out.exists()
    with exclusive_batch():
        root.mkdir(parents=True);out.mkdir();env=clean_env();evidence=[]
        def stage(name,args,folder):
            start=time.perf_counter()
            with (root/f'{name}.log').open('x') as f:
                code=subprocess.run(['/usr/bin/python3','-u','-m','nomad_phase17.launch',*args,'--output',str(folder)],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
            r=dict(stage=name,exit_code=code,wall_s=time.perf_counter()-start,output=str(folder),excluded=True)
            evidence.append(r);write(root/'validation.json',evidence);return r
        folder=root/'inspect/SLW'
        r=stage('inspect_SLW',['--mode','inspect','--scene','SLW'],folder)
        if r['exit_code']:raise RuntimeError('SLW depth inspection failed; no retry')
        inspection_plot(folder,out/'start_SLW.png');r['inspection']=read(folder/'inspection.json')
        print('[inspect] SLW PASS',flush=True)
        previous=ROOT.parent/'artifacts/isaac6/phase16_multiscene_01/main/CL_058_D750_FRESHEST-SAFE+GRAPH-depth/events.jsonl'
        events=[json.loads(l) for l in previous.read_text().splitlines()]
        first=next(e for e in events if e['phase16']['fallback_mode']=='STOP_WAIT')
        start_pose=first['agent_pose_at_switch']
        manifest=p['topomap_reuse']['CL']['manifest']
        from .metrics import audit
        for name,method,pose in [('CL_CLR',METHODS[5],None),('CL_recovery',METHODS[0],start_pose)]:
            folder=root/'smoke'/name
            args=['--mode','navigation','--scene','CL','--method',method,'--index','901','--delay','.75',
                  '--timeout','30','--smoke','--topomap',manifest]
            if pose is not None:args+=['--start-pose',*[str(x) for x in pose]]
            r=stage(name,args,folder)
            if pose is not None:r['start_source']=dict(file=str(previous),sha256=sha256_file(previous),fresh_id=first['id'],pose=pose)
            if r['exit_code']==0:
                try:
                    r.update(audit(folder))
                    if pose is not None:assert r['recovery_completed']>=1,'Live stop-to-rotation not observed; preserve and stop'
                except Exception as e:r.update(technical_validation='FAIL',error=repr(e))
            else:r['technical_validation']='FAIL'
            write(root/'validation.json',evidence);print(f"[smoke] {name} {r['technical_validation']}",flush=True)
        verify_sources()
        result=dict(passed=all(r['exit_code']==0 and r.get('technical_validation','PASS')=='PASS' for r in evidence),
            evidence=evidence,navigation_attempts=2,main_attempts=0,scope='EXCLUDED_TECHNICAL_SMOKES',
            runtime_source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in Path(__file__).parent.glob('*.py')},
            protocol_sha256=sha256_file(Path(__file__).with_name('protocol.json')))
        write(out/'validation.json',result);write(root/'complete.json',result)
        if not result['passed']:raise RuntimeError('Technical preflight failed; no retries or campaign')
        write(out/'readiness.json',result)


if __name__=='__main__':main()
