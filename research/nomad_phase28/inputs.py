"""Inventory saved C0 SAFE FRESH events without sampling, solving, or replay."""
import json
from collections import Counter
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file

def inventory(all_methods=False):
    source=ROOT/'research/results/phase27r/runs.json';runs=json.loads(source.read_text());cases=[];hashes={str(source):sha256_file(source)}
    for run in runs:
        if (not all_methods and run['method']!='C0') or run['technical_validation']!='PASS':continue
        folder=Path(run['output']);fresh_file=folder/'events.jsonl';path_file=folder/'repair.jsonl'
        fresh={e['id']:e for line in fresh_file.read_text().splitlines() if (e:=json.loads(line)).get('application_sim_s') is not None}
        applications=[e for line in path_file.read_text().splitlines() if (e:=json.loads(line))['event']=='PATH_APPLIED']
        hashes[str(fresh_file)]=sha256_file(fresh_file);hashes[str(path_file)]=sha256_file(path_file)
        for i,a in enumerate(applications):
            if a['kind']!='SAFE':continue
            e=fresh[a['id']];snapshot=e['phase16']['selection']['snapshot'];file=Path(snapshot['file'])
            assert abs(a['simulation_time_s']-e['application_sim_s'])<1e-8
            cases.append(dict(scene=run['scene'],index=run['index'],source_method=run['method'],output=str(folder),native_id=a['id'],application_index=i,
                tick=a['tick'],time_s=a['simulation_time_s'],B=a['pose'],previous_vw=a['previous_vw'],selected_path=a['path_world'],
                selected_sample=e['phase16']['selection']['selected_sample'],snapshot=snapshot,snapshot_available=file.exists(),application_monotonic_ns=e['application_monotonic_ns']))
    result=dict(status='INVENTORY_ONLY_NOT_SAMPLED',eligible_events=len(cases),available_snapshots=sum(c['snapshot_available'] for c in cases),
        by_scene=dict(Counter(c['scene'] for c in cases)),cases=cases,input_sha256=hashes,
        pending='Inventory only; sampling and solves use the separate frozen offline entry point')
    out=ROOT/'research/results/phase28/preparation';out.mkdir(parents=True,exist_ok=True)
    (out/'input_inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    r=inventory();print(json.dumps({k:r[k] for k in ('status','eligible_events','available_snapshots','by_scene')}))
