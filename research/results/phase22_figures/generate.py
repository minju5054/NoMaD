"""Read-only saved-run figures. No model, solver, controller or experiment calls."""
import hashlib,json,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon,Rectangle,Circle,FancyArrowPatch
from PIL import Image
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase20f.visualize import load,occupancy,frame_map
from nomad_phase22.drive_geometry import corners

OUT=ROOT/'research/results/phase22_figures'
CASES=(('L2',122,'phase22_refine_drive_01'),('L2B',123,'phase22_l2b_rerun_01'))
METHODS=('P0_ASTAR','P1_GRAPH','P2F_ASTAR_GRAPH')
LABELS=('P0 · A*','P1 · Graph','P2F · A* + Graph')
NORM=Normalize(0,90);ORANGE='#e87314';BLUE='#2678c8';GRAY='#737373'
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})

def rows(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x]
def prepare(scene,index,folder,method):
    metric=ROOT.parent/'artifacts/isaac6'/folder/'metrics'/f'{scene}_{index}_{method}.json'
    record=json.loads(metric.read_text());d=load(record);assert d is not None
    d.update(scene=scene,index=index,method=method,label=LABELS[METHODS.index(method)])
    jobs={j['job_id']:j for j in rows(d['run']/'repair_pool_jobs.jsonl') if j['kind']=='R3'}
    ends={j['job_id']:j for j in d['detours'] if j['event']=='END'};plans=[]
    for event in d['detours']:
        if event['event']!='APPLIED':continue
        job=jobs[event['job_id']];end=ends.get(event['job_id']);path=np.asarray(event['path'])
        np.testing.assert_allclose(path,job['results'][job['selected_sample']]['path'],atol=1e-12,rtol=0)
        raw=None
        if method=='P2F_ASTAR_GRAPH':
            a=job['stage_results']['astar']
            if a['selected_sample'] is not None:raw=np.asarray(a['results'][a['selected_sample']]['path'])
        duration=(end['simulation_time_s'] if end else d['t'][-1])-event['simulation_time_s']
        plans.append(dict(job_id=event['job_id'],path=path,raw=raw,start=event['simulation_time_s'],end=end,executed_ticks=round(duration*72),branch=job.get('branch','ASTAR' if method=='P0_ASTAR' else 'GRAPH')))
    d['plans']=plans;d['ends']=[p['end'] for p in plans if p['end'] is not None]
    d['input_sha256']={str(f):sha256_file(f) for f in [metric,*[d['run']/name for name in ('summary.json','agent_trajectory.csv','controller.jsonl','detour.jsonl','repair.jsonl','repair_pool_jobs.jsonl','phase20_commands.jsonl','dynamic/spawn.json','depth/updates.jsonl')]]}
    d['zero_tick_refined']=any(p['branch']=='REFINED' and p['executed_ticks']==0 for p in plans)
    return d

def scene_axes(ax,d,full=True):
    c=json.loads((d['run']/'summary.json').read_text())['scenario']['corridor'];h=c['half_width']
    ax.add_patch(Rectangle((c['xmin'], -h),c['xmax']-c['xmin'],2*h,fill=False,color='#495057',lw=1.4,zorder=1))
    ax.set_aspect('equal');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.grid(alpha=.14,lw=.5,zorder=0)
    if full:ax.set_xlim(c['xmin']-.12,c['xmax']+.12);ax.set_ylim(-h-.15,h+.15)
    else:
        allp=[corners(d['spawn']['obstacle'])]
        for p in d['plans']:allp.extend([p['path']]+([p['raw']] if p['raw'] is not None else []))
        q=np.concatenate(allp);lo=q.min(0)-.2;hi=q.max(0)+.2
        ax.set_xlim(lo[0],hi[0]);ax.set_ylim(max(-h-.12,lo[1]),min(h+.12,hi[1]))

def box(ax,d):
    p=Polygon(corners(d['spawn']['obstacle']),facecolor='#9973b4',edgecolor='#61377c',alpha=.48,lw=1.2,zorder=2);ax.add_patch(p);return p

