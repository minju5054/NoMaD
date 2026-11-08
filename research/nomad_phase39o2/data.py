"""Reference Phase39-O inputs and immutable V0 outputs, without copying paths."""
import json,hashlib
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase33p.storage import load_snapshot
from nomad_phase20d.recent import RecentSnapshot

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase39o2'
OLD=ROOT/'research/results/phase39o';INPUTS=OLD/'preparation/inputs.json'
def read(path):return json.loads(Path(path).read_text())
def cB_bin(value):return '<0' if value<0 else '0<=cB<0.03125' if value<.03125 else '>=0.03125'

def clusters(cases):
    groups={};result={}
    for c in cases:groups.setdefault(c['run'],[]).append(c)
    for run,items in sorted(groups.items()):
        ordered=sorted(items,key=lambda c:(c['job']['simulation_time_s'],c['job'].get('dispatch_ns',0),c['job_id']))
        previous=None;number=-1
        for c in ordered:
            xy=np.asarray(c['job']['B'])[:2]
            distance=float(np.linalg.norm(xy-previous)) if previous is not None else None
            if distance is None or distance>=.01:number+=1
            result[c['case_id']]=dict(group=f'{Path(run).parent.name}/{Path(run).name}/G{number:03d}',
                previous_B_distance_m=distance,group_number=number)
            previous=xy
    return result

def collect_metadata():
    from nomad_phase39o.prepare import verify as verify_old
    verify_old(inputs=True)
    cases=read(INPUTS);hashes={str(INPUTS):sha256_file(INPUTS)};meta=[];group=clusters(cases)
    old_manifest=read(OLD/'result_hashes.json')
    for c in cases:
        path=OLD/'jobs'/f"{c['case_id']}_V0.json";h=sha256_file(path)
        assert h==old_manifest[f"jobs/{path.name}"]
        baseline=read(path);assert baseline['variant']=='V0' and baseline['case_id']==c['case_id']
        field=load_snapshot(RecentSnapshot,c['job']['snapshot_file']);cB=float(field.query(np.asarray(c['job']['B'])[None,:2])[0][0])-field.error_bound
        for result in baseline['numeric']['results']:
            recorded=result.get('cB',result.get('cB_depth_clearance_m'))
            if recorded is not None:np.testing.assert_allclose(cB,recorded,atol=1e-12,rtol=0)
        hashes[str(path)]=h
        meta.append(dict(case_id=c['case_id'],run=c['run'],scene=c['scene'],kind=c['kind'],seed=c['seed'],job_id=c['job_id'],
            cB=cB,cB_bin=cB_bin(cB),baseline_file=str(path),baseline_sha256=h,**group[c['case_id']]))
    return cases,meta,hashes

def runtime_cases():
    metadata={r['case_id']:r for r in read(OUT/'preparation/metadata.json')}
    return [dict(c,o2=metadata[c['case_id']]) for c in read(INPUTS)]
