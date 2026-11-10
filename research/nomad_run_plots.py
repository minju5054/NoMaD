"""Saved-log-only representative run plots, reusable with --phase and --runs.

No experiment imports, simulation, solver, rollout, EC re-evaluation or outcome
reclassification. Published run metrics supply titles/tables; raw logs supply
all plotted samples/events. Only timestamp alignment for drawing is performed.
"""
import argparse,csv,hashlib,json,re
from collections import Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle,Polygon,Rectangle,Patch

ROOT=Path(__file__).resolve().parents[1]
COLORS={'NORMAL':'#0072B2','KEEP_ACTIVE':'#009E73','ALIGN_ROTATE':'#D55E00',
        'ALIGN_BRAKE':'#CC79A7','STOP_WAIT':'#202020','WAYPOINT_TIMEOUT':'#888888',
        'RECOVER_ROTATE':'#56B4E9','WAIT_FRESH':'#9A7600','ENDPOINT':'#8C564B',
        'DECLARED_ARRIVAL':'#007F61','REPAIR_WAIT':'#A4A2BA','DETOUR_WAIT':'#8B87A3',
        'INITIAL_INFERENCE_WAIT':'#C4C4C4','OTHER':'#8F969D'}
CUT='#828282';GRAPH='#E69F00';BOX='#9566AE';REJECT='#C51B30'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':11,
    'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,
    'grid.alpha':.16,'grid.linewidth':.5,'savefig.facecolor':'white'})

class Inputs:
    def __init__(self):self.files={}
    def text(self,p):
        p=Path(p);raw=p.read_bytes();st=p.stat()
        self.files[str(p)]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=st.st_size,mtime_ns=st.st_mtime_ns)
        return raw.decode()
    def json(self,p):return json.loads(self.text(p))
    def rows(self,p,required=False):
        if not Path(p).exists():
            if required:raise FileNotFoundError(p)
            return []
        return [json.loads(s) for s in self.text(p).splitlines() if s.strip()]
    def unchanged(self):
        for p,item in self.files.items():
            f=Path(p);st=f.stat()
            assert st.st_size==item['bytes'] and st.st_mtime_ns==item['mtime_ns'],f'Input changed: {p}'
            assert hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256'],f'Input changed: {p}'

def phase_name(value):
    p=re.sub(r'[^a-z0-9]','',value.lower());p=p if p.startswith('phase') else 'phase'+p
    if not re.fullmatch(r'phase[0-9]+[a-z]*',p):raise ValueError('Use e.g. phase53p, Phase53-P or 53-P')
    return p

def time_of(e):
    for key in ('simulation_time_s','time_s','latched_sim_s','received_sim_s','detected_sim_s'):
        if e.get(key) is not None:return float(e[key])
    raise ValueError('Event has no logged simulation timestamp')

def label(r):
    # Exact persisted classification (including WRONG_STOP), not new evaluation.
    return r.get('classification',r.get('technical_validation','UNKNOWN'))

def number(v,suffix='s'):
    return '—' if v is None else f'{v:.2f}{suffix}'

def rate(r):
    n=r.get('graph_attempts',r.get('graph_dispatches',0));a=r.get('graph_applied',0)
    p=r.get('graph_adoption_rate',r.get('graph_acceptance_rate'))
    if p is None:return '—'
    return f'{100*p:.1f}% ({a}/{n})'

def align_time(r):
    return r.get('align_rotate_s',r.get('command_state_seconds',{}).get('ALIGN_ROTATE'))

def obstacle_corners(o):
    x,y=o['center_xy_m'];w,h=o['size_xyz_m'][:2]
    yaw=float(o.get('yaw_rad',np.deg2rad(o.get('yaw_deg',0.))))
    pts=np.array([[-w,-h],[w,-h],[w,h],[-w,h]])/2
    rot=np.array([[np.cos(yaw),-np.sin(yaw)],[np.sin(yaw),np.cos(yaw)]])
    return pts@rot.T+np.array([x,y])

def contacts(summary):
    found={}
    def visit(obj):
        if isinstance(obj,dict):
            c=obj.get('first_contact')
            if c and c.get('detected_pose') is not None:
                key=(c['detected_sim_s'],*c['detected_pose']);found[key]=c
            for k,v in obj.items():
                if k not in ('scenario','first_contact'):visit(v)
        elif isinstance(obj,list):
            for v in obj:visit(v)
    visit(summary);return sorted(found.values(),key=lambda x:x['detected_sim_s'])

