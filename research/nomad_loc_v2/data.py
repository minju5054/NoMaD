"""Reuse HMM replay loading/alignment; explicit disjoint calibration/evaluation roots."""
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT
from nomad_hmm_replay.data import load as frozen_load
from nomad_phase42l.analyze import read,sha
HERE=Path(__file__).parent;OUT=ROOT/'research/results/loc_v2_replay';RUN_ROOT=ROOT.parent/'artifacts/isaac6/loc_v2_replay_01'
SOURCES=(
 ('CAL','Phase47-C','research/nomad_phase47c/protocol.json','phase47c_01',('OURS-DETOUR+HMM',)),
 ('CAL','Phase52-P','research/nomad_phase52p/protocol.json','phase52p_01',None),
 ('CAL','Phase53-P','research/nomad_phase53p/protocol.json','phase53p_01',None),
 ('CAL','NIGHT_E1','research/nomad_night20261111/protocol_E1.json','night_queue_20261111_01/E1',None),
 ('CAL','NIGHT_E3','research/nomad_night20261111/protocol_E3.json','night_queue_20261111_01/E3',None),
 ('EVAL','Phase57-P','research/nomad_phase57p/protocol.json','phase57p_01',('MIN','MIN+G18')),
 ('EVAL','Phase58-P','research/nomad_phase58p/protocol.json','phase58p_01',None),
 ('EVAL','Phase59-P','research/nomad_phase59p/protocol.json','phase59p_01',None))

def discover():
    groups={'CAL':[],'EVAL':[]};coverage=[]
    for split,phase,protocol,relative,methods in SOURCES:
        p=read(ROOT/protocol);root=ROOT.parent/'artifacts/isaac6'/relative
        for job in p['main_order']:
            if methods is not None and job['method'] not in methods:continue
            if split=='EVAL':assert job['index'] in (227,228)
            else:assert job['index'] not in (227,228)
            scene=job['scene'];key=f"{scene}_{job['index']:03d}_{job['method']}";metric=root/'metrics'/(key+'.json')
            rec=dict(split=split,phase=phase,key=key,uid=phase+'/'+key,scene=scene.removesuffix('_D075').removesuffix('_D150'),
                condition='D150' if scene.endswith('_D150') else 'D075',seed=job['index'],method=job['method'])
            if not metric.exists():coverage.append(dict(rec,status='NOT_FINALIZED_OR_NOT_RUN'));continue
            row=read(metric);folder=Path(row['output']);required=[folder/f for f in ('scenario.json','summary.json','model/inference.jsonl','agent_trajectory.csv','received.jsonl')]
            if not all(f.exists() for f in required):coverage.append(dict(rec,status='MISSING_INPUT'));continue
            cfg=read(required[0]);manifest=Path(cfg['topomap_manifest'])
            if not cfg.get('phase43p'):coverage.append(dict(rec,status='NOT_HMM'));continue
            if split=='CAL':assert cfg.get('phase59p_transition','HMM0')=='HMM0'
            if not manifest.exists():coverage.append(dict(rec,status='MISSING_TOPOMAP'));continue
            files=[metric,*required,manifest];stop=folder/'declared_arrival.json'
            if stop.exists():files.append(stop)
            item=dict(rec,row=row,folder=str(folder),metric=str(metric),input_sha256={str(f):sha(f) for f in files})
            groups[split].append(item);coverage.append(dict(rec,status='AVAILABLE',technical_validation=row['technical_validation']))
    a={str(Path(x['folder']).resolve()) for x in groups['CAL']};b={str(Path(x['folder']).resolve()) for x in groups['EVAL']}
    assert not a&b,'Calibration/evaluation directory overlap'
    return groups,coverage

def load(item):
    events,n,spacing,stop,missing=frozen_load(item)
    cfg=read(Path(item['folder'])/'scenario.json');nodes=read(cfg['topomap_manifest'])['nodes']
    xy=np.asarray([x['world_pose'][:2] for x in nodes],float)
    assert np.all(np.diff([e['id'] for e in events])>0)
    return events,xy,spacing,stop,missing

def tangents(xy):
    """Fixed geometry convention: central adjacent difference, one-sided ends."""
    xy=np.asarray(xy,float);delta=np.empty_like(xy);delta[0]=xy[1]-xy[0];delta[-1]=xy[-1]-xy[-2]
    delta[1:-1]=xy[2:]-xy[:-2];edges=np.diff(xy,axis=0)
    for i in range(len(xy)):
        if np.linalg.norm(delta[i])<=1e-12:
            valid=[k for k in range(len(edges)) if np.linalg.norm(edges[k])>1e-12]
            if not valid:raise ValueError('No nonzero Topomap tangent')
            k=min(valid,key=lambda k:(abs((k+.5)-i),k));delta[i]=edges[k]
    return delta/np.linalg.norm(delta,axis=1)[:,None]
