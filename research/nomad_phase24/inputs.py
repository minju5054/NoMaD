"""Inventory and scheduling estimate before fixing the offline decision mapping."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase23o3.diagnose import input_stage

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase24_offline';SOURCE=ROOT/'research/results/phase23o3'
def read(file):return json.loads(Path(file).read_text())
def write(file,value):Path(file).parent.mkdir(parents=True,exist_ok=True);Path(file).write_text(json.dumps(value,indent=2)+'\n')
def inventory():
    m=read(SOURCE/'manifest.json');original=read(ROOT/'research/nomad_phase23/protocol.json');grid=[dict(time=t,goal=g,curvature=k) for t in original['grid']['time'] for g in original['grid']['goal'] for k in original['grid']['curvature']];ukey=f'U{grid.index(original["selected"]):02d}'
    cases=[];hashes={};counts=Counter();frame_count=0;update_samples=[]
    for c in m['training']:
        file=SOURCE/'comparators'/(c['case_id']+'.json');data=read(file);c0=data['methods']['C0']['plan'];attempted=any(s['kind']=='R3' for s in c0.get('stages',[]))
        ufile=ROOT/'research/results/phase23o/training'/(c['case_id']+'.json');hashes[str(file)]=sha256_file(file);hashes[str(ufile)]=sha256_file(ufile);hashes[c['snapshot_file']]=sha256_file(c['snapshot_file'])
        stage='STATIC' if c['group']=='static' else input_stage(c);counts[stage]+=1
        cases.append(dict(c,input_stage=stage,c0_record=str(file),u_record=str(ufile),u_selected_key=ukey,c0_disposition=c0['disposition'],c0_attempted_R3=attempted))
    for run in sorted({c['run'] for c in cases}):
        updates=[json.loads(s) for s in (Path(run)/'depth/updates.jsonl').read_text().splitlines()]
        maximum=max(c['tick']/72 for c in cases if c['run']==run);frame_count+=sum(r['sim_s']<=maximum for r in updates)
        if 'phase20f_' in run:update_samples.extend(r['update_ms']+r.get('snapshot_copy_ms',0.) for r in updates)
    # Allow replay of every run, even if only detour cases eventually need it.
    per_frame=2*float(np.quantile(update_samples,.95))/1000 if update_samples else .15
    post=read(ROOT/'research/results/phase23o2/preparation.json')['estimate']['per_rollout_allowance_s']
    components=dict(G_planning_s=242*.5,rollout_oracle_s=242*post,history_replay_s=frame_count*per_frame,io_report_s=180.)
    seconds=1.25*sum(components.values());estimate=dict(minutes=seconds/60,over_one_hour=seconds>3600,components=components,depth_frames=frame_count,per_frame_s=per_frame,
        basis='500ms per G solve; stored postprocessing allowance; twice measured20Fmap-update p95 for every source frame;180s IO/report;25% allowance. Comparators/U reused, no new inference/render.')
    result=dict(cases=cases,input_hashes=hashes,counts=dict(counts),c0_modes_if_attempted_R3_rule=dict(NORMAL=sum(not c['c0_attempted_R3'] for c in cases),DETOUR=sum(c['c0_attempted_R3'] for c in cases)),estimate=estimate,definitions_pending=True)
    write(OUT/'inventory.json',result);print(json.dumps({k:result[k] for k in ('counts','c0_modes_if_attempted_R3_rule','estimate','definitions_pending')}));return result
if __name__=='__main__':inventory()
