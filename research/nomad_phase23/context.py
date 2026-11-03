"""Read-only timing references for secondary metrics; no new observations."""
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase0.chunk_report import trace
from nomad_phase15b.depth import Snapshot
from nomad_phase22.drive_geometry import rotation
from nomad_phase20.execution import SPAlignment

OUT=ROOT/'research/results/phase23o'
def prepare():
    m=json.loads((OUT/'manifest.json').read_text());cases=m['training']+m['evaluation'];contexts={};hashes={}
    for run in sorted({c['run'] for c in cases}):
        cc=[c for c in cases if c['run']==run];p=Path(run)
        commands_file=p/'phase20_commands.jsonl';commands=[]
        if commands_file.exists():
            commands=[json.loads(x) for x in commands_file.read_text().splitlines()];hashes[str(commands_file)]=sha256_file(commands_file)
        for c in cc:
            path=c.get('baseline_old_path',c.get('old_path'));state=dict(mode='GO',source='OLD already installed; no new alignment trigger')
            prior=[r for r in commands if r['tick']<c['tick'] and r.get('SP')]
            if prior and path is not None:
                latest=prior[-1];mode=latest['SP']['mode']
                if mode in ('BRAKE','ROTATE'):
                    start=next(r for r in prior if r.get('path_source_id')==latest.get('path_source_id'))
                    ctl=SPAlignment();ctl.replace_path(path,start['pose'],start['before_vw'][0])
                    if ctl.target_yaw is not None:state=dict(mode=mode,target_yaw=ctl.target_yaw,source='Saved prior SP mode and original path-application heading target',source_tick=latest['tick'])
            contexts[c['case_id']]=dict(executing_path=path,executing_state=state)
        if cc[0]['group']!='sudden':continue
        rr,poses=trace(p);ns=np.array([int(r['monotonic_ns']) for r in rr],dtype=np.int64);t=np.array([float(r['simulation_time_s']) for r in rr]);s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(poses[:,:2],axis=0),axis=1))]
        file=p/'depth/updates.jsonl';updates=[json.loads(x) for x in file.read_text().splitlines()];hashes[str(file)]=sha256_file(file)
        spawn=cc[0].get('spawn');first=None
        if spawn:
            box=spawn['obstacle'];R=rotation(box);half=np.asarray(box['size_xyz_m'][:2])/2
            for u in updates:
                if u['sim_s']<spawn['simulation_time_s'] or u['publication_monotonic_ns']>ns[-1]:continue
                field=Snapshot.load(u['file']);iy,ix=np.nonzero(field.occupied);points=field.origin+np.c_[ix,iy]*field.h
                local=(points-box['center_xy_m'])@R
                if np.any(np.all(np.abs(local)<=half+.015,axis=1)):
                    pub=u['publication_monotonic_ns'];first=dict(first_map_available_s=float(np.interp(pub,ns,t)),first_map_publication_ns=pub,snapshot_file=u['file'],snapshot_sha256=sha256_file(u['file']),frame_id=u['frame_id']);break
        for c in cc:
            reference=dict(first or {},distance_to_snapshot_m=0.)
            if first:reference['distance_to_snapshot_m']=max(0.,float(s[c['tick']]-np.interp(first['first_map_publication_ns'],ns,s)))
            contexts[c['case_id']]['reaction_reference']=reference
    result=dict(contexts=contexts,input_hashes=hashes,source_manifest_sha256=sha256_file(OUT/'manifest.json'),
        detection='Evaluation-only: first published occupied-cell map intersecting actual box in box-local coordinates with15mm cell/noise tolerance, after spawn and during recorded run; publication time mapped through saved pose timestamps.',
        reaction='First sampled output whose future suffix has no box overlap and reaches a side outside the box support plus radius+25mm while progressing in+x. Short stop paths do not qualify. Sparse-snapshot onset is an upper bound/censored measurement; no online reaction claim.')
    file=OUT/'input_context_050.json';file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(contexts=len(contexts),sudden_references=sum('reaction_reference' in c for c in contexts.values()),new_inference=0,new_render=0)))
    return result
if __name__=='__main__':prepare()
