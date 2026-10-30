"""Apply only the frozen predicate to saved20D L2 trigger snapshots, once."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase20.metrics import rows
from nomad_phase15b.depth import Snapshot
from nomad_phase19r.evaluate import csv_write
from .trigger import obstacle_ahead


def main():
    out=ROOT/'research/results/phase20e_offline';out.mkdir(exist_ok=False)
    source=ROOT/'research/results/phase20d/runs.json';records=json.loads(source.read_text());events=[];hashes={str(source):sha256_file(source)}
    for r in records:
        if r['scene']!='L2' or r['method']!='M3_DETOUR':continue
        log=Path(r['output'])/'detour.jsonl';hashes[str(log)]=sha256_file(log)
        passage=r['spawn_s']+r['box_passage_time_s'] if r.get('passed_box') else None
        for event in rows(log):
            if event['event']!='TRIGGER' or event['trigger']!='B':continue
            file=event['depth_snapshot']['file'];field=Snapshot.load(file);detail=obstacle_ahead(field,event['B'],event['u_ref']);hashes[file]=sha256_file(file)
            stage='AFTER_PASSAGE' if passage is not None and event['simulation_time_s']>=passage else 'BEFORE_PASSAGE'
            events.append(dict(index=r['index'],job_id=event['job_id'],time_s=event['simulation_time_s'],B=event['B'],u_ref=event['u_ref'],stage=stage,
                before_spawn=r['spawn_s'] is None or event['simulation_time_s']<r['spawn_s'],passage_s=passage,snapshot_age_s=event['simulation_time_s']-field.metadata['sim_s'],**detail))
    assert len(events)==23
    result={stage:dict(original=sum(e['stage']==stage for e in events),retained=sum(e['stage']==stage and e['obstacle_ahead'] for e in events)) for stage in ('BEFORE_PASSAGE','AFTER_PASSAGE')}
    result.update(before_spawn_original=sum(e['before_spawn'] for e in events),before_spawn_retained=sum(e['before_spawn'] and e['obstacle_ahead'] for e in events),
        scope='Descriptive filter of saved triggers only; no solve, rollout, inference or navigation; later saved motion is not recomputed',
        protocol_sha256=sha256_file(Path(__file__).with_name('protocol.json')))
    csv_write(out/'triggers.csv',events);(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');(out/'input_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
