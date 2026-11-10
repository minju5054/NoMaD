import argparse,json,subprocess
from pathlib import Path
import numpy as np
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,CONDITIONS,BASE_SCENES,verify,split

NUMERIC=('goal_time_s','mean_speed_m_s','stopped_s','initial_wait_s','minimum_clearance_m','tracking_error_p50_m','tracking_error_p95_m',
    'chunk_heading_jump_p50_deg','chunk_heading_jump_p95_deg','raw_candidate_distance_mean_m','stop_distance_m','ec_rejects',
    'graph_solve_p50_s','graph_solve_p95_s','graph_acceptance_rate','hold_after_rejection_s')

def generate(root=RUN_ROOT,output=OUT,document=None):
    p=verify();root=Path(root);output=Path(output);runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    keys=[(r['scene'],r['index'],r['method']) for r in runs];expected={(j['scene'],j['index'],j['method']) for j in p['main_order']}
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    baseline=json.loads((OUT/'preparation/baselines.json').read_text());allrows=runs+baseline;stats=[]
    for group,subset in [('Phase52',runs),*[(g,[b for b in baseline if b['historical_group']==g]) for g in ('Phase47_D075','Phase51_L150','Phase51_WIDE')]]:
        for condition,method in sorted({(r.get('condition','D075'),r['method']) for r in subset}):
            for scene in (*BASE_SCENES,'ALL'):
                rr=[r for r in subset if (r.get('condition','D075'),r['method'])==(condition,method) and (scene=='ALL' or r.get('base_scene',r['scene'])==scene)]
                good=[r for r in rr if r['technical_validation']=='PASS']
                if not rr:continue
                stats.append(dict(group=group,condition=condition,method=method,scene=scene,n=len(rr),valid=len(good),
                    success=sum(r['success'] for r in good),timeout=sum(r['timeout_without_declaration'] for r in good),collision=sum(r['collision'] for r in good),
                    wrong_stop=sum(r['wrong_stop'] for r in good),box_passage=sum(r['box_passage'] for r in good),box_passage_from_spawn_median_s=median([r['box_passage_from_spawn_s'] for r in good if r.get('box_passage_from_spawn_s') is not None]),
                    **{k+'_median':median([r[k] for r in good if r.get(k) is not None]) for k in NUMERIC}))
    by={(r['scene'],r['index'],r['method']):r for r in runs};pairs=[];states=[];box=[];graphs=[]
    for j in p['main_order']:
        scene,condition=split(j['scene']);r=by.get((j['scene'],j['index'],j['method']));row=dict(condition=condition,scene=scene,seed=j['index'],method=j['method'],status=r['technical_validation'] if r else 'NOT_RUN')
        for k in ('success','collision','timeout_without_declaration','wrong_stop','box_passage','box_passage_from_spawn_s',*NUMERIC):row[k]=r.get(k) if r and r['technical_validation']=='PASS' else None
        for group in ('Phase47_D075','Phase51_L150','Phase51_WIDE'):
            b=next(x for x in baseline if x['historical_group']==group and x.get('base_scene',x['scene'])==scene and x['index']==j['index'])
            for k in ('success','collision','goal_time_s','stopped_s','tracking_error_p95_m','box_passage','box_passage_from_spawn_s','wrong_stop'):
                row[group+'_'+k]=b.get(k)
        pairs.append(row)
    for r in allrows:
        key=dict(group=r.get('historical_group','Phase52'),condition=r.get('condition','D075'),scene=r.get('base_scene',r['scene']),seed=r['index'],method=r['method'])
        states.extend(dict(**key,state=k,seconds=v) for k,v in r.get('command_state_seconds',{}).items())
        box.extend(dict(**key,**b) for b in r.get('spawn_path_observations',[]))
        if not r.get('historical_group'):graphs.append(dict(**key,**{k:v for k,v in r.items() if k.startswith('graph_') or k.startswith('hold_after_')}))
    state=dict(status='COMPLETE' if len(runs)==40 else 'PARTIAL',completed=len(runs),planned=40,protocol_sha256=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest(),
        audit_revision_sha256=__import__('hashlib').sha256((HERE/'audit_revision.json').read_bytes()).hexdigest())
    output.mkdir(parents=True,exist_ok=True);save(output/'runs.json',runs);save(output/'analysis.json',state)
    for name,data in [('summary',stats),('paired',pairs),('command_states',states),('spawn_path_observations',box),('graph',graphs)]:csvout(output/(name+'.csv'),data)
    defs=[dict(item=k,value=v) for k,v in p['report_definitions'].items()]
    defs.append(dict(item='startup audit correction',value='Only pre-first-chunk missing WAYPOINT_TIMEOUT is allowed; any new_timeout or WAYPOINT_TIMEOUT after first chunk remains a technical failure. initial_wait_s ends at first control with chunk; latch time also recorded. Original frozen protocol unchanged.'))
    startup=[dict(scene=r['scene'],seed=r['index'],method=r['method'],**{k:r.get(k) for k in
        ('initial_wait_s','first_chunk_received_s','first_chunk_control_s','startup_missing_timeout_rows','new_timeout_count','post_chunk_waypoint_timeout_rows','selected_attempt')}) for r in runs]
    csvout(output/'initial_wait.csv',startup)
    doc=Path(document) if document else ROOT/'docs/PHASE52P_RESULTS.md';doc.write_text('\n\n'.join(table(d or [dict(n=0)]) for d in ([state],defs,stats,pairs,startup,states,box,graphs))+'\n');return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args();assert a.run_root.resolve()==RUN_ROOT.resolve();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase52-P CUT-HOLD and reconstruction comparison','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
