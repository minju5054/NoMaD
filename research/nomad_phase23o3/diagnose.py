"""Read-only pre-passage audit and five frozen-U3 additional-seed diagnostics."""
import argparse,hashlib,json,time,types,multiprocessing as mp
from pathlib import Path
import numpy as np
from scipy.ndimage import label
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase15b.depth import Snapshot
from nomad_phase15.evaluate import suffix
from nomad_phase23.graph import resample,side_initializations,wrap
from nomad_phase23.optimized import vectorized_menger
from nomad_phase23.runtime import managed_pool
from nomad_phase23.anytime import select_messages
from nomad_phase20d.pool import initialize,ping
from nomad_phase23o2.graph import mixture,FIXED_WEIGHTS
from nomad_phase23o2.report import plan_passage
from nomad_phase23o2.inputs import read,write
from nomad_phase23.report import csv_write
from nomad_phase17.report import table
from nomad_phase19r.evaluate import clean
from nomad_phase22.drive_geometry import bounds,corners
from . import graph as frozen
from .report import gate,summaries

HERE=Path(__file__).parent;SOURCE=ROOT/'research/results/phase23o3';OUT=ROOT/'research/results/phase23o3_diagnosis'

def save(path,value):write(path,clean(value))
def selected_values(c,p):
    saved=read(SOURCE/'training'/(c['case_id']+'.json'))['methods'][f"U3_{p['selected_index']:02d}"]
    base=read(SOURCE/'comparators'/(c['case_id']+'.json'))['methods'];return saved,base

def input_stage(c):
    s=c.get('spawn')
    if not s or c['tick']<s['tick']:return 'PRE_SPAWN'
    return 'ALREADY_PASSED' if c['B'][0]-c['oracle_config']['agent_radius_m']>bounds(s['obstacle'])[1][0] else 'PRE_PASSAGE'

def graph_for(c,plan,p,deadline=None):
    B=plan['B_pred'];q,sigma,ages,meta,current=mixture(c,B);weights=dict(FIXED_WEIGHTS,u2=dict(c=1.,T_m=p['selected']['T_m'],w7=p['selected']['w7'],ages_s=ages.tolist()))
    g=frozen.U3Graph(B,plan['application_previous_vw'][0],q,sigma,Snapshot.load(c['snapshot_file']),weights,deadline or time.monotonic_ns()+60_000_000_000)
    return g,q,ages,meta,current,weights

def from_saved(g,plan):
    pose=np.asarray(plan['poses']);return np.r_[np.c_[(pose[1:,:2]-g.B[:2])@g.R,wrap(pose[1:,2]-g.B[2])].ravel(),np.asarray(plan['dt'])]

def convert_path(g,world):
    tail,_=suffix(world,g.B);q=resample(np.vstack([g.B[:2],tail]));local=(q-g.B[:2])@g.R;delta=np.diff(local,axis=0)
    target=np.arctan2(delta[:,1],delta[:,0]);heading=[0.]
    # XY-only paths have no native headings. Use chord targets, projecting each
    # heading increment to the existing wmax*dtmax limit, not a new parameter.
    for desired in target:heading.append(heading[-1]+float(np.clip(wrap(desired-heading[-1]),-.4,.4)))
    heading=np.asarray(heading);length=np.linalg.norm(delta,axis=1)
    required=np.maximum.reduce([np.full(10,.05),length/.3,np.abs(wrap(np.diff(heading)))/.4])
    if np.max(required)>1.+1e-9:raise ValueError('Fixed11point geometry cannot meet hard timing/speed bounds')
    dt=np.minimum(required,1.);x=np.r_[np.c_[local[1:],heading[1:]].ravel(),dt]
    lag=np.abs(wrap(heading[1:]-target))
    return x,dict(world_path=q.tolist(),world_poses=np.c_[q,wrap(heading+g.B[2])].tolist(),dt=dt.tolist(),heading_lag_max_deg=float(np.rad2deg(lag.max())),heading_lag_mean_deg=float(np.rad2deg(lag.mean())),source_path=world)

