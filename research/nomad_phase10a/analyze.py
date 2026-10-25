"""One-pass, read-only analysis of Phase 8/9. Never constructs/solves a Graph."""
import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from nomad_isaac.common import ROOT, local_to_world
from nomad_phase0.graph_v4 import previous_stencil
from nomad_phase0.graph_v3 import side_labels
from nomad_phase2.config import native_safety
from nomad_phase6.metrics import application_measure

OUT = ROOT / 'research/results/phase10a'
DOC = ROOT / 'docs/PHASE10A_ANALYSIS.md'
PROTOCOL = Path(__file__).with_name('protocol.json')
EPS = 1e-6
HASHES = {}
CHECKS = Counter()


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p, expected=None):
    p = Path(p); data = p.read_bytes(); h = hashlib.sha256(data).hexdigest()
    if expected is not None:
        assert h == expected, f'Input hash mismatch: {p}'
        CHECKS['prior_provenance_hashes'] += 1
    HASHES[str(p)] = dict(sha256=h, bytes=len(data))
    return data.decode()


def jread(p):
    return json.loads(read(p))


def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def csvwrite(name, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (OUT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in r.items()})


def stat(values):
    a = np.asarray([v for v in values if v is not None], dtype=float)
    return dict(n=len(a), mean=float(a.mean()) if len(a) else None,
                median=float(np.median(a)) if len(a) else None,
                p95=float(np.percentile(a, 95)) if len(a) else None)


def wrap(a):
    return (a + np.pi) % (2*np.pi) - np.pi


def length(xy):
    return float(np.linalg.norm(np.diff(xy, axis=0), axis=1).sum())


def valid(r):
    return r.get('technical_validation') == 'PASS'


def bootstrap(values, draws):
    a = np.asarray(values, dtype=float); sample = a[draws]
    return dict(n=len(a), mean=float(a.mean()), median=float(np.median(a)),
                mean_ci95=np.quantile(sample.mean(axis=1), [.025,.975]).tolist(),
                median_ci95=np.quantile(np.median(sample, axis=1), [.025,.975]).tolist(),
                differences=a.tolist())


class Run:
    def __init__(self, record, saved_hashes):
        self.r = record; self.p = Path(record['output']); self.expected = saved_hashes.get(record['key']) or {}
        self.cache = {}
        rr = list(csv.DictReader(self.load('agent_trajectory.csv').splitlines()))
        self.t = np.array([float(x['simulation_time_s']) for x in rr])
        self.ns = np.array([int(x['monotonic_ns']) for x in rr], dtype=np.int64)
        self.pose = np.array([[float(x[k]) for k in ('x_m','y_m','yaw_rad')] for x in rr])
        assert np.all(np.diff(self.t) > 0) and np.all(np.diff(self.ns) >= 0)
        self.ctrl = self.lines('controller.jsonl'); self.end = float(self.t[-1])
        self.ct = np.array([c['simulation_time_s'] for c in self.ctrl])
        self.ce = np.r_[self.ct[1:], self.end]
        self.config = json.loads(self.load('scenario.json'))
        assert abs(self.end-record['duration_s']) < 1e-8
        self.graph = self.lines('stage2_graph.jsonl') if (self.p/'stage2_graph.jsonl').exists() else []
        self.events = self.lines('events.jsonl')
        CHECKS['run_duration_matches'] += 1

    def load(self, name):
        if name not in self.cache:
            # Every selected raw log should be covered by the already saved audit.
            assert name in self.expected, f'Missing provenance: {self.r["key"]}/{name}'
            self.cache[name] = read(self.p/name, self.expected[name])
        return self.cache[name]

    def lines(self, name):
        return [json.loads(x) for x in self.load(name).splitlines() if x.strip()]

    def window_weights(self, start, end):
        return np.maximum(0, np.minimum(self.ce,end)-np.maximum(self.ct,start))

    def at(self, t):
        return self.pose[min(int(np.searchsorted(self.t,t)),len(self.t)-1)]

    def next_time(self, ns):
        i = int(np.searchsorted(self.ns, ns)); return float(self.t[i]) if i < len(self.t) else None


def mechanisms(run):
    r = run.r; c = run.ctrl; dt = run.window_weights(0,run.end)
    active = np.array([x['valid'] and x['pure_pursuit']['stop_reason'] is None and
                       not x['pure_pursuit'].get('endpoint_stop',False) and x['stage2'].get('kappa_pp') is not None for x in c])
    k = np.array([abs(x['stage2'].get('kappa_pp') or 0) for x in c])
    target = np.array([x['stage2'].get('v_target_m_s', .3) or 0 for x in c])
    v = np.array([x['commanded_v_m_s'] for x in c])
    # Startup/timeout ticks store null; they are outside the active denominator.
    clamp = np.array([bool(x['pure_pursuit'].get('endpoint_clamped',False)) for x in c],dtype=bool)
    den = float(dt[active].sum())
    def fraction(mask): return float(dt[active & mask].sum()/den) if den else None
    for x in c:
        st=x['stage2']; kp=st.get('kappa_pp')
        if kp is not None and x['pure_pursuit']['stop_reason'] is None:
            expect=float(np.clip(.4/max(abs(kp),1e-30),.05,.3))
            assert abs(st['v_target_m_s']-expect)<1e-12
            CHECKS['logged_curv_targets'] += 1
    fn='phase6_applications.jsonl' if (run.p/'phase6_applications.jsonl').exists() else 'phase5_applications.jsonl'
    apps=run.lines(fn); measures=[]
    for a in apps:
        np.testing.assert_allclose(a['pose'],run.pose[a['tick']],atol=1e-12,rtol=0)
        measures.append(application_measure(a,run.pose[a['tick']]))
        CHECKS['application_poses'] += 1
    fresh=[a for a in measures if a['kind']!='GRAPH']; corrected=[a for a in measures if a['kind']=='GRAPH']
    return dict(key=r['key'],method=r['method'],index=r['index'],success=r['success'],classification=r['classification'],
        goal_time_s=r['goal_time_s'],mean_speed_m_s=r['mean_speed_m_s'],duration_s=run.end,active_pp_time_s=den,
        kappa_over2_fraction=fraction(k>2),endpoint_clamp_fraction=fraction(clamp),
        curv_target_below_point2_fraction=fraction(target<.2-1e-12),actual_speed_below_point2_fraction=fraction(v<.2-1e-12),
        actual_speed_below_point2_whole_run_fraction=float(dt[v<.2-1e-12].sum()/run.end),
        switch_heading=stat([a['heading_abs_rad'] for a in fresh]),switch_cross_track=stat([a['cross_track_m'] for a in fresh]),
        correction_heading=stat([a['heading_abs_rad'] for a in corrected]),correction_cross_track=stat([a['cross_track_m'] for a in corrected]),
        all_application_heading=stat([a['heading_abs_rad'] for a in measures]),heading_invalid=sum(a['heading_abs_rad'] is None for a in fresh))


