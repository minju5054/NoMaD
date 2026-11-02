"""Fixed30-case solver diagnosis. No tuning, rollout, inference or Isaac."""
import argparse,itertools,json,time,multiprocessing as mp
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase15b.depth import Snapshot
from nomad_phase19r.evaluate import clean
from nomad_phase20d.pool import initialize,ping
from .graph import UnifiedGraph,prepare_candidates,side_initializations
from .optimized import OptimizedGraph
from .runtime import managed_pool,wall_limit

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase23o_solver_check'
LIMITLESS=2**63-1
GROUPS=[('F2_nodes',0,11),('F2_midpoints',11,21),('F3_speed',21,31),('F3_omega_positive',31,41),('F3_omega_negative',41,51),('F3_accel_positive',51,61),('F3_accel_negative',61,71)]

def read(p):return json.loads(Path(p).read_text())
def write(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_suffix('.tmp');temp.write_text(json.dumps(clean(x),indent=2)+'\n');temp.replace(p)
class CountField:
    def __init__(self,field):self.field=field;self.calls=0
    def __getattr__(self,name):return getattr(self.field,name)
    def query(self,p):self.calls+=1;return self.field.query(p)

class Trace:
    def __init__(self,*a,**kw):
        self.objective_api_calls=0;self.constraint_api_calls=0;self.first_feasible_ns=None
        super().__init__(*a,**kw)
    def objective(self,x):self.objective_api_calls+=1;return super().objective(x)
    def constraints(self,x):self.constraint_api_calls+=1;return super().constraints(x)
    def observe(self,x):
        super().observe(x)
        if self.first_feasible_ns is None and self.best is not None:self.first_feasible_ns=self.best[2]
class Original(Trace,UnifiedGraph):pass
class Improved(Trace,OptimizedGraph):pass

def active_constraints(g,x):
    h,_=g.constraints(x);labels=[];violated=[];counts={}
    for name,lo,hi in GROUPS:
        counts[name]=int(np.sum(np.abs(h[lo:hi])<=1e-5))
        if counts[name]:labels.append(name)
        if np.any(h[lo:hi]<-1e-7):violated.append(name)
    for name,indices in [('F3_dt_lower',np.arange(30,40)),('F3_yaw_bounds',np.arange(2,30,3))]:
        b=x[indices]-g.bounds.lb[indices] if name=='F3_dt_lower' else np.minimum(x[indices]-g.bounds.lb[indices],g.bounds.ub[indices]-x[indices]);counts[name]=int(np.sum(np.abs(b)<=1e-5))
        if counts[name]:labels.append(name)
        if np.any(b<-1e-7):violated.append(name)
    dt=x[30:];counts['F3_dt_upper']=int(np.sum(abs(dt-1.)<=1e-5))
    if counts['F3_dt_upper']:labels.append('F3_dt_upper')
    violation=max(0.,float(-h.min()),float(np.max(g.bounds.lb-x)),float(np.max(x-g.bounds.ub)))
    return dict(final_feasible=violation<=1e-7,final_violation=violation,active_groups=labels,active_counts=counts,violated_groups=violated,fixed_B_infeasible=bool(h[0]<-1e-7))

def solve_one(case,candidates,sigma,path,field,weights,optimized,index):
    counted=CountField(field);start=time.monotonic_ns();cls=Improved if optimized else Original
    g=cls(case['B'],case['previous_vw'][0],candidates,sigma,counted,weights,LIMITLESS,.03);x=g.initial(path);g.observe(x)
    result=minimize(g.objective,x,jac=True,method='SLSQP',bounds=g.bounds,
        constraints=[dict(type='ineq',fun=lambda z:g.constraints(z)[0],jac=lambda z:g.constraints(z)[1])],callback=g.observe,options=dict(maxiter=100,ftol=1e-8))
    g.observe(result.x);finished=time.monotonic_ns()
    counts=dict(solver_nfev=int(result.nfev),solver_njev=int(result.njev),objective_api_calls=g.objective_api_calls,constraint_api_calls=g.constraint_api_calls,
        objective_kernel_calls=g.evaluations,constraint_kernel_calls=getattr(g,'constraint_kernel_calls',g.constraint_api_calls),sdf_query_calls=counted.calls)
    final=active_constraints(g,result.x)
    return dict(initialization=index,kind='candidate' if index<8 else 'left' if index==8 else 'right',solver_success=bool(result.success),solver_status=int(result.status),message=str(result.message),iterations=int(result.nit),
        wall_s=(finished-start)/1e9,any_feasible=g.best is not None,first_feasible_s=(g.first_feasible_ns-start)/1e9 if g.first_feasible_ns else None,
        best_found_s=(g.best[2]-start)/1e9 if g.best else None,best_cost=g.best[0] if g.best else None,best_x=g.best[1].tolist() if g.best else None,
        final_x=result.x.tolist(),final_cost=float(result.fun),mixture_switches=sum(a!=b for a,b in zip(g.trajectory[:-1],g.trajectory[1:])),**counts,**final)

def prepare():
    protocol=HERE/'solver_check_protocol.json';assert not protocol.exists(),'Fixed sample already exists'
    manifest=read(ROOT/'research/results/phase23o/manifest.json');p=read(HERE/'protocol.json');rng=np.random.default_rng(20261102);cases=[]
    for group in ('static','sudden'):
        choices=[c for c in manifest['training'] if c['group']==group];ids=sorted(rng.choice(len(choices),15,replace=False).tolist());cases.extend(choices[i] for i in ids)
    combinations=[dict(zip(p['grid'],v)) for v in itertools.product(*p['grid'].values())];middle=(len(combinations)-1)//2
    config=dict(status='FROZEN',base_commit='a3177ce',seed=20261102,case_ids=[c['case_id'] for c in cases],weights=combinations[middle],grid_index_zero_based=middle,
        middle_rule='Lower median of the existing Cartesian grid:8even-sized combinations have no unique center; fourth existing combination, no new weights.',
        solver=dict(method='SLSQP',jac='analytic',maxiter=100,ftol=1e-8,wall_deadline='none in before/after single-process check'),
        initialization_order='candidate0..7,left,right; absent component => side slots unavailable, not fabricated; no cross-snapshot warm start in isolated check',
        time_to_best='preparation + sequential earlier starts + first timestamp where globally lowest-cost feasible iterate was observed; total time separately reported for all snapshots',
        variants=dict(mode='registered4-worker envelope; measurement only, no candidate selected',reference=dict(starts='all',deadline_s=.25),i=dict(starts='prior2+side',deadline_s=.25),ii=dict(starts='all',deadline_s=.5),iii=dict(starts='prior2+side',deadline_s=.5),
            prior_rank='F1 max-mixture cost of each candidate initialization; self-match gives0/ties, lower candidate index wins. No invented confidence score.'),
        data_read_timing='Parent immutable SDF load excluded from solve timing in both passes; candidate/side preparation included in snapshot totals.',
        original_source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in (HERE/'graph.py',HERE/'planner.py',HERE/'protocol.json')},source_manifest_sha256=sha256_file(ROOT/'research/results/phase23o/manifest.json'))
    write(OUT/'cases.json',cases);write(protocol,config);print('Frozen15static+15sudden; grid index3; no outcomes used')

