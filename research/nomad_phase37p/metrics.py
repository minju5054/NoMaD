"""Read frozen outcomes; add trigger oracle labels only after a run ends."""
import json
from pathlib import Path
from collections import Counter
from nomad_phase35.metrics import audit as frozen_audit
from nomad_phase32.report import lines
from nomad_phase37.evaluate import load_run
from nomad_phase37.geometry import classify

def audit(root):
    root=Path(root);r=frozen_audit(root);cfg=json.loads((root/'scenario.json').read_text());r['method']=cfg['phase37p_method']
    _,_,poses,reference,static,boxes=load_run(dict(output=str(root)))
    events=[]
    for event in lines(root/'detour.jsonl'):
        if event['event']!='TRIGGER':continue
        tick=round(event['simulation_time_s']*72)
        label,objects=classify(event['B'],event['u_ref'],event['simulation_time_s'],static,boxes)
        events.append(dict(job_id=event['job_id'],trigger=event['trigger'],time_s=event['simulation_time_s'],tick=tick,
            pose=event['B'],u_ref=event['u_ref'],oracle_class=label,oracle_objects=objects))
    r.update(trigger_events=events,trigger_counts=dict(Counter(e['trigger'] for e in events)),
             trigger_oracle_counts={t:dict(Counter(e['oracle_class'] for e in events if e['trigger']==t)) for t in ('A','B')})
    if r['method']=='OURS+PROV':
        updates=lines(root/'depth/updates.jsonl');assert updates and all(e.get('prov_schema_version')==1 for e in updates)
        r['provenance_updates']=len(updates);r['provenance_final_confirmed_cells']=updates[-1]['prov_confirmed_free_cells']
    else:r['provenance_updates']=0;r['provenance_final_confirmed_cells']=None
    return r