def paired(records, mech):
    methods=('SELECT+GRAPH','SELECT','GRAPH','CURV')
    by={m:{r['index']:r for r in records if r['method']==m and r['delay_s']==.75 and 9<=r['index']<=24} for m in methods}
    details=[]; summaries=[]
    for a,b in [('SELECT+GRAPH','SELECT'),('GRAPH','SELECT'),('SELECT+GRAPH','GRAPH'),('SELECT+GRAPH','CURV')]:
        ids=[i for i in range(9,25) if all(i in by[m] and valid(by[m][i]) and by[m][i]['success'] for m in (a,b))]
        rng=np.random.default_rng(20261025); draws=rng.integers(0,len(ids),(20000,len(ids))) if ids else None
        metrics={}; exclusions=[]
        for i in range(9,25):
            if i not in ids: exclusions.append(dict(index=i,**{m:by[m].get(i,{}).get('classification','MISSING') for m in (a,b)}))
        for metric in ('goal_time_s','mean_speed_m_s','kappa_over2_fraction','endpoint_clamp_fraction',
                       'curv_target_below_point2_fraction','actual_speed_below_point2_fraction','switch_heading_median_rad','switch_cross_track_median_m'):
            vals=[]
            for i in ids:
                def value(m):
                    row=by[m][i]; mm=mech[row['key']]
                    if metric.startswith('switch_heading'): return mm['switch_heading']['median']
                    if metric.startswith('switch_cross'): return mm['switch_cross_track']['median']
                    return row[metric] if metric in row else mm[metric]
                av,bv=value(a),value(b)
                vals.append(av-bv if av is not None and bv is not None else None)
                details.append(dict(pair=f'{a} minus {b}',index=i,metric=metric,first=av,second=bv,difference=vals[-1]))
            metrics[metric]=bootstrap(vals,draws) if vals and all(v is not None for v in vals) else dict(n=0,reason='missing paired measurement')
        ci=metrics['goal_time_s'].get('mean_ci95')
        verdict='INCONCLUSIVE' if len(ids)<10 else 'SPEED_ADVANTAGE' if ci[1]<0 else 'SPEED_NOT_SHOWN'
        summaries.append(dict(pair=f'{a} minus {b}',indices=ids,n=len(ids),exclusions=exclusions,metrics=metrics,verdict=verdict))
    return summaries,details


def segments(times, mask):
    starts=np.flatnonzero(mask & ~np.r_[False,mask[:-1]])
    ends=np.flatnonzero(mask & ~np.r_[mask[1:],False])
    return [[float(times[a]),float(times[min(b+1,len(times)-1)])] for a,b in zip(starts,ends)]


def dynamic_state(run):
    pub=run.lines('overnight_oracle.jsonl'); spawn=json.loads(run.load('dynamic/spawn.json'))
    assert len(pub)==1
    p=pub[0]; box=p['obstacle'];rear=box['center_xy_m'][0]+box['size_xyz_m'][0]/2
    active=(run.ns>=p['publication_monotonic_ns']) & (run.pose[:,0]<=rear+.30)
    passes=np.flatnonzero(run.pose[:,0]>rear+run.config['agent_radius_m'])
    inactive=np.flatnonzero((run.ns>=p['publication_monotonic_ns']) & ~active)
    side=1 if box['center_xy_m'][1]<=0 else -1
    return dict(box=box,rear=rear,side=side,public_ns=p['publication_monotonic_ns'],
                public_s=run.next_time(p['publication_monotonic_ns']),
                oracle_capture_pose_time_s=p['gate']['available_from']['observation_sim_s'],
                spawn_s=spawn['tick']/72,active_intervals=segments(run.t,active),
                pass_s=float(run.t[passes[0]]) if len(passes) else None,
                deactivate_s=float(run.t[inactive[0]]) if len(inactive) else None,
                recross_after_pass=bool(len(passes) and np.any(run.pose[passes[0]:,0]<=rear+run.config['agent_radius_m'])))


