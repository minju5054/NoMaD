"""Fixed sixteen-block saved-log visualization, no experiment recomputation."""
import hashlib,json,time
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle,Polygon,Circle
from nomad_run_plots import ROOT,Inputs,load_run,extent,obstacle_corners,COLORS,CUT,GRAPH,BOX,REJECT,time_of
from nomad_h1v2_trial.figures import candidates

SCENES=('L2','H1','H2','H1-v2');SEEDS=(225,226);METHODS=('CUT','GRAPH-HO','OURS-R3')
COHORTS=(('E3','D150'),('E1','D075'));R3='#1565C0';R2='#9366AA'
# Rendering colors only; separate normal driving from the requested blue R3.
STATE_COLORS={**COLORS,'NORMAL':'#009E73','KEEP_ACTIVE':'#56B4E9','RECOVER_ROTATE':'#A783C2'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                     'axes.grid':True,'grid.alpha':.14,'grid.linewidth':.5})

def fnum(value):return '—' if value is None else f'{float(value):.1f}s'
def passage(r):
    if r.get('box_passage'):return 'YES / '+fnum(r.get('box_passage_from_spawn_s'))
    return 'NO'

def prepare_run(r,inputs):
    d=load_run(r,inputs);d['native'],d['native_info']=candidates(d,inputs)
    manifest=inputs.json(Path(d['cfg']['topomap_manifest']));nodes=manifest['nodes']
    d['nodes']=np.asarray([n['world_pose'][:2] for n in nodes]);d['node_ids']=[int(n['node_id']) for n in nodes]
    apps=[e for e in inputs.rows(d['root']/'repair.jsonl') if e.get('event')=='PATH_APPLIED']
    assert len(apps)==len(d['plans'])
    for p,a in zip(d['plans'],apps):
        p['type']='R3' if a['kind']=='DETOUR' else 'R2' if a['kind']=='REPAIR' else 'GRAPH' if p['graph'] else 'CUT'
    detours=inputs.rows(d['root']/'detour.jsonl');applied_ids={e['job_id'] for e in detours if e.get('event')=='APPLIED'}
    d['triggers']=[e for e in detours if e.get('event')=='TRIGGER']
    d['ends']=[e for e in detours if e.get('event')=='END' and e.get('job_id') in applied_ids]
    assert len(applied_ids)==r.get('detour_applied_count',len(applied_ids))
    d['declaration_node']=None
    if d['declared']:
        declaration=d['declared'];hmm=int(declaration['closest_node']);assert hmm in d['node_ids']
        position=np.asarray(declaration['pose'])[:2]
        # Requested display-only nearest-node annotation at the DECLARATION
        # pose; do not reuse the report's observation-time node-error value.
        nearest_idx=int(np.argmin(np.sum((d['nodes']-position)**2,axis=1)));nearest=d['node_ids'][nearest_idx]
        d['declaration_node']=dict(time_s=time_of(declaration),pose=position.tolist(),hmm_node=hmm,
            hmm_node_xy=d['nodes'][d['node_ids'].index(hmm)].tolist(),nearest_node=nearest,
            nearest_node_xy=d['nodes'][nearest_idx].tolist(),signed_node_difference=hmm-nearest,
            definition='Euclidean nearest saved topomap node to saved declared-arrival pose;display geometry only;no HMM replay')
    return d