def pass_run(mode):
    p=read(HERE/'solver_check_protocol.json');cases=read(OUT/'cases.json');folder=OUT/mode;folder.mkdir(parents=True,exist_ok=True)
    start_all=time.monotonic()
    for case in cases:
        file=folder/f"{case['case_id']}.json"
        if file.exists():continue
        field=Snapshot.load(case['snapshot_file']);start=time.monotonic();candidates,sigma,flags=prepare_candidates(case['samples_world'],case['B'],case.get('old_path'),'retain');lateral,component=side_initializations(candidates,case['B'],field);prep=time.monotonic()-start
        starts=list(candidates)+lateral;rows=[];offset=prep
        for index,path in enumerate(starts):
            r=solve_one(case,candidates,sigma,path,field,p['weights'],mode=='after',index);r.update(start_offset_s=offset);offset+=r['wall_s'];rows.append(r)
        feasible=[r for r in rows if r['any_feasible']];best=min(feasible,key=lambda r:(r['best_cost'],r['initialization'])) if feasible else None
        record=dict(case_id=case['case_id'],group=case['group'],scene=case['scene'],index=case['index'],mode=mode,preparation_s=prep,total_wall_s=time.monotonic()-start,initializations=rows,available_starts=len(rows),side_unavailable=not bool(lateral),component=component,
            any_feasible=bool(feasible),converged_feasible=any(r['solver_success'] and r['final_feasible'] for r in rows),final_feasible=any(r['final_feasible'] for r in rows),best_initialization=best['initialization'] if best else None,
            best_found_s=best['start_offset_s']+best['best_found_s'] if best else None,first_feasible_s=min((r['start_offset_s']+r['first_feasible_s'] for r in feasible),default=None))
        write(file,record);print(f'[{mode}] {case["case_id"]} {record["total_wall_s"]:.3f}s feasible={bool(feasible)}',flush=True)
        if time.monotonic()-start_all>900:print('[budget]15min operational limit; saved cases retained, no reruns');return

