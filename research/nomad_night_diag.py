"""Requested A/B/C saved-log diagnosis only; no simulator, solver or EC/HMM replay."""
import argparse,csv,hashlib,json,math,time
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle,Polygon,Circle
from matplotlib.lines import Line2D
from nomad_run_plots import ROOT,Inputs,obstacle_corners
from nomad_isaac.common import local_to_world

NIGHT=('E1','E3');METHODS=('CUT','GRAPH-HO','OURS-R3');DEV=('phase47c','phase52p','phase53p','h1v2_trial')
LABELS={'APPLIED':'적용','NO_SOLUTION':'해 없음','CERTIFICATE_FAIL':'인증 실패','EC_REJECT':'EC 거절','SUPERSEDED':'새 chunk에 밀림','LATE':'계산 늦음','OTHER':'기타'}
I=Inputs();CACHE={}
def read_run(r):
    key=r['output']
    if key not in CACHE:
        p=Path(key);s=I.json(p/'summary.json');traj=list(csv.DictReader(I.text(p/'agent_trajectory.csv').splitlines()))
        CACHE[key]=dict(root=p,summary=s,cfg=s['scenario'],t=np.array([float(x['simulation_time_s']) for x in traj]),
            xy=np.array([[float(x['x_m']),float(x['y_m'])] for x in traj]),distance=np.array([float(x['goal_distance_m']) for x in traj]))
    return CACHE[key]
def rows(p):return I.rows(p)
def q(x,a):return float(np.quantile(x,a)) if len(x) else None
def fmt(x):
    if x is None:return '—'
    if isinstance(x,float):return f'{x:.4g}'
    if isinstance(x,(list,tuple)):return ', '.join('—' if v is None else f'{v:.1f}' if isinstance(v,float) else str(v) for v in x)
    return str(x).replace('|','/')
def table(data,keys=None):
    if not data:return '자료 없음'
    keys=keys or list(data[0]);return '\n'.join(['| '+' | '.join(keys)+' |','|'+'|'.join(['---']*len(keys))+'|']+['| '+' | '.join(fmt(r.get(k)) for k in keys)+' |' for r in data])
def delay(e):return 'D075' if e=='E1' else 'D150'
def timestamp_pose(d,t):
    ix=int(np.argmin(np.abs(d['t']-t)));assert abs(d['t'][ix]-t)<1/72+1e-8
    return d['xy'][ix],float(d['distance'][ix])
def boxes_of(d):
    dyn=d['summary'].get('dynamic_obstacle') or {};return dyn.get('boxes',[dyn] if dyn.get('spawn') else [])

def classify_trigger(result,applied):
    if applied:return 'APPLIED'
    if not result:return 'OTHER'
    disposition=result.get('disposition','');n=result.get('numeric_result') or {};samples=n.get('results',[])
    if 'SUPERSEDED' in disposition:return 'SUPERSEDED'
    if 'TIMEOUT' in disposition or 'LATE' in disposition:return 'LATE'
    if n.get('ec_checks') and not any(c['passed'] for c in n['ec_checks']) and n.get('ec_original_selected_sample') is not None:return 'EC_REJECT'
    if disposition=='APPLICATION_UNSAFE':return 'CERTIFICATE_FAIL'
    if any((s.get('solver_success') and s.get('constraint_violation',float('inf'))<=1e-7 and s.get('certificate_pass') is False) or 'CERTIFICATE' in s.get('disposition','') for s in samples):return 'CERTIFICATE_FAIL'
    if disposition=='REJECTED' and samples:return 'NO_SOLUTION'
    return 'OTHER'