def post_pass(run, state):
    start=state['pass_s']
    if start is None:return dict(available=False)
    end=min(run.end,start+3);dt=run.window_weights(start,end)
    active=np.array([c['valid'] and c['pure_pursuit']['stop_reason'] is None for c in run.ctrl])
    corrected=np.array([c['stage2']['corrected_path_active'] for c in run.ctrl]); moving=dt[active].sum()
    a=run.at(start);b=run.at(end);mask=(run.t>=start)&(run.t<=end);ps=run.pose[mask]
    center_heading=np.where(ps[:,1]>0,-np.pi/2,np.pi/2)
    eligible=abs(ps[:,1])>EPS
    return dict(available=True,start_s=start,end_s=end,truncated=end-start<3-1e-9,
        y_start_m=float(a[1]),y_end_m=float(b[1]),abs_y_change_m=float(abs(b[1])-abs(a[1])),
        yaw_start_rad=float(a[2]),yaw_end_rad=float(b[2]),
        center_heading_abs_error_rad=stat(abs(wrap(ps[eligible,2]-center_heading[eligible])).tolist()),
        centerward_heading_fraction=float(np.mean(-np.sign(ps[eligible,1])*np.sin(ps[eligible,2])>EPS)) if eligible.any() else None,
        corrected_fraction_of_valid=float(dt[active&corrected].sum()/moving) if moving else None,
        raw_fraction_of_valid=float(dt[active&~corrected].sum()/moving) if moving else None,
        invalid_stop_time_s=float(dt[~active].sum()),
        y_series=[dict(time_s=float(t),y_m=float(p[1]),yaw_rad=float(p[2])) for t,p in zip(run.t[mask][::18],ps[::18])])


def graph_analysis(run,state):
    r=run.r; jobs=[x for x in run.graph if x['event']=='SUBMIT'];results={x['job_id']:x for x in run.graph if x['event']=='RESULT'}
    terminal={x['job_id'] for x in run.graph if x['event']=='TERMINAL_UNAPPLIED'}
    previous=None
    for event in run.graph:
        if event['event']=='SUBMIT':
            assert (previous is None)==(event['previous_xy'] is None)
            if previous is not None:np.testing.assert_array_equal(event['previous_xy'],previous)
            CHECKS['previous_accepted_identity']+=1
        elif event['event']=='RESULT' and event['disposition']=='ACCEPTED': previous=event['applied_world_xy']
    events={e['id']:e for e in run.events}; output=[]; first_five=[]
    for job in jobs:
        res=results.get(job['job_id'],{});sol=res.get('solver',{});cfg=job['public_config'];intent=cfg.get('public_intent')
        xy=np.array(job['world_xy']);b=np.array(job['boundary']);prev=job.get('previous_xy');out=np.array(res['poses'])[:,:2] if 'poses' in res else None
        np.testing.assert_allclose(local_to_world(np.array(events[job['id']]['overnight_metric_samples'])[0],np.array(job['observation_pose'])),xy,atol=1e-12,rtol=0)
        np.testing.assert_array_equal(b,run.pose[round(job['switch_sim_s']*72)])
        CHECKS['graph_observation_anchor_and_boundary']+=1
        enabled=bool(cfg['obstacles']);stage='BEFORE_PUBLIC' if not enabled else 'INTENT_ACTIVE' if intent else 'INTENT_INACTIVE'
        assert enabled==(cfg['geometry_snapshot_monotonic_ns']>=state['public_ns'])
        assert bool(intent)==(enabled and b[0]<=state['rear']+.30)
        label=side_labels(xy,cfg).get('DynamicObstacle',{})
        forced=intent['side'] if intent else None
        gap=native_safety(xy,cfg)['minimum_clearance_m'] if enabled else None
        resultgap=sol.get('exact_path_certificate',{}).get('obstacle_clearance_m')
        d=dict(key=r['key'],index=r['index'],delay_s=r['delay_s'],job_id=job['job_id'],fresh_id=job['id'],
            time_s=job['switch_sim_s'],stage=stage,public_geometry=enabled,sdf_enforced=enabled,
            side_forced=forced,native_side=label.get('sign'),native_side_status=label.get('status','NOT_PUBLIC'),
            side_factor_sign=forced if intent else label.get('sign'),
            intent_conflict=bool(intent and label.get('sign') is not None and label['sign']!=intent['side']),
            disposition=res.get('disposition','TERMINAL_UNAPPLIED' if job['job_id'] in terminal else 'MISSING_RESULT'),
            solver_present=bool(sol),solver_success=sol.get('success'),nonconverged=bool(sol and not sol['success']),
            solver_message=sol.get('message'),solver_iterations=sol.get('iterations'),solver_wall_s=sol.get('solver_wall_s'),
            initialization_rejected=bool(res.get('initialization_rejected')),initialization_error=res.get('error'),
            previous_speed_m_s=job['previous_command'][0],fresh_length_m=length(xy),
            result_length_m=length(out) if out is not None else None,fresh_obstacle_clearance_m=gap,result_obstacle_clearance_m=resultgap,
            minimum_scaled_constraint=sol.get('minimum_scaled_inequality'),equality_error=sol.get('scaled_equality_error'),
            boundary_y_m=float(b[1]),fresh_end_y_m=float(xy[-1,1]),fresh_centerward_endpoint=bool(-np.sign(b[1])*(xy[-1,1]-b[1])>EPS) if abs(b[1])>EPS else None,
            fresh_y_change_m=float(xy[-1,1]-b[1]),previous_prior_present=prev is not None,
            previous_prior_factor_cost=sol.get('factor_costs',{}).get('previous_corrected_xy'),
            heuristic_factor_present='heuristic_intent_xy' in sol.get('factor_costs',{}),
            native_side_factor_present='definite_side_preservation' in sol.get('factor_costs',{}),
            side_factor_cost=sol.get('factor_costs',{}).get('definite_side_preservation'),
            applied_time_s=res.get('applied_tick',0)/72 if res.get('disposition')=='ACCEPTED' else None)
        if prev is not None:
            target=previous_stencil(prev,b,xy)
            d.update(prior_minus_fresh_y_mean_m=float(np.mean(target[:,1]-xy[:,1])),
                prior_fresh_y_rms_m=float(np.sqrt(np.mean((target[:,1]-xy[:,1])**2))),
                prior_end_y_m=float(target[-1,1]),prior_sideward_offset_m=float(state['side']*np.mean(target[:,1]-xy[:,1])))
            if out is not None:
                d.update(result_fresh_y_rms_m=float(np.sqrt(np.mean((out[:,1]-xy[:,1])**2))),
                    result_prior_y_rms_m=float(np.sqrt(np.mean((out[:,1]-target[:,1])**2))),
                    result_minus_fresh_y_mean_m=float(np.mean(out[:,1]-xy[:,1])),
                    result_sideward_shift_m=float(state['side']*np.mean(out[:,1]-xy[:,1])),
                    result_end_y_m=float(out[-1,1]))
                d['closer_to_prior']=d['result_prior_y_rms_m']+EPS<d['result_fresh_y_rms_m']
                d['closer_to']='PRIOR' if d['closer_to_prior'] else 'FRESH' if d['result_fresh_y_rms_m']+EPS<d['result_prior_y_rms_m'] else 'TIE'
        output.append(d)
        if stage=='INTENT_INACTIVE' and len(first_five)<5:first_five.append(d)
    # Neighboring *saved* calls, not rerun predictions or optimizations.
    for i,d in enumerate(output):
        for offset,name in ((-1,'previous'),(1,'next')):
            other=output[i+offset] if 0<=i+offset<len(output) else None
            for field in ('job_id','stage','fresh_length_m','result_length_m','fresh_obstacle_clearance_m','result_obstacle_clearance_m'):
                d[name+'_'+field]=other[field] if other else None
    return output,first_five


