"""New fixed box center; reuse H1-v2 geometry predicates and one-shot monitor."""
import copy
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_h1v2 import scene as frozen
from nomad_phase38.scenes import gap_check

HERE=Path(__file__).parent
SIZE=frozen.SIZE
CORNER=np.array([2.4,.9])

def center_choice(points):
    requested,requested_s=frozen.target(points,.70)
    half=np.array(SIZE[:2])/2
    corner_overlap=bool(np.all(CORNER>=requested-half-1e-10) and np.all(CORNER<=requested+half+1e-10))
    selected,s=frozen.target(points,.65) if corner_overlap else (requested,requested_s)
    return selected,s,dict(requested_y_m=.70,requested_center_xy_m=requested.tolist(),corner_xy_m=CORNER.tolist(),
        corner_overlap=corner_overlap,adjustments=int(corner_overlap),selected_y_m=.65 if corner_overlap else .70,
        reason='INNER_CORNER_OVERLAP_SINGLE_0.65_ADJUSTMENT' if corner_overlap else 'NO_ADJUSTMENT')

def build_spec():
    old=frozen.load_spec();c=old['frozen_geometry'];points=old['topomap_nodes_xy_m']
    center,s,choice=center_choice(points)
    box=dict(id='DynamicObstacle',center_xy_m=center.tolist(),size_xyz_m=list(SIZE),yaw_rad=0.,arc_m=s)
    front_s,front=frozen.box_front(points,center);spawn_s=front_s-1.
    assert spawn_s>=0
    spawn,i=frozen.at(points,spawn_s);delta=np.array(points[i+1])-points[i]
    overlaps=frozen.overlap_reasons(c,center)
    gap=gap_check(c,box,1);right=gap.get('gaps_m',[0.,0.])[1]
    check=dict(no_wall_static_overlap=not overlaps,right_gap_at_least_028=bool(right>=.28),
               phase38_gap=bool(gap['passed']),spawn_arc_nonnegative=spawn_s>=0)
    p=copy.deepcopy(old)
    p.update(scene='H1-v3',status='GEOMETRY_PREPARED' if all(check.values()) else 'GEOMETRY_CHECK_FAIL',
        box=box,requested_target=choice,position_adjusted_for_overlap=bool(choice['adjustments']),
        static_overlap_reasons=overlaps,static_checks=check,
        previous_h1v2_preview=dict(box=old['box'],scene_sha256=sha256_file(frozen.HERE/'scene.json')),
        nearest_position_rule='Only y=.70; exactly one y=.65 adjustment if InnerCorner(2.4,.9) intersects; no other search or relocation',
        box_front=dict(position_xy_m=front.tolist(),arc_m=front_s,definition=old['box_front']['definition']),
        spawn=dict(position_xy_m=spawn.tolist(),heading_rad=float(np.arctan2(delta[1],delta[0])),arc_m=spawn_s,lead_arc_m=1.,rule=old['spawn']['rule']),
        gap_check=dict(gap,left_m=gap['gaps_m'][0],right_m=right,left_definition='-x (looking along +y)',right_definition='+x (looking along +y)'),
        return_gap_check=frozen.return_gap_check(c,box),simulations=0,renders=0)
    p['source_sha256'].update({str(f.relative_to(ROOT)):sha256_file(f) for f in (frozen.HERE/'scene.py',frozen.HERE/'scene.json')})
    return p

def load_spec():
    p=json.loads((HERE/'scene.json').read_text())
    for f,h in p['source_sha256'].items():assert sha256_file(ROOT/f)==h,f
    return p

def configure(h1v2):
    assert h1v2['scene_variant']=='H1-v2'
    p=load_spec();assert p['status']=='GEOMETRY_PREPARED',p['static_checks']
    assert {k:h1v2[k] for k in p['frozen_geometry']}==p['frozen_geometry']
    assert sha256_file(h1v2['topomap_manifest'])==p['topomap_sha256']
    c=copy.deepcopy(h1v2);c['scene_variant']='H1-v3'
    # The frozen H1-v2 monitor is data-driven: same event and collision code,
    # with this variant's immutable center/front/spawn-arc metadata only.
    c['h1v2']=p
    c['dynamic_obstacle']=dict(c['dynamic_obstacle'],center_xy_m=p['box']['center_xy_m'])
    return c

install_environment=frozen.install_environment
triggered=frozen.triggered
place=frozen.place