def section_a(night):
    events=[];applied_rows=[];summary=[];association=[]
    for e in NIGHT:
        lat=[];counts=Counter();assoc=Counter()
        for r in night[e]:
            if r['method']!='OURS-R3':continue
            d=read_run(r);es=rows(d['root']/'detour.jsonl');triggers=[x for x in es if x['event']=='TRIGGER']
            outcomes={x['job_id']:x for x in es if x['event']=='RESULT'};apps={x['job_id']:x for x in es if x['event']=='APPLIED'};ends={x['job_id']:x for x in es if x['event']=='END'}
            app_times=sorted(x['simulation_time_s'] for x in apps.values())
            for trigger in triggers:
                jid=trigger['job_id'];a=apps.get(jid);result=outcomes.get(jid);label=classify_trigger(result,a);counts[label]+=1
                dt=a['simulation_time_s']-trigger['simulation_time_s'] if a else None
                if dt is not None:lat.append(dt)
                n=(result or {}).get('numeric_result') or {}
                events.append(dict(지연=delay(e),run=r['key'],job=jid,trigger=trigger['trigger'],trigger_s=trigger['simulation_time_s'],결과=LABELS[label],raw_disposition=(result or {}).get('disposition'),적용지연_s=dt,
                    numeric_accepted=sum(bool(s.get('accepted')) for s in n.get('results',[])),EC_tested=len(n.get('ec_checks',[]))))
                if not a:continue
                start=a['simulation_time_s'];end=ends.get(jid,{}).get('simulation_time_s',r['duration_s']);next_app=min((t for t in app_times if t>start+1e-9),default=r['duration_s'])
                eligible=[];during=[];after=[]
                for bi,b in enumerate(boxes_of(d),1):
                    spawn=b['spawn']['simulation_time_s'];passage=(b.get('evaluation') or {}).get('passage');pt=passage.get('simulation_time_s') if passage else None
                    if spawn>start+1e-9 or (pt is not None and pt<=start+1e-9):continue
                    eligible.append(bi)
                    if pt is not None and start+1e-9<pt<=end+1e-9:during.append(bi)
                    elif pt is not None and end+1e-9<pt<=next_app+1e-9:after.append(bi)
                tag='R3_ACTIVE_PASS' if during else 'AFTER_HANDOVER_PASS' if after else 'NO_OBSERVED_PASS' if eligible else 'NO_UNPASSED_SPAWNED_BOX'
                assoc[tag]+=1
                applied_rows.append(dict(지연=delay(e),run=r['key'],job=jid,적용_s=start,종료_s=end,종료사유=ends.get(jid,{}).get('reason','RUN_END_NO_END_RECORD'),
                    적용시_미통과상자=eligible,실행중_통과상자=during,넘김후_다음우회전_통과상자=after,관측연관=tag))
        expected=53 if e=='E1' else 100;assert sum(counts.values())==expected
        summary.append(dict(지연=delay(e),트리거=sum(counts.values()),**{v:counts[k] for k,v in LABELS.items()},적용지연_p50_s=q(lat,.5),적용지연_p95_s=q(lat,.95)))
        association.append(dict(지연=delay(e),적용=sum(assoc.values()),실행중통과=assoc['R3_ACTIVE_PASS'],넘김후다음우회전통과=assoc['AFTER_HANDOVER_PASS'],미통과=assoc['NO_OBSERVED_PASS'],해당상자없음=assoc['NO_UNPASSED_SPAWNED_BOX']))
    return summary,events,association,applied_rows

def angle_to_ref(end,B,reference):
    v=np.asarray(end)-np.asarray(B)
    if np.linalg.norm(v)<1e-9 or np.linalg.norm(reference)<1e-9:return None
    return float(np.degrees(np.arctan2(reference[0]*v[1]-reference[1]*v[0],reference@v)))
def side(a):
    if a is None:return 'NONE'
    if abs(a)>90:return 'BACK'
    return 'LEFT' if a>1e-10 else 'RIGHT' if a< -1e-10 else 'STRAIGHT'
def path_hash(p):return hashlib.sha256(np.asarray(p,dtype=np.float64).tobytes()).hexdigest()

