"""Tables only; no confirmatory label or scene/method changes after runs."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,verify

def generate(root=RUN_ROOT,output=OUT,document=None):
    p=verify();root=Path(root);output=Path(output)
    rows=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    expected={(j['scene'],j['index'],j['method']) for j in p['main_order']}
    keys=[(r['scene'],r['index'],r['method']) for r in rows];assert len(set(keys))==len(keys) and set(keys)<=expected
    summary=[]
    for condition in SCENES:
        group=[r for r in rows if r['scene']==condition];valid=[r for r in group if r['technical_validation']=='PASS']
        summary.append(dict(condition=condition,n=len(group),valid=len(valid),technical_failure=len(group)-len(valid),
            success_0p5=sum(r['success'] for r in valid),collision=sum(r['collision'] for r in valid),person_collision=sum(r['person_collision'] for r in valid),
            wrong_stop=sum(r['wrong_stop'] for r in valid),person_spawned=sum(r['person_spawned'] for r in valid),
            min_person_center_distance_m=median([r['minimum_person_center_distance_m'] for r in valid if r.get('minimum_person_center_distance_m') is not None]),
            min_person_surface_clearance_m=median([r['minimum_person_clearance_m'] for r in valid if r.get('minimum_person_clearance_m') is not None]),
            stopped_median_s=median([r['stopped_s'] for r in valid]),slow_moving_median_s=median([r['slow_moving_s'] for r in valid]),
            decelerating_median_s=median([r['decelerating_s'] for r in valid]),ec_slow_cap_median_s=median([r['ec_slow_cap_s'] for r in valid])))
    details=[];contacts=[];ghosts=[];removals=[]
    for r in rows:
        key=dict(condition=r['scene'],seed=r['index'])
        details.append(dict(**key,**{k:r.get(k) for k in ('technical_validation','success','collision','person_collision','wrong_stop','stop_distance_m',
            'minimum_person_center_distance_m','minimum_person_clearance_m','goal_time_s','stopped_s','slow_moving_s','decelerating_s','ec_slow_cap_s',
            'ec_reject_stopped_s','ec_checks','ec_rejects','person_spawned','spawn_reference_remaining_m','post_removal_5s_available','ghost_last_offset_s')}))
        contacts.extend(dict(**key,**e) for e in r.get('ec_before_contact_2s',[]))
        ghosts.extend(dict(**key,**e) for e in r.get('ghost_by_second',[]))
        removals.append(dict(**key,removed=r.get('person_removal') is not None,**(r.get('person_removal') or {})))
    state=dict(status='COMPLETE' if len(rows)==12 else 'PARTIAL',completed=len(rows),planned=12,
        protocol_sha256=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest())
    definitions=[dict(item=k,definition=v) for k,v in p['measurement_definitions'].items()]
    output.mkdir(parents=True,exist_ok=True);save(output/'runs.json',rows);save(output/'analysis.json',state)
    for name,data in [('summary',summary),('runs_table',details),('ec_before_collision_2s',contacts),('removals',removals),('ghost_after_removal',ghosts)]:csvout(output/(name+'.csv'),data)
    doc=Path(document) if document else ROOT/'docs/PHASE50P_RESULTS.md'
    doc.write_text('\n\n'.join(table(d or [dict(n=0)]) for d in ([state],definitions,summary,details,removals,ghosts,contacts))+'\n');return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    assert a.run_root.resolve()==RUN_ROOT.resolve();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase50-P moving-cylinder pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

if __name__=='__main__':main()