_field_key=None;_field=None
def budget_worker(arg):
    global _field_key,_field
    case,candidates,sigma,path,weights,deadline,index=arg
    key=(case['snapshot_file'],deadline)
    if _field_key!=key:_field=Snapshot.load(case['snapshot_file']);_field_key=key
    from .optimized import solve_start
    r=solve_start(case['B'],case['previous_vw'][0],np.asarray(candidates),sigma,_field,weights,np.asarray(path),deadline,.03)
    return dict(initialization=index,**r)

def variants():
    p=read(HERE/'solver_check_protocol.json');cases=read(OUT/'cases.json');ctx=mp.get_context('spawn');queue=ctx.Queue()
    with managed_pool(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
        fs=[pool.submit(ping) for _ in range(4)]
        for _ in range(4):queue.get(timeout=90)
        for f in fs:f.result()
        for name,subset,budget in [('reference',False,.25),('i',True,.25),('ii',False,.5),('iii',True,.5)]:
            for c in cases:
                file=OUT/'variants'/f'{name}_{c["case_id"]}.json'
                if file.exists():continue
                field=Snapshot.load(c['snapshot_file']);start=time.monotonic_ns();deadline=start+round(budget*1e9)
                cand,sigma,_=prepare_candidates(c['samples_world'],c['B'],c.get('old_path'),'retain');sides,_=side_initializations(cand,c['B'],field)
                selected=list(range(8));ranker=UnifiedGraph(c['B'],c['previous_vw'][0],cand,sigma,field,p['weights'],LIMITLESS,.03)
                prior_costs=[float(ranker.active(ranker.unpack(ranker.initial(path))[0])[1].min()) for path in cand]
                if subset:selected=sorted(selected,key=lambda i:(prior_costs[i],i))[:2]
                starts=[(i,cand[i]) for i in selected]+[(8+i,s) for i,s in enumerate(sides)]
                payload={k:c[k] for k in ('snapshot_file','B','previous_vw')}
                with wall_limit(5.,'VARIANT_SOLVE_WATCHDOG'):rr=list(pool.map(budget_worker,[(payload,cand,sigma,path,p['weights'],deadline,i) for i,path in starts]))
                ended=time.monotonic_ns();on_time=ended<=deadline;feasible=[r for r in rr if r['accepted'] and r['ready_ns']<=deadline]
                write(file,dict(variant=name,case_id=c['case_id'],group=c['group'],compute_s=(ended-start)/1e9,budget_s=budget,deadline_overrun=not on_time,delivered_feasible=on_time and bool(feasible),feasible_before_deadline=bool(feasible),prior_costs=prior_costs,selected_candidate_initializations=selected,available_starts=len(starts),results=rr))
            print(f'[variant] {name}30cases done (no selection)',flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--pass',dest='mode',choices=['before','after']);ap.add_argument('--variants',action='store_true');a=ap.parse_args()
    if a.prepare:prepare()
    if a.mode:
        with wall_limit(960.,'UNLIMITED_CHECK_OPERATIONAL_WATCHDOG'):pass_run(a.mode)
    if a.variants:variants()
if __name__=='__main__':main()
