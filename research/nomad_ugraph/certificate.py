"""Independent frozen EC-tail on Graph XY, not a new obstacle check."""
import numpy as np
from nomad_phase52ec.rollout import certify

class StationaryEndpoint:
    """Circle footprint invariant: an exactly stationary XY path is already at endpoint."""
    trigger_S=False
    def control(self,pose,actual_v):return (0.,0.),dict(completed=True)

def validate(case,result,field):
    x=np.asarray(result['states']);xy=x[:,:2];stationary=float(np.max(np.linalg.norm(xy-xy[0],axis=1)))<=1e-9
    kwargs={}
    if stationary:
        if abs(case['v'])>1e-9 or np.max(abs(x[:,3]))>1e-8:return dict(passed=False,reason='DEGENERATE_XY_WITH_NONZERO_SPEED')
        kwargs['controller']=StationaryEndpoint()
    try:
        r=certify(case['pose'],[case['v'],case['omega']],xy,field,return_trace=True,**kwargs)
        r['model']='FROZEN_C0_NA_PP_SP_XY_BRAKING_TAIL' if not stationary else 'STATIONARY_CIRCULAR_FOOTPRINT_ENDPOINT'
        r['graph_velocity_used']=False
        if 'trace' in r:r['trace']={k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in r['trace'].items()}
        return r
    except (ValueError,FloatingPointError) as exc:return dict(passed=False,reason='EC_INVALID_INPUT',error=str(exc),graph_velocity_used=False)