def load_run(record,inputs):
    r=dict(record);root=Path(r['output'])
    cfg=inputs.json(root/'scenario.json');summary=inputs.json(root/'summary.json')
    tr=list(csv.DictReader(inputs.text(root/'agent_trajectory.csv').splitlines()))
    t=np.array([float(x['simulation_time_s']) for x in tr]);xy=np.array([[float(x[k]) for k in ('x_m','y_m')] for x in tr])
    assert len(t)>1 and np.all(np.diff(t)>0)
    assert np.all(np.abs(np.diff(t)-1/72)<1e-8),'Expected saved72Hz trajectory'
    v=np.array([float(x['v_m_s']) for x in tr]);w=np.array([float(x['w_rad_s']) for x in tr])
    distance=np.array([float(x['goal_distance_m']) for x in tr]) # logged, not recomputed
    commands=inputs.rows(root/'phase20_commands.jsonl',True)
    commands=sorted(commands,key=time_of)
    # A command at t applies to the subsequent72Hz interval. No command before
    # the first record is invented; label that interval as initial waiting.
    ct=np.array([time_of(x) for x in commands]);idx=np.searchsorted(ct,t[:-1]+1e-10,side='right')-1
    states=np.array([commands[i]['source'] if i>=0 else 'INITIAL_INFERENCE_WAIT' for i in idx])
    intervals=[]
    for i,c in enumerate(commands):
        a=time_of(c);b=time_of(commands[i+1]) if i+1<len(commands) else t[-1]
        if a<t[-1] and b>a:intervals.append((max(a,0),min(b,t[-1]),c['source'],c.get('pose')))
    if ct.size and ct[0]>0:intervals.insert(0,(0,ct[0],'INITIAL_INFERENCE_WAIT',xy[0]))
    repair=inputs.rows(root/'repair.jsonl',True)
    applications=[e for e in repair if e.get('event')=='PATH_APPLIED']
    ho=inputs.rows(root/'graph_ho.jsonl');rec=inputs.rows(root/'reconstruction.jsonl')
    if any(e.get('event')=='INSTALL' for e in ho):
        plans=[dict(time=time_of(e),points=np.asarray(e['path_world']),graph=e['path_type']!='CUT',id=e.get('id')) for e in ho if e.get('event')=='INSTALL']
        attempts=[time_of(e) for e in ho if e.get('event')=='SOLVE']
        applied=[time_of(e) for e in ho if e.get('event')=='SOLVE' and e.get('applied')]
        assert len(plans)==len(applications),'Every installed path must appear in Graph/CUT metadata'
        for p,a in zip(plans,applications):
            assert abs(p['time']-time_of(a))<1e-9
            np.testing.assert_array_equal(p['points'],a['path_world'])
    else:
        plans=[dict(time=time_of(e),points=np.asarray(e['path_world']),graph='GRAPH' in e.get('kind',''),id=e.get('id')) for e in applications]
        attempts=[time_of(e) for e in rec if e.get('event')=='DISPATCH']
        applied=[time_of(e) for e in rec if e.get('event')=='RESULT' and e.get('applied')]
        for at in applied:assert any(p['graph'] and abs(at-p['time'])<1e-9 for p in plans)
    checks=[e for e in inputs.rows(root/'exec_cert.jsonl',True) if e.get('event')=='CHECK']
    received=inputs.rows(root/'received.jsonl',True)
    arrivals=[float(e['latched_sim_s']) for e in received if e.get('latched_sim_s') is not None and not e.get('terminal_unapplied',False)]
    declared=inputs.json(root/'declared_arrival.json') if (root/'declared_arrival.json').exists() else None
    dyn=summary.get('dynamic_obstacle') or {};boxes=[]
    for b in dyn.get('boxes',[dyn]):
        s=b.get('spawn')
        if s and s.get('obstacle'):boxes.append(dict(obstacle=s['obstacle'],time=time_of(s),pose=s.get('pose')))
    assert len(checks)==r.get('ec_checks',len(checks))
    assert len(attempts)==r.get('graph_attempts',r.get('graph_dispatches',len(attempts)))
    assert len(applied)==r.get('graph_applied',len(applied))
    return dict(record=r,root=root,cfg=cfg,summary=summary,t=t,xy=xy,v=v,w=w,distance=distance,
        states=states,intervals=intervals,plans=plans,attempts=attempts,applied=applied,checks=checks,
        arrivals=arrivals,declared=declared,contacts=contacts(summary),boxes=boxes)