def section_b(night):
    all_chunks=[];summaries=[];example=[];target_keys=[];blockset=[]
    for e in NIGHT:
        target=[r for r in night[e] if r.get('primary_cause')=='DETOUR_FAIL' and r['classification']=='TIMEOUT' and not r['box_passage']]
        target_keys.extend(r['key'] for r in target);blocks=sorted({(r['scene'],r['index']) for r in target});blockset.extend((e,*b) for b in blocks)
        for r in night[e]:
            if (r['scene'],r['index']) not in blocks:continue
            d=read_run(r);boxes=boxes_of(d);first_spawn=min((b['spawn']['simulation_time_s'] for b in boxes),default=None)
            received=rows(d['root']/'received.jsonl');fresh={x['id']:x for x in rows(d['root']/'events.jsonl')}
            ec=rows(d['root']/'exec_cert.jsonl');checks=defaultdict(list);installs=defaultdict(list)
            for x in ec:
                if x['event']=='CHECK' and x.get('scope')=='INSTALL':checks[x['check_tick']].append(x)
                if x['event']=='INSTALL' and x.get('state')=='NORMAL':installs[(x['apply_tick'],x['id'])].append(x)
            saved_native=defaultdict(list)
            ho=rows(d['root']/'graph_ho.jsonl')
            for item in ho:
                if item['event']=='INSTALL':saved_native[(item['tick'],item['id'])].append(np.asarray(item['original_candidate_world']))
            if not ho:
                for item in rows(d['root']/'repair.jsonl'):
                    if item['event']=='PATH_APPLIED' and item['kind']=='SAFE':saved_native[(item['tick'],item['id'])].append(np.asarray(item['path_world']))
            nodes=I.json(Path(d['cfg']['topomap_manifest']))['nodes'];node_xy={int(n['node_id']):np.array(n['world_pose'][:2]) for n in nodes}
            chunk_rows=[];paths=[];seen=set();previous=None;flips=0
            for received_event in received:
                ident=received_event['id']
                if ident in seen or received_event.get('terminal_unapplied') or received_event.get('latched_sim_s') is None:continue
                seen.add(ident);ev=fresh.get(ident);t=ev['application_sim_s'] if ev else received_event['latched_sim_s']
                if first_spawn is None or t<first_spawn or t>r['duration_s']+1e-8:continue
                B=np.asarray(ev['agent_pose_at_switch'])[:2] if ev else timestamp_pose(d,t)[0]
                packet=ev or received_event;local=packet.get('overnight_metric_samples')
                if local is None:
                    f=d['root']/'model/derived'/f'{ident:04d}.npz';raw=f.read_bytes();st=f.stat();I.files[str(f)]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=st.st_size,mtime_ns=st.st_mtime_ns)
                    import io
                    with np.load(io.BytesIO(raw),allow_pickle=False) as z:local=z['metric'].copy()
                worlds=np.array([local_to_world(np.asarray(p),packet['observation_pose']) for p in local]);assert worlds.shape[0]==8
                meta=packet['topomap'];next_node=min(int(meta['closest_node'])+1,int(meta['goal_node']));ref=node_xy[next_node]-B
                angles=[angle_to_ref(p[-1],B,ref) for p in worlds];labels=[side(a) for a in angles]
                selection=(ev or {}).get('phase16',{}).get('selection');depth_safe=sum(c['safe'] for c in selection['candidates']) if selection else None
                tick=round(t*72);key_to_idx=defaultdict(list)
                for i,p in enumerate(worlds):key_to_idx[path_hash(p)].append(i)
                # Match preserved native coordinates, not recomputed EC. NumPy
                # versions can differ by1ULP in the world-frame transform.
                for saved_path in saved_native[(tick,ident)]:
                    if saved_path.shape==worlds[0].shape:
                        close=[i for i,p in enumerate(worlds) if np.allclose(saved_path,p,rtol=0,atol=1e-12)]
                        key_to_idx[path_hash(saved_path)].extend(close)
                tested=set();passed=set();fullpassed=set();slowpassed=set();unmatched=set()
                for check in checks[tick]:
                    indices=key_to_idx.get(check['path_sha256'],[]);tested.update(indices)
                    if not indices:unmatched.add(check['path_sha256'])
                    if check['passed']:
                        passed.update(indices);(slowpassed if check.get('speed_cap_m_s') is not None else fullpassed).update(indices)
                installed=installs.get((tick,ident),[]);install=installed[-1] if installed else None
                chosen=int(install['selected_sample']) if install and install.get('selected_sample') is not None else None
                chosen_angle=angles[chosen] if chosen is not None else None;chosen_side=side(chosen_angle)
                changed=previous in ('LEFT','RIGHT') and chosen_side in ('LEFT','RIGHT') and previous!=chosen_side
                flips+=int(changed);previous=chosen_side
                if chosen is not None:paths.append(dict(path=worlds[chosen].tolist(),B=B.tolist(),side=chosen_side,time=t,angle=chosen_angle))
                row=dict(지연=delay(e),run=r['key'],chunk=ident,시각_s=t,B_x=float(B[0]),B_y=float(B[1]),next_node=next_node,
                    후보각도_0to7=angles,depth_SAFE=depth_safe,EC_검사후보=len(tested),EC_미매칭경로=len(unmatched),EC_PASS=len(passed) if tested else None,
                    EC_full_PASS=len(fullpassed) if tested else None,EC_slow_PASS=len(slowpassed) if tested else None,
                    SAFE_EC미검사_상한=(len({c['index'] for c in selection['candidates'] if c['safe']}-tested) if selection else None),
                    선택후보=chosen,선택각도=chosen_angle,방향=chosen_side,좌우전환=bool(changed),
                    설치경로=install.get('kind') if install else None,선택없음상태=(ev or {}).get('phase20',{}).get('source','NOT_APPLIED') if chosen is None else None)
                chunk_rows.append(row)
            all_chunks.extend(chunk_rows)
            aa=[abs(v) for row in chunk_rows for v in row['후보각도_0to7'] if v is not None];selected=[row for row in chunk_rows if row['선택후보'] is not None]
            distributions=[sum(a<20 for a in aa),sum(20<=a<45 for a in aa),sum(45<=a<=90 for a in aa),sum(a>90 for a in aa)]
            summaries.append(dict(지연=delay(e),run=r['key'],역할='DETOUR_FAIL' if r['key'] in target_keys else '같은블록비교',분류=r['classification'],상자통과=r['box_passage'],
                출현후chunk=len(chunk_rows),각도표본=len(aa),후보_abs20미만=distributions[0],후보_20to45=distributions[1],후보_45to90=distributions[2],후보_90초과=distributions[3],
                후보_abs각도_p50=q(aa,.5),후보_abs각도_p95=q(aa,.95),depth_SAFE중앙값=q([row['depth_SAFE'] for row in chunk_rows if row['depth_SAFE'] is not None],.5),
                EC검사후보합=sum(row['EC_검사후보'] for row in chunk_rows),EC_PASS관측합=sum(row['EC_PASS'] or 0 for row in chunk_rows),
                EC_미매칭경로합=sum(row['EC_미매칭경로'] for row in chunk_rows),SAFE_EC미검사_상한합=sum(row['SAFE_EC미검사_상한'] or 0 for row in chunk_rows),선택chunk=len(selected),
                좌선택=sum(row['방향']=='LEFT' for row in selected),우선택=sum(row['방향']=='RIGHT' for row in selected),뒤선택=sum(row['방향']=='BACK' for row in selected),좌우전환=flips,
                선택없음=len(chunk_rows)-len(selected),첫spawn_s=first_spawn))
            if (e,r['scene'],r['index'])==blockset[0]:example.append((r,d,paths))
    assert len(target_keys)==13 and len(summaries)==27 and len(blockset)==9
    return summaries,all_chunks,example,target_keys,blockset


