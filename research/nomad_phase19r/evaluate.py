"""One frozen offline pass: depth-only repairs, then independent oracle evaluation."""
import argparse,csv,json,subprocess,time
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,local_to_world,sha256_file
from nomad_phase0.chunk_report import trace
from nomad_phase15.evaluate import suffix
from nomad_phase15b.depth import Snapshot,evaluate_samples
from nomad_phase16d.diagnose import clearance,point_clearance,classify_A,choose_escape
from nomad_phase18d.rollout import rollout
from .repair import solve_sample,initialize

HERE=ROOT/'research/nomad_phase19r';OUT=ROOT/'research/results/phase19r'
CAUSE_NAMES={'MARGINAL_DEADLOCK':'MARGINAL','TRUE_BLOCK':'TRUE_BLOCK','NEAR_START_POSE':'NEAR_START','OTHER':'OTHER'}

def clean(x):
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,np.ndarray):return clean(x.tolist())
    if isinstance(x,np.generic):return clean(x.item())
    if isinstance(x,float) and not np.isfinite(x):return None
    return x
def dump(path,value):
    with Path(path).open('x') as f:json.dump(clean(value),f,indent=2,allow_nan=False);f.write('\n')
def csv_write(path,records):
    keys=list(dict.fromkeys(k for r in records for k in r))
    with Path(path).open('x',newline='') as f:
        w=csv.DictWriter(f,keys);w.writeheader()
        for r in records:w.writerow({k:json.dumps(clean(v)) if isinstance(v,(dict,list,tuple)) else clean(v) for k,v in r.items()})
def rows(path):return [json.loads(l) for l in Path(path).read_text().splitlines() if l] if Path(path).exists() else []
def stats(values):
    a=[v for v in values if v is not None and np.isfinite(v)]
    return dict(n=len(a),median=float(np.median(a)) if a else None,p95=float(np.quantile(a,.95)) if a else None,max=max(a) if a else None)
def cause(marginal,blocked,near,n=1):return CAUSE_NAMES[classify_A(marginal,blocked,near,n)]

class Inputs:
    def __init__(self):self.hashes={};self.runs={}
    def track(self,file,expected=None):
        p=Path(file).resolve();key=str(p)
        if key not in self.hashes:self.hashes[key]=sha256_file(p)
        if expected:assert self.hashes[key]==expected,p
        return p
    def load(self,path):
        path=Path(path).resolve()
        if str(path) not in self.runs:
            config=json.loads(self.track(path/'scenario.json').read_text())
            events={e['id']:e for e in rows(self.track(path/'events.jsonl'))}
            self.track(path/'agent_trajectory.csv');records,poses=trace(path)
            recovery=rows(self.track(path/'recovery.jsonl')) if (path/'recovery.jsonl').exists() else []
            self.runs[str(path)]=dict(config=config,events=events,trace=records,poses=poses,recovery=recovery)
        return self.runs[str(path)]
    def event(self,split,event_id,run,scene,method,index,identifier,source_split='main'):
        d=self.load(run);e=d['events'][identifier];B=np.array(e['agent_pose_at_switch']);tick=round(e['application_sim_s']*72)
        np.testing.assert_allclose(B,d['poses'][tick],atol=1e-12,rtol=0)
        selected=e['phase16']['selection'];assert selected['all_unsafe']
        meta=selected['snapshot'];assert meta['publication_monotonic_ns']<=e['phase16_selection_ns']
        field=Snapshot.load(self.track(meta['file']));assert field.metadata['sim_s']==meta['sim_s']
        with np.load(self.track(Path(run)/f'model/derived/{identifier:04d}.npz')) as z:metric=z['metric'].copy()
        np.testing.assert_array_equal(metric,e['overnight_metric_samples']);assert metric.shape==(8,8,2)
        native=np.array([local_to_world(x,e['observation_pose']) for x in metric])
        _,detail=evaluate_samples(native,B,field);assert detail['all_unsafe']
        depth=[x['clearance_m'] for x in detail['candidates']];length=[x['remaining_length_m'] for x in detail['candidates']]
        np.testing.assert_allclose(depth,[x['clearance_m'] for x in selected['candidates']],atol=1e-12,rtol=0)
        oracle=[clearance(suffix(x,B)[0],d['config']) for x in native]
        cB=float(field.query(B[None,:2])[0][0])-field.error_bound;best=max(oracle)
        marginal=0<=best<.025;blocked=all(v<0 for v in oracle);near=cB<.025
        escape=choose_escape(depth,length,cB);freshest=min(range(8),key=lambda i:(-length[i],i))
        row=dict(split=split,event_id=event_id,run=Path(run).name,output=str(Path(run).resolve()),scene=scene,method=method,index=index,
            source_split=source_split,fresh_id=identifier,time_s=e['application_sim_s'],tick=tick,B=B.tolist(),
            previous_actual_v_m_s=float(d['trace'][tick]['v_m_s']),previous_actual_w_rad_s=float(d['trace'][tick]['w_rad_s']),
            observation_pose=e['observation_pose'],snapshot_file=meta['file'],snapshot_time_s=meta['sim_s'],
            mode=e['phase16']['fallback_mode'],actual_mode=e.get('phase16_fallback_mode'),
            depth_clearances_m=depth,oracle_clearances_m=oracle,remaining_lengths_m=length,
            B_depth_clearance_m=cB,B_oracle_clearance_m=point_clearance(B,d['config']),
            marginal_event=marginal,true_block_event=blocked,near_start_event=near,cause=cause(int(marginal),int(blocked),int(near)),
            freshest_sample=freshest,STOP_progress_m=0.,STOP_oracle_clearance_m=point_clearance(B,d['config']))
        for name in ('E1','E2'):
            chosen=escape[name];row[name+'_selected']=chosen is not None;row[name+'_sample']=chosen
            row[name+'_oracle_clearance_m']=oracle[chosen] if chosen is not None else None
        start=next((r for r in d['recovery'] if r['event']=='START' and r['id']==identifier),None)
        if start:
            end=next((r for r in d['recovery'] if r['event']=='END' and r['recovery_id']==start['recovery_id']),None)
            fresh=next((r for r in d['recovery'] if r['event']=='FIRST_FRESH' and r['recovery_id']==start['recovery_id']),None)
            row.update(actual_recovery_started=True,actual_recovery_seconds=end['duration_s'] if end else None,
                actual_recovery_first_fresh_safe=fresh['safe_sample_count']>0 if fresh else None)
        else:row['actual_recovery_started']=False
        return dict(row=row,native=native,config=d['config'])