def comparison_events(run,state):
    out=[]
    for e in run.events:
        t=e['application_sim_s'];b=np.array(e['agent_pose_at_switch']);meta=e['overnight'];intent=meta['intent']
        if meta['geometry_snapshot_monotonic_ns']<state['public_ns']:continue
        if state['pass_s'] is not None and t>state['pass_s']:continue
        xy=np.array(e['chunk']['world_xy_m']);cfg={**run.config,'obstacles':[state['box']]}
        label=side_labels(xy,cfg)['DynamicObstacle']
        out.append(dict(key=run.r['key'],method=run.r['method'],index=run.r['index'],delay_s=run.r['delay_s'],
            id=e['id'],time_s=t,native_side=label['sign'],native_status=label['status'],heuristic_side=state['side'],
            conflict=label['sign'] is not None and label['sign']!=state['side'],
            native_crossings=label['crossings'],native_end_y_m=float(xy[-1,1]),active_intent=bool(intent),
            native_safe=native_safety(xy,cfg)['safe']))
    return out


def summarize_jobs(js):
    n=len(js);sol=[j for j in js if j['solver_present']]
    return dict(calls=n,solver_calls=len(sol),nonconverged=sum(j['nonconverged'] for j in js),
        nonconvergence_per_call=sum(j['nonconverged'] for j in js)/n if n else None,
        nonconvergence_per_solve=sum(j['nonconverged'] for j in js)/len(sol) if sol else None,
        initialization_rejected=sum(j['initialization_rejected'] for j in js),
        zero_speed_rejected=sum(j['initialization_rejected'] and j['previous_speed_m_s']<=0 for j in js),
        superseded=sum(j['disposition']=='SUPERSEDED' for j in js),
        superseded_fraction=sum(j['disposition']=='SUPERSEDED' for j in js)/n if n else None,
        sdf_enforced=sum(j['sdf_enforced'] for j in js),
        dispositions=dict(Counter(j['disposition'] for j in js)),
        nonconverged_messages=dict(Counter(j['solver_message'] for j in js if j['nonconverged'])))


def table(rows,keys):
    def fmt(v):
        if v is None:return 'N/A'
        if isinstance(v,float):return f'{v:.4f}'
        if isinstance(v,(list,dict)):return json.dumps(v,ensure_ascii=False)
        return str(v)
    return ['|'+'|'.join(keys)+'|','|'+'|'.join(['---']*len(keys))+'|']+['|'+'|'.join(fmt(r.get(k)).replace('|','/') for k in keys)+'|' for r in rows]


