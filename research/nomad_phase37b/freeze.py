import json,time,subprocess
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase32o.evaluate import save

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase37b'
def main():
    assert not (HERE/'protocol.json').exists()
    sources=list(HERE.glob('*.py'))+[ROOT/'research'/s for s in ('nomad_phase24r/trigger.py','nomad_phase20f/history.py',
        'nomad_phase20f/direction.py','nomad_phase20d/recent.py','nomad_phase20c/shadow.py','nomad_phase15/occupancy.py',
        'nomad_phase37/evaluate.py','nomad_phase37/geometry.py','nomad_phase37/audit.py','nomad_phase37/protocol.json')]
    sources += [ROOT/'research/results/phase37/triggers.csv',ROOT/'research/results/phase37/preparation/cohort.json']
    sources += list((OUT/'evidence').glob('*.npz'))
    p=dict(status='FROZEN_OFFLINE',phase='37-B',created_unix=time.time(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        cohort='Phase37 exactly4915 common eligible9Hz opportunities, 30 runs',
        PROV='Original new-component mask AND previously published observed=True and occupied=False on a ray-clearing frame before original first occupied',
        interpretation='Final post-shadow published state; first_free_tick alone already proves ray clearing but not post-shadow observed=True',
        witness='last_free_tick == saved capture frame_tick AND observed AND NOT occupied AND frame_tick < first_occupied_tick',
        negative_log_odds_requirement=False,
        unchanged=['component connectivity/minimum5 cells','component identity/t_new/u_ref','1.0x0.4m rectangle','no-progress predicate',
            'selection order','passed rule','recorded eligibility/busy/cooldown','A/R2/R3/EC','maintenance/handover','oracle classification'],
        no_10s_direction_guard=True,
        missing_history='Unmeasured, never assume invalid. Confirmed-only replay descriptive; possible selected components and distance-drop bounds provide conservative gate bounds.',
        gate=dict(retain_original_BOX_AHEAD_fraction=.95,nonbox_fraction_max=.5,nonbox=['STATIC_AHEAD','PASSED_BOX','NOTHING_AHEAD'],
            same_time_opportunity=True,pass_rule='recall lower>=.95 AND nonbox upper<=.5 original',
            fail_rule='recall upper<.95 OR nonbox lower>.5 original',otherwise='PROV_NOT_ESTABLISHED_MISSING_HISTORY'),
        simulation=False,navigation_preparation=False,oracle_usage='analysis only',
        source_hashes={str(f.relative_to(ROOT)):sha256_file(f) for f in sources})
    save(HERE/'protocol.json',p);print(sha256_file(HERE/'protocol.json'))
if __name__=='__main__':main()
