"""Online entry point for the registered Phase52 braking-tail numerical rule."""
import time
from nomad_phase52ec.rollout import certify as braking_certificate
from nomad_phase28.telemetry import builtin

def certify_tail(pose,vw,path,field,speed_cap=None,controller=None,start_tick=0):
    start=time.perf_counter()
    result=braking_certificate(pose,vw,path,field,speed_cap,controller,start_tick)
    return builtin(dict(result,compute_s=time.perf_counter()-start,model='C0_NA_BRAKING_TAIL'))