def main():
    assert not OUT.exists() and not DOC.exists(), 'Never overwrite prior outputs'
    protocol=jread(PROTOCOL)
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    rows8=jread(ROOT/'research/results/phase8/runs.json'); rows9=jread(ROOT/'research/results/phase9/runs.json')
    hashes8=jread(ROOT/'research/results/phase8/input_hashes.json');hashes9=jread(ROOT/'research/results/phase9/input_hashes.json')
    for phase,folder in [(8,'phase8_combo_rtc_01'),(9,'phase9_sudden_01')]:
        complete=jread(ROOT.parent/'artifacts/isaac6'/folder/'complete.json')
        assert complete['status']=='COMPLETE'
    # Record source evidence; these modules are inspected/imported as pure helpers only.
    source_files=['nomad_phase9/graph.py','nomad_phase9/intent.py','nomad_phase9/worker.py','nomad_phase8/execution.py',
        'nomad_phase8/metrics.py','nomad_phase8/report.py','nomad_phase6/metrics.py','nomad_phase0/graph_v4.py',
        'nomad_phase0/graph_v3.py','nomad_phase0/graph_v4_protocol.json','nomad_phase4c/execution.py','nomad_phase5/graph.py',
        'nomad_phase10a/analyze.py','nomad_phase10a/protocol.json']
    for name in source_files:read(ROOT/'research'/name)
    static=[r for r in rows8 if r['method'] in ('CURV','SELECT','GRAPH','SELECT+GRAPH') and r['delay_s']==.75 and 9<=r['index']<=24]
    assert len(static)==64 and len({r['key'] for r in static})==64
    mechanisms_by={}; exclusions=[]
    for r in static:
        if valid(r): mechanisms_by[r['key']]=mechanisms(Run(r,hashes8))
        else:exclusions.append(dict(key=r['key'],reason=r['classification']))
    pairs,pair_details=paired(static,mechanisms_by)
    all_jobs=[];prior=[];failures=[];run_info=[];conflicts=[];windows=[];plot_data=None
    dyn=[r for r in rows9 if r['method'] in ('CURV','INTENT-SPLICE','GRAPH-v6')]
    dyn.sort(key=lambda r:(-r['delay_s'],r['index'],r['method']))
    for r in dyn:
        assert valid(r)
        run=Run(r,hashes9);state=dynamic_state(run);window=post_pass(run,state)
        ce=comparison_events(run,state);conflicts.extend(ce)
        ri=dict(key=r['key'],method=r['method'],index=r['index'],delay_s=r['delay_s'],success=r['success'],
            termination=r['termination_reason'],s=-1 if r['index']%2==0 else 1,heuristic_side=state['side'],
            end_s=run.end,final_pose=run.pose[-1].tolist(),**state,
            native_definite_count=sum(e['native_side'] is not None for e in ce),native_conflict_count=sum(e['conflict'] for e in ce),
            native_undefined_count=sum(e['native_side'] is None for e in ce))
        run_info.append(ri)
        if r['method']!='GRAPH-v6':continue
        js,p5=graph_analysis(run,state);all_jobs.extend(js);prior.extend(p5)
        expected=r['graph']['calls'];assert len(js)==expected
        assert sum(j['nonconverged'] for j in js)==r['graph']['independent_nonconverged']
        CHECKS['graph_count_matches']+=1
        window.update(key=r['key'],success=r['success'],delay_s=r['delay_s'],index=r['index'])
        if window['available']:
            wjobs=[j for j in js if window['start_s']<=j['time_s']<=window['end_s'] and j['fresh_centerward_endpoint'] is not None]
            window.update(fresh_calls=len(wjobs),fresh_centerward=sum(j['fresh_centerward_endpoint'] for j in wjobs),
                fresh_not_centerward=sum(not j['fresh_centerward_endpoint'] for j in wjobs))
        windows.append(window)
        if not r['success']:
            deact=state['deactivate_s'];activejs=[j for j in js if j['stage']=='INTENT_ACTIVE']
            row=dict(key=r['key'],index=r['index'],delay_s=r['delay_s'],termination=r['termination_reason'],
                spawn_s=state['spawn_s'],public_s=state['public_s'],public_monotonic_ns=state['public_ns'],
                oracle_capture_pose_time_s=state['oracle_capture_pose_time_s'],intent_intervals=state['active_intervals'],
                first_active_job_s=activejs[0]['time_s'] if activejs else None,pass_s=state['pass_s'],
                deactivate_s=deact,first_inactive_job_s=p5[0]['time_s'] if p5 else None,
                failure_s=run.end,failure_pose=run.pose[-1].tolist(),post_inactive_duration_s=run.end-deact if deact is not None else None,
                prior_first5_jobs=[j['job_id'] for j in p5],recross_after_pass=state['recross_after_pass'],post_pass=window)
            failures.append(row)
            if plot_data is None:plot_data=(run.t.copy(),run.pose.copy(),row,state)
    d0=[j for j in all_jobs if j['delay_s']==0]
    d0_stage=[dict(stage=s,**summarize_jobs([j for j in d0 if j['stage']==s])) for s in ('BEFORE_PUBLIC','INTENT_ACTIVE','INTENT_INACTIVE')]
    d0_total=summarize_jobs(d0)
    nonconv=[]
    for j in d0:
        if j['nonconverged']:nonconv.append(j)
    inactive=[j for j in all_jobs if j['stage']=='INTENT_INACTIVE']
    failure_keys={r['key'] for r in failures};wall_keys={r['key'] for r in failures if 'corridor' in r['termination']}
    c1=[]
    for j in prior:
        if j['key'] not in wall_keys or j['disposition']!='ACCEPTED':continue
        if j.get('prior_sideward_offset_m',0)<=EPS or j.get('result_sideward_shift_m',0)<=EPS or not j.get('closer_to_prior'):continue
        info=next(r for r in run_info if r['key']==j['key'])
        if abs(info['final_pose'][1])-abs(j['boundary_y_m'])>EPS:c1.append(dict(key=j['key'],job_id=j['job_id']))
    c3=[w['key'] for w in windows if not w['success'] and w['available'] and w['abs_y_change_m']>EPS and w.get('fresh_calls',0)>0 and w['fresh_not_centerward']>w['fresh_calls']/2]
    present=[r for r in d0_stage if r['calls']]
    peak=max(present,key=lambda r:r['nonconverged'])
    concentrated=(len(present)>=2 and all(peak['nonconvergence_per_call']>r['nonconvergence_per_call'] for r in present if r is not peak)
        and peak['nonconverged']/max(1,d0_total['nonconverged'])>peak['calls']/d0_total['calls'])
    c5=[j for j in all_jobs if j['index']%2==0 and j['stage']=='INTENT_ACTIVE' and j['intent_conflict']]
    decisions={
        'C1_PRIOR_DRAG':dict(verdict='SUPPORTED' if c1 else 'UNCLEAR' if any(j['previous_prior_present'] for j in prior if j['key'] in failure_keys) else 'NOT_SUPPORTED',evidence=c1,causal_isolation='not possible without new ablation'),
        'C2_SIDE_FACTOR_PERSISTS':dict(verdict='SUPPORTED' if any(j['heuristic_factor_present'] or j['side_forced'] is not None for j in inactive) else 'NOT_SUPPORTED',inactive_calls=len(inactive),heuristic_factor_remaining=sum(j['heuristic_factor_present'] for j in inactive),recomputed_native_side_defined=sum(j['side_factor_sign'] is not None for j in inactive)),
        'C3_NO_RECENTER':dict(verdict='SUPPORTED' if c3 else 'NOT_SUPPORTED' if any(w['available'] and not w['success'] for w in windows) else 'UNCLEAR',evidence_runs=c3),
        'C4_D0_NONCONVERGENCE':dict(verdict='SUPPORTED' if concentrated else 'NOT_SUPPORTED' if len(present)>=2 else 'UNCLEAR',peak_stage=peak['stage'],total=d0_total,stages=d0_stage),
        'C5_INTENT_CONFLICT':dict(verdict='SUPPORTED' if c5 else 'NOT_SUPPORTED' if any(j['native_side'] is not None for j in all_jobs if j['index']%2==0 and j['stage']=='INTENT_ACTIVE') else 'UNCLEAR',conflict_calls=len(c5),runs=sorted({j['key'] for j in c5}),causal_success_attribution='UNCLEAR')}
    # No optimization, navigation, inference, or intervention is invoked anywhere above.
    for name,meta in HASHES.items():assert digest(Path(name))==meta['sha256'],'Source changed during analysis'
    CHECKS['inputs_unchanged_after_analysis']=len(HASHES)
    OUT.mkdir(parents=True)
    write('protocol.json',protocol);write('paired.json',pairs);csvwrite('paired.csv',pair_details)
    csvwrite('speed_mechanisms.csv',list(mechanisms_by.values()));write('static_exclusions.json',exclusions)
    csvwrite('graph_calls.csv',all_jobs);csvwrite('prior_first5.csv',prior);csvwrite('d0_nonconvergence.csv',nonconv)
    csvwrite('d0_stages.csv',d0_stage);csvwrite('timelines.csv',failures);write('post_pass_windows.json',windows)
    csvwrite('run_comparison.csv',run_info);csvwrite('native_intent.csv',conflicts)
    summary=dict(source_git_sha=sha,analysis_source_sha256=HASHES[str(Path(__file__))]['sha256'],part1=pairs[0],part2=decisions,
        static_valid=len(mechanisms_by),static_exclusions=exclusions,graph_runs=12,graph_failures=len(failures),
        validation=dict(CHECKS),scope='Saved logs only; oracle geometry; SE(2) kinematic execution; observational diagnosis')
    write('summary.json',summary);write('input_hashes.json',HASHES)
    plot(pairs[0],plot_data)
    report(summary,pairs,list(mechanisms_by.values()),failures,windows,prior,run_info,d0_stage,all_jobs)
    print(json.dumps(dict(part1=pairs[0]['verdict'],pairs=pairs[0]['n'],goal_time=pairs[0]['metrics']['goal_time_s'],
                         part2={k:v['verdict'] for k,v in decisions.items()},d0_calls=d0_total['calls'],d0_nonconverged=d0_total['nonconverged'],output=str(OUT)),ensure_ascii=False))