def scene(ax,d,lo,hi):
    c=d['cfg'];bounds=c['corridor'];h=bounds['half_width'];x0,x1=bounds['xmin'],bounds['xmax'];y0,y1=bounds.get('ymin',-h),bounds.get('ymax',h)
    wall=.10
    for x,y,w,hh in [(x0-wall,y0-wall,wall,y1-y0+2*wall),(x1,y0-wall,wall,y1-y0+2*wall),(x0,y0-wall,x1-x0,wall),(x0,y1,x1-x0,wall)]:
        ax.add_patch(Rectangle((x,y),w,hh,fc='#BABABA',ec='#808080',lw=.5,zorder=1))
    for o in c.get('obstacles',[]):ax.add_patch(Polygon(obstacle_corners(o),fc='#D0D0D0',ec='#858585',lw=.8,zorder=2))
    if d['native']:ax.add_collection(LineCollection(d['native'],colors='#8A8FA2',linewidths=.45,alpha=.055,zorder=3))
    for kind,color,ls,width,alpha in [('CUT',CUT,':',.85,.30),('GRAPH',GRAPH,'--',1.0,.55),('R2',R2,':',1.1,.6),('R3',R3,'-',1.6,.72)]:
        paths=[p['points'] for p in d['plans'] if p['type']==kind]
        if paths:ax.add_collection(LineCollection(paths,colors=color,linestyles=ls,linewidths=width,alpha=alpha,zorder=4))
    xy=d['xy'];segments=np.stack([xy[:-1],xy[1:]],axis=1)
    ax.add_collection(LineCollection(segments,colors=[STATE_COLORS.get(s,STATE_COLORS['OTHER']) for s in d['states']],linewidths=2.3,zorder=6))
    for state in set(d['states'])-{'NORMAL','KEEP_ACTIVE'}:
        points=np.asarray([pose[:2] for a,b,s,pose in d['intervals'] if s==state and pose is not None])
        if len(points):ax.scatter(*points.T,c=STATE_COLORS.get(state,STATE_COLORS['OTHER']),s=8,alpha=.45,lw=0,zorder=7)
    # All node numbers are saved node IDs, not newly selected subgoals.
    ax.plot(*d['nodes'].T,color='#6A849D',ls=':',lw=.55,alpha=.55,zorder=3)
    ax.scatter(*d['nodes'].T,s=13,fc='white',ec='#486986',lw=.55,zorder=8)
    for node,point in zip(d['node_ids'],d['nodes']):
        ax.annotate(str(node),point,xytext=(0,6 if node%2==0 else -10),textcoords='offset points',ha='center',fontsize=7.5,color='#486986',zorder=9)
    for i,b in enumerate(d['boxes'],1):
        poly=obstacle_corners(b['obstacle']);center=np.asarray(b['obstacle']['center_xy_m'])
        ax.add_patch(Polygon(poly,fc=BOX,ec='#683E7E',alpha=.42,lw=1.,zorder=5))
        anchor=np.array([center[0],poly[:,1].max()]);ax.annotate(f"box{i} @ {b['time']:.1f}s",anchor,xytext=(0,7),textcoords='offset points',ha='center',color='#65357C',fontsize=8,
            bbox=dict(fc='white',ec='none',alpha=.8,pad=1.2),zorder=12)
        if b.get('pose') is not None:
            ax.scatter(*b['pose'][:2],marker='D',s=40,fc=BOX,ec='white',lw=.6,zorder=13)
            ax.annotate(f"spawn{i}",b['pose'][:2],xytext=(4,-11),textcoords='offset points',fontsize=6.5,color='#65357C',zorder=13)
    if not d['boxes']:ax.text(.02,.93,'BOX NOT SPAWNED',transform=ax.transAxes,color='#65357C',fontsize=8)
    rejected=[e for e in d['checks'] if not e['passed']]
    if rejected:
        points=np.asarray([e['pose'][:2] for e in rejected]);ax.scatter(*points.T,marker='x',c=REJECT,s=24,lw=.9,zorder=10)
    for e in d['triggers']:ax.scatter(*e['B'][:2],marker='^',s=45,fc=R3,ec='white',lw=.55,zorder=14)
    for e in d['ends']:ax.scatter(*e['pose'][:2],marker='s',s=33,fc='none',ec=R3,lw=1.25,zorder=14)
    start=np.asarray(c['start_pose']);goal=np.asarray(c['goal_pose'])
    ax.scatter(*start[:2],marker='^',s=60,fc='white',ec='#111111',lw=1.3,zorder=15)
    ax.add_patch(Circle(goal[:2],.5,fc='#009E7309',ec='#167B50',ls='--',lw=1.,zorder=2))
    ax.scatter(*goal[:2],marker='*',s=120,c='#167B50',ec='white',lw=.5,zorder=13)
    declaration=d['declaration_node']
    if declaration:
        a=np.asarray(declaration['pose']);b=np.asarray(declaration['hmm_node_xy']);near=np.asarray(declaration['nearest_node_xy'])
        ax.plot([a[0],b[0]],[a[1],b[1]],color='#111111',lw=.85,alpha=.8,zorder=11)
        ax.scatter(*a,marker='o',s=75,fc='none',ec='black',lw=1.6,zorder=17)
        ax.scatter(*b,marker='x',s=70,c='black',lw=1.5,zorder=17)
        ax.scatter(*near,marker='o',s=50,fc='none',ec='#4B522D',lw=1.1,zorder=16)
        ax.annotate(f"stop {declaration['time_s']:.1f}s",a,xytext=(5,8),textcoords='offset points',fontsize=7,
            bbox=dict(fc='white',ec='none',alpha=.8,pad=1),zorder=18)
    elif d['contacts']:
        ax.scatter(*d['contacts'][0]['detected_pose'][:2],marker='X',s=90,c=REJECT,ec='white',lw=.5,zorder=17)
    else:ax.scatter(*xy[-1],marker='s',s=45,fc='white',ec='black',lw=1.3,zorder=15)
    ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),xlabel='x (m)',ylabel='y (m)');ax.set_aspect('equal',adjustable='box')
    r=d['record'];tail=f"R3 applied {r.get('detour_applied_count',0)}" if r['method']=='OURS-R3' else 'Graph adopt '+(f"{100*r['graph_adoption_rate']:.1f}%" if r.get('graph_adoption_rate') is not None else 'N/A')
    ax.set_title(f"{r['method']} | {r['classification']}\nbox {passage(r)} | goal {fnum(r.get('goal_time_s'))}\nstop {fnum(r.get('stopped_s'))} | {tail}",fontsize=11,pad=10)
    if declaration:
        msg=f"Declared pose: HMM n{declaration['hmm_node']} / nearest n{declaration['nearest_node']} / delta n={declaration['signed_node_difference']:+d}"
    else:msg='No declared arrival; HMM stop-node marker N/A'
    ax.text(.5,-.17,msg,ha='center',va='top',transform=ax.transAxes,fontsize=9,
        bbox=dict(fc='#F6F6F6',ec='#D6D6D6',lw=.5,pad=3.5))
    ax.text(.01,.01,f"EC reject {len(rejected)} | raw {d['native_info']['candidates']} paths",transform=ax.transAxes,fontsize=7,
        bbox=dict(fc='white',ec='none',alpha=.85,pad=1.4),zorder=20)

