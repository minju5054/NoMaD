"""Frozen Phase53 outcome/audit; extra saved-install selection counters only."""
import json
from pathlib import Path
import numpy as np
from nomad_phase53p.metrics import audit as frozen_audit
from nomad_phase24r.online_metrics import rows

def choice_metrics(installs):
    previous_side=None;switches=backward=robot_backward=0;records=[]
    for e in installs:
        B=np.asarray(e['pose']);end=np.asarray(e['original_candidate_world'])[-1];ref=e.get('reference_endpoint_before')
        ref_delta=np.asarray(ref)-B[:2] if ref is not None else np.array([np.cos(B[2]),np.sin(B[2])]);delta=end-B[:2]
        ref_yaw=float(np.arctan2(ref_delta[1],ref_delta[0])) if np.linalg.norm(ref_delta)>1e-12 else float(B[2])
        yaw=float(np.arctan2(delta[1],delta[0])) if np.linalg.norm(delta)>1e-12 else float(B[2])
        angle=float(np.arctan2(np.sin(yaw-ref_yaw),np.cos(yaw-ref_yaw)));robot=float(np.arctan2(np.sin(yaw-B[2]),np.cos(yaw-B[2])))
        side='LEFT' if robot>1e-12 else 'RIGHT' if robot<-1e-12 else 'CENTER'
        if side!='CENTER':
            switches+=int(previous_side is not None and side!=previous_side);previous_side=side
        backward+=int(abs(angle)>np.pi/2);robot_backward+=int(abs(robot)>np.pi/2)
        records.append(dict(tick=e['tick'],id=e['id'],reference_angle_deg=float(np.rad2deg(angle)),robot_angle_deg=float(np.rad2deg(robot)),side=side))
    return dict(left_right_switches=switches,backward_reference_selections=backward,backward_robot_selections=robot_backward,selection_count=len(installs),selection_records=records)

def audit(root):
    root=Path(root);r=frozen_audit(root);c=json.loads((root/'scenario.json').read_text());assert c['phase58p']
    method=c['phase58p_method'];installs=[e for e in rows(root/'graph_ho.jsonl') if e['event']=='INSTALL']
    for e in installs:assert e['endpoint_latch'] and e['selection_method']==method
    commands=rows(root/'phase20_commands.jsonl');latch=None
    for e in commands:
        now=e['time_s']
        if latch is not None and any(latch<x['simulation_time_s']<=now for x in installs):latch=None
        if latch is not None:assert e['source'] not in ('NORMAL','KEEP_ACTIVE'),(latch,now,e['source'])
        if e['source']=='ENDPOINT':latch=now
    r.update(choice_metrics(installs));r.update(method=method,base_scene=c['phase58p_level'],scene=c['phase58p_level'])
    return r
