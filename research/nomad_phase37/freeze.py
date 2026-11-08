"""Freeze the user-resolved offline measurement rules before computation."""
import json,subprocess,time
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase32o.evaluate import save

HERE=Path(__file__).parent
def main():
    assert not (HERE/'protocol.json').exists()
    sources=list(HERE.glob('*.py'))
    sources += [ROOT/'research'/name for name in ('nomad_phase24r/trigger.py','nomad_phase20f/direction.py','nomad_phase20f/history.py',
        'nomad_phase20c/trigger.py','nomad_phase20c/detour_known.py','nomad_isaac/topomap.py','nomad_phase0/pure_pursuit.py')]
    sources += [ROOT/'research/results/phase32/runs.json',ROOT/'research/results/phase35/runs.json']
    p=dict(status='FROZEN_OFFLINE',phase='37',frozen_unix=time.time(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_hashes={str(f.relative_to(ROOT)):sha256_file(f) for f in sources},
        data=dict(runs=30,Phase32='all15 C0-NA+EC main runs',Phase35='all15 OURS main runs',map_policy='common saved maps only; no older-map replacement',
            trigger_unit='same eligible9Hz logged decision opportunity; logged busy/alignment/recovery/repair/cooldown schedule held common',
            map_priority='actual condition snapshot if recorded, otherwise same-control-tick snapshot'),
        TRIG=dict(length_m=1.,width_m=.4,min_cells=5,mask='observed & occupied',new_cell_required=False,
            t_ref='first observed occupied entry in forward rectangle; known first_occupied tick backdated only if cell already in the base forward rectangle at birth; otherwise first common available entry',
            association='4-connected observed occupied sets associate earliest t_ref/distance; 5-cell threshold on full rectangle, no extra component minimum',
            baseline_direction='displacement over [t_ref-3s,t_ref], <0.3m uses t_ref heading; unavailable uses original A direction',
            guard='angle of baseline u_ref (3s displacement or heading fallback) vs10s displacement both ending at t_ref >90deg AND10s distance>=0.3m ->10s; otherwise baseline',
            no_progress='current3s projected motion<0.20m OR current component fixed-cell minimum-distance drop<0.10m',
            untouched=['A','R2','R3','EC','fallback','maintenance/handover','executor','depth map']),
        oracle_labels=['BOX_AHEAD','STATIC_AHEAD','PASSED_BOX','NOTHING_AHEAD'],
        oracle_geometry='same rule u_ref rectangle1.0x0.4m, physical polygons, active spawns only; existing recorded passage is not undone on return',
        reference='Topomap photographed world poses joined as a polyline; nearest-projection tangent',
        TRIG_gate=dict(box_recall='TRIG fires at >=95% of same-tick original-fired BOX_AHEAD opportunities',
            false_positive='TRIG(PASSED_BOX+NOTHING_AHEAD)<=0.5*original count',
            direction='TRIG fraction angle>90deg <=0.5*original fraction; STATIC_AHEAD excluded from all gates',
            missing_denominator='not established, never OFFLINE_OK'),
        TOPO_H=dict(radius=4,close_threshold=3,backward_queries=3,initial_H=0,initial_c=0,
            update='r>=H: H=r,c=0; r<H: c+=1; at c>=3 H=r,c=0',
            subgoal='min(H+int(dist[H]<3),goal_node); if H>=goal_node-1 use goal_node',
            robot_pose='RGB query observation_pose',behind='subgoal reference s < robot reference s -0.2m',
            ahead='subgoal index > nearest physical Topomap node index +2',
            missing_scores='no imputation/inference; conservative reachable-state/subgoal bounds',
            gate='failure behind upper<=0.5 original; success behind and ahead upper increases<=0.02'),
        next_stage='Only if TRIG OFFLINE_OK; add TOPO-H only if TOPO_OK, otherwise TRIG alone',
        requested_online=dict(methods=['OURS','conditional selected TRIG variant'],scenes=['SLW','LC','L2','H1','H2'],seeds=[215,216],
            order_seed=20261110,planned=20,run_root='../artifacts/isaac6/phase37p_01',decision='PROMISING iff variant goals>OURS AND collisions<=OURS'),
        simulation_started=False)
    save(HERE/'protocol.json',p);print(sha256_file(HERE/'protocol.json'))
if __name__=='__main__':main()