def draw_b(example):
    colors={'LEFT':'#0072B2','RIGHT':'#E69F00','BACK':'#C51B30','STRAIGHT':'#555555','NONE':'#AAAAAA'}
    example=sorted(example,key=lambda x:METHODS.index(x[0]['method']));fig,axes=plt.subplots(1,3,figsize=(18,7))
    fig.subplots_adjust(left=.05,right=.98,top=.80,bottom=.18,wspace=.18)
    for ax,(r,d,paths) in zip(axes,example):
        c=d['cfg'];b=c['corridor'];x0,x1=b['xmin'],b['xmax'];y0,y1=b.get('ymin',-b['half_width']),b.get('ymax',b['half_width'])
        ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec='#777777',lw=2))
        for o in c['obstacles']:ax.add_patch(Polygon(obstacle_corners(o),fc='#D1D1D1',ec='#888888',lw=.7))
        for box in boxes_of(d):ax.add_patch(Polygon(obstacle_corners(box['spawn']['obstacle']),fc='#AC88BA',ec='#775388',alpha=.45))
        ax.plot(*d['xy'].T,c='#555555',lw=1.,alpha=.5)
        for name,color in colors.items():
            lines=[p['path'] for p in paths if p['side']==name]
            if lines:ax.add_collection(LineCollection(lines,colors=color,linewidths=1.,alpha=.55,zorder=4))
        ax.scatter(*c['goal_pose'][:2],c='#00805B',marker='*',s=90);ax.add_patch(Circle(c['goal_pose'][:2],.5,fill=False,ls='--',ec='#00805B',lw=.8))
        ax.set(xlim=(x0-.1,x1+.1),ylim=(y0-.1,y1+.1),xlabel='x(m)',ylabel='y(m)');ax.set_aspect('equal');ax.grid(alpha=.15)
        ax.set_title(f"{r['method']} | {r['classification']}\ninstalled native choices {len(paths)}",fontsize=11)
    handles=[Line2D([],[],c=colors[k],lw=2,label=k) for k in ('LEFT','RIGHT','BACK','STRAIGHT')]+[Line2D([],[],c='#555555',lw=1,label='actual72Hz trajectory')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.07),ncol=5,frameon=False)
    fig.suptitle('B fixed first target block: '+example[0][0]['scene']+' / seed'+str(example[0][0]['index'])+'\nOnly actually selected native candidate paths; direction relative to next topomap node at B',fontsize=12)
    f=ROOT/'docs/figures/nightdiag_B_selected.png';fig.savefig(f,dpi=150);plt.close(fig);return f.name