def trail(ax,d,stop=None,lw=2.):
    stop=len(d['t'])-1 if stop is None else stop
    xy=d['poses'][:stop+1,:2];segments=np.stack([xy[:-1],xy[1:]],axis=1) if len(xy)>1 else []
    line=LineCollection(segments,cmap='viridis',norm=NORM,linewidth=lw,zorder=3);line.set_array(d['t'][1:stop+1]);ax.add_collection(line);return line

def markers(ax,d,until=math.inf):
    triggers=[r['B'][:2] for r in d['detours'] if r['event']=='TRIGGER' and r['simulation_time_s']<=until]
    ends=[r['pose'][:2] for r in d['ends'] if r['simulation_time_s']<=until]
    if triggers:q=np.array(triggers);ax.scatter(q[:,0],q[:,1],marker='D',s=62,facecolors='#fff4cc',edgecolors='#292929',linewidths=1.1,zorder=8)
    if ends:q=np.array(ends);ax.scatter(q[:,0],q[:,1],marker='o',s=27,c='#111111',edgecolors='white',linewidths=.7,zorder=9)

def plan_lines(ax,d):
    for p in d['plans']:
        if p['raw'] is not None:ax.plot(*p['raw'].T,color=GRAY,ls=(0,(2,2)),lw=1.8,zorder=5)
        ax.plot(*p['path'].T,color=BLUE if d['method']=='P0_ASTAR' else ORANGE,ls=(0,(5,2)),lw=2.1,zorder=6)

def title(d,split=False):
    r=d['record'];c=r.get('detour_minimum_clearance_m');gap=f'{100*c:.1f} cm' if c is not None else 'N/A (0 executed ticks)'
    separator='\n' if split else '  |  '
    return f"{d['label']}  |  {r['classification']}"+separator+f"passage {r['box_passage_time_s']:.2f} s  |  detour min clearance {gap}"

LEGEND=[Line2D([],[],color=BLUE,ls='--',lw=2,label='Applied A* detour (P0)'),Line2D([],[],color=ORANGE,ls='--',lw=2,label='Applied Graph / refined plan'),Line2D([],[],color=GRAY,ls=':',lw=2,label='P2F A* initializer (not executed)'),
    Line2D([],[],color='none',marker='D',markerfacecolor='#fff4cc',markeredgecolor='#292929',markersize=7,label='Trigger'),Line2D([],[],color='none',marker='o',markerfacecolor='#111111',markeredgecolor='white',markersize=7,label='Return to NoMaD pipeline')]

def comparison(data,scene,index):
    fig,axes=plt.subplots(3,2,figsize=(16,10.6),gridspec_kw={'width_ratios':[2.2,1]},layout='constrained')
    for i,d in enumerate(data):
        for ax,full in zip(axes[i],(True,False)):
            scene_axes(ax,d,full);box(ax,d);trail(ax,d);plan_lines(ax,d);markers(ax,d)
        axes[i,0].set_title(title(d,split=True),loc='left',fontsize=10.5,pad=8)
        axes[i,1].set_title('Detour detail'+(' · box yaw +20°' if scene=='L2B' else ''),fontsize=10)
        if d['zero_tick_refined']:
            note='REFINED was APPLIED and ended at the same tick.\n0 executed ticks; dashed plan was not followed.'
            axes[i,0].text(.02,.05,note,transform=axes[i,0].transAxes,fontsize=9,color='#9b3f08',bbox=dict(facecolor='white',edgecolor='#e0aa79',alpha=.94,pad=4))
        elif d['method']=='P2F_ASTAR_GRAPH':
            seconds=sum(p['executed_ticks'] for p in d['plans'])/72
            axes[i,0].text(.02,.05,f'REFINED detour executed for {seconds:.2f} s',transform=axes[i,0].transAxes,fontsize=9,bbox=dict(facecolor='white',edgecolor='none',alpha=.85))
    fig.suptitle(f'Phase 22 · {scene} · seed {index} — saved actual trajectories and applied detour plans',fontsize=15)
    fig.get_layout_engine().set(rect=(0,.075,1,.925))
    fig.legend(handles=LEGEND,loc='lower center',bbox_to_anchor=(.5,.005),ncol=3,frameon=False,fontsize=10)
    fig.colorbar(plt.cm.ScalarMappable(norm=NORM,cmap='viridis'),ax=axes.ravel().tolist(),fraction=.018,pad=.012,label='Simulation time (s)')
    fig.savefig(OUT/f'drive_{scene}_{index}.png',dpi=180);plt.close(fig)

