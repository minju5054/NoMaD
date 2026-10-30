"""History replay from archived grids, never rerenders or invokes a solver."""
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase20.metrics import rows
from nomad_phase0.chunk_report import trace
from nomad_phase20d.recent import RecentSnapshot
from nomad_phase19r.evaluate import csv_write
from .history import CellHistory
from .trigger import choose_ahead
from .config import protocol


def main():
    p=protocol();assert p['status']=='FROZEN' and p['offline']['scope']=='ACTUAL_TRIGGERS'
    out=ROOT/'research/results/phase20f_offline';out.mkdir(exist_ok=False);source=ROOT/'research/results/phase20e/runs.json';records=json.loads(source.read_text());result=[];hashes={str(source):sha256_file(source)}
    for r in records:
        if r['method']!='M3_DETOUR':continue
        run=Path(r['output']);updates=rows(run/'depth/updates.jsonl');triggers=[e for e in rows(run/'detour.jsonl') if e['event']=='TRIGGER' and e['trigger']=='B']
        _,poses=trace(run);history=None;cache={};wanted={e['depth_snapshot']['frame_id'] for e in triggers};by_frame={};passage=r['spawn_s']+r['box_passage_time_s'] if r.get('passed_box') else None
        for f in (run/'depth/updates.jsonl',run/'detour.jsonl',run/'agent_trajectory.csv'):hashes[str(f)]=sha256_file(f)
        for u in updates:
            field=RecentSnapshot.load(u['file']);hashes[u['file']]=sha256_file(u['file'])
            if history is None:history=CellHistory(field.values.shape)
            history.update(field.last_free_tick,field.occupied,round(u['sim_s']*72))
            if u['frame_id'] not in wanted:continue
            augmented=SimpleNamespace(**field.__dict__,first_free_tick=history.first_free_tick,first_occupied_tick=history.first_occupied_tick,new_component_ids=history.new_component_ids,component_births=history.births)
            for event in [e for e in triggers if e['depth_snapshot']['frame_id']==u['frame_id']]:
                tick=event['evaluation_tick'];chosen,info=choose_ahead(augmented,poses,tick,cache)
                progress=float((poses[tick,:2]-poses[tick-216,:2])@np.array(chosen['u_ref'])) if chosen and tick>=216 else None
                keep=chosen is not None and progress is not None and progress<.20
                result.append(dict(index=r['index'],job_id=event['job_id'],tick=tick,time_s=tick/72,B=poses[tick].tolist(),stage='AFTER_PASSAGE' if passage is not None and tick/72>=passage else 'BEFORE_PASSAGE',
                    goal_near=bool(poses[tick,0]>6.5),retained=keep,component=chosen,progress_m=progress,snapshot_age_s=tick/72-u['sim_s'],reason='NEW_TRIGGER' if keep else 'NO_NEW_OBSTACLE_AHEAD' if chosen is None else 'PROGRESS',**info))
        print(f"[history] seed{r['index']} {len(triggers)} original triggers",flush=True)
    assert len(result)==30
    result.sort(key=lambda r:(r['index'],r['tick']));csv_write(out/'triggers.csv',result)
    summary={stage:dict(original=sum(r['stage']==stage for r in result),retained=sum(r['stage']==stage and r['retained'] for r in result)) for stage in ('BEFORE_PASSAGE','AFTER_PASSAGE')}
    summary.update(goal_near_original=sum(r['goal_near'] for r in result),goal_near_retained=sum(r['goal_near'] and r['retained'] for r in result),
        scope='Only actual20E M3 NO_PROGRESS trigger instants; direction/progress and new-cell predicate re-evaluated; no future counterfactual motion or newly arising trigger is inferred',protocol_sha256=sha256_file(Path(__file__).with_name('protocol.json')))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(out/'input_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