def extent(data):
    # Include all stored installed paths (even parts not subsequently executed).
    allxy=[]
    for d in data:
        c=d['cfg']['corridor'];h=c['half_width'];y0=c.get('ymin',-h);y1=c.get('ymax',h)
        allxy.extend([np.array([[c['xmin'],y0],[c['xmax'],y1]]),d['xy']])
        allxy.extend(p['points'] for p in d['plans'])
    q=np.concatenate(allxy);return q.min(0)-.16,q.max(0)+.16

def topdown(ax,d,lo,hi):
    c=d['cfg'];bounds=c['corridor'];h=bounds['half_width'];x0,x1=bounds['xmin'],bounds['xmax'];y0,y1=bounds.get('ymin',-h),bounds.get('ymax',h)
    wall=.10
    for x,y,w,hh in [(x0-wall,y0-wall,wall,y1-y0+2*wall),(x1,y0-wall,wall,y1-y0+2*wall),(x0,y0-wall,x1-x0,wall),(x0,y1,x1-x0,wall)]:
        ax.add_patch(Rectangle((x,y),w,hh,fc='#B0B0B0',ec='#777777',lw=.5,zorder=1))
    for o in c.get('obstacles',[]):ax.add_patch(Polygon(obstacle_corners(o),fc='#C8C8C8',ec='#777777',lw=.8,zorder=2))
    for i,b in enumerate(d['boxes'],1):
        poly=obstacle_corners(b['obstacle']);ax.add_patch(Polygon(poly,fc=BOX,ec='#663780',alpha=.48,lw=1.2,zorder=3))
        center=np.asarray(b['obstacle']['center_xy_m']);anchor=poly[np.argmax(poly[:,1])]
        ax.annotate(f"Box{i} @ {b['time']:.2f}s",xy=center,xytext=(anchor[0],anchor[1]+.13),ha='center',fontsize=8,color='#623578',
            bbox=dict(facecolor='white',edgecolor='none',alpha=.8,pad=1.5),arrowprops=dict(arrowstyle='-',color=BOX,lw=.6),zorder=12)
    # Every installation is represented; no smoothing, thinning or re-solving.
    for graph,color in [(False,CUT),(True,GRAPH)]:
        paths=[p['points'] for p in d['plans'] if p['graph']==graph]
        if paths:ax.add_collection(LineCollection(paths,colors=color,linewidths=1.05,linestyles='--' if graph else ':',alpha=.55 if graph else .35,zorder=4))
    xy=d['xy'];segments=np.stack([xy[:-1],xy[1:]],axis=1)
    ax.add_collection(LineCollection(segments,colors=[COLORS.get(s,COLORS['OTHER']) for s in d['states']],linewidths=2.4,zorder=6))
    # Rotation/stops have zero-length trajectory; explicit colored pose dots
    # keep them visible. Dots mean state occurrence, not duration (see strip).
    for a,b,state,pose in d['intervals']:
        if state not in ('NORMAL','KEEP_ACTIVE') and pose is not None:
            ax.scatter(pose[0],pose[1],s=9,c=COLORS.get(state,COLORS['OTHER']),alpha=.45,zorder=7,linewidths=0)
    rejected=[e for e in d['checks'] if not e['passed']]
    if rejected:
        q=np.asarray([e['pose'][:2] for e in rejected]);ax.scatter(q[:,0],q[:,1],marker='x',c=REJECT,s=30,lw=1.1,zorder=9)
    start=np.asarray(c['start_pose']);goal=np.asarray(c['goal_pose'])
    ax.scatter(*start[:2],marker='^',s=65,fc='white',ec='#161616',lw=1.4,zorder=13)
    ax.add_patch(Circle(goal[:2],.5,fc='#009E7310',ec='#009E73',ls='--',lw=1,zorder=2))
    ax.scatter(*goal[:2],marker='*',s=145,c='#009E73',ec='white',lw=.5,zorder=10)
    if d['declared']:
        q=d['declared']['pose'];ax.scatter(*q[:2],marker='o',s=80,fc='none',ec='#111111',lw=1.7,zorder=14)
        ax.annotate(f"declared {time_of(d['declared']):.2f}s",q[:2],xytext=(5,9),textcoords='offset points',fontsize=8,zorder=15,
            bbox=dict(facecolor='white',edgecolor='none',alpha=.8,pad=1.5))
    if d['contacts']:
        q=d['contacts'][0]['detected_pose'];ax.scatter(*q[:2],marker='X',s=125,c=REJECT,ec='white',lw=.7,zorder=15)
        ax.annotate(f"collision {d['contacts'][0]['detected_sim_s']:.2f}s",q[:2],xytext=(12,-26),textcoords='offset points',fontsize=8,zorder=16,
            bbox=dict(facecolor='white',edgecolor='none',alpha=.9,pad=1.5))
    elif not d['declared']:ax.scatter(*xy[-1],marker='s',s=65,fc='white',ec='black',lw=1.5,zorder=13)
    ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),xlabel='x (m)',ylabel='y (m)');ax.set_aspect('equal',adjustable='box')
    r=d['record'];clearance=r.get('minimum_clearance_m')
    title=f"{r['method']}  |  {label(r)}\narrival {number(r.get('goal_time_s'))}   stop {number(r.get('stopped_s'))}   ALIGN {number(align_time(r))}"
    ax.set_title(title,pad=9,fontsize=10.5)
    ax.text(.01,.015,f"installed CUT {sum(not p['graph'] for p in d['plans'])} / GRAPH {sum(p['graph'] for p in d['plans'])}   |   EC reject {len(rejected)}/{len(d['checks'])}",
        transform=ax.transAxes,fontsize=8,bbox=dict(facecolor='white',edgecolor='none',alpha=.85,pad=2),zorder=20)

