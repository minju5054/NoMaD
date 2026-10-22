"""Read-only Phase2 aggregation; never launches a run or changes an artifact."""
import argparse
from collections import Counter,defaultdict
import csv,json
from pathlib import Path
import numpy as np
from nomad_isaac.common import write_json,sha256_file
from nomad_phase0.s0_batch_metrics import wilson


def boot(values):
    if not values:return {'n':0,'mean':None,'ci95':[None,None]}
    a=np.array(values,dtype=float);rng=np.random.default_rng(20261022)
    draws=a[rng.integers(len(a),size=(10000,len(a)))].mean(axis=1)
    return {'n':len(a),'mean':float(a.mean()),'ci95':np.percentile(draws,[2.5,97.5]).tolist()}

def csvwrite(path,data):
    if not data:return
    fields=list(dict.fromkeys(k for r in data for k in r))
    with path.open('x') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
        for r in data:w.writerow({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()})

def paired_table(records,family):
    groups=defaultdict(dict)
    for r in records:
        if r['stage'] in (('s2a','s2b') if family=='main16' else ('s2c0','s2c1')):
            groups[(r['d_m'],r['D_s'],r['index'])][r['method']]=r
    pairs=[];cases=[]
    for (d,D,i),group in sorted(groups.items()):
        statuses={m:group[m]['classification'] if m in group else 'NOT_RUN' for m in ('M0','M3','M5')}
        values={m:statuses[m]=='SUCCESS' for m in statuses}
        incomplete=any(statuses[m] in ('NOT_RUN','TECHNICAL_FAILURE','PLACEMENT_INVALID') for m in statuses)
        harms=values['M0'] and not(values['M3'] and values['M5']) and not incomplete
        graph_case=not values['M3'] and values['M5'] and not incomplete
        selection_case=not values['M0'] and values['M3'] and not incomplete
        label=('INCOMPLETE' if incomplete else 'ALL_SUCCESS' if all(values.values()) else
               'M0_SUCCESS_INTERVENTION_HARM' if harms else 'M0_FAIL_M3_SUCCESS' if selection_case else
               'M3_FAIL_M5_SUCCESS' if graph_case else 'ALL_FAIL' if not any(values.values()) else 'OTHER')
        no_witness={m:all(r.get('feasibility',{}).get('first_visible_B',{}).get(b,{}).get('status')=='NO_PATH_FOUND' for b in ('B0','B1')) for m,r in group.items()}
        row={'family':family,'d_m':d,'D_s':D,'index':i,'seed_offset':i*10000,'category':label,**statuses,
             'M3_minus_M0':int(values['M3'])-int(values['M0']) if not incomplete else None,
             'M5_minus_M3':int(values['M5'])-int(values['M3']) if not incomplete else None,
             'graph_associated_candidate':graph_case,'intervention_harm':harms,'both_no_witness_by_method':no_witness,
             'not_impossibility_proof':True}
        pairs.append(row)
        if graph_case or harms:
            details={}
            for m,r in group.items():
                run=Path(r['output']); events=[json.loads(l) for l in (run/'events.jsonl').read_text().splitlines() if l]
                interventions=[e for e in events if e['phase2']['selected_sample']!=0 or e['phase2']['graph_applied']]
                summary=[]
                for e in interventions:
                    with np.load(run/f"model/derived/{e['id']:04d}.npz") as data:
                        from nomad_isaac.common import local_to_world
                        native=local_to_world(data['metric'][e['phase2']['selected_sample']],np.array(e['observation_pose']))
                        raw0=local_to_world(data['metric'][0],np.array(e['observation_pose']))
                    actual=np.array(e['phase2']['world_xy_m'])
                    summary.append({'id':e['id'],'selected_sample':e['phase2']['selected_sample'],'graph_applied':e['phase2']['graph_applied'],
                        'switch_s':e['application_sim_s'],'B':e['agent_pose_at_switch'],
                        'correction_rms_m':float(np.sqrt(np.mean(np.sum((actual-native)**2,axis=1)))),
                        'difference_from_sample0_rms_m':float(np.sqrt(np.mean(np.sum((actual-raw0)**2,axis=1)))),
                        'world_xy_m':actual.tolist(),'applied_vw':[e['applied_v_m_s'],e['applied_w_rad_s']]})
                details[m]={'classification':r['classification'],'spawn':r.get('spawn'),'interventions':summary,
                    'graph':r.get('graph'),'executed_trace':str(run/'agent_trajectory.csv'),
                    'trace_sha256':sha256_file(run/'agent_trajectory.csv')}
            cases.append({'pair':row,'actual_runs':details,'scope':'Different closed-loop RGB/placement possible; association, not necessity proof'})
    return pairs,cases

