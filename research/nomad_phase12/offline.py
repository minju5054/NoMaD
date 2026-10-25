"""Thirty frozen real Phase8 handoffs; functionality only, no inference/navigation."""
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,local_to_world
from nomad_isaac.async_report import rows
from nomad_phase0.pure_pursuit import XYPath,PurePursuit
from nomad_phase0.chunk_execution import protocol as pp_protocol
from nomad_phase9.intent import hermite
from .config import protocol
from .methods import hermite_splice,bid_select,TemporalTargets,freshest
from .gf_worker import NUMERIC_SHAPES,SCALARS,validate_job,solve_job
from nomad_isaac.async_report import stats


def cases():
    p=protocol()['offline'];records=json.loads((ROOT/p['source_results']).read_text());hashes=json.loads((ROOT/p['source_hashes']).read_text())
    pools=[];used={}
    for r in sorted([r for r in records if r['method']=='SELECT+GRAPH' and 17<=r['index']<=24 and not r.get('reused') and r['technical_validation']=='PASS'],key=lambda r:r['index']):
        run=Path(r['output']);saved=hashes[r['key']];names=['events.jsonl','phase6_applications.jsonl','controller.jsonl','stage2_graph.jsonl']
        for n in names:
            assert sha256_file(run/n)==saved[n];used[str(run/n)]=saved[n]
        events=rows(run/'events.jsonl');apps=rows(run/'phase6_applications.jsonl');ctrl=rows(run/'controller.jsonl');pool=[]
        graph=rows(run/'stage2_graph.jsonl');jobs={j['id']:j for j in graph if j['event']=='SUBMIT'};results={r['job_id']:r for r in graph if r['event']=='RESULT'}
        for e in events:
            tick=round(e['application_sim_s']*72);old=[a for a in apps if a['tick']<tick]
            if not old or old[-1]['world_xy'] is None:continue
            # Selection independent of new baseline outputs or future outcomes.
            try:XYPath(old[-1]['world_xy']);XYPath(e['chunk']['world_xy_m'])
            except ValueError:continue
            if tick<8 or not ctrl[tick//8-1]['valid']:continue
            path=run/f"model/derived/{e['id']:04d}.npz";h=sha256_file(path);assert saved[str(path.relative_to(run))]==h
            original=jobs[e['id']]
            numeric={k:original[k] for k in set(NUMERIC_SHAPES)|SCALARS}
            validate_job(numeric)
            pool.append(dict(key=r['key'],event=e,old=old[-1],file=str(path),sha256=h,job=numeric,recorded_graph=results.get(original['job_id'])))
        pools.append(pool)
    selected=[]
    for k in range(max(map(len,pools))):
        for pool in pools:
            if k<len(pool):selected.append(pool[k])
            if len(selected)==30:return selected,used
    raise AssertionError('Fewer than30 eligible real handoffs')


def check_hermite(case):
    e=case['event'];b=np.array(e['agent_pose_at_switch']);xy=np.array(e['chunk']['world_xy_m'])
    # Hermite analytic endpoint positions and derivatives; sampled curve approximation is distinct.
    path,meta=hermite_splice(xy,b);j=np.array(meta['join_xy']);ta=np.array(meta['tangent_start']);tj=np.array(meta['tangent_end'])
    np.testing.assert_allclose(path[0],b[:2],atol=1e-12);np.testing.assert_allclose(path[meta['curve_points']-1],j,atol=1e-12)
    h=1e-25;start=np.imag(hermite(b[:2],j,ta,tj,1j*h))/h;end=np.imag(hermite(b[:2],j,ta,tj,1+1j*h))/h
    np.testing.assert_allclose(start/np.linalg.norm(start),[np.cos(b[2]),np.sin(b[2])],atol=1e-10)
    np.testing.assert_allclose(end/np.linalg.norm(end),meta['join_tangent'],atol=1e-10)
    fresh=XYPath(xy);tail=fresh.points[fresh.s>meta['join_s_m']+1e-12]
    np.testing.assert_allclose(path[meta['curve_points']:],tail,atol=1e-12)
    assert np.max(np.linalg.norm(np.diff(path[:meta['curve_points']],axis=0),axis=1))<=.020001


def check_temporal(case):
    e=case['event'];b=np.array(e['agent_pose_at_switch']);xy=np.array(e['chunk']['world_xy_m'])
    ensemble=TemporalTargets();now=e['received_monotonic_ns']+1
    ensemble.push(xy,e['id'],e['received_monotonic_ns']);diag,detail=ensemble.control(b,now)
    _,expected=PurePursuit(xy,pp_protocol()['follower']).control(b)
    np.testing.assert_array_equal([diag['target_x_m'],diag['target_y_m']],[expected['target_x_m'],expected['target_y_m']])
    for i in range(2):ensemble.push(xy,e['id']+i+1,e['received_monotonic_ns'])
    _,detail=ensemble.control(b,now);assert abs(sum(detail['weights'])-1)<1e-15
    assert detail['weights'][0]>detail['weights'][1]>detail['weights'][2]


def check_bid(case):
    e=case['event'];b=np.array(e['agent_pose_at_switch']);xy=np.array(e['chunk']['world_xy_m'])
    with np.load(case['file']) as f:samples=np.array([local_to_world(x,np.array(e['observation_pose'])) for x in f['metric']])
    chosen,bid=bid_select(samples,b,case['old']['world_xy']);old=XYPath(case['old']['world_xy']);so,_=old.project(b[:2]);scores=[]
    for i,sample in enumerate(samples):
        candidate=XYPath(sample);sf,_=candidate.project(b[:2]);length=min(old.s[-1]-so,candidate.s[-1]-sf)
        grid=np.r_[np.arange(0,length,.01),length]
        score=float(np.mean([np.linalg.norm(old.at(so+s)-candidate.at(sf+s)) for s in grid])) if length>=.02 else None
        if score is None:assert bid['candidates'][i]['score_m'] is None
        else:np.testing.assert_allclose(bid['candidates'][i]['score_m'],score,atol=1e-12,rtol=0)
        if score is not None:scores.append((score,i))
    expected=min(scores)[1] if scores else 0;assert bid['selected_sample']==expected;np.testing.assert_array_equal(chosen,samples[expected])
    _,fallback=bid_select(samples,b,None);assert fallback['selected_sample']==0 and fallback['fallback']=='NO_VALID_OLD'
    short=np.array([b[:2],b[:2]+[.01,0.]])
    _,fallback=bid_select(samples,b,short);assert fallback['selected_sample']==0 and fallback['fallback']=='COMMON_LENGTH_BELOW_2CM'


def main():
    out=ROOT/'research/nomad_phase12/offline_validation_r2.json';assert not out.exists(),'Preserve previous functionality check'
    selected,inputs=cases();results=[]
    checks={'HERMITE':True,'TEMPORAL-ENSEMBLE':True,'BID':True,'GRAPH-GF_GEOMETRY_FIREWALL':True}
    functions={'HERMITE':check_hermite,'TEMPORAL-ENSEMBLE':check_temporal,'BID':check_bid}
    # Freeze identities and configuration before the first numerical solve.
    sources=[f for f in (ROOT/'research/nomad_phase12').glob('*.py')]+[ROOT/'research/nomad_phase12/protocol.json']
    source={str(f.relative_to(ROOT)):sha256_file(f) for f in sources}
    manifest=out.with_name('offline_cases_r2.json')
    with manifest.open('x') as f:json.dump(dict(source_sha256=source,cases=[dict(run=c['key'],id=c['event']['id'],input_sha256=c['sha256']) for c in selected]),f,indent=2)
    journal=out.with_name('offline_cases_r2.jsonl')
    with journal.open('x') as log:
        for case in selected:
            inputs[case['file']]=case['sha256'];result={}
            for name,func in functions.items():
                try:func(case);result[name]=dict(passed=True)
                except Exception as exc:result[name]=dict(passed=False,error=repr(exc));checks[name]=False
            e=case['event']
            with np.load(case['file']) as f:samples=np.array([local_to_world(x,np.asarray(e['observation_pose'])) for x in f['metric']])
            xy,selection=freshest(samples,np.asarray(e['agent_pose_at_switch']))
            job=dict(case['job'],world_xy=xy.tolist());validate_job(job)
            assert job['boundary']==e['agent_pose_at_switch']
            # One solve only; initialization rejection/nonconvergence preserved.
            gf=solve_job(job);checks['GRAPH-GF_GEOMETRY_FIREWALL'] &= gf['geometry_free_assert']
            old=case['recorded_graph']
            record=dict(run=case['key'],fresh_id=e['id'],checks=result,selection=selection,
                graph_gf=gf,phase8_recorded_graph=old)
            log.write(json.dumps(record)+'\n');log.flush();results.append(record)
    def summary(which):
        r=[c[which] for c in results if c[which] is not None];solved=[x for x in r if 'solver' in x]
        return dict(n=len(r),solver_executed=len(solved),initialization_rejected=sum(x.get('initialization_rejected',False) for x in r),
            converged=sum(x['solver']['success'] for x in solved),solver_accepted=sum(x.get('accepted',False) for x in r),
            solver_time_s=stats([x['solver']['solver_wall_s'] for x in solved]),
            worker_time_s=stats([(x['worker_end_ns']-x['worker_start_ns'])/1e9 for x in r]),
            online_accepted=sum(x.get('disposition')=='ACCEPTED' for x in r) if which=='phase8_recorded_graph' else None)
    new,old=summary('graph_gf'),summary('phase8_recorded_graph')
    out.write_text(json.dumps(dict(count=len(results),checks=checks,graph_gf=new,phase8_graph=old,
        case_results=str(journal.relative_to(ROOT)),input_sha256=inputs,source_sha256=source,
        new_navigation=0,new_inference=0,graph_solves_requested=30,
        scope=protocol()['offline']['graph_comparison']),indent=2)+'\n')
    print('30 handoffs: '+', '.join(k+' '+('PASS' if v else 'FAIL') for k,v in checks.items())+
          f"; GF convergence {new['converged']}/30, acceptance {new['solver_accepted']}/30, solve median/p95 {new['solver_time_s']['median']:.4f}/{new['solver_time_s']['p95']:.4f}s; stored Phase8 accepted {old['solver_accepted']}/{old['n']}, median/p95 {old['solver_time_s']['median']:.4f}/{old['solver_time_s']['p95']:.4f}s")
    if not all(checks.values()):raise SystemExit(1)

if __name__=='__main__':main()