def timelines(fig,grid,d,max_t):
    av=fig.add_subplot(grid[1]);ag=fig.add_subplot(grid[2],sharex=av);ab=fig.add_subplot(grid[3],sharex=av);ae=fig.add_subplot(grid[4],sharex=av)
    av.plot(d['t'],d['v'],color='#0072B2',lw=1.1,label='v (m/s)');av.set(ylim=(-.015,.34),ylabel='v (m/s)')
    aw=av.twinx();aw.plot(d['t'],d['w'],color='#009E73',lw=.9,alpha=.85,label='omega (rad/s)');aw.set(ylim=(-.45,.45),ylabel='omega (rad/s)');aw.grid(False)
    av.tick_params(axis='y',labelcolor='#0072B2');aw.tick_params(axis='y',labelcolor='#009E73')
    av.legend(handles=[Line2D([],[],color='#0072B2',lw=1.2,label='v'),Line2D([],[],color='#009E73',lw=1.2,label='omega')],loc='upper right',ncol=2,fontsize=7,framealpha=.8)
    ag.plot(d['t'],d['distance'],color='#4F5770',lw=1.2);ag.axhline(.5,color='#009E73',ls=':',lw=.9);ag.set(ylabel='goal dist. (m)',ylim=(0,max(1.,float(d['distance'].max())*1.08)))
    for a,b,state,_ in d['intervals']:ab.broken_barh([(a,b-a)],(0,1),facecolors=COLORS.get(state,COLORS['OTHER']),edgecolors='none')
    ab.set(ylim=(0,1),yticks=[],ylabel='state');ab.grid(False)
    passes=[time_of(e) for e in d['checks'] if e['passed']];rejects=[time_of(e) for e in d['checks'] if not e['passed']]
    ae.scatter(d['arrivals'],np.zeros(len(d['arrivals'])),marker='|',s=55,c='#444444',linewidths=.9)
    ae.scatter(d['attempts'],np.ones(len(d['attempts'])),marker='o',s=14,fc='none',ec='#6C6C6C',lw=.7)
    ae.scatter(d['applied'],np.ones(len(d['applied'])),marker='*',s=48,c=GRAPH,ec='#9F6A00',lw=.45,zorder=5)
    ae.scatter(passes,np.full(len(passes),2),marker='.',s=11,c='#009E73',alpha=.65)
    ae.scatter(rejects,np.full(len(rejects),2),marker='x',s=32,c=REJECT,lw=1.2,zorder=6)
    ae.set(yticks=[0,1,2],yticklabels=['chunk','graph','EC'],ylim=(-.5,2.6),xlabel='Simulation time (s)')
    for ax in (av,ag,ab,ae):
        ax.set_xlim(0,max_t)
        if ax is not ae:ax.tick_params(axis='x',labelbottom=False)
        if d['t'][-1]<max_t-.01:ax.axvspan(d['t'][-1],max_t,color='#eeeeee',zorder=-1)
        for b in d['boxes']:ax.axvline(b['time'],color=BOX,ls=':',lw=.65,alpha=.6)
        if d['declared']:ax.axvline(time_of(d['declared']),color='#222222',ls='--',lw=.9)
        if d['contacts']:ax.axvline(d['contacts'][0]['detected_sim_s'],color=REJECT,ls='--',lw=.9)
    return (av,ag,ab,ae)