def aggregate(root,out):
    out.mkdir(exist_ok=False)
    records=[json.loads(p.read_text()) for p in sorted((root/'metrics').glob('*.json'))]
    amendments={p.stem:json.loads(p.read_text()) for p in (root/'audit_amendments').glob('*.json')}
    records=[amendments.get(r['key'],r) for r in records]
    grouped=defaultdict(list)
    for r in records:
        stage='pilot' if r['stage']=='s0' else 'baseline' if r['stage']=='s1' else 'main' if r['stage'] in ('s2a','s2b') else 'hard_selected'
        grouped[(stage,r['d_m'],r['D_s'],r['method'])].append(r)
    conditions=[]
    for (stage,d,D,m),rr in sorted(grouped.items(),key=str):
        valid=[r for r in rr if r['classification'] not in ('TECHNICAL_FAILURE','PLACEMENT_INVALID')]
        row={'stage':stage,'d_m':d,'D_s':D,'method':m,'attempts':len(rr),'valid_n':len(valid),
             'outcomes':dict(Counter(r['classification'] for r in rr)),
             'success':wilson([r.get('success',False) for r in valid]),
             'collision':wilson([r.get('geometric_overlap',False) for r in valid]),
             'timeout':wilson([r.get('timeout',False) for r in valid]),
             'corridor_intrusion':wilson([r.get('corridor_intrusion',False) for r in valid]),
             'margin_violating_runs':sum(r.get('margin_violation_s',0)>0 for r in valid),
             'strict_margin_goal_successes':sum(r.get('success',False) and r.get('margin_violation_s',0)==0 for r in valid),
             'continuous':{k:boot([r[k] for r in valid if r.get(k) is not None]) for k in
                 ('goal_time_s','stop_s','minimum_clearance_m','margin_violation_s','distance_m','y_std_m','max_abs_y_m')},
             'exploratory_only':True}
        conditions.append(row)
    pairs,cases=paired_table(records,'main16');hardpairs,hardcases=paired_table(records,'hard_subset')
    diff={}
    for family,data in (('main16',pairs),('hard_selected',hardpairs)):
        g=defaultdict(list)
        for r in data:g[(r['d_m'],r['D_s'])].append(r)
        diff[family]=[{ 'd_m':d,'D_s':D,**{k:boot([r[k] for r in rr if r[k] is not None]) for k in ('M3_minus_M0','M5_minus_M3')}} for (d,D),rr in g.items()]
    delay_fail={str(D):any(r['stage']=='s1' and r['D_s']==D and r['classification']!='SUCCESS' for r in records) for D in (.25,.5)}
    result={'scope':'Exploratory N4; Oracle geometry; SE2 kinematic Isaac Sim, no causal/necessity proof',
        'attempts':len(records),'conditions':conditions,'paired_differences':diff,
        'main16_categories':{k:sum(r['category']==k for r in pairs) for k in
            ('ALL_SUCCESS','M0_FAIL_M3_SUCCESS','M3_FAIL_M5_SUCCESS','ALL_FAIL','M0_SUCCESS_INTERVENTION_HARM','INCOMPLETE','OTHER')},
        'hard_selected_categories':dict(Counter(r['category'] for r in hardpairs)),
        'baseline_delay_failure':delay_fail,'graph_associated_cases':sum(r['graph_associated_candidate'] for r in pairs+hardpairs),
        'harm_cases':sum(r['intervention_harm'] for r in pairs+hardpairs),
        'both_no_witness_method_runs':sum(sum(r['both_no_witness_by_method'].values()) for r in pairs+hardpairs),
        'both_no_witness_is_not_impossibility':True,
        'graph_counts':{k:sum(r.get('graph',{}).get(k,0) for r in records) for k in ('calls','returned','accepted','applied','nonconverged','initialization_rejected','stale')},
        'branch':json.loads((root/'branch.json').read_text()) if (root/'branch.json').exists() else None,
        'pilot_excluded_from_performance_inference':True,'full_record_hashes':{p.name:sha256_file(p) for p in (root/'metrics').glob('*.json')}}
    write_json(out/'summary.json',result);write_json(out/'individual_cases.json',cases+hardcases)
    csvwrite(out/'conditions.csv',conditions);csvwrite(out/'paired_main16.csv',pairs);csvwrite(out/'paired_hard.csv',hardpairs)
    csvwrite(out/'runs.csv',[{k:r.get(k) for k in ('key','stage','index','seed_offset','execution_git_sha','D_s','d_m','method',
        'classification','geometric_overlap','corridor_intrusion','conservative_contact_stop','termination_reason',
        'duration_s','goal_time_s','minimum_clearance_m','margin_violation_s','stop_s','distance_m','passage',
        'y_std_m','max_abs_y_m','sample0_unsafe_count','selection_replacement_count','actual_replacement_count',
        'ALL_UNSAFE_count','graph','switch_abs_dw','curvature_saturated_control_count','controller_count',
        'waypoint_timeouts','requests','switches','first_fresh','feasibility','packet_release_s','warm_inference_ms','validation')} for r in records])
    print(json.dumps({k:result[k] for k in ('attempts','main16_categories','hard_selected_categories','graph_associated_cases','harm_cases')}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();aggregate(a.root,a.output)
