"""Narrow diagnostic options; legacy Phase 2 constraints remain unchanged."""
import json
import re
from pathlib import Path
from nomad_isaac.common import ROOT, sha256_file

HERE = Path(__file__).parent

def protocol():
    return json.loads((HERE/'protocol.json').read_text())

def validate_options(args):
    p=protocol()
    assert args.phase2_method=='M0' and args.asynchronous and args.pure_pursuit and args.topomap
    assert args.diagnostic_condition in ('C1','C2','C3')
    assert not any((args.prepare_only,args.s1_mode,args.s1_v2_mode,args.oracle_safety_stop,
                   args.early_obstacle_mode,args.controlled_delivery_delay,args.render_topomap_reference))
    assert args.s1_distance_m is None and args.uniform_delivery_delay_s==0.
    assert sha256_file(args.scenario)==p['scenario_sha256']
    assert sha256_file(args.topomap)==p['topomap_sha256']
    assert re.fullmatch(r'DIAG_C[123]_0[123]',args.run_id or '')
    assert args.run_id.split('_')[1]==args.diagnostic_condition
    assert args.seed_offset==int(args.run_id[-2:])*10000
    assert args.phase2_distance_m in ((.8,1.2) if args.diagnostic_condition=='C1' else (1.,))

class MaskSchedule:
    """Diagnostic oracle mode choice, after next-frame publication; no path correction."""
    def __init__(self,condition):
        self.condition=condition;self.finished=False
    def decide(self,gate,box,snapshot):
        available=bool(gate and gate['geometry_available'] and box is not None)
        if self.condition=='C3' and available and snapshot['pose'][0]>box['center_xy_m'][0]+box['size_xyz_m'][0]/2+.30:
            self.finished=True
        mask=int(self.condition=='C3' and available and not self.finished)
        return {'goal_mask':mask,'mode':'exploration' if mask else 'goal_conditioned',
                'diagnostic_oracle_switch':self.condition=='C3','geometry_public':available,
                'exploration_finished':self.finished,'decision_pose':snapshot['pose'],
                'decision_tick':snapshot['tick'],'decision_monotonic_ns':snapshot['monotonic_ns']}

def ratio_band(value):
    if value is None:return 'NO_OBSERVATIONS'
    return 'RARE' if value<.10 else 'INDETERMINATE' if value<.30 else 'SUFFICIENT'