def plot(data,phase,run,out):
    n=len(data);lo,hi=extent(data);ratio=float((hi[1]-lo[1])/(hi[0]-lo[0]));mapheight=max(2.5,min(5.8,6.8*ratio))
    width=8*n if n>1 else 11.;height=mapheight+7.5
    fig=plt.figure(figsize=(width,height));outer=fig.add_gridspec(1,n,left=.075,right=.915,bottom=.235,top=.88,wspace=.28 if n>1 else .1)
    allstates=set();max_t=max(d['t'][-1] for d in data)
    for i,d in enumerate(data):
        grid=outer[i].subgridspec(5,1,height_ratios=[mapheight,1.,1.,.27,1.05],hspace=.50)
        topdown(fig.add_subplot(grid[0]),d,lo,hi);timelines(fig,grid,d,max_t);allstates.update(d['states'])
    fig.suptitle(f'{phase.upper()}  |  {run}  |  saved 72 Hz trajectories',fontsize=14,y=.975)
    handles=[Line2D([],[],color=COLORS[s],lw=3,label=s) for s in COLORS if s in allstates]
    handles.extend(Line2D([],[],color=COLORS['OTHER'],lw=3,label=s) for s in sorted(allstates-COLORS.keys()))
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.118),ncol=min(5,len(handles)),frameon=False,fontsize=8,columnspacing=1.1,handlelength=1.8)
    second=[Line2D([],[],color=CUT,ls=':',lw=1.4,label='installed CUT'),Line2D([],[],color=GRAPH,ls='--',lw=1.4,label='installed GRAPH'),
        Line2D([],[],marker='x',ls='',color=REJECT,label='EC REJECT'),Line2D([],[],marker='.',ls='',color='#009E73',label='EC PASS'),
        Line2D([],[],marker='o',ls='',mfc='none',color='#777777',label='Graph attempt'),Line2D([],[],marker='*',ls='',color=GRAPH,label='Graph applied'),
        Line2D([],[],marker='|',ls='',color='#444444',label='chunk latched')]
    fig.legend(handles=second,loc='lower center',bbox_to_anchor=(.5,.063),ncol=7 if n>1 else 4,frameon=False,fontsize=8,columnspacing=.9,handlelength=1.5)
    fig.text(.5,.020,'Top: triangle=start; green star / dashed 0.5 m circle=goal; open circle=declared stop; red X=contact; square=timeout.\nAll installed plans are dashed/dotted; translucent boxes show their final saved placement, with spawn times. State dots mark stationary commands.',ha='center',fontsize=7.5,color='#4b4b4b')
    fig.savefig(out,dpi=150);plt.close(fig)

