"""New analysis-only EC: endpoint/2s brake request, frozen stop_command to rest."""
import copy
import numpy as np
from nomad_phase28.alignment import NoAlignment
from nomad_phase32.policy import CappedNA
from nomad_phase16.execution import stop_command
from nomad_isaac.common import integrate_se2
from nomad_phase32o.exec_cert import swept_clearance,rollout as frozen_rollout
from nomad_phase32.policy import continuation_certificate

HZ=72;CONTROL=8;HORIZON=144;MAX_TICKS=216

def rollout(pose,vw,path,speed_cap=None,controller=None,start_tick=0):
    assert speed_cap in (None,.1)
    q=np.asarray(pose,float).copy();v,w=map(float,vw)
    assert -.0000001<=v<=.3000001 and abs(w)<=.4000001
    continuation=controller is not None
    if continuation:ctl=copy.deepcopy(controller);phase=int(start_tick)%8
    else:ctl=CappedNA();ctl.replace_path(path,q,v);ctl.speed_cap=speed_cap;phase=0
    poses=[q.copy()];commands=[];braking=False;reason=None;request=None;brake_tick=None;endpoint=False
    for step in range(MAX_TICKS+1):
        if step>=HORIZON and not braking:
            braking=True;reason='HORIZON';request=step
        if (phase+step)%CONTROL==0:
            if not braking:
                (nv,nw),diag=ctl.control(q,v)
                if diag['completed']:
                    braking=True;endpoint=True;reason='ENDPOINT';request=step
                else:v,w=float(nv),float(nw)
            if braking:
                if brake_tick is None:brake_tick=step
                v,w=stop_command(v)
                if v<=1e-12:
                    return dict(poses=np.asarray(poses),commands=np.asarray(commands).reshape(-1,2),duration_s=step/HZ,
                        stop_reason=reason,endpoint_reached=endpoint,brake_request_s=request/HZ,brake_start_s=brake_tick/HZ,
                        control_rounding_ticks=brake_tick-request,braking_s=(step-brake_tick)/HZ,terminal_vw=[0.,0.],
                        stopped=True,continuation=continuation,alignment=bool(ctl.trigger_S))
        if step==MAX_TICKS:break
        q=integrate_se2(q,v,w,1/HZ);poses.append(q.copy());commands.append([v,w])
    raise RuntimeError('Brake rollout failed to stop within analytical .3/.5 + control-grid bound')

def certify(pose,vw,path,field,speed_cap=None,controller=None,start_tick=0,return_trace=False):
    trace=rollout(pose,vw,path,speed_cap,controller,start_tick);cert=swept_clearance(field,trace['poses'],trace['commands'])
    result={k:v for k,v in trace.items() if k not in ('poses','commands')};result.update(cert)
    if return_trace:result['trace']=trace
    return result

def original(check,path,field,controller=None):
    if check.get('continuation'):
        if controller is None:raise ValueError('Missing continuation controller state')
        return continuation_certificate(controller,check['pose'],check['actual_vw'],field,check['check_tick'])
    trace=frozen_rollout(check['pose'],check['actual_vw'],path,check.get('speed_cap_m_s'))
    return dict(swept_clearance(field,trace['poses'],trace['commands']),duration_s=trace['duration_s'],endpoint_reached=trace['endpoint_reached'])
