"""Checkpointed offline-only tuning -> frozen commit -> evaluation -> report."""
import argparse,hashlib,itertools,json,multiprocessing as mp,subprocess,tempfile,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase19r.evaluate import clean,csv_write
from nomad_phase20d.pool import initialize,ping,evaluate_job as graph_job
from nomad_phase21.pool import evaluate_job as astar_job
from nomad_phase20d.recent import load_cache
from .refine import graph_refine,smooth
from .metrics import characterize,decision

HERE=ROOT/'research/nomad_phase22';OUT=ROOT/'research/results/phase22o'
def read(p):return json.loads(Path(p).read_text())
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(clean(v),indent=2,ensure_ascii=False)+'\n')
def commit(message,paths):
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','add','--',*[str(Path(p).relative_to(ROOT)) for p in paths]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m',message],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)

def prepare_case(c,p):
    c=dict(c)
    if p['anchor_mode']=='spawn_pose':c['anchor_xy']=c['candidate_anchor_xy'];c['anchor_source']='SPAWN_PREVIOUS_ODOMETRY' if c['appearance_available'] else 'CURRENT_B_NO_FUTURE_POSE'
    else:raise ValueError('Anchor definition must be finalized before any solve')
    return c

def pool_plan(pool,c,kind,cache):
    job=dict(kind='R3',job_id=0,B=c['B'],u_ref=c['u_ref'],evaluation_tick=c['tick'],snapshot_file=c['snapshot_file'],cache_file=str(cache),dispatch_ns=time.monotonic_ns())
    if kind=='P0':
        selected=read(ROOT/'research/nomad_phase21/protocol.json')['astar']['selected'];r=astar_job(pool,job,selected['lambda'],selected['smoothing_iterations'])
    else:r=graph_job(pool,job)
    index=r['selected_sample'];p=r['results'][index] if index is not None else {};elapsed=r['dispatch_to_complete_s']
    return {**p,'accepted':index is not None and elapsed<=1.,'path':p.get('path'),'disposition':'TIMEOUT' if elapsed>1 else p.get('disposition','NO_ACCEPTED_INITIALIZATION'),
            'compute_s':elapsed,'numeric_results':r['results']}

def grid(p):
    keys=list(p['p2_grid']);return [dict(zip(keys,x)) for x in itertools.product(*(p['p2_grid'][k] for k in keys))]

def case_run(pool,c,p,split):
    folder=OUT/split;folder.mkdir(exist_ok=True);file=folder/f"{c['case_id']}.json"
    if file.exists():return read(file)['rows']
    plans={};rows=[];traces={};start=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='phase22_cache_') as tmp:
        cache=Path(tmp)/'cache.npz';plans['P0']=pool_plan(pool,c,'P0',cache)
        # Same R3 map is already serialized by the frozen P0 backend.
        t=time.monotonic();base,strict=load_cache(cache);transfer_s=time.monotonic()-t
        plans['P1']=pool_plan(pool,c,'P1',Path(tmp)/'reference_cache.npz')
        strengths=p['p3_strength_grid'] if split=='training' else [p['selected']['p3_strength']]
        configurations=grid(p) if split=='training' else [p['selected']['p2_settings']]
        for i,strength in enumerate(strengths):
            name=f'P3_{i:02d}' if split=='training' else 'P3';p0=plans['P0'];spent=p0['compute_s']+transfer_s
            if not p0['accepted']:r=dict(accepted=False,path=None,disposition='P0_FAILED',refinement_wall_s=0.)
            else:r=smooth(c['B'],c['u_ref'],base,strict,p0['path'],strength,time.monotonic_ns()+round(max(0.,1.-spent)*1e9))
            r['compute_s']=spent+r['refinement_wall_s']
            if r['compute_s']>1:r.update(accepted=False,disposition='TIMEOUT')
            if r.get('disposition')=='P0_FALLBACK':r['depth_clearance_m']=p0.get('depth_clearance_m')
            plans[name]=r
        for i,settings in enumerate(configurations):
            name=f'P2_{i:02d}' if split=='training' else 'P2';p0=plans['P0'];spent=p0['compute_s']+transfer_s
            if not p0['accepted']:r=dict(accepted=False,path=None,disposition='P0_FAILED',refinement_wall_s=0.)
            else:r=graph_refine(c['B'],c['u_ref'],base,strict,p0['path'],c['anchor_xy'],settings,time.monotonic_ns()+round(max(0.,1.-spent)*1e9))
            r['compute_s']=spent+r['refinement_wall_s']
            if r['compute_s']>1:r.update(accepted=False,disposition='TIMEOUT')
            # No fallback unless explicitly registered by the user.
            if p['p2_failure']=='fallback' and not r['accepted'] and p0['accepted'] and r['compute_s']<=1:r.update(accepted=True,path=p0['path'],disposition='P0_FALLBACK')
            if r.get('disposition')=='P0_FALLBACK':r['depth_clearance_m']=p0.get('depth_clearance_m')
            plans[name]=r
        for name,plan in plans.items():
            row,roll=characterize(c,name,plan);rows.append(row)
            if roll is not None and split=='evaluation':traces[name]=dict(poses=roll['poses'].tolist(),commands=roll['commands'])
    write(file,dict(case=c,plans=plans,rows=rows,traces=traces,wall_s=time.monotonic()-start));return rows