def legend(fig,data):
    states={s for d in data for s in d['states']}
    a=[Line2D([],[],color=STATE_COLORS[s],lw=3,label=s) for s in STATE_COLORS if s in states]
    fig.legend(handles=a,loc='lower center',bbox_to_anchor=(.5,.105),ncol=min(7,len(a)),frameon=False,fontsize=8.5,columnspacing=1.1)
    b=[Line2D([],[],color=CUT,ls=':',label='CUT path'),Line2D([],[],color=GRAPH,ls='--',label='GRAPH-HO path'),
       Line2D([],[],color=R3,label='R3 path'),Line2D([],[],color=R2,ls=':',label='R2 path'),
       Line2D([],[],color=R3,marker='^',ls='',label='R3 trigger'),Line2D([],[],color=R3,marker='s',mfc='none',ls='',label='R3 end'),
       Line2D([],[],color=BOX,marker='D',ls='',label='robot at spawn'),Line2D([],[],color=REJECT,marker='x',ls='',label='EC REJECT'),
       Line2D([],[],color='black',marker='o',mfc='none',ls='',label='declared pose'),Line2D([],[],color='black',marker='x',ls='',label='HMM node'),
       Line2D([],[],color='#4B522D',marker='o',mfc='none',ls='',label='actual nearest node'),Line2D([],[],color='#8A8FA2',alpha=.4,lw=.6,label='raw8 candidates')]
    fig.legend(handles=b,loc='lower center',bbox_to_anchor=(.5,.035),ncol=6,frameon=False,fontsize=8.5,columnspacing=1.4)