def goal_records(r,cohort,pose_time='delivery'):
    d=read_run(r);root=d['root'];received={x['id']:x for x in rows(root/'received.jsonl')}
    declared=I.json(root/'declared_arrival.json') if (root/'declared_arrival.json').exists() else None
    out=[];excluded=Counter()
    for inference in rows(root/'model/inference.jsonl'):
        m=inference.get('topomap',{})
        if not m.get('hmm'):excluded['NON_HMM_INFERENCE']+=1;continue
        if m.get('closest_node')!=m.get('goal_node'):continue
        goal=int(m['goal_node']);ids=m.get('candidate_ids',[]);values=m.get('distances',[])
        if goal not in ids or len(ids)!=len(values):excluded['GOAL_DISTANCE_NOT_LOGGED']+=1;continue
        predicted=float(values[ids.index(goal)])
        if not np.isfinite(predicted):excluded['NONFINITE_PREDICTION']+=1;continue
        identifier=inference['id'];receipt=received.get(identifier)
        if pose_time=='observation':
            actual=float(np.linalg.norm(np.asarray(inference['observation_pose'])[:2]-np.asarray(d['cfg']['goal_pose'])[:2]));t=inference['observation_sim_s'];source='OBSERVATION_POSE'
        elif declared is not None and declared['id']==identifier:
            t=declared['simulation_time_s'];actual=timestamp_pose(d,t)[1];source='DECLARATION_SAVED_GOAL_DISTANCE'
        elif receipt and not receipt.get('terminal_unapplied') and receipt.get('latched_sim_s') is not None and receipt['latched_sim_s']<=r['duration_s']+1e-8:
            t=receipt['latched_sim_s'];actual=timestamp_pose(d,t)[1];source='LATCHED_SAVED_GOAL_DISTANCE'
        else:excluded['NO_OBSERVED_DELIVERY_POSE']+=1;continue
        out.append(dict(cohort=cohort,run=r['key'],method=r['method'],scene=r['scene'],seed=r['index'],inference=identifier,d_goal=predicted,
            actual_goal_distance_m=actual,within_05=bool(actual<=.5),time_s=t,pose_time=source))
    return out,dict(excluded)

def fit_tau(points):
    # Every distinct finite observed prediction is a permissible cutoff. Ties
    # enter together under <=. No scene-specific fit, floor onN, or retuning.
    curve=[]
    for value in sorted({p['d_goal'] for p in points}):
        accepted=[p for p in points if p['d_goal']<=value];correct=sum(p['within_05'] for p in accepted);n=len(accepted)
        curve.append(dict(tau=value,n=n,within_05=correct,outside_05=n-correct,precision=correct/n,eligible=20*correct>=19*n))
    eligible=[p for p in curve if p['eligible']]
    return (max(eligible,key=lambda p:p['tau']) if eligible else None),curve

