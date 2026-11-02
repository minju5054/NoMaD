"""Scheduling-only estimate; never changes the selected evaluation manifest."""
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT
from .inputs import evenly

OUT=ROOT/'research/results/phase23o'
def estimate():
    m=json.loads((OUT/'manifest.json').read_text());probe=json.loads((OUT/'execution_checks/TS0000_serial_01/summary.json').read_text())
    measured=probe['throughput_measurement'];per_tick=measured['oracle_s_per_tick']+measured['rollout_s_per_tick'];old=probe['estimate']['components']
    phase18={r['output']:r for r in json.loads((ROOT/'research/results/phase18/runs.json').read_text())}
    proposals=[];new_static=0
    for run in sorted({c['run'] for c in m['evaluation'] if c['group']=='static'}):
        r=phase18[run];events=[json.loads(x) for x in (Path(run)/'events.jsonl').read_text().splitlines()]
        events=[e for e in events if 'application_sim_s' in e and 'overnight_metric_samples' in e and 'topomap' in e]
        chosen=evenly(events,5)
        if not r['success']:
            tail=[(i,e) for i,e in enumerate(events) if e['application_sim_s']>=r['duration_s']-10]
            chosen=sorted(set(chosen+[tail[i][0] for i in evenly([e for _,e in tail],5)]))
        new_static+=len(chosen);proposals.append(dict(run=run,count=len(chosen),fresh_ids=[events[i]['id'] for i in chosen]))
    old_static=sum(c['group']=='static' for c in m['evaluation']);sudden=len(m['evaluation'])-old_static;training=len(m['training'])*8
    def compute(static):
        nu=training+static+sudden;nb=static+2*sudden
        overhead=max(0.,max(r['solve_wall_s'] for r in probe['rows'])-.25)
        # Full3m U horizon plus the newly required36integration ticks.
        uticks=nu*(int(np.ceil(3/.05*72))+2+36)
        # Same previous conservative baseline2m/alignment allowance, plus2s
        # STOP_WAIT upper allowance if the original drive waiting model is used.
        bticks=nb*(int(np.ceil(72*(2/.05+np.pi/.4+.6+2)))+2+144)
        components=dict(U_planning_s=nu*(.5+overhead),baseline_planning_allowance_s=nb*2.2,
            postprocessing_s=(uticks+bticks)*per_tick+(nu+nb)*max(r['EXACT_CLEARANCE'] for r in probe['rows']),
            timestamp_replay_s=old['timestamp_replay_s'],report_io_allowance_s=120.)
        total=1.25*sum(components.values())
        return dict(training_snapshots=len(m['training']),grid_combinations=8,evaluation_static=static,evaluation_sudden=sudden,seconds=total,hours=total/3600,over_2h=total>7200,components=components)
    result=dict(full=compute(old_static),proposed_static5=compute(new_static),proposal_selected=False,proposed_case_selection=proposals,
        assumptions='Previous measured oracle/synthetic-rollout throughput;500ms U budget plus prior load overhead;3m U horizon+0.5s OLD prefix; conservative2m/alignment comparator horizon+up to2s wait; unchanged timestamp replay runs;25% scheduling allowance. No new solves or selected-matrix changes.')
    (OUT/'amendment_050_estimate.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    r=estimate();print(json.dumps({k:r[k] for k in ('full','proposed_static5','proposal_selected')}))