def animation(d):
    fig,ax=plt.subplots(figsize=(12,4.7),dpi=90,layout='constrained');scene_axes(ax,d);obstacle=box(ax,d);obstacle.set_visible(False)
    cloud=ax.scatter([],[],s=1,c='#b8b8b8',alpha=.35,zorder=0);line=trail(ax,d,0)
    current,=ax.plot([],[],color='#9868ac',lw=1.2,ls=':',zorder=4)
    raw,=ax.plot([],[],color=GRAY,lw=1.7,ls=(0,(2,2)),zorder=5)
    refined,=ax.plot([],[],color=BLUE if d['method']=='P0_ASTAR' else ORANGE,lw=2.,ls='--',zorder=6)
    trigger=ax.scatter([],[],marker='D',s=58,facecolors='#fff4cc',edgecolors='#292929',zorder=8)
    end=ax.scatter([],[],marker='o',s=27,c='#111111',edgecolors='white',zorder=9)
    body=Circle(d['poses'][0,:2],.09,facecolor='white',edgecolor='black',lw=1.2,zorder=10);ax.add_patch(body)
    heading=FancyArrowPatch((0,0),(.22,0),arrowstyle='->',mutation_scale=12,color='black',zorder=11);ax.add_patch(heading)
    label=ax.text(.01,.02,'',transform=ax.transAxes,fontsize=8,bbox=dict(facecolor='white',edgecolor='none',alpha=.9))
    fig.colorbar(plt.cm.ScalarMappable(norm=NORM,cmap='viridis'),ax=ax,orientation='horizontal',fraction=.035,pad=.08,label='Trajectory simulation time (s)')
    fig.suptitle(f"{d['scene']} · seed {d['index']} · {d['label']} | saved replay, 10×",fontsize=12)
    times=list(np.arange(0,d['t'][-1],1.))+[float(d['t'][-1])];frames=[];depth_hashes={}
    for t in times:
        tick=min(round(t*72),len(d['t'])-1);pose=d['poses'][tick]
        xy=d['poses'][:tick+1,:2];line.set_segments(np.stack([xy[:-1],xy[1:]],axis=1) if tick else []);line.set_array(d['t'][1:tick+1])
        body.center=pose[:2];heading.set_positions(pose[:2],pose[:2]+.24*np.array([np.cos(pose[2]),np.sin(pose[2])]))
        obstacle.set_visible(t>=d['spawn']['simulation_time_s'])
        update=frame_map(d,t);cloud.set_offsets(occupancy(d,update))
        if update and update['file'] not in depth_hashes:depth_hashes[update['file']]=sha256_file(update['file'])
        ts=[r['B'][:2] for r in d['detours'] if r['event']=='TRIGGER' and r['simulation_time_s']<=t]
        es=[r['pose'][:2] for r in d['ends'] if r['simulation_time_s']<=t]
        trigger.set_offsets(np.array(ts).reshape(-1,2));end.set_offsets(np.array(es).reshape(-1,2))
        commands=[c for c in d['commands'] if c['time_s']<=t];command=commands[-1] if commands else None
        paths=[r for r in d['repairs'] if r['event']=='PATH_APPLIED' and r['simulation_time_s']<=t]
        active=next((p for p in reversed(d['plans']) if p['start']<=t<(p['end']['simulation_time_s'] if p['end'] else d['t'][-1])),None)
        inactive=not command or command.get('path_source_id') is None or command['source'] in ('STOP_WAIT','REPAIR_WAIT','DETOUR_WAIT','RECOVER_ROTATE','WAIT_FRESH','WAYPOINT_TIMEOUT','ENDPOINT')
        current.set_data([],[]);raw.set_data([],[]);refined.set_data([],[])
        if active:
            refined.set_data(*active['path'].T)
            if active['raw'] is not None:raw.set_data(*active['raw'].T)
        elif paths and not inactive:current.set_data(*np.asarray(paths[-1]['path_world']).T)
        notice=''
        if d['zero_tick_refined'] and t>=d['plans'][0]['start']:notice=' | REFINED ended immediately: 0 executed ticks'
        label.set_text((command['source'] if command else 'initial')+notice)
        ax.set_title(title(d)+f'\nt={t:.2f}s · gray cloud: latest already-published depth map',fontsize=9)
        fig.canvas.draw();frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:,:,:3].copy()).convert('P',palette=Image.Palette.ADAPTIVE,colors=128))
    file=OUT/f'drive_{d["scene"]}_{d["index"]}_{d["method"]}.gif'
    frames[0].save(file,save_all=True,append_images=frames[1:],duration=100,loop=0,optimize=False)
    plt.close(fig);d['input_sha256'].update(depth_hashes)
    return dict(file=file.name,frames=len(frames),duration_ms=100*len(frames),speedup=10)