def section_c(night,pose_time):
    dev=[];coverage=[];seen=set()
    for phase in DEV:
        source=I.json(ROOT/f'research/results/{phase}/runs.json');counts=Counter();added=[]
        for r in source:
            assert r['index'] not in (225,226),'NIGHT seed leaked into calibration'
            if r['output'] in seen:counts['DUPLICATE_OUTPUT']+=1;continue
            seen.add(r['output'])
            if r['technical_validation']!='PASS':counts['TECHNICAL_FAILURE_RUN']+=1;continue
            values,missing=goal_records(r,phase,pose_time);dev.extend(values);added.extend(values);counts.update(missing)
        coverage.append(dict(phase=phase,registered_runs=len(source),HMM_MAP_goal_points=len(added),qualified_runs=len({p['run'] for p in added}),
            비HMM추론=counts['NON_HMM_INFERENCE'],전달pose없음=counts['NO_OBSERVED_DELIVERY_POSE'],목표거리미기록=counts['GOAL_DISTANCE_NOT_LOGGED'],기술실패run=counts['TECHNICAL_FAILURE_RUN']))
    selected,curve=fit_tau(dev);tau=selected['tau'] if selected else None
    # Persist/fix nothing into runtime; this variable is applied once to NIGHT.
    evaluated=[];wrong_total=0;success_total=0
    for e in NIGHT:
        for r in night[e]:
            if not (r.get('wrong_stop') or r.get('success')):continue
            wrong_total+=bool(r.get('wrong_stop'));success_total+=bool(r.get('success'))
            d=read_run(r);declaration=I.json(d['root']/'declared_arrival.json');inf=next(x for x in rows(d['root']/'model/inference.jsonl') if x['id']==declaration['id'])
            m=inf['topomap'];ids=m['candidate_ids'];goal=m['goal_node'];assert m['closest_node']==goal and m.get('hmm')
            predicted=float(m['distances'][ids.index(goal)]) if goal in ids else None
            evaluated.append(dict(지연=delay(e),run=r['key'],기존분류=r['classification'],기존성공=bool(r['success']),기존잘못된도착=bool(r['wrong_stop']),
                선언_s=declaration['simulation_time_s'],d_goal=predicted,기존선언거리_m=r['stop_distance_m'],
                기존시점선언차단=(predicted>tau) if tau is not None and predicted is not None else None,
                성공수재판정=False))
    assert wrong_total==21 and success_total==27
    outcomes=[]
    for group in ('D075','D150','ALL'):
        rr=[r for r in evaluated if group=='ALL' or r['지연']==group];bad=[r for r in rr if r['기존잘못된도착']];good=[r for r in rr if r['기존성공']]
        outcomes.append(dict(지연=group,기존잘못된도착=len(bad),그시점선언차단=sum(r['기존시점선언차단'] is True for r in bad) if tau is not None else None,
            기존성공=len(good),성공선언차단_지연또는소실가능=sum(r['기존시점선언차단'] is True for r in good) if tau is not None else None,
            임계값적용불가=sum(r['기존시점선언차단'] is None for r in rr)))
    return coverage,dev,selected,curve,evaluated,outcomes