def inventory(inputs):
    devfile=inputs.track(ROOT/'research/results/phase16d/stop_events.csv')
    with devfile.open() as f:dev=list(csv.DictReader(f))
    assert len(dev)==1110 and len({(r['run'],r['id']) for r in dev})==1110
    events=[]
    for i,r in enumerate(dev):
        run=ROOT.parent/'artifacts/isaac6/phase16_multiscene_01'/r['split']/r['run']
        obj=inputs.event('dev',i,run,r['scene'],r['method'],int(r['index']),int(r['id']),r['split'])
        for key in ('oracle_clearances_m','depth_clearances_m'):
            np.testing.assert_allclose(obj['row'][key],json.loads(r[key]),atol=1e-12,rtol=0)
        events.append(obj)
    records=json.loads(inputs.track(ROOT/'research/results/phase18/runs.json').read_text())
    order=json.loads(inputs.track(ROOT/'research/nomad_phase18/protocol.json').read_text())['main_order']
    lookup={(r['scene'],r['index'],r['method']):r for r in records};counter=0;deferred=0
    for spec in order:
        r=lookup[spec['scene'],spec['index'],spec['method']];run=Path(r['output'])
        inputs.track(run/'events.jsonl',r.get('input_sha256',{}).get('events.jsonl'))
        es=rows(run/'events.jsonl')
        for e in es:
            deferred+=bool(e.get('phase17_selection_deferred'))
            if not e.get('phase16',{}).get('selection',{}).get('all_unsafe'):continue
            obj=inputs.event('eval',counter,run,r['scene'],r['method'],r['index'],e['id']);events.append(obj);counter+=1
    assert counter==241 and deferred==89
    groups=defaultdict(list)
    for obj in events:groups[obj['row']['split'],obj['row']['run']].append(obj['row'])
    for rr in groups.values():
        label=cause(sum(r['marginal_event'] for r in rr),sum(r['true_block_event'] for r in rr),sum(r['near_start_event'] for r in rr),len(rr))
        for r in rr:r['run_cause_70_percent']=label
    examples={c:next((o['row']['event_id'] for o in events if o['row']['split']=='eval' and o['row']['cause']==c),None) for c in ('TRUE_BLOCK','MARGINAL')}
    return events,dict(dev_events=1110,eval_events=counter,phase18_deferred_without_selection=deferred,example_event_ids=examples,
        ordering='dev: Phase16D CSV order; eval: frozen Phase18 main_order then actual FRESH order',
        eval_modes=dict(Counter(o['row']['actual_mode'] for o in events if o['row']['split']=='eval')))

