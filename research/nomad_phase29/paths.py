"""Phase22 P3 geometry on a normal FRESH suffix; Phase18 depth certificate."""
import numpy as np
from nomad_phase22.refine import resample
from nomad_phase15.evaluate import suffix

def certificate(path,field):
    clearance=float(field.exact_clearance(np.asarray(path)))
    return dict(passed=clearance>=.025-1e-8,depth_site_clearance_m=clearance,oracle_used=False)

def smooth(path,B,field):
    p0,length=suffix(path,B)
    if length<=1e-12:return np.asarray(path),dict(applied=False,reason='EMPTY_SUFFIX',attempts=[])
    original=resample(p0)
    curve=np.vstack([p0[:1],np.stack([.75*p0[:-1]+.25*p0[1:],.25*p0[:-1]+.75*p0[1:]],axis=1).reshape(-1,2),p0[-1:]])
    rounded=resample(curve);attempts=[]
    for retry in range(4):
        strength=.5/(2**retry);candidate=(1-strength)*original+strength*rounded
        candidate[0]=np.asarray(B)[:2];candidate[-1]=p0[-1]
        c=certificate(candidate,field);attempts.append(dict(strength=strength,**c))
        if c['passed']:return candidate,dict(applied=True,reason='ACCEPTED',attempts=attempts)
    return np.asarray(path),dict(applied=False,reason='CERTIFICATE_FAILED',attempts=attempts)