def terms(g,x):
    p,heading,dt=g.unpack(x);active,costs=g.active(p);target=g.candidates[active];d,_,margin=g.queries(p);delta=np.diff(p,axis=0);co=np.cos(heading);si=np.sin(heading)
    nh=((co[:-1]+co[1:])*delta[:,1]-(si[:-1]+si[1:])*delta[:,0])/g.nh_sigma
    backward=np.minimum(0,co[:-1]*delta[:,0]+si[:-1]*delta[:,1])/g.nh_sigma
    full,_=g.full_constraints(x);acc=.5-full[-20:-10];acc_res=np.maximum(0,np.abs(acc)-.5)/.05
    k,_=vectorized_menger(p);length=np.linalg.norm(delta,axis=1);valid=(length[:-1]>=.01)&(length[1:]>=.01)&(np.linalg.norm(p[2:]-p[:-2],axis=1)>=.01);dk=np.diff(k)*(valid[:-1]&valid[1:])
    out=dict(F1=float(costs[active]),F1_age=float(g.age_cost[active]),F2=float(np.sum((np.maximum(0,.15-d)/.05)**2)),
        F3_nonholonomic=float(nh@nh),F3_backward=float(backward@backward),F3_acceleration=float(acc_res@acc_res),
        F4=float(dt.sum()),F5=float(np.sum((p[-1]-target[-1])**2)/.3**2),F6=.01*float(dk@dk),F7=float(g.f7(x)[0]),active_component=active)
    out['F1_cauchy']=out['F1']-out['F1_age'];out['F3']=out['F3_nonholonomic']+out['F3_backward']+out['F3_acceleration'];out['total']=sum(out[f'F{i}'] for i in range(1,8))
    actual=float(g.objective(x)[0]);out['decomposition_error']=abs(actual-out['total']);assert out['decomposition_error']<=1e-6*max(1.,abs(actual))
    h,_=g.constraints(x);v=length/dt;omega=wrap(np.diff(heading))/dt
    out.update(strict_feasible=bool(h.min()>=-1e-7 and np.all(x>=g.bounds.lb-1e-9) and np.all(x<=g.bounds.ub+1e-9)),minimum_hard_slack=float(h.min()),F2_minimum_slack_m=float(h[:21].min()),
        v_max=float(v.max()),omega_max=float(np.abs(omega).max()),dt_min=float(dt.min()),dt_max=float(dt.max()),max_abs_acceleration=float(np.abs(acc).max()),
        max_acceleration_excess=float(np.maximum(0,np.abs(acc)-.5).max()),nonholonomic_rms_m=float(np.sqrt(np.mean(nh**2))*g.nh_sigma))
    return out

class DiagnosticGraph(frozen.U3Graph):
    def __init__(self,*args,**kwargs):
        weights=args[5] if len(args)>5 else kwargs['weights'];self.diagnostic_initial=weights.get('_diagnostic_initial')
        super().__init__(*args,**kwargs)
    def initial(self,path):return np.asarray(self.diagnostic_initial,dtype=float).copy() if self.diagnostic_initial is not None else super().initial(path)
_kernel=types.FunctionType(frozen.worker.__code__,dict(frozen.worker.__globals__,U3Graph=DiagnosticGraph),argdefs=frozen.worker.__defaults__)
def diagnostic_worker(payload,channel):return _kernel(payload,channel)

def path_info(c,selection):
    if selection is None:return dict(accepted=False,planned_passage=False)
    return dict(accepted=True,planned_passage=bool(plan_passage(dict(case=c),dict(plan=dict(path=selection['path'])))),cost=selection['cost'],output_type=selection.get('output_type','FEASIBLE'),path=selection['path'],poses=selection['poses'],dt=selection['dt'])