def recovery_reference(inputs):
    result=[]
    for phase in (17,18):
        path=inputs.track(ROOT/f'research/results/phase{phase}/runs.json');records=json.loads(path.read_text())
        groups=defaultdict(list)
        for r in records:
            if r.get('technical_validation')=='PASS':groups[r['scene'],r['method']].append(r)
        for (scene,method),rr in groups.items():
            # Reuse the existing independently audited actual recovery summaries.
            started=sum(r.get('recovery_count',0) for r in rr);completed=sum(r.get('recovery_completed',0) for r in rr)
            seen=sum(r.get('recovery_observed_outcomes',0) for r in rr);safe=sum(r.get('recovery_safe_outcomes',0) for r in rr)
            seconds=sum(r.get('recovery_time_s',0.) for r in rr);duration=sum(r['duration_s'] for r in rr)
            result.append(dict(phase=phase,scene=scene,method=method,runs=len(rr),started=started,completed=completed,
                first_fresh_observed=seen,first_fresh_safe=safe,first_fresh_safe_fraction=safe/seen if seen else None,
                actual_rotation_seconds=seconds,rotation_time_fraction=seconds/duration if duration else None,
                scope='Actual main-run reference only; not a matched offline recovery counterfactual'))
    return result

def select_repair(results):
    accepted=[(i,r) for i,r in enumerate(results) if r['accepted']]
    return min(accepted,key=lambda p:(p[1]['mean_edit_m'],p[0]))[0] if accepted else None

def decision(events,repairs):
    ev=[e for e in events if e['split']=='eval'];rr=[r for r in repairs if r['split']=='eval'];accepted=[r for r in rr if r['accepted']]
    chosen=[e for e in ev if e['repair_success']];penetrating=sum(r['oracle_clearance_m']<0 for r in accepted)
    overlaps=sum(e['rollout_overlap'] for e in chosen);rate=overlaps/len(chosen) if chosen else None
    success=len(chosen)/len(ev);edit=stats([e['selected_mean_edit_m'] for e in chosen]);timing=stats([r['attempt_wall_s'] for r in rr if r['solver_started']])
    unsafe=penetrating>0 or (rate is not None and rate>.01)
    if unsafe:label='REPAIR_UNSAFE'
    elif success<.5:label='REPAIR_RARE'
    elif timing['p95']>.20 or edit['median']>.15:label='REPAIR_SLOW'
    else:label='REPAIR_VIABLE'
    return dict(label=label,eval_events=len(ev),repair_successes=len(chosen),repair_success_fraction=success,
        accepted_sample_paths=len(accepted),accepted_oracle_penetrations=penetrating,selected_rollout_overlaps=overlaps,
        selected_path_oracle_penetrations=sum(e['selected_oracle_clearance_m']<0 for e in chosen),
        selected_rollout_count=len(chosen),selected_rollout_overlap_fraction=rate,selected_mean_edit_m=edit,
        sample_solve_time_s=timing,eight_sample_wall_s=stats([e['eight_sample_wall_s'] for e in ev]),
        safety_evidence_available=bool(chosen),no_repair_convention='If no accepted repair: REPAIR_RARE, rollout rate unavailable; never claim safety validated',
        selected_rollout_progress_m=stats([e['rollout_progress_m'] for e in chosen]),
        zero_progress_selections=sum(e['rollout_progress_m']<=1e-9 for e in chosen),
        cause_success={c:dict(events=sum(e['cause']==c for e in ev),successes=sum(e['cause']==c and e['repair_success'] for e in ev),
            fraction=sum(e['cause']==c and e['repair_success'] for e in ev)/sum(e['cause']==c for e in ev) if any(e['cause']==c for e in ev) else None) for c in ('MARGINAL','TRUE_BLOCK','NEAR_START','OTHER')},
        scope='Offline path repair and same-event short rollout; no subsequent NoMaD, depth update or FRESH; closed-loop confirmation required')

