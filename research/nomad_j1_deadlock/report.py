"""No simulation, solver, SDF replay, causal labels or repair proposals."""
import csv
import hashlib
import io
import json
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
ARTIFACTS=ROOT.parent/'artifacts/isaac6/j1_01'
OUT=ROOT/'research/results/j1_deadlock'
METHODS=('OURS','OURS-noEC','OURS-noGRAPH')
FILES=('summary.json','launch_complete.json','agent_trajectory.csv','received.jsonl','events.jsonl',
       'j_applications.jsonl','stage2_graph.jsonl','exec_cert.jsonl','controller.jsonl')

def digest(data):return hashlib.sha256(data).hexdigest()
def read_run(run):
    assert (run/'launch_complete.json').exists() and (run/'summary.json').exists(),'Only completed artifacts may be read'
    data={};hashes={}
    for name in FILES:
        file=run/name
        if not file.exists():data[name]=[];continue
        raw=file.read_bytes();hashes[str(file)]=digest(raw)
        if name.endswith('.jsonl'):data[name]=[json.loads(x) for x in raw.decode().splitlines() if x]
        elif name.endswith('.csv'):data[name]=list(csv.DictReader(io.StringIO(raw.decode())))
        else:data[name]=json.loads(raw)
    assert data['launch_complete.json']['exit_code']==0
    return data,hashes

def stop_intervals(trace):
    t=np.array([float(r['simulation_time_s']) for r in trace]);v=np.array([float(r['v_m_s']) for r in trace]);w=np.array([float(r['w_rad_s']) for r in trace])
    np.testing.assert_allclose(t,np.arange(len(trace))/72,atol=1e-9,rtol=0)
    mask=(np.abs(v[1:])<1e-12)&(np.abs(w[1:])<1e-12)
    edges=np.diff(np.r_[False,mask,False].astype(int));starts=np.flatnonzero(edges==1);ends=np.flatnonzero(edges==-1)
    return [dict(start_tick=int(a),end_tick=int(b),start_s=a/72,end_s=b/72,duration_s=(b-a)/72)
            for a,b in zip(starts,ends) if b-a>=360]

def within(t,segment):return segment['start_s']-1e-10<=t<segment['end_s']-1e-10
def lengths(points,pose):
    p=np.asarray(points,float);delta=np.diff(p,axis=0);ds=np.linalg.norm(delta,axis=1)
    if not len(ds):return 0.,0.
    s=np.r_[0.,np.cumsum(ds)];den=np.sum(delta*delta,axis=1)
    u=np.clip(np.divide(np.sum((np.asarray(pose)[:2]-p[:-1])*delta,axis=1),den,out=np.zeros(len(ds)),where=den>1e-24),0,1)
    projected=p[:-1]+u[:,None]*delta;k=int(np.argmin(np.sum((projected-np.asarray(pose)[:2])**2,axis=1)))
    return float(s[-1]),float(s[-1]-s[k]-u[k]*ds[k])

def candidate_details(event):
    selection=event.get('j_selection');assert selection is not None
    candidates=selection['candidates'];safe=[c for c in candidates if c['safe']]
    longest=lambda rr:min(rr,key=lambda c:(-c['remaining_length_m'],c['index'])) if rr else None
    observation=np.asarray(event['observation_pose']);b=np.asarray(event['agent_pose_at_switch'])
    c,s=np.cos(observation[2]),np.sin(observation[2]);worlds=np.asarray(event['overnight_metric_samples'])@np.array([[c,s],[-s,c]])+observation[:2]
    row=dict(safe_count=len(safe),safe_any=bool(safe),selected_sample=selection['selected_sample'],
             native_installed=bool(selection['installed']),selection_disposition=selection['disposition'])
    for name,choice in (('longest_all',longest(candidates)),('longest_safe',longest(safe))):
        row[name+'_index']=choice['index'] if choice else None
        row[name+'_remaining_m']=float(choice['remaining_length_m']) if choice else None
        forward=worlds[choice['index'],-1]-b[:2] if choice else None
        row[name+'_forward_body_m']=float(forward@np.array([np.cos(b[2]),np.sin(b[2])])) if choice else None
        row[name+'_forward_plus_y_m']=float(forward[1]) if choice else None
    return row

def result_reason(r):
    if r.get('disposition')=='INITIALIZATION_REJECTED' and 'boundary curvature undefined' in r.get('error','').lower():return 'BOUNDARY_CURVATURE_UNDEFINED'
    return r.get('disposition','NO_RESULT_LOG')