def plot(primary, data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    t,pose,r,state=data
    fig,ax=plt.subplots(figsize=(9,4))
    ax.plot(t,pose[:,1],color='#176b8c',lw=1.7,label='Executed y (72 Hz)')
    for i,(a,b) in enumerate(state['active_intervals']):ax.axvspan(a,b,color='#e6ac35',alpha=.22,label='Intent active' if i==0 else None)
    for tm,color,label in [(state['public_s'],'#888888','Oracle public'),(state['pass_s'],'#258942','Footprint passed rear'),(r['failure_s'],'#b52f36','Failure / termination')]:
        if tm is not None:ax.axvline(tm,color=color,ls='--',label=label)
    ax.axhline(0,color='gray',lw=.7);ax.axhline(1.41,color='gray',ls=':');ax.axhline(-1.41,color='gray',ls=':')
    ax.set(xlabel='Simulation time (s)',ylabel='World y (m)',title=f"{r['key']} — {r['termination']}")
    ax.legend(fontsize=8,loc='best');fig.tight_layout();fig.savefig(OUT/'graph_failure_y.png',dpi=160);plt.close(fig)
    v=primary['metrics']['goal_time_s'];ids=primary['indices'];diff=np.array(v['differences'])
    fig,ax=plt.subplots(figsize=(8,4))
    ax.bar([str(i) for i in ids],diff,color=np.where(diff<0,'#247f91','#cc6546'))
    ax.axhline(0,color='black',lw=.8);ax.axhline(v['mean'],color='#70449c',ls='--',label=f"Mean {v['mean']:.2f} s")
    ax.set(xlabel='Paired index (both SUCCESS)',ylabel='SELECT+GRAPH − SELECT goal time (s)',title=f"n={len(ids)}; mean paired bootstrap 95% CI [{v['mean_ci95'][0]:.2f}, {v['mean_ci95'][1]:.2f}] s")
    ax.legend();fig.tight_layout();fig.savefig(OUT/'paired_goal_time.png',dpi=160);plt.close(fig)


def report(s,pairs,mech,failures,windows,prior,runs,stages,jobs):
    p=s['part1'];dec=s['part2'];lines=['# Phase 10A — 저장 로그 기반 속도 및 GRAPH-v6 진단','',
        f"입력 Git SHA: `{s['source_git_sha']}`. 분석 스크립트 SHA-256: `{s['analysis_source_sha256']}`.",
        '새 navigation, inference, Graph solve 없음. 원본 로그와 이전 결과는 변경하지 않았다. Oracle geometry / SE(2) kinematic Isaac Sim 범위의 사후 관찰 분석이다.','',
        '## Part 1 — 양쪽 성공 run의 paired 속도 비교','',
        'Index 9–24, D750. 기술 검증 PASS 및 양쪽 SUCCESS 교집합만 사용했다. 실패 run 시간을 90초로 대입하지 않았다. Paired index 단위 percentile bootstrap 20,000회, seed 20261025. 평균 차이와 차이의 median 모두 CI를 계산했다. 주 판정에는 **평균 goal 시간 차이의 CI**를 사용한다.','']
    pr=[]
    for row in pairs:
        for metric in ('goal_time_s','mean_speed_m_s'):
            x=row['metrics'][metric];pr.append(dict(pair=row['pair'],metric=metric,n=row['n'],indices=row['indices'],mean=x.get('mean'),median=x.get('median'),mean_ci95=x.get('mean_ci95'),median_ci95=x.get('median_ci95')))
    lines+=table(pr,['pair','metric','n','indices','mean','median','mean_ci95','median_ci95'])
    lines+=['',f"주 판정: **{p['verdict']}**. 기술 제외: {json.dumps(s['static_exclusions'])}.",
        '성공 조건부 분석이므로 전체 run의 인과적 속도 개선이나 실패율 효과와 동일하지 않다. 동일 index라도 closed-loop RGB와 prediction은 달라진다.','',
        '### 속도 메커니즘 (run별 원자료: speed_mechanisms.csv)','',
        '`|κ|>2`는 요청한 진단 기준이며 `|κ|>8` 포화 flag와 다르다. 비율은 실제 종료에서 자른 9Hz 명령 유지시간으로 가중하고 유효한 비정지 PP 시간으로 나눈다. CURV target<0.2와 실제 v<0.2를 분리했다. Heading/cross-track은 기존 20mm tangent 검사로 계산하며 FRESH switch와 보정 교체는 별도 저장했다.','']
    mr=[]
    for m in ('CURV','SELECT','GRAPH','SELECT+GRAPH'):
        for success in (True,False):
            rs=[r for r in mech if r['method']==m and r['success']==success]
            if not rs:continue
            row=dict(method=m,success=success,n=len(rs))
            for k in ('kappa_over2_fraction','endpoint_clamp_fraction','curv_target_below_point2_fraction','actual_speed_below_point2_fraction'):
                row[k]=stat([r[k] for r in rs])['mean']
            row['heading_run_median_mean_rad']=stat([r['switch_heading']['median'] for r in rs])['mean'];row['cross_track_run_median_mean_m']=stat([r['switch_cross_track']['median'] for r in rs])['mean'];mr.append(row)
    lines+=table(mr,list(mr[0]))
    diag=[]
    for k in ('kappa_over2_fraction','endpoint_clamp_fraction','curv_target_below_point2_fraction','actual_speed_below_point2_fraction','switch_heading_median_rad','switch_cross_track_median_m'):
        v=p['metrics'][k];diag.append(dict(metric=k,mean_difference=v.get('mean'),mean_ci95=v.get('mean_ci95')))
    lines+=['','주 paired 교집합의 SELECT+GRAPH − SELECT 메커니즘 차이:','']+table(diag,list(diag[0]))
    lines+=['','![Paired goal differences](../research/results/phase10a/paired_goal_time.png)','','## Part 2 — GRAPH-v6 실패 타임라인','',
        '12개 GRAPH-v6 run 전체를 분석했다. 실패 시각은 실제 종료 시각(충돌, 복도, timeout 구분)이다. 공개 monotonic 시각은 그 이후 첫 실제 72Hz pose에 매핑했다. 통과는 x>상자 뒷면+반경이며 안전 통과 판정이 아니다. 의도 해제는 x>뒷면+0.30; 재진입 시 의도 재활성 구간도 보존했다.','']
    lines+=table(failures,['key','termination','spawn_s','public_s','intent_intervals','pass_s','deactivate_s','failure_s','failure_pose','recross_after_pass'])
    lines+=['','### 통과 후 3초: 실제 복귀와 RAW fallback','']
    failed_windows=[w for w in windows if not w['success']]
    lines+=table(failed_windows,['key','available','start_s','end_s','truncated','y_start_m','y_end_m','abs_y_change_m','centerward_heading_fraction','corrected_fraction_of_valid','raw_fraction_of_valid','fresh_calls','fresh_centerward','fresh_not_centerward'])
    lines+=['','`centerward_heading_fraction`은 yaw의 횡방향 성분이 y=0을 향한 비율이다. FRESH 복귀 여부는 native endpoint−B의 횡방향 부호 진단이며 실제 PP rollout이라고 해석하지 않는다. 전체 y/yaw 표본은 post_pass_windows.json에 보존했다.','',
        '### 의도 해제 후 첫 5개 Graph 호출과 이전 prior','',
        '기존 `previous_stencil`(B의 prior 최근접 투영 + 현재 경로 정규화 arclength)을 그대로 사용했다. prior 경로가 없는 경우 거리를 만들지 않았다. 최종 solver 출력과 실제 ACCEPTED 적용을 분리한다.','']
    lines+=table([j for j in prior if j['key'] in {f['key'] for f in failures}],['key','job_id','disposition','previous_prior_present','prior_minus_fresh_y_mean_m','prior_fresh_y_rms_m','result_fresh_y_rms_m','result_prior_y_rms_m','closer_to','result_sideward_shift_m','previous_prior_factor_cost'])
    lines+=['','### 측면 factor 코드/로그 근거','',
        '`nomad_phase9/graph.py`는 매 호출마다 Graph를 새로 만들고 `public_intent`가 있을 때만 heuristic XY와 강제 side를 추가한다. 해제 후에는 v4의 `side_labels(FRESH, public_geometry)`가 새로 계산된다. `previous_accepted` 경로는 해제 시 초기화되지 않으므로 prior는 남지만 강제 heuristic side 상태의 지속과는 다르다.',
        f"Inactive 호출 {dec['C2_SIDE_FACTOR_PERSISTS']['inactive_calls']}개, heuristic factor 잔존 {dec['C2_SIDE_FACTOR_PERSISTS']['heuristic_factor_remaining']}개, native side 재판정 {dec['C2_SIDE_FACTOR_PERSISTS']['recomputed_native_side_defined']}개.",
        'factor 적용/잔존은 초기화 성공 시 solver factor_costs와 교차 확인했다. 비용 0은 factor가 없다는 뜻으로 사용하지 않았다.','',
        '### D0 미수렴 분포','']
    lines+=table(stages,['stage','calls','solver_calls','nonconverged','nonconvergence_per_call','nonconvergence_per_solve','sdf_enforced','initialization_rejected','zero_speed_rejected','superseded','superseded_fraction'])
    total=dec['C4_D0_NONCONVERGENCE']['total']
    lines += ['',f"D0 합계: {total['nonconverged']}/{total['calls']} calls 미수렴, 실제 solver {total['solver_calls']}회. 초기화 거부와 SUPERSEDED는 solver 성공 여부와 별개다. 단계는 job dispatch 시점 기준이다.",
        'SDF enabled는 공개 obstacle을 제약에 넣었음을 뜻한다. 최종 active-set SDF row는 로그에 없어 미수렴을 SDF 단독 원인으로 확정할 수 없다. 모든 미수렴의 이전/현재/다음 저장 호출 길이·clearance는 d0_nonconvergence.csv에 있다.','']
    nn=[]
    for stage in ('BEFORE_PUBLIC','INTENT_ACTIVE','INTENT_INACTIVE'):
        js=[j for j in jobs if j['delay_s']==0 and j['stage']==stage and j['nonconverged']]
        if not js:continue
        row=dict(stage=stage,n=len(js))
        for key in ('previous_fresh_length_m','fresh_length_m','result_length_m','next_fresh_length_m','previous_fresh_obstacle_clearance_m','fresh_obstacle_clearance_m','result_obstacle_clearance_m','next_fresh_obstacle_clearance_m'):
            row[key]=stat([j[key] for j in js])['median']
        nn.append(row)
    if nn:lines+=table(nn,list(nn[0]))
    lines+=['','### s = −1 paired 조건 비교','',
        'D750 짝수 index 비교. 동일 seed여도 world 배치/RGB/선택 경로가 다르므로 같은 observation의 정책 반사실 비교가 아니다. native side는 장애물 중심 x에서 ±(반폭+반경) 밖의 분명한 교차만 분류하며 나머지는 UNDEFINED이다.','']
    lines+=table([r for r in runs if r['s']==-1 and r['delay_s']==.75],['index','method','success','termination','heuristic_side','pass_s','native_definite_count','native_conflict_count','native_undefined_count'])
    lines+=['','### 원인 후보 판정 (독립)','']
    lines+=table([dict(candidate=k,verdict=v['verdict'],evidence={a:b for a,b in v.items() if a not in ('verdict','stages','total')}) for k,v in dec.items()],['candidate','verdict','evidence'])
    lines+=['','SUPPORTED는 저장 로그에 해당 기제가 관찰됐다는 후보 근거다. prior 제거 실험이나 intent 반전 재실행 없이 실패의 단독 인과 원인/개선 효과는 확정할 수 없다. C3의 직선 복도 복귀는 solver 목표가 아니라 로그의 FRESH 방향 진단이다.','',
        '![Graph failure y](../research/results/phase10a/graph_failure_y.png)','','### 수정안 후보 (미구현)','']
    proposals=[]
    if dec['C3_NO_RECENTER']['verdict']=='SUPPORTED':proposals.append('통과 후 intent를 종료하는 것과 별도로, 안전한 centerline 복귀 목표가 필요한지 제한된 ablation으로 검증한다.')
    if dec['C1_PRIOR_DRAG']['verdict']!='NOT_SUPPORTED':proposals.append('의도 해제 직후 prior를 제거/감쇠하는 대조군으로 이전 보정 prior의 독립 효과를 검증한다.')
    if dec['C4_D0_NONCONVERGENCE']['verdict']=='SUPPORTED':proposals.append('단계별 SDF·경계 equality·trust 제약의 위반 row를 기록해 D0 미수렴의 실제 제약 원인을 구분한다.')
    if len(proposals)<3 and dec['C5_INTENT_CONFLICT']['verdict']=='SUPPORTED':proposals.append('heuristic side와 native의 분명한 반대 side가 만나는 호출에서 intent 충돌 처리 규칙을 별도 검증한다.')
    lines += ['- '+p for p in proposals[:3]]
    lines += ['', '### 검증 및 한계','',
        f"{json.dumps(s['validation'],ensure_ascii=False)}. 입력 hash는 기존 Phase8/9 audit와 대조하고 분석 종료 전 불변을 다시 확인했다.",
        'paired 유효 수, 제외 사유, 12개 GRAPH-v6 전체 호출 및 5개 실패를 저장했다. D0에는 INTENT-SPLICE comparator가 없으므로 생성/대체하지 않았다. 신규 solve·주행·추론, parameter 수정, 추가 시각화 없음.','']
    DOC.write_text('\n'.join(lines))


if __name__=='__main__':
    main()