def select(rows,p):
    p3scores=[]
    for i,strength in enumerate(p['p3_strength_grid']):
        name=f'P3_{i:02d}';rr=[r for r in rows if r['method']==name];by={(r['case_id'],r['method']):r for r in rows}
        good=[r for r in rr if r.get('safe_completion')]
        median=lambda k:float(np.median([r[k] for r in good])) if good else float('inf')
        mismatch=sum(by[r['case_id'],'P0'].get('side') in ('+Y','-Y') and r.get('side')!=by[r['case_id'],'P0'].get('side') for r in rr)
        score=(sum(r.get('oracle_collision',False) for r in rr),sum(r['planning_failed'] for r in rr),mismatch,median('jerk_rms'),median('heading_error_rad')+median('lateral_error_m'),median('completion_time_s'),strength)
        p3scores.append((score,name,strength))
    _,p3,strength=min(p3scores);scores=[];decisions=[]
    for i,settings in enumerate(grid(p)):
        name=f'P2_{i:02d}';rr=[r for r in rows if r['method'] in ('P0',p3,name)];d=decision(rr,name,p3);flags=d['criteria'];med=d['medians']
        ratios=sum(med[name][k]/max(med['P0'][k],1e-12) for k in ('jerk_rms','heading_error_rad','lateral_error_m')) if d['common_completion_n'] else float('inf')
        score=(not(flags['i'] and flags['ii']),-sum(flags[k] for k in ('iii','iv','v')),d['collisions'][name],d['failure_fraction'][name],ratios,med[name]['completion_time_s'] if d['common_completion_n'] else float('inf'),i)
        scores.append((score,i,settings));decisions.append(dict(candidate=i,settings=settings,decision=d,score=score))
    _,i,settings=min(scores);return dict(p3_strength=strength,p3_name=p3,p2_settings=settings,p2_candidate=i),dict(p3_scores=p3scores,p2_decisions=decisions)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--all',action='store_true');ap.add_argument('--status',action='store_true');ap.add_argument('--publish',action='store_true');ap.add_argument('--budget-s',type=float);a=ap.parse_args();wall_start=time.monotonic()
    if a.status:
        print(json.dumps(dict(protocol=read(HERE/'protocol.json')['status'],training_done=len(list((OUT/'training').glob('T*.json'))),training_total=26,evaluation_done=len(list((OUT/'evaluation').glob('E*.json'))),evaluation_total=24,complete=(OUT/'complete.json').exists())));return
    p=read(HERE/'protocol.json');assert p['anchor_mode'] is not None and p['p2_failure'] is not None,'Two pending definitions must be resolved first'
    manifest=read(OUT/'manifest.json');assert manifest['disjoint'];ctx=mp.get_context('spawn');q=ctx.Queue()
    with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(q,)) as pool:
        f=[pool.submit(ping) for _ in range(4)]
        for _ in range(4):q.get(timeout=90)
        for x in f:x.result()
        if p['status']!='FROZEN':
            commit('Register Phase22O definitions and tuning grid before evaluation',[HERE,OUT/'manifest.json']);rows=[]
            fresh_times=[]
            for i,c in enumerate(manifest['training']):
                existed=(OUT/'training'/f"{c['case_id']}.json").exists();started=time.monotonic();rows.extend(case_run(pool,prepare_case(c,p),p,'training'));print(f'[tune] {i+1}/26',flush=True)
                if not existed:fresh_times.append(time.monotonic()-started)
                if a.budget_s and fresh_times:
                    forecast=(26-i-1)*max(fresh_times)+24*max(fresh_times)/4+30
                    if time.monotonic()-wall_start+forecast>a.budget_s:
                        write(OUT/'handoff.json',dict(reason='PROJECTED_TIME_BUDGET',training_completed=i+1,forecast_remaining_s=forecast));print('[handoff] projected remaining wall time exceeds assistant budget; no evaluation started',flush=True);return
            selected,scores=select(rows,p);write(OUT/'tuning_selection.json',dict(selected=selected,scores=scores));p['selected']=selected;p['status']='FROZEN';write(HERE/'protocol.json',p)
            commit('Freeze Phase22O selected refinement weights before held-out evaluation',[HERE,OUT/'training',OUT/'tuning_selection.json']);print('[tune] FROZEN committed',flush=True)
        for i,c in enumerate(manifest['evaluation']):case_run(pool,prepare_case(c,p),p,'evaluation');print(f'[evaluate] {i+1}/24',flush=True)
    from .report import generate
    generate();write(OUT/'complete.json',dict(complete=True,git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()))
    if a.publish:
        subprocess.run(['git','add','-f','--',*[str(x.relative_to(ROOT)) for x in OUT.glob('*.png')]],cwd=ROOT,check=True)
        # A separate narrow commit includes derived report/data; staged figures intentional.
        subprocess.run(['git','add','--',str(HERE.relative_to(ROOT)),str(OUT.relative_to(ROOT)),'docs/PHASE22O_REFINE.md'],cwd=ROOT,check=True)
        subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase22O offline refinement validation'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
    print(json.dumps(read(OUT/'decision.json'),ensure_ascii=False))
if __name__=='__main__':main()