def summary_range(values):
    a=[float(v) for v in values if v is not None]
    return dict(n=len(a),minimum=min(a) if a else None,median=float(np.median(a)) if a else None,maximum=max(a) if a else None)

def text_range(r):
    return 'N/A' if not r['n'] else f"{r['minimum']:.4f} / {r['median']:.4f} / {r['maximum']:.4f}"

def timeline(data,segment,seed):
    start=segment['start_s'];lo=max(0.,start-3.);out=[]
    def add(t,event,identifier,detail,ns=None):
        if lo-1e-10<=t<=start+1e-10:
            out.append(dict(seed=seed,time_s=float(t),relative_to_stop_s=float(t-start),event=event,id=identifier,detail=detail,monotonic_ns=ns))
    for r in data['received.jsonl']:
        if not r['terminal_unapplied']:add(r['latched_sim_s'],'CHUNK_RECEIVED',r['id'],'',r['latched_monotonic_ns'])
    for r in data['events.jsonl']:
        detail=candidate_details(r)
        add(r['application_sim_s'],'FRESH_SELECTION',r['id'],
            f"SAFE={detail['safe_count']}; {detail['selection_disposition']}; longest_SAFE_remaining={detail['longest_safe_remaining_m']}; forward_body={detail['longest_safe_forward_body_m']}; forward_+y={detail['longest_safe_forward_plus_y_m']}",r.get('j_selection_ns'))
    for r in data['stage2_graph.jsonl']:
        if r['event']=='SUBMIT':add(r['switch_sim_s'],'GRAPH_SUBMIT',r['job_id'],f"chunk={r['id']}; v={r['previous_command'][0]}",r['dispatch_ns'])
        if r['event']=='RESULT':
            s=r.get('solver',{})
            add(r['evaluated_sim_s'],'GRAPH_RESULT',r['job_id'],f"{result_reason(r)}; converged={s.get('success','N/A')}; constraints={s.get('constraints_satisfied','N/A')}; message={s.get('message',r.get('error',''))}",r.get('evaluated_monotonic_ns'))
    for r in data['exec_cert.jsonl']:
        if r['event']=='CHECK':add(r['simulation_time_s'],'EC_'+r['scope'],r['check_id'],f"pass={r['passed']}; {r['reason']}; clearance={r.get('clearance_m')}",r['check_started_ns'])
        elif r['event']=='PERIODIC_APPLY':add(r['apply_tick']/72,'EC_PERIODIC_APPLY',r['check_id'],r['action'])
    for r in data['j_applications.jsonl']:
        length,remaining=lengths(r['world_xy'],r['pose'])
        add(r['simulation_time_s'],'PATH_INSTALL',r['id'],f"{r['kind']}; graph_job={r.get('graph_job_id')}; length={length:.4f}; remaining={remaining:.4f}")
    previous=None
    for r in data['controller.jsonl']:
        source=r['applied_command_source']
        if source!=previous:
            add(r['simulation_time_s'],'COMMAND_SOURCE',r['waypoint_id'],f"{source}; v={r['commanded_v_m_s']:.6f}; w={r['commanded_w_rad_s']:.6f}",r['monotonic_ns'])
        previous=source
    tr=data['agent_trajectory.csv'][segment['start_tick']]
    add(start,'STOP_INTERVAL_START',None,f"duration={segment['duration_s']:.6f}; pose=({tr['x_m']},{tr['y_m']},{tr['yaw_rad']})")
    # Stored monotonic fields mix tick-input stamps and actual event stamps.
    # Order only by simulation time; do not invent within-tick chronology.
    return sorted(out,key=lambda r:r['time_s'])

