"""Exactly one excluded 30-second CL SAFE+RTC-hard technical smoke."""
import argparse,json,subprocess,time
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase0.s0_batch import exclusive_batch
from .config import verify_sources,RTC
from .campaign import clean_env,read,write

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);a=ap.parse_args()
    root=a.run_root.resolve();p=verify_sources();out=ROOT/'research/results/phase18_preflight'
    assert p['status']=='FROZEN'
    assert read(out/'rtc_replay.json',{}).get('passed'),'Stored RTC input replay must pass first'
    assert not root.exists(),'No smoke retry or overwrite'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).strip()
    with exclusive_batch():
        root.mkdir(parents=True);folder=root/'CL_901_SAFE_RTC';start=time.perf_counter()
        argv=['/usr/bin/python3','-u','-m','nomad_phase18.launch','--scene','CL','--mode','navigation',
              '--method',RTC,'--index','901','--delay','.75','--timeout','30','--smoke',
              '--topomap',p['topomaps']['CL']['manifest'],'--output',str(folder)]
        with (root/'smoke.log').open('x') as f:code=subprocess.run(argv,cwd=ROOT,env=clean_env(),stdout=f,stderr=subprocess.STDOUT).returncode
        r=dict(exit_code=code,output=str(folder),excluded=True,wall_s=time.perf_counter()-start,navigation_attempts=1,main_attempts=0)
        if code==0:
            try:
                from .metrics import audit
                r.update(audit(folder));assert r['rtc_inference_count']>0
                assert r['switch_count']>0
            except Exception as e:r.update(technical_validation='FAIL',error=repr(e))
        else:r.update(technical_validation='FAIL',error=f'Launcher exit {code}')
        verify_sources();r['passed']=r['technical_validation']=='PASS'
        write(out/'smoke.json',r);write(root/'complete.json',r)
        if not r['passed']:raise RuntimeError('RTC smoke technical failure; preserve output, no retry/main campaign')
        write(out/'readiness.json',dict(passed=True,smoke=r,
            protocol_sha256=sha256_file(Path(__file__).with_name('protocol.json')),
            runtime_source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in Path(__file__).parent.glob('*.py')},
            scope='EXCLUDED_TECHNICAL_SMOKE_ONLY'))
        print(f"SAFE+RTC-hard smoke PASS: {r['request_count']} requests, {r['switch_count']} switches, d0={r['rtc_d0_count']}, pose error={r['pose_replay_error']}")

if __name__=='__main__':main()