def extra_solve(pool,c,original,p,initial,x):
    field=Snapshot.load(c['snapshot_file']);start=time.monotonic_ns();deadline=start+500_000_000
    from nomad_phase23.prediction import prefix
    policy=read(ROOT/'research/nomad_phase23/protocol.json')['policy'];motion=prefix(c,.5,policy['prediction_mode']);np.testing.assert_allclose(motion['B_pred'],original['B_pred'],atol=1e-12,rtol=0)
    B=motion['B_pred'];q,sigma,ages,meta,current=mixture(c,B);sides,component=side_initializations(current,B,field)
    starts=[np.asarray(initial['world_path']),*list(current),*sides];names=['EXTRA_DETOUR',*[f'CURRENT_{i}' for i in range(8)],*['LEFT','RIGHT'][:len(sides)]]
    weights=dict(FIXED_WEIGHTS,u2=dict(c=1.,T_m=p['selected']['T_m'],w7=p['selected']['w7'],ages_s=ages.tolist()))
    payloads=[dict(index=i,B=B,v0=motion['previous_vw'][0],candidates=q,sigma=sigma,path=path,weights=dict(weights,_diagnostic_initial=x.tolist()) if i==0 else weights,deadline_ns=deadline,snapshot_file=c['snapshot_file']) for i,path in enumerate(starts)]
    delivered=frozen.Collector.collect(pool,payloads,deadline,task=diagnostic_worker);end=time.monotonic_ns();records=[]
    for i,name in enumerate(names):
        messages=[m for m in delivered['messages'] if m['index']==i];last=delivered['latest'].get(i,{})
        choice=frozen.choose_output(dict(selected=select_messages(messages,deadline),latest={i:last} if last else {}),deadline)
        records.append(dict(initializer=name,index=i,solver_success=last.get('solver_success'),iteration=last.get('iteration'),solver_message=last.get('message','NOT_FINISHED_BEFORE_CUTOFF'),**path_info(c,choice)))
    return dict(wall_s=(end-start)/1e9,starts=records,selected_initializer=names[delivered['selected']['index']] if delivered['selected'] else None,
        selected=path_info(c,delivered['selected']),raw=delivered,extra_first_diagnostic_only=True)


def prepare():
    assert not (OUT/'protocol.json').exists();OUT.mkdir(parents=True,exist_ok=True);p=read(HERE/'protocol.json');m=read(SOURCE/'manifest.json');pre=[c for c in m['training'] if c['group']=='sudden' and input_stage(c)=='PRE_PASSAGE'];pairs=[]
    for c in pre:
        _,base=selected_values(c,p)
        for method in ('C0','C1'):
            if base[method]['row']['planned_box_passage']:pairs.append(dict(case_id=c['case_id'],method=method))
    assert len(pre)==16 and len(pairs)==5
    fig=list(dict.fromkeys(r['case_id'] for r in pairs));fig+=[c['case_id'] for c in pre if c['case_id'] not in fig][:4-len(fig)]
    protocol=dict(base_weights_commit='46aeb31',preserved_registered_result_commit='a2ce323',settings=p['selected'],c=1.,cases=[c['case_id'] for c in pre],pairs=pairs,figures=fig,
        conversion='Same saved U3 B_pred; protected suffix projection then11point arclength resampling. Chord-heading targets projected sequentially onto abs(delta_heading)<=omega_max*dt_max=.4rad. dt=max(.05,segment_length/.3,abs(delta_heading)/.4). All geometry and heading lag are retained; F3 cost includes the lag. No geometry optimization during conversion.',
        additional_initialization='Diagnostic-only EXTRA_DETOUR first, then frozen8current candidates and available left/right starts; shared500ms/fourworkers, maxiter100/ftol1e-8. Extra-first ensures it is scheduled. This is not the U3 method.',
        labels='Cost(reference)<cost(saved U3):INIT_LIMITED; greater:OBJECTIVE_LIMITED; equality unclassified. Feasibility accompanies every cost label. DIRECTION_WRONG if at least9of16directions differ from oracle+x by>=45degrees.',
        original_gate_sha256=sha256_file(SOURCE/'gate.json'),frozen_sources=read(HERE/'protocol.json')['frozen_sources'],diagnosis_source_sha256=sha256_file(Path(__file__)),evaluation_oracle_only=True)
    save(OUT/'protocol.json',protocol);print(json.dumps(dict(cases=16,pairs=pairs,figures=fig)))