def summaries(events,repairs):
    output=[]
    for split in ('dev','eval'):
        for c in ('ALL','MARGINAL','TRUE_BLOCK','NEAR_START','OTHER'):
            ev=[e for e in events if e['split']==split and (c=='ALL' or e['cause']==c)]
            rr=[r for r in repairs if r['split']==split and (c=='ALL' or r['cause']==c)];accepted=[r for r in rr if r['accepted']]
            chosen=[e for e in ev if e['repair_success']]
            output.append(dict(split=split,cause=c,events=len(ev),repair_successes=len(chosen),repair_success_fraction=len(chosen)/len(ev) if ev else None,
                accepted_paths=len(accepted),oracle_penetrations=sum(r['oracle_clearance_m']<0 for r in accepted),
                rollout_overlaps=sum(e['rollout_overlap'] for e in chosen),rollout_count=len(chosen),
                selected_mean_edit_m=stats([e['selected_mean_edit_m'] for e in chosen]),
                per_sample_solve_s=stats([r['attempt_wall_s'] for r in rr if r['solver_started']]),
                eight_sample_wall_s=stats([e['eight_sample_wall_s'] for e in ev]),
                selected_rollout_progress_m=stats([e['rollout_progress_m'] for e in chosen]),
                zero_progress_selections=sum(e['rollout_progress_m']<=1e-9 for e in chosen),
                no_eligible_events=sum(e['eligible_samples']==0 for e in ev),
                fixed_B_infeasible_samples=sum(bool(r.get('fixed_B_safety_impossible')) for r in rr),
                freshest_only_successes=sum(e['freshest_only_success'] for e in ev),
                E1_selected=sum(e['E1_selected'] for e in ev),E1_penetrating=sum(e['E1_selected'] and e['E1_oracle_clearance_m']<0 for e in ev),
                E2_selected=sum(e['E2_selected'] for e in ev),E2_penetrating=sum(e['E2_selected'] and e['E2_oracle_clearance_m']<0 for e in ev),
                dispositions=dict(Counter(r['disposition'] for r in rr))))
    return output

def run(out):
    assert not out.exists(),'Preserve every offline attempt; no restart or overwrite'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).strip(),'Commit the fixed code/protocol before execution'
    protocol=json.loads((HERE/'protocol.json').read_text());inputs=Inputs()
    for file,h in protocol['protected_sha256'].items():inputs.track(ROOT/file,h)
    for file in HERE.glob('*.py'):inputs.track(file)
    inputs.track(HERE/'protocol.json');sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    out.mkdir(parents=True);dump(out/'protocol.json',protocol)
    inventory_events,inventory_meta=inventory(inputs);recovery=recovery_reference(inputs)
    dump(out/'inventory.json',inventory_meta);dump(out/'input_manifest_before_repairs.json',dict(git_sha=sha,sha256=inputs.hashes))
    print(f"[inventory] dev={inventory_meta['dev_events']} eval={inventory_meta['eval_events']}; fixed examples={inventory_meta['example_event_ids']}",flush=True)
    events=[];repairs=[];example_data={}
    with (out/'repair_journal.jsonl').open('x') as journal:
        for number,obj in enumerate(inventory_events):
            e=dict(obj['row']);native=obj['native'];B=np.array(e['B']);field=Snapshot.load(e['snapshot_file'])
            started=time.perf_counter();results=[solve_sample(sample,B,field) for sample in native];e['eight_sample_wall_s']=time.perf_counter()-started
            selected=select_repair(results);e.update(repair_success=selected is not None,selected_sample=selected,
                freshest_only_success=results[e['freshest_sample']]['accepted'],freshest_only_disposition=results[e['freshest_sample']]['disposition'],
                eligible_samples=sum(r['solver_started'] for r in results))
            for i,r in enumerate(results):
                record={**{k:e[k] for k in ('split','event_id','run','scene','method','index','fresh_id','cause')},'sample':i,**r}
                if r['path'] is not None:
                    record['oracle_clearance_m']=clearance(np.array(r['path']),obj['config'])
                    record['unknown_fraction']=field.unknown_fraction(np.array(r['path']))
                else:record['oracle_clearance_m']=None
                journal.write(json.dumps(clean(record),allow_nan=False)+'\n');journal.flush()
                repairs.append({k:v for k,v in record.items() if k not in ('path','reference')})
            reference=results[e['freshest_sample']]
            if reference['path'] is not None:
                e.update(freshest_only_mean_edit_m=reference['mean_edit_m'],freshest_only_depth_clearance_m=reference['depth_clearance_m'],
                    freshest_only_oracle_clearance_m=clearance(np.array(reference['path']),obj['config']))
            roll=None
            if selected is not None:
                r=results[selected];oracle=clearance(np.array(r['path']),obj['config'])
                roll=rollout(B,r['path'],e['previous_actual_v_m_s'],'SP',obj['config'])
                e.update(selected_mean_edit_m=r['mean_edit_m'],selected_max_edit_m=r['max_edit_m'],selected_depth_clearance_m=r['depth_clearance_m'],selected_oracle_clearance_m=oracle,
                    rollout_minimum_clearance_m=roll['minimum_clearance_m'],rollout_overlap=roll['overlap'],rollout_negative_witness=roll['geometric_negative_witness'],
                    rollout_progress_m=roll['distance_m'],rollout_mean_speed_m_s=roll['average_speed_m_s'],rollout_duration_s=roll['duration_s'],rollout_termination=roll['termination'])
            events.append(e)
            if e['split']=='eval' and e['event_id'] in inventory_meta['example_event_ids'].values():
                example_data[str(e['event_id'])]=dict(event=e,native=native.tolist(),repairs=results,selected=selected,config=obj['config'],
                    rollout=roll['poses'].tolist() if roll else None)
            if (number+1)%50==0:print(f'[repair] {number+1}/{len(inventory_events)} events preserved',flush=True)
    summary=summaries(events,repairs);verdict=decision(events,repairs)
    csv_write(out/'events_dev.csv',[e for e in events if e['split']=='dev']);csv_write(out/'events_eval.csv',[e for e in events if e['split']=='eval'])
    csv_write(out/'repairs.csv',repairs);csv_write(out/'summary.csv',summary);csv_write(out/'recovery_reference.csv',recovery)
    dump(out/'decision.json',verdict);dump(out/'examples.json',example_data)
    from .report import render
    render(out,summary,verdict,recovery,example_data,repairs,protocol,sha)
    for file,h in inputs.hashes.items():assert sha256_file(file)==h,file
    dump(out/'complete.json',dict(git_sha=sha,events=len(events),sample_records=len(repairs),solver_attempts=sum(r['solver_started'] for r in repairs),
        label=verdict['label'],input_hashes_unchanged=True,Isaac_navigation=0,NoMaD_inference=0,Isaac_render=0))
    print(json.dumps(dict(label=verdict['label'],repair_success=verdict['repair_success_fraction'],penetrating=verdict['accepted_oracle_penetrations'],rollout_overlap=verdict['selected_rollout_overlap_fraction'])),flush=True)

