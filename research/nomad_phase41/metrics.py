"""Frozen collision/technical audit; preregistered declared-arrival outcomes."""
import json
from pathlib import Path
import numpy as np
from nomad_phase38.metrics import audit as frozen_audit


def outcomes(declared,distance,collision,termination):
    return dict(declared_arrival=bool(declared),
        success=bool(declared and distance<=.5 and not collision),
        success_0p3=bool(declared and distance<=.3 and not collision),
        success_1p0=bool(declared and distance<=1. and not collision),
        wrong_stop=bool(declared and distance>.5),
        timeout_without_declaration=bool(not declared and termination in ('simulation_timeout','navigation_wall_timeout')))


def audit(root):
    root=Path(root);r=frozen_audit(root)
    summary=json.loads((root/'summary.json').read_text());cfg=summary['scenario']
    assert cfg['nomad_goal_stop'] is True
    path=root/'declared_arrival.json';declared=path.exists()
    assert declared==(summary['termination_reason']=='declared_arrival')
    stop=json.loads(path.read_text()) if declared else None
    if declared:
        assert stop['closest_node']==stop['goal_node'] and stop['stop_command']==[0.,0.]
        np.testing.assert_array_equal(stop['pose'],summary['final_pose'])
        assert abs(stop['simulation_time_s']-summary['simulation_duration_s'])<1e-10
        distance=float(np.linalg.norm(np.asarray(stop['pose'])[:2]-np.asarray(cfg['goal_pose'])[:2]))
    else:distance=float(summary['final_goal_distance_m'])
    r.update(outcomes(declared,distance,r['collision'],r['termination']))
    r.update(method=cfg['phase38_method'],stop_distance_m=distance if declared else None,
             final_goal_distance_m=float(summary['final_goal_distance_m']),stop_time_s=stop['simulation_time_s'] if declared else None,
             stop_inference_id=stop['id'] if declared else None,goal_time_s=stop['simulation_time_s'] if r['success'] else None)
    r['classification']='SUCCESS' if r['success'] else 'COLLISION' if r['collision'] else 'WRONG_STOP' if r['wrong_stop'] else 'TIMEOUT' if r['timeout_without_declaration'] else 'OTHER'
    return r