def run():
    protocol=read(OUT/'protocol.json');assert sha256_file(Path(__file__))==protocol['diagnosis_source_sha256']
    for f,h in protocol['frozen_sources'].items():assert sha256_file(ROOT/f)==h,f
    assert sha256_file(SOURCE/'gate.json')==protocol['original_gate_sha256'];assert not (OUT/'complete.json').exists()
    p=read(HERE/'protocol.json');m=read(SOURCE/'manifest.json');by={c['case_id']:c for c in m['training']};cost_rows=[];availability=[];directions=[];set_rows=[];records={};pair_rows=[];start_rows=[]
    pre_rows=[]
    for identity in protocol['cases']:
        c=by[identity];original,base=selected_values(c,p);g,q,ages,meta,current,weights=graph_for(c,original['plan'],p);x=from_saved(g,original['plan']) if original['plan']['accepted'] else None
        base_terms=terms(g,x) if x is not None else None
        if base_terms is not None:assert abs(base_terms['total']-original['plan']['selected']['cost'])<=1e-6*max(1.,abs(base_terms['total']))
        side,info=side_initializations(current,g.B,g.field);expected=original['plan']['initialization_count']-8;assert len(side)==expected
        availability.append(dict(case_id=identity,left=bool(side),right=len(side)==2,reason=info.get('reason','DEPTH_COMPONENT_SELECTED'),initialization_count=8+len(side),**{k:v for k,v in info.items() if k!='reason'}))
        world=g.R@g.direction;angle=float(np.rad2deg(abs(np.arctan2(world[1],world[0])))) if g.direction_info['enabled'] else None
        candidate_rows=[]
        for i,item in enumerate(meta):
            delta=q[i,-1]-g.B[:2];length=float(np.linalg.norm(delta));signed=float(np.rad2deg(np.arctan2(delta[1],delta[0]))) if length else None
            row=dict(case_id=identity,component=i,set_index=item['set_index'],sample=item['sample'],age_s=ages[i],weight=float(np.exp(-ages[i]/p['selected']['T_m'])),endpoint_distance_m=length,direction_deg=signed,absolute_angle_to_x_deg=abs(signed) if signed is not None else None,F7_valid=length>=.05,native_remaining_m=item['native_remaining_m'],supplemented=item['supplemented']);candidate_rows.append(row)
        directions.extend(candidate_rows)
        for k in sorted({r['set_index'] for r in candidate_rows}):
            rr=[r for r in candidate_rows if r['set_index']==k];valid=[r for r in rr if r['F7_valid']];aa=[r['absolute_angle_to_x_deg'] for r in valid]
            mean=np.sum([np.array([np.cos(np.deg2rad(r['direction_deg'])),np.sin(np.deg2rad(r['direction_deg']))]) for r in valid],axis=0) if valid else np.zeros(2)
            set_rows.append(dict(case_id=identity,set_index=k,age_s=rr[0]['age_s'],age_weight=rr[0]['weight'],effective_direction_weight=len(valid)*rr[0]['weight'],valid_candidates=len(valid),mean_direction_deg=float(np.rad2deg(np.arctan2(mean[1],mean[0]))) if np.linalg.norm(mean)>1e-12 else None,angle_p10=float(np.quantile(aa,.1)) if aa else None,angle_median=float(np.median(aa)) if aa else None,angle_p90=float(np.quantile(aa,.9)) if aa else None))
        records[identity]=dict(case=c,original=original,base=base,U3_terms=base_terms,direction_world=world.tolist(),direction_angle_deg=angle,side=info,extra={})
        for name,value in dict(base,U3=original).items():pre_rows.append(dict(value['row'],method=name))
    rejudge=gate(summaries(pre_rows));rejudge['original_registered_label']='GO_ONLINE';rejudge['label']='PRE_PASSAGE_NO_GO';assert not rejudge['conditions']['planned_passage']
    save(OUT/'rejudgement.json',rejudge)
    ctx=mp.get_context('spawn');queue=ctx.Queue()
    with managed_pool(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
        ff=[pool.submit(ping) for _ in range(4)]
        for _ in range(4):queue.get(timeout=90)
        for f in ff:f.result()
        for spec in protocol['pairs']:
            identity,method=spec['case_id'],spec['method'];record=records[identity];c=record['case'];original=record['original'];g,_,_,_,_,_=graph_for(c,original['plan'],p)
            x,converted=convert_path(g,record['base'][method]['plan']['path']);before=terms(g,x);base_terms=record['U3_terms'];delta=before['total']-base_terms['total'];label_name='INIT_LIMITED' if delta<0 else 'OBJECTIVE_LIMITED' if delta>0 else None
            cost_rows.extend([dict(case_id=identity,reference_method=method,trajectory=name,**value) for name,value in [('saved_U3',base_terms),('converted_'+method,before)]])
            pair=dict(case_id=identity,method=method,cost_label=label_name,cost_delta_vs_U3=delta,reference_cost=before['total'],U3_cost=base_terms['total'],reference_strict_feasible=before['strict_feasible'],reference_F2_slack_m=before['F2_minimum_slack_m'],reference_heading_lag_max_deg=converted['heading_lag_max_deg'],reference_planned_passage=bool(plan_passage(dict(case=c),dict(plan=dict(path=converted['world_path'])))))
            differences={f'F{i}':before[f'F{i}']-base_terms[f'F{i}'] for i in range(1,8)};largest=max(differences,key=differences.get);pair.update(largest_term_delta=largest,largest_term_delta_value=differences[largest])
            outcome=extra_solve(pool,c,original['plan'],p,converted,x);save(OUT/'solves'/f'{identity}_{method}.json',outcome)
            for start in outcome['starts']:
                if start['accepted']:
                    xx=from_saved(g,start);start['diagnostic_terms']=terms(g,xx);start['strict_feasible']=start['diagnostic_terms']['strict_feasible']
                start_rows.append(dict(case_id=identity,reference_method=method,**{k:v for k,v in start.items() if k not in ('path','poses','dt','diagnostic_terms')}))
            extra=outcome['starts'][0];selected=outcome['selected'];pair.update(extra_solver_success=extra['solver_success'],extra_iterations=extra['iteration'],extra_accepted=extra['accepted'],extra_strict_feasible=extra.get('strict_feasible'),extra_passage=extra['planned_passage'],extra_cost=extra.get('cost'),selected_initializer=outcome['selected_initializer'],selected_passage=selected['planned_passage'],selected_cost=selected.get('cost'),wall_s=outcome['wall_s'])
            pair_rows.append(pair);record['extra'][method]=dict(converted=converted,outcome=outcome);print('[diagnosis]',identity,method,flush=True)
    wrong=sum(r['direction_angle_deg'] is not None and r['direction_angle_deg']>=45 for r in records.values())
    summary=dict(label='PRE_PASSAGE_NO_GO',original_label='GO_ONLINE',cases=16,cost_label_counts={k:sum(r['cost_label']==k for r in pair_rows) for k in ('INIT_LIMITED','OBJECTIVE_LIMITED')},direction_wrong_count=wrong,direction_wrong=wrong>8,
        extra_start_passage=sum(r['extra_passage'] for r in pair_rows),selected_passage=sum(r['selected_passage'] for r in pair_rows),pairs=5,online_preparation_held=True)
    csv_write(OUT/'factor_costs.csv',cost_rows);csv_write(OUT/'pairs.csv',pair_rows);csv_write(OUT/'initializations.csv',start_rows);csv_write(OUT/'side_initializations.csv',availability);csv_write(OUT/'candidate_directions.csv',directions);csv_write(OUT/'memory_sets.csv',set_rows)
    csv_write(OUT/'directions.csv',[dict(case_id=i,angle_to_positive_x_deg=r['direction_angle_deg'],direction_world=r['direction_world']) for i,r in records.items()]);save(OUT/'summary.json',summary)
    save(OUT/'paths.json',{i:dict(case=r['case'],direction_world=r['direction_world'],U3=r['original']['plan']['path'],comparators={k:v['plan'].get('path') for k,v in r['base'].items()},extra={k:dict(converted=v['converted'],selected=v['outcome']['selected'],extra_start=v['outcome']['starts'][0]) for k,v in r['extra'].items()}) for i,r in records.items()})
    from .diagnosis_report import generate
    generate(protocol,records,cost_rows,pair_rows,availability,set_rows,summary,rejudge)
    save(OUT/'complete.json',dict(summary=summary,additional_multistart_jobs=5,new_navigation=0,new_inference=0,new_tuning=0));print(json.dumps(summary),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');a=ap.parse_args();prepare() if a.prepare else run()