def run_groups(records,selectors):
    result=[]
    for selector in selectors:
        exact=[r for r in records if r.get('key')==selector]
        chosen=exact or [r for r in records if r.get('key','').startswith(selector+'_')]
        if not chosen:raise ValueError(f'No saved run matches {selector}')
        chosen=sorted(chosen,key=lambda r:(0 if r['method'].startswith('CUT') else 1,r['method']))
        assert len({r['method'] for r in chosen})==len(chosen),'Duplicate method; select a full block key'
        assert all(r['technical_validation']=='PASS' for r in chosen),'Cannot plot a technical failure as a completed run'
        result.append((selector,chosen))
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--phase',required=True);ap.add_argument('--runs',required=True,nargs='+',help='Block IDs (paired methods), or exact full run keys (single); space/comma separated')
    a=ap.parse_args();phase=phase_name(a.phase);selectors=[x for value in a.runs for x in value.split(',') if x]
    for s in selectors:assert re.fullmatch(r'[A-Za-z0-9_+.-]+',s) and '..' not in s,'Invalid run key'
    inputs=Inputs();records=inputs.json(ROOT/'research/results'/phase/'runs.json');groups=run_groups(records,selectors)
    output=ROOT/'docs/figures';output.mkdir(exist_ok=True);doc=ROOT/'docs'/f'{phase.upper()}_RUN_PLOTS.md'
    table=['| Run | 분류 | 도착시간 | 정지시간 | ALIGN_ROTATE | Graph 채택률 |','|---|---|---:|---:|---:|---:|'];figures=[];manifest=[]
    for selector,rr in groups:
        data=[load_run(r,inputs) for r in rr];filename=f'{phase}_{selector}.png';plot(data,phase,selector,output/filename)
        figures.append(f'![{selector}: saved run comparison](figures/{filename})')
        for d in data:
            r=d['record'];table.append(f"| {r['key']} | {label(r)} | {number(r.get('goal_time_s'))} | {number(r.get('stopped_s'))} | {number(align_time(r))} | {rate(r)} |")
            manifest.append(dict(key=r['key'],output=str(d['root']),figure=filename,trajectory_samples=len(d['t']),
                installed_paths=len(d['plans']),installed_graph_paths=sum(p['graph'] for p in d['plans']),graph_attempts=len(d['attempts']),graph_applied=len(d['applied']),
                ec_pass=sum(e['passed'] for e in d['checks']),ec_reject=sum(not e['passed'] for e in d['checks']),chunk_arrivals=len(d['arrivals']),
                boxes=[dict(id=b['obstacle'].get('id'),spawn_s=b['time']) for b in d['boxes']],
                terminal_unapplied_chunks_omitted=True))
        print(json.dumps(dict(figure=filename,runs=len(data)),ensure_ascii=False),flush=True)
    inputs.unchanged()
    command='PYTHONPATH=research /usr/bin/python3 -m nomad_run_plots --phase '+phase+' --runs '+' '.join(selectors)
    doc.write_text(f'# {phase.upper()} 대표 주행 기록\n\n저장된 결과·로그만 시각화했다. 시뮬레이션, solver, rollout, EC·성과 지표 재계산은 하지 않았다. PNG 150 dpi; 쌍은 CUT 왼쪽·GRAPH 오른쪽.\n\n'+
        '\n'.join(table)+'\n\n위: 실제 72Hz 궤적의 명령 상태 색, 설치된 모든 CUT(회색 점선)·GRAPH(주황 파선) 경로, 벽·정적 장애물(회색), 돌발 상자(보라·출현 시각), 목표·선언·접촉. 정지/회전은 위치 점도 표시한다. 아래: 저장 v·ω·목표 거리, 명령 상태 띠, EC·Graph·chunk 수신 시각. 쌍은 같은 좌표·시간 축을 쓰며 종료 이후는 회색이다.\n\n'+
        '표의 도착시간은 성공 run만 표시한다(—는 미도착). 잘못된 도착도 그림에는 실제 선언 시각·위치를 표시한다. 채택률 분모는 저장 report의 Graph 시도 수이다. `WAYPOINT_TIMEOUT`은 로그 출처명 그대로이며 첫 chunk 이전 missing 대기도 포함할 수 있다. Chunk 표시는 controller에 latch된 시각이며 종료 후 미적용 결과는 제외한다. 한 top-down 그림에 시간 전체를 겹쳤으므로 상자는 출현 전에도 배치 윤곽이 보인다.\n\n'+
        '\n\n'.join(figures)+'\n\n재사용 명령: `'+command+'`\n')
    manifest_path=output/f'{phase}_run_plots_manifest.json'
    manifest_path.write_text(json.dumps(dict(phase=phase,selectors=selectors,dpi=150,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        saved_only=True,simulations=0,solves=0,ec_reevaluations=0,input_files=inputs.files,runs=manifest),indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(dict(document=str(doc.relative_to(ROOT)),figures=len(groups),read_only_inputs=len(inputs.files))))
if __name__=='__main__':main()
