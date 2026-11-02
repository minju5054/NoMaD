"""Reproduce the scheduling estimate from already measured timings; no solves."""
import argparse
import numpy as np
from .run import read,write
from .report import OUT

def estimate(probe):
    summary=read(probe/'summary.json');m=read(OUT/'manifest.json');measurement=read(probe/'throughput.json')
    original=summary.get('initial_estimate',summary['estimate']);components=original['components'].copy()
    n_u=len(m['training'])*8+len(m['evaluation']);n_baseline=len(m['evaluation'])+sum(c['group']=='sudden' for c in m['evaluation'])
    u_ticks=n_u*(int(np.ceil(3/.05*72))+2);baseline_ticks=strict_ticks=0
    for c in m['evaluation']:
        copies=2 if c['group']=='sudden' else 1
        length=float(np.linalg.norm(np.diff(np.asarray(c['samples_world']),axis=1),axis=2).sum(axis=1).max())
        baseline_ticks+=copies*(int(np.ceil(72*(max(2.,length)/.05+np.pi/.4+.6+2)))+2)
        strict_ticks+=copies*(int(np.ceil(72*((length+2*7*.75*np.sqrt(2))/.05+np.pi/.4+.6+2)))+2)
    per_tick=measurement['oracle_s_per_tick']+measurement['rollout_s_per_tick']
    components['postprocessing_s']=(u_ticks+baseline_ticks)*per_tick+(n_u+n_baseline)*max(r['EXACT_CLEARANCE'] for r in summary['rows'])
    seconds=1.25*sum(components.values());strict=seconds+1.25*(strict_ticks-baseline_ticks)*per_tick
    return dict(seconds=seconds,hours=seconds/3600,over_2h=seconds>7200,components=components,strict_R2_trustbox_upper_hours=strict/3600,
        limitation='Conservative scheduling extrapolation, not a guarantee: U3m bound, baseline full2m R3 or larger native path plus alignment, measured oracle/rollout throughput,25% allowance; strict R2 trust-box bound separately shown.')

if __name__=='__main__':
    from pathlib import Path
    import json
    ap=argparse.ArgumentParser();ap.add_argument('--probe',type=Path,required=True);a=ap.parse_args();print(json.dumps(estimate(a.probe)))