def analyze():
    segments=[];chunks=[];selections=[];graph_rows=[];installed=[];ec_rows=[];rejections=[];examples=[];coverage=[];all_hashes={}
    for method in METHODS:
        for seed in range(231,240):
            key=f'H1-v3_{seed}_D750_{method}';run=ARTIFACTS/'main'/key/'attempt1'
            data,hashes=read_run(run);all_hashes.update(hashes)
            stops=stop_intervals(data['agent_trajectory.csv']);events={r['id']:r for r in data['events.jsonl']}
            results={r['job_id']:r for r in data['stage2_graph.jsonl'] if r['event']=='RESULT'}
            terminal={r['job_id'] for r in data['stage2_graph.jsonl'] if r['event']=='TERMINAL_UNAPPLIED'}
            coverage.append(dict(method=method,seed=seed,run=key,stop_intervals=len(stops),stop_seconds=sum(s['duration_s'] for s in stops)))
            example=next((s for s in stops if s['start_tick']>0),stops[0] if stops else None)
            if method=='OURS' and seed in (233,236) and example:examples.extend(timeline(data,example,seed))
            for number,stop in enumerate(stops,1):
                sid=f'{key}_S{number:02d}';identity=dict(segment=sid,method=method,seed=seed)
                arrivals=[r for r in data['received.jsonl'] if not r['terminal_unapplied'] and within(r['latched_sim_s'],stop)]
                fresh=[r for r in data['events.jsonl'] if within(r['application_sim_s'],stop)]
                select_rows=[]
                for r in fresh:
                    d=candidate_details(r);record=dict(identity,id=r['id'],application_s=r['application_sim_s'],**d)
                    selections.append(record);select_rows.append(record)
                    if not d['native_installed']:
                        rejections.append(dict(identity,source='FRESH_SELECTION',reason=d['selection_disposition'],id=r['id']))
                for r in arrivals:
                    e=events.get(r['id']);d=candidate_details(e) if e else {}
                    chunks.append(dict(identity,id=r['id'],latched_s=r['latched_sim_s'],application_s=e['application_sim_s'] if e else None,
                        application_in_same_stop=bool(e and within(e['application_sim_s'],stop)),**d))
                submitted=[r for r in data['stage2_graph.jsonl'] if r['event']=='SUBMIT' and within(r['switch_sim_s'],stop)]
                cohort=[]
                for r in submitted:
                    result=results.get(r['job_id']);s=(result or {}).get('solver',{})
                    item=dict(identity,job_id=r['job_id'],chunk_id=r['id'],submit_s=r['switch_sim_s'],
                        result_s=result['evaluated_sim_s'] if result else None,result_in_same_stop=bool(result and within(result['evaluated_sim_s'],stop)),
                        disposition=result_reason(result) if result else 'TERMINAL_UNAPPLIED_NO_RESULT' if r['job_id'] in terminal else 'NO_RESULT_LOG',converged=s.get('success'),constraints_satisfied=s.get('constraints_satisfied'),
                        exact_certificate_pass=s.get('exact_certificate_pass'),message=s.get('message'),error=(result or {}).get('error'))
                    cohort.append(item);graph_rows.append(item)
                handled=[r for r in results.values() if within(r['evaluated_sim_s'],stop)]
                for r in handled:
                    if r['disposition']!='ACCEPTED':rejections.append(dict(identity,source='GRAPH_RESULT',reason=result_reason(r),id=r['job_id']))
                checks=[r for r in data['exec_cert.jsonl'] if r['event']=='CHECK' and within(r['simulation_time_s'],stop)]
                ec_install=[r for r in checks if r['scope'] in ('SAFE_INSTALL','GRAPH_INSTALL')]
                for r in checks:
                    ec_rows.append(dict(identity,check_id=r['check_id'],time_s=r['simulation_time_s'],scope=r['scope'],passed=r['passed'],reason=r['reason'],clearance_m=r.get('clearance_m')))
                    if r in ec_install and not r['passed']:
                        rejections.append(dict(identity,source='EC_INSTALL_CHECK',reason=r['scope']+':'+r['reason'],id=r['check_id']))
                apps=[r for r in data['j_applications.jsonl'] if within(r['simulation_time_s'],stop)]
                app_rows=[]
                for a in apps:
                    length,remaining=lengths(a['world_xy'],a['pose'])
                    row=dict(identity,time_s=a['simulation_time_s'],id=a['id'],kind=a['kind'],graph_job_id=a.get('graph_job_id'),length_m=length,remaining_at_install_m=remaining)
                    installed.append(row);app_rows.append(row)
                prior=[a for a in data['j_applications.jsonl'] if a['simulation_time_s']<=stop['start_s']+1e-10]
                trace=data['agent_trajectory.csv'][stop['start_tick']];pose=[float(trace[k]) for k in ('x_m','y_m','yaw_rad')]
                before_length,before_remaining=lengths(prior[-1]['world_xy'],pose) if prior else (None,None)
                graph_enabled=method!='OURS-noGRAPH';ec_enabled=method!='OURS-noEC'
                segments.append(dict(identity,**stop,start_x_m=pose[0],start_y_m=pose[1],initial_wait=not bool(prior),
                    chunks_received=len(arrivals),fresh_evaluations=len(fresh),arrivals_missing_application=sum(r['id'] not in events for r in arrivals),
                    fresh_with_SAFE=sum(r['safe_any'] for r in select_rows),fresh_without_SAFE=sum(not r['safe_any'] for r in select_rows),
                    longest_all_remaining=summary_range([r['longest_all_remaining_m'] for r in select_rows]),
                    longest_all_forward_body=summary_range([r['longest_all_forward_body_m'] for r in select_rows]),
                    longest_all_forward_plus_y=summary_range([r['longest_all_forward_plus_y_m'] for r in select_rows]),
                    longest_SAFE_remaining=summary_range([r['longest_safe_remaining_m'] for r in select_rows]),
                    longest_SAFE_forward_body=summary_range([r['longest_safe_forward_body_m'] for r in select_rows]),
                    longest_SAFE_forward_plus_y=summary_range([r['longest_safe_forward_plus_y_m'] for r in select_rows]),
                    graph_enabled=graph_enabled,graph_submitted=len(submitted),graph_result_events=len(handled),
                    graph_submit_outcomes=dict(Counter(r['disposition'] for r in cohort)),
                    graph_solver_evaluated=sum(r['converged'] is not None for r in cohort),
                    graph_solver_converged=sum(r['converged'] is True for r in cohort),graph_solver_constraints_false=sum(r['constraints_satisfied'] is False for r in cohort),
                    graph_exact_certificate_false=sum(r['exact_certificate_pass'] is False for r in cohort),
                    graph_result_after_stop=sum(r['result_s'] is not None and not r['result_in_same_stop'] for r in cohort),
                    ec_enabled=ec_enabled,ec_install_checks=len(ec_install),ec_install_rejects=sum(not r['passed'] for r in ec_install),
                    ec_install_reasons=dict(Counter(r['scope']+':'+r['reason'] for r in ec_install if not r['passed'])),
                    ec_periodic_rejects=sum(r['scope']=='PERIODIC' and not r['passed'] for r in checks),
                    installed_paths=len(apps),installed_kinds=dict(Counter(r['kind'] for r in apps)),
                    installed_lengths=summary_range([r['length_m'] for r in app_rows]),installed_remaining=summary_range([r['remaining_at_install_m'] for r in app_rows]),
                    path_at_stop_start_length_m=before_length,path_at_stop_start_remaining_m=before_remaining))
    why=[]
    for method in METHODS:
        rr=[r for r in rejections if r['method']==method]
        for source,reason in sorted({(r['source'],r['reason']) for r in rr}):
            selected=[r for r in rr if r['source']==source and r['reason']==reason]
            why.append(dict(method=method,source=source,logged_reason=reason,events=len(selected),stop_intervals=len({r['segment'] for r in selected}),runs=len({r['seed'] for r in selected})))
    overview=[]
    for method in METHODS:
        ss=[s for s in segments if s['method']==method]
        overview.append(dict(method=method,runs=9,runs_with_stop=len({r['seed'] for r in ss}),stop_intervals=len(ss),stop_s=sum(s['duration_s'] for s in ss),
            no_path_installed_intervals=sum(s['installed_paths']==0 for s in ss),path_installed_intervals=sum(s['installed_paths']>0 for s in ss),
            chunks_received=sum(s['chunks_received'] for s in ss),fresh_with_SAFE=sum(s['fresh_with_SAFE'] for s in ss),fresh_without_SAFE=sum(s['fresh_without_SAFE'] for s in ss),
            graph_submitted=sum(s['graph_submitted'] for s in ss) if method!='OURS-noGRAPH' else None,
            ec_install_rejected=sum(s['ec_install_rejects'] for s in ss) if method!='OURS-noEC' else None,installed_paths=sum(s['installed_paths'] for s in ss)))
    graph_summary=[]
    reasons=('ACCEPTED','NONCONVERGED','CONSTRAINT_FAILED','BOUNDARY_CURVATURE_UNDEFINED','INITIALIZATION_REJECTED',
             'STALE','SUPERSEDED','WAYPOINT_EXPIRED','EXEC_CERT_REJECT','TERMINAL_UNAPPLIED_NO_RESULT','NO_RESULT_LOG')
    for method in METHODS:
        rr=[r for r in graph_rows if r['method']==method];counts=Counter(r['disposition'] for r in rr);enabled=method!='OURS-noGRAPH'
        graph_summary.append(dict(method=method,attempts=len(rr) if enabled else None,
            solver_evaluated=sum(r['converged'] is not None for r in rr) if enabled else None,
            **{reason:counts[reason] if enabled else None for reason in reasons}))
    return dict(overview=overview,coverage=coverage,segments=segments,chunks=chunks,selections=selections,graph_jobs=graph_rows,graph_summary=graph_summary,
                ec_checks=ec_rows,installed_paths=installed,rejection_events=rejections,rejection_summary=why,examples=examples,input_sha256=all_hashes)