def publish(out):
    assert (out/'complete.json').exists()
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    paths=['research/nomad_phase19r',str(out.relative_to(ROOT)),'docs/PHASE19R_REPAIR.md']
    ignore=out/'.gitignore'
    if ignore.exists():assert ignore.read_text()=='/repair_journal.jsonl\n'
    else:ignore.write_text('/repair_journal.jsonl\n')
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    png=list(out.glob('*.png'))
    if png:subprocess.run(['git','add','-f','--',*[str(p.relative_to(ROOT)) for p in png]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase19R depth-only path repair offline validation'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

def report_saved(out):
    assert (out/'complete.json').exists()
    def parse(v):
        if v=='':return None
        if v in ('True','False'):return v=='True'
        try:return json.loads(v)
        except (ValueError,TypeError):return v
    def read_csv(name):
        with (out/name).open() as f:return [{k:parse(v) for k,v in r.items()} for r in csv.DictReader(f)]
    from .report import render
    sha=json.loads((out/'complete.json').read_text())['git_sha']
    render(out,read_csv('summary.csv'),json.loads((out/'decision.json').read_text()),read_csv('recovery_reference.csv'),
        json.loads((out/'examples.json').read_text()),read_csv('repairs.csv'),json.loads((out/'protocol.json').read_text()),sha,replace_presentation=True)
    dump(out/'presentation.json',dict(numerical_execution_sha=sha,report_source_sha256=sha256_file(HERE/'report.py'),
        changes='Label example methods; full-support density histogram; distinguish selected path safety from rollout safety',additional_solves=0,additional_rollouts=0))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');ap.add_argument('--report-only',action='store_true');a=ap.parse_args()
    if a.report_only:report_saved(OUT)
    elif OUT.exists():assert (OUT/'complete.json').exists(),'Partial attempt preserved; no automatic restart'
    else:run(OUT)
    if a.publish:publish(OUT)

if __name__=='__main__':main()