def main():
    OUT.mkdir(parents=True,exist_ok=True);manifest=dict(only_saved_data=True,new_navigation=False,new_inference=False,new_solver_calls=False,records=[],gifs=[])
    for scene,index,root in CASES:
        data=[prepare(scene,index,root,m) for m in METHODS];comparison(data,scene,index)
        for d in data:
            manifest['gifs'].append(animation(d))
            plans=[dict(job_id=p['job_id'],branch=p['branch'],applied_s=p['start'],end_s=p['end']['simulation_time_s'] if p['end'] else None,end_reason=p['end']['reason'] if p['end'] else None,executed_ticks=p['executed_ticks']) for p in d['plans']]
            manifest['records'].append(dict(scene=scene,index=index,method=d['method'],run=str(d['run']),classification=d['record']['classification'],passage_s=d['record']['box_passage_time_s'],detour_min_clearance_m=d['record'].get('detour_minimum_clearance_m'),plans=plans,input_sha256=d['input_sha256']))
            print(f'[figures] {scene}/{index} {d["method"]} GIF complete',flush=True)
    # Verify no saved source file was modified by figure generation.
    for r in manifest['records']:
        for file,h in r['input_sha256'].items():assert sha256_file(file)==h,file
    manifest['output_sha256']={f.name:sha256_file(f) for f in OUT.iterdir() if f.suffix in ('.png','.gif')}
    manifest['generator_sha256']=sha256_file(Path(__file__))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    text='# Phase22 saved-run trajectory figures\n\n'
    text+='No experiment, inference, planning solve, report or runtime code was changed. Passage time is measured from box spawn. Clearance is the stored minimum footprint oracle clearance to box/walls during executed R3 detour intervals; it is not the whole-run minimum. Black circles are logged END positions (return to the normal NoMaD pipeline, not necessarily the next FRESH application).\n\n'
    text+='**L2B seed123 P2F caveat:** REFINED was ACCEPTED/APPLIED at27.1111s and ended with NO_NEW_OBSTACLE_AHEAD at the same tick. It executed0ticks, so detour clearance is N/A. Its dashed refined plan is shown as a logged applied plan, not as a path the robot followed. L2 seed122 P2F did execute its refined detour for2.4444s (176ticks).\n\n'
    for scene,index,_ in CASES:
        text+=f'## {scene} seed {index}\n\n![Comparison](drive_{scene}_{index}.png)\n\n'
        for method in METHODS:text+=f'- [{method} GIF](drive_{scene}_{index}_{method}.gif)\n'
        text+='\n'
    text+='GIFs replay stored72Hz poses at10× (1sim-second per100ms frame), with a0.09m circular footprint and heading. Depth occupancy updates once per simulation second using only snapshots already published by that time. A* gray initializer paths are shown for active P2F refined detours; the zero-duration L2B P2F plan is not displayed as an active executed route. All selected raw paths and output hashes are recorded in manifest.json.\n'
    (OUT/'README.md').write_text(text)

if __name__=='__main__':main()