def plot_block(data,delay,scene_name,seed,out):
    lo,hi=extent(data);ratio=float((hi[1]-lo[1])/(hi[0]-lo[0]));height=max(6.2,min(10.,4.+6.*ratio))
    fig,axes=plt.subplots(1,3,figsize=(22,height));fig.subplots_adjust(left=.035,right=.985,top=.80,bottom=.255,wspace=.19)
    for ax,d in zip(axes,data):scene(ax,d,lo,hi)
    fig.suptitle(f"NIGHT {delay} | {scene_name} | seed {seed} | fixed block: CUT / GRAPH-HO / OURS-R3",fontsize=15,y=.98)
    legend(fig,data)
    fig.text(.5,.012,'Saved trajectories/plans only. All boxes are overlaid at their recorded spawn positions; labels give spawn time. Black link: declared robot pose to logged HMM node.',ha='center',fontsize=7.5,color='#555555')
    fig.savefig(out,dpi=150);plt.close(fig)

def summary_text(r):
    passed='통과 '+fnum(r.get('box_passage_from_spawn_s')) if r.get('box_passage') else '미통과'
    return f"{r['classification']} · {passed} · 도착 {fnum(r.get('goal_time_s'))}"

def main():
    started=time.monotonic();inputs=Inputs();out=ROOT/'docs/figures';out.mkdir(exist_ok=True)
    blocks=[];counts=[];details=[];files=[]
    for e,delay in COHORTS:
        records=inputs.json(ROOT/f'research/results/night20261111/{e}/runs.json')
        by={(r['scene'],r['index'],r['method']):r for r in records};cohort=[]
        for scene_name in SCENES:
            for seed in SEEDS:
                # Fixed selection, with no outcome filtering and no attempt swapping.
                rr=[by[(scene_name+'_'+delay,seed,m)] for m in METHODS]
                assert all(r['technical_validation']=='PASS' for r in rr),'Selected block lacks validated saved data'
                data=[prepare_run(r,inputs) for r in rr];name=f'graphcmp_{delay}_{scene_name}_{seed}.png'
                plot_block(data,delay,scene_name,seed,out/name);files.append(name)
                blocks.append(dict(delay=delay,scene=scene_name,seed=seed,records=rr,figure=name));cohort.append(rr)
                for d in data:
                    details.append(dict(experiment=e,key=d['record']['key'],output=str(d['root']),figure=name,
                        samples_72hz=len(d['t']),installed_paths=len(d['plans']),path_types={kind:sum(p['type']==kind for p in d['plans']) for kind in ('CUT','GRAPH','R2','R3')},
                        r3_triggers=len(d['triggers']),r3_ends=len(d['ends']),native=d['native_info'],declared_node=d['declaration_node']))
                print(json.dumps(dict(figure=name,runs=3)),flush=True)
        counts.append(dict(delay=delay,blocks=len(cohort),r3_only=sum(c[2]['box_passage'] and not c[0]['box_passage'] and not c[1]['box_passage'] for c in cohort),
            r3_and_cut=sum(c[2]['box_passage'] and c[0]['box_passage'] for c in cohort),
            r3_and_graph=sum(c[2]['box_passage'] and c[1]['box_passage'] for c in cohort),
            r3_pass_then_wrong_stop=sum(c[2]['box_passage'] and c[2]['wrong_stop'] for c in cohort)))
    inputs.unchanged();assert len(blocks)==16 and len(details)==48
    table=['| 지연 | 고정 블록 | R3만 통과(다른 둘 미통과) | 둘 다: R3+CUT | 둘 다: R3+GRAPH-HO | R3 통과 후 잘못된 도착 |',
           '|---|---:|---:|---:|---:|---:|']
    for c in counts:table.append(f"| {c['delay']} | {c['blocks']} | {c['r3_only']} | {c['r3_and_cut']} | {c['r3_and_graph']} | {c['r3_pass_then_wrong_stop']} |")
    table.append('| 합계 | 16 | '+' | '.join(str(sum(c[k] for c in counts)) for k in ('r3_only','r3_and_cut','r3_and_graph','r3_pass_then_wrong_stop'))+' |')
    lines=['# Graph 성공/실패 비교 주행 그림','\n'.join(table),
        '고정 선택: E3(D150) 및 E1(D075), L2·H1·H2·H1-v2 × seed225·226 전체16블록/48run. 기존 report가 선택한 attempt를 그대로 사용했다. 위 집계는 저장된 `box_passage`와 `wrong_stop`만 사용한다. “R3만”은 CUT·GRAPH-HO 모두 미통과, “둘 다”는 세 방법의 모호함을 피하려고 두 짝을 각각 표시했다. 집계 열은 서로 배타적이지 않다. H2의 통과는 동결 지표대로 두 상자 모두 통과한 경우다.',
        '저장 로그만 읽었다. 시뮬레이션·solver·EC 재검사·HMM 재생·분류/성과 지표 재계산은 없다. 도착 선언 pose와 그 순간 로그된 HMM 노드를 검은 선으로 연결했다. 실제 최근접 노드는 **저장 선언 pose**에서 Topomap node pose까지의 유클리드 거리 최소 노드이며 표시용 기하 계산만 했다(관측 시점의 기존 node error를 대신 쓰지 않음). Δn=HMM−최근접, 노드번호는0부터 시작한다. 선언이 없는 timeout/collision run은 해당 마커를 만들지 않았다.',
        '| 블록 | CUT: 분류·통과·도착시간 | GRAPH-HO: 분류·통과·도착시간 | OURS-R3: 분류·통과·도착시간 |\n|---|---|---|---|\n'+
        '\n'.join('| '+f"{b['delay']} {b['scene']} {b['seed']}"+' | '+' | '.join(summary_text(r) for r in b['records'])+' |' for b in blocks),
        '패널은 CUT | GRAPH-HO | OURS-R3 순서다. 제목의 통과 시간은 출현→통과 시간, 도착시간은 성공 run의 기존 값이다(—=미도착). R3 파란삼각형은 모든 저장 trigger, 파란사각형은 실제 적용된 job의 저장 END 위치다. R2는 CUT으로 오인하지 않도록 보라 점선으로 따로 표시했다. 원8후보는 controller에 도착한 각 chunk의 저장 metric을 관측 pose로 world 변환해 아주 옅게 그렸다. 상자 윤곽은 시간 전체를 겹친 것이며 실제 출현 시각과 출현 순간 로봇 위치(보라 마름모)를 함께 표시했다.']
    lines.extend(f"![{b['delay']} {b['scene']} seed{b['seed']}](figures/{b['figure']})" for b in blocks)
    lines.append('재생성(저장 로그만): `PYTHONPATH=research /usr/bin/python3 -m nomad_graphcmp_plots`')
    (ROOT/'docs/GRAPH_SUCCESS_FAILURE_PLOTS.md').write_text('\n\n'.join(lines)+'\n')
    manifest=dict(selection=dict(cohorts=COHORTS,scenes=SCENES,seeds=SEEDS,methods=METHODS),figures=files,dpi=150,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),counts=counts,runs=details,input_files=inputs.files,
        simulations=0,solves=0,ec_reevaluations=0,hmm_replays=0,elapsed_s=time.monotonic()-started)
    (out/'graphcmp_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(dict(figures=len(files),runs=len(details),input_files_unchanged=len(inputs.files),elapsed_s=manifest['elapsed_s'],counts=counts)))
if __name__=='__main__':main()