def save_csv(path,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader()
        w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)

def table(rows):
    if not rows:return '0건.'
    keys=list(dict.fromkeys(k for r in rows for k in r))
    def fmt(v):
        if v is None:return 'N/A'
        if isinstance(v,float):return f'{v:.4f}'
        if isinstance(v,dict):return json.dumps(v,ensure_ascii=False)
        return str(v).replace('|','/')
    return '\n'.join(['| '+' | '.join(keys)+' |','| '+' | '.join(['---']*len(keys))+' |']+
                     ['| '+' | '.join(fmt(r.get(k)) for k in keys)+' |' for r in rows])

def main():
    data=analyze()
    # Completed raw inputs must remain byte-identical across this read-only pass.
    assert all(digest(Path(path).read_bytes())==h for path,h in data['input_sha256'].items())
    OUT.mkdir(parents=True,exist_ok=True)
    for key in ('overview','coverage','segments','chunks','selections','graph_jobs','graph_summary','ec_checks','installed_paths','rejection_events','rejection_summary','examples'):
        save_csv(OUT/(key+'.csv'),data[key])
    (OUT/'analysis.json').write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    (OUT/'validation.json').write_text(json.dumps(dict(runs=27,input_files=len(data['input_sha256']),inputs_unchanged=True,
        simulations=0,solver_runs=0,SDF_replays=0,original_worktree_written=False),indent=2)+'\n')
    candidate_table=[];forward_table=[];graph_table=[];path_table=[]
    for s in data['segments']:
        candidate_table.append(dict(segment=s['segment'],start_s=s['start_s'],end_s=s['end_s'],duration_s=s['duration_s'],
            chunks=s['chunks_received'],FRESH=s['fresh_evaluations'],SAFE_yes=s['fresh_with_SAFE'],SAFE_no=s['fresh_without_SAFE'],
            longest_all_remaining=text_range(s['longest_all_remaining']),longest_SAFE_remaining=text_range(s['longest_SAFE_remaining'])))
        forward_table.append(dict(segment=s['segment'],longest_all_forward_body=text_range(s['longest_all_forward_body']),
            longest_all_forward_plus_y=text_range(s['longest_all_forward_plus_y']),
            longest_SAFE_forward_body=text_range(s['longest_SAFE_forward_body']),longest_SAFE_forward_plus_y=text_range(s['longest_SAFE_forward_plus_y'])))
        graph_table.append(dict(segment=s['segment'],Graph_attempts=s['graph_submitted'] if s['graph_enabled'] else None,
            outcomes=s['graph_submit_outcomes'] if s['graph_enabled'] else None,solver_evaluated=s['graph_solver_evaluated'] if s['graph_enabled'] else None,
            converged=s['graph_solver_converged'] if s['graph_enabled'] else None,
            constraints_false=s['graph_solver_constraints_false'] if s['graph_enabled'] else None,certificate_false=s['graph_exact_certificate_false'] if s['graph_enabled'] else None,
            result_after_stop=s['graph_result_after_stop'] if s['graph_enabled'] else None,
            EC_install_rejects=s['ec_install_rejects'] if s['ec_enabled'] else None,EC_install_reasons=s['ec_install_reasons'] if s['ec_enabled'] else None,
            periodic_rejects=s['ec_periodic_rejects'] if s['ec_enabled'] else None))
        path_table.append(dict(segment=s['segment'],installed=s['installed_paths'],kinds=s['installed_kinds'],
            installed_length_m=text_range(s['installed_lengths']),installed_suffix_m=text_range(s['installed_remaining']),
            active_at_stop_length_m=s['path_at_stop_start_length_m'],active_at_stop_suffix_m=s['path_at_stop_start_remaining_m']))
    lines=['# J1 H1-v3 정지 구간 기록',
        '대상: seed231–239 × OURS·OURS-noEC·OURS-noGRAPH =27개 완료run. 저장 artifacts만 읽었다. 시뮬레이션·추론·Graph 재풀이·SDF 재계산·원래 작업 트리 수정은0회다. 아래는 기록 수치와 로그 disposition의 집계이며 원인 판정·수정 제안은 포함하지 않는다.',
        '정지: 저장72Hz 구간에서 |v|<1e−12m/s AND |ω|<1e−12rad/s가 연속360tick(5s) 이상. 표의 [start,end) 안 이벤트를 센다. 시작 추론 대기도 조건을 만족하면 포함한다. chunk도착=received.jsonl의 latched_sim_s(terminal_unapplied 제외),FRESH판정=application_sim_s여서 두 수는 다를 수 있다.',
        '남은 길이/SAFE는 당시 저장된 selection 값을 사용했다. 최장 SAFE가 없으면N/A이고 전체8개 중 최장 후보도 별도로 남겼다. 전진 성분은 (후보끝점−실제B)와B heading의 내적(body) 및 +y 축 성분을 함께 표시한다. 표의 길이/전진 값은 최소/중앙/최대(m),chunk별 수치는 CSV에 있다. 새 depth 판정은 하지 않았다.',
        table(data['overview']),
        '## 로그에 기록된 새 경로 미설치·거절 코드',
        'FRESH_SELECTION·GRAPH_RESULT·EC_INSTALL_CHECK는 서로 다른 사건 단위다. 같은 거절이 둘 이상의 로그에 기록될 수 있으므로 출처 간 행을 더해 독립 원인 수로 해석하지 않는다. Graph 경계 곡률 항목은 저장 error에 boundary curvature undefined가 있는 INITIALIZATION_REJECTED만 묶었다.',
        table(data['rejection_summary']),
        '## 정지 구간별 chunk·SAFE·후보 수치',table(candidate_table),table(forward_table),
        '## 정지 구간별 Graph·EC 기록',
        'Graph_attempts와 outcomes는 구간 안에서 제출한 job cohort이며 그 job의 최종 저장 결과를 연결했다(result_after_stop 별도). solver_evaluated는 solver 결과 flag가 존재하는 수다. converged·constraints_false·certificate_false는 독립 집계로 서로 배타적이지 않다. 주기EC거절은 설치거절과 별도 열이다. 기능 없는 방법은N/A다.',table(data['graph_summary']),table(graph_table),
        '## 설치 경로 길이',
        'installed는 정지 구간 내 실제 j_applications 기록 수다. active_at_stop은 시작 직전/동일tick 마지막 설치 경로를 정지 시작 pose에 투영한 값이다. 경로가 바뀌지 않았으면 installed_length는N/A이고 기존 경로 길이를 별도로 표시한다.',table(path_table)]
    for seed in (233,236):
        rows=[r for r in data['examples'] if r['seed']==seed]
        lines.extend([f'## OURS seed{seed}: 정지 시작 전3초 사건',
            '해당run의 첫 주행 후 5s이상 정지 구간을 선택했다(없으면 첫 초기 정지). simulation 시각 순이며, 동일tick 행의 내부 순서는 주장하지 않는다. 저장monotonic 필드에 제어tick 입력 시각과 이벤트 시각이 혼재하므로 이를 실제 명령 적용 순서로 해석하지 않는다.',
            table([{k:r[k] for k in ('time_s','relative_to_stop_s','event','id','detail')} for r in rows])])
    lines.extend(['## 기록 파일',
        '`research/results/j1_deadlock/`: segments.csv(구간),chunks.csv(도착chunk별 SAFE/길이/전진),selections.csv(FRESH별),graph_jobs.csv(job별 status·message·flag),ec_checks.csv,installed_paths.csv,rejection_summary.csv,examples.csv. analysis.json에 원 입력 SHA256을 포함하며 분석 후 전부 재확인했다.'])
    (ROOT/'docs/J1_DEADLOCK_DIAG.md').write_text('\n\n'.join(lines)+'\n')
    print(json.dumps(dict(overview=data['overview'],rejections=data['rejection_summary'],input_files=len(data['input_sha256']),inputs_unchanged=True),ensure_ascii=False))

if __name__=='__main__':main()