def draw_c(points,curve,selected):
    fig,axes=plt.subplots(1,2,figsize=(12,4.6));fig.subplots_adjust(left=.08,right=.94,bottom=.17,top=.82,wspace=.3)
    x=[r['tau'] for r in curve];y=[r['precision'] for r in curve]
    axes[0].step(x,y,where='post',color='#0072B2',lw=1.4,label='empirical P(distance<=0.5m | d_goal<=tau)')
    axes[0].axhline(.95,color='#B5414A',ls='--',lw=1,label='required95%');axes[0].set(xlabel='tau (raw NoMaD distance units)',ylabel='Empirical precision',ylim=(0,1.05));axes[0].grid(alpha=.15)
    ax=axes[0].twinx();ax.step(x,[r['n'] for r in curve],where='post',c='#7A7A7A',ls=':',lw=1,label='N accepted');ax.set_ylabel('Accepted inference count',color='#777777')
    if selected:
        axes[0].axvline(selected['tau'],c='#009E73',ls='--');axes[0].scatter([selected['tau']],[selected['precision']],c='#009E73',s=35,zorder=5)
        axes[0].set_title(f"largest eligible tau={selected['tau']:.6g}; N={selected['n']}")
    else:axes[0].set_title('NO_ELIGIBLE_TAU; no NIGHT classification imposed')
    axes[0].legend(loc='lower left',fontsize=7)
    a=np.array([p['d_goal'] for p in points]);b=np.array([p['actual_goal_distance_m'] for p in points])
    axes[1].scatter(a,b,s=16,c=np.where(b<=.5,'#0072B2','#D55E00'),alpha=.7)
    axes[1].axhline(.5,c='#B5414A',ls='--',lw=1)
    if selected:axes[1].axvline(selected['tau'],c='#009E73',ls='--',lw=1)
    axes[1].set(xlabel='d_goal (raw NoMaD distance units)',ylabel='Saved goal distance (m)',title='Development logs only; HMM MAP=goal');axes[1].grid(alpha=.15)
    fig.suptitle('C: fixed95% empirical precision criterion; no NIGHT data in threshold selection',fontsize=12)
    f=ROOT/'docs/figures/nightdiag_C_tau.png';fig.savefig(f,dpi=150);plt.close(fig);return f.name

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--goal-pose-time',choices=('delivery','observation'),default='delivery');a=parser.parse_args();start=time.monotonic()
    night={e:I.json(ROOT/f'research/results/night20261111/{e}/runs.json') for e in NIGHT}
    a_summary,a_events,associations,a_applied=section_a(night)
    b_summary,b_chunks,example,targets,blocks=section_b(night);b_figure=draw_b(example)
    c_coverage,c_points,selected,c_curve,c_night,c_summary=section_c(night,a.goal_pose_time);c_figure=draw_c(c_points,c_curve,selected)
    I.unchanged();digest=hashlib.sha256(json.dumps({p:r['sha256'] for p,r in sorted(I.files.items())},sort_keys=True).encode()).hexdigest()
    tau_text=('**NO_ELIGIBLE_TAU**: 관측된 cutoff 중95%를 충족하는 값이 없어 NIGHT에는 임계값을 적용하지 않았다.' if selected is None else
        f"선택 τ = **{selected['tau']!r}** (NoMaD 원거리 출력 단위). 선택 범위 n={selected['n']}, 실제0.5m 이내={selected['within_05']}, 밖={selected['outside_05']}, 경험 정밀도={100*selected['precision']:.3f}%.")
    lines=['# NIGHT 로그 진단 — 20261111',
        '범위는 A·B·C뿐이다. E1(D075)·E3(D150) 저장결과를 사용했다. 시뮬레이션·solver·EC 재검사·HMM 재생은 없고 기존 성공/실패/통과 수는 수정하지 않았다. E2는 이 분석에서 제외했다(잘못된 도착21건=E1 14+E3 7).',
        '## A. R3 trigger153건의 처리 결과',table(a_summary),
        '분류 우선순위: APPLIED 기록 → SUPERSEDED → TIMEOUT/LATE → 수치 수락 해가 있지만 EC가 전부 거절 → APPLICATION_UNSAFE 또는 수렴·제약 통과 뒤 certificate 실패 → 허용 해 없음(비수렴/진전 미달 포함) → 기타. 실패한 초기값의 certificate=False만으로 job을 인증 실패라 세지 않는다. 최종 적용 여부를 기준으로 trigger마다 한 범주만 부여했다. 적용 지연은 저장 simulation_time_s의 APPLIED−TRIGGER이며 적용된15/24건만 p50/p95에 포함한다.',
        '### 적용된 우회의 상자 통과와 시간상 연관',table(associations),
        '적용 시 이미 출현했고 아직 통과하지 않은 상자만 대상이다. `R3_ACTIVE_PASS`는 적용 이후~저장 END(없으면run종료) 사이에 통과한 경우, `AFTER_HANDOVER_PASS`는 END 뒤~다음 R3 적용/run종료 사이에 통과한 경우다. 둘 다 없으면 미통과, 대상 상자가 없으면 N/A다. **이는 로그의 시간상 동반 여부이며, 우회를 쓰지 않았을 반사실이 없어 인과적 기여를 확정하지 않는다.**',
        table(a_applied),'<details><summary>A 전체153 trigger 원장</summary>\n\n'+table(a_events)+'\n\n</details>',
        '## B. 상자 미통과 시간초과와 같은 블록 비교',
        f"대상은 기존 primary_cause=DETOUR_FAIL AND classification=TIMEOUT AND box_passage=False인13run, 해당9블록의 세 방법27run이다. 예시는 결과로 고르지 않고 E1→E3, 블록명·seed 정렬의 첫 블록 **{example[0][0]['scene']} / {example[0][0]['index']}**로 고정했다.",
        '첫 상자 출현 이후 controller에 전달된 chunk를 모두 센다(종료 후 미적용 결과 제외). 각 후보의 진행 방향은 현재 FRESH 적용 B(미적용이면 저장 latch pose)→원 후보 끝점, 기준은 B→min(로그 HMM closest+1,goal) Topomap node다. 각도는−180~180°, 좌양수/우음수, |각도|>90°는뒤. 영벡터는미정. 선택각도는 EC가 실제 설치한 원 후보 index이며, KEEP/R3/회복 등으로 새 후보를 설치하지 않은 chunk는NONE으로 둔다. 실제 선택이 연속한두chunk에서LEFT↔RIGHT일 때만 전환을 센다(BACK/NONE은연속을끊음). Graph 보정 경로를 원후보로 오인하지 않는다.',
        'depth SAFE 수는 저장 selection.candidates의8개 판정이다. EC는 조기 종료하므로8개 모두의 판정이 보존된 것이 아니다. 같은 적용tick의 INSTALL 검사에서 원 후보 path hash를 연결했다. world좌표 변환의 NumPy 마지막비트 차이는 저장된 원후보 좌표와1e−12m 이내인 경우 해당 저장path hash를 연결해 처리했다. 좌표가 없는 미매칭 검사 경로 수는 별도 표기하며, EC검사/PASS후보수는 식별된 것의 하한, SAFE미검사는상한이다. 전속도/0.1m/s PASS는 구분하고 전체 PASS는 합집합이다. 검사되지 않은SAFE는 **미검사**, 선택을보류해depth판정이없는chunk는—이다. 새 EC 계산으로 빈 값을 메우지 않았다.',
        table(b_summary),f'![B selected candidate example](figures/{b_figure})',
        '<details><summary>B 출현 후 chunk별 원장:8후보 각도·depth/EC·실제 선택</summary>\n\n'+table(b_chunks)+'\n\n</details>',
        '## C. 개발 로그의 목표 정밀도 임계값',
        ('거리 시점 가정: 선언 규칙에 직접 대응하는 **수신·선언 시점**을 사용했다. 해당 id의 declared_arrival이 있으면 선언tick, 아니면실제latched tick의72Hz 저장 goal_distance_m를 사용한다. 전달되지 않은 추론은 동시점pose가없어 제외한다. 비HMM 방법은 제외한다.' if a.goal_pose_time=='delivery' else
         '거리 시점: RGB observation_pose에서 목표까지 거리. 추론창 밖 목표 거리 미기록은 제외한다.'),
        '개발은 Phase47-C·52-P·53-P·H1-v2 trial의 게시된 선택attempt만 사용했고 NIGHT seed225·226은금지했다. HMM MAP=goal일 때 candidate_ids 중 goal의 저장 distance값을 d_goal로 읽었다. d_goal은미터가아닌 NoMaD 원출력단위다. 중복output은제외한다.',table(c_coverage),tau_text,
        '규칙은관측된서로다른유한d_goal값을cutoff후보로해 d_goal≤τ의경험정밀도≥95%인값중가장큰값이다. 동점값은함께포함한다. 최소표본수·장면별튜닝·NIGHT성적에따른재조정은추가하지않았다. 95%는관측비율이며신뢰구간하한이아니다. 표본범위밖으로τ를외삽하지않는다.',
        f'![C tau curve](figures/{c_figure})',table(c_curve),
        '### 동결 τ의 NIGHT 선언시점 적용(탐색적)',table(c_summary),
        '기존 잘못된 도착21건과 기존 성공27건의 선언을 일으킨 같은 inference의 d_goal에만 τ를 적용했다. 기존 성공에서 d_goal>τ면 **기존시점선언차단 → 지연또는소실가능**으로센다. 원run이이미그때끝나므로그이후경로·새추론은없으며지연과영구소실은구분할수없다. 잘못된선언차단을새성공으로간주하지않고성공수도다시계산하지않았다.',table(c_night),
        '<details><summary>C 개발 MAP=goal 원장</summary>\n\n'+table(c_points)+'\n\n</details>',
        f"검증: 읽은입력{len(I.files)}개 hash·크기·mtime 불변. 입력 SHA256 집계digest `{digest}`. 원실험코드·프로토콜·결과문서는수정하지않았다. 생성명령: `PYTHONPATH=research /usr/bin/python3 -m nomad_night_diag --goal-pose-time {a.goal_pose_time}`."]
    (ROOT/'docs/NIGHT_DIAG_20261111.md').write_text('\n\n'.join(lines)+'\n')
    print(json.dumps(dict(A=a_summary,A_passage_association=associations,B_target_runs=len(targets),B_blocks=len(blocks),B_runs=len(b_summary),B_chunks=len(b_chunks),
        C_development_points=len(c_points),tau=selected,C_night=c_summary,input_files_unchanged=len(I.files),seconds=time.monotonic()-start),ensure_ascii=False))
if __name__=='__main__':main()
