"""Fixed-case scientific figures and 10x top-down replay from saved data only."""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle,FancyArrowPatch
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from nomad_isaac.common import ROOT
from nomad_phase0.chunk_report import trace
from nomad_phase15b.depth import Snapshot
from nomad_phase20.metrics import rows
from .config import protocol,runtime_config,place

COLORS={'M1_ROTATE':'tab:blue','M3_DETOUR':'tab:orange'}

NO_DATA='TECHNICAL_FAILURE (no data)'
REQUIRED=('summary.json','agent_trajectory.csv','events.jsonl','repair.jsonl','recovery.jsonl',
          'phase20_commands.jsonl','depth/updates.jsonl','detour.jsonl','observations.jsonl')


def blank_panel(ax,method):
    ax.clear();ax.set_axis_off();ax.set_title(method,fontsize=9)
    ax.text(.5,.5,NO_DATA,transform=ax.transAxes,ha='center',va='center',fontsize=10)


def load(record,issues=None):
    run=Path(record['output'])
    def unavailable(reason):
        if issues is not None:issues.append(dict(method=record['method'],output=str(run),reason=reason))
        return None
    missing=[name for name in REQUIRED if not (run/name).is_file()]
    if missing:return unavailable('Missing required files: '+', '.join(missing))
    try:
        summary=json.loads((run/'summary.json').read_text());epoch=int(summary['epoch_monotonic_ns'])
        rr,poses=trace(run);t=np.array([float(r['simulation_time_s']) for r in rr])
        if not len(t) or not np.isfinite(poses).all() or not np.isfinite(t).all():return unavailable('Empty or invalid pose trace')
        spawn=json.loads((run/'dynamic/spawn.json').read_text()) if (run/'dynamic/spawn.json').exists() else None
        data=dict(record=record,run=run,poses=poses,t=t,spawn=spawn,epoch_ns=epoch,events=rows(run/'events.jsonl'),repairs=rows(run/'repair.jsonl'),
            recovery=rows(run/'recovery.jsonl'),commands=rows(run/'phase20_commands.jsonl'),updates=rows(run/'depth/updates.jsonl'),
            detours=rows(run/'detour.jsonl'),observations=[r for r in rows(run/'observations.jsonl') if 'observation_id' in r],snapshot_cache={})
        if not data['commands']:return unavailable('Empty command log')
        if not data['observations']:return unavailable('No saved RGB observation records')
        required=[Path(u['file']) for u in data['updates']]+[run/o['rgb_file'] for o in data['observations']]
        absent=[str(f) for f in required if not f.is_file()]
        if absent:return unavailable(f'Missing referenced depth/RGB files ({len(absent)}): '+', '.join(absent[:3]))
        return data
    except (OSError,ValueError,KeyError,TypeError) as exc:
        return unavailable('Unreadable required visualization input: '+str(exc))


def occupancy(data,update):
    if update is None:return np.empty((0,2))
    file=update['file']
    if file not in data['snapshot_cache']:
        field=Snapshot.load(file);iy,ix=np.nonzero(field.occupied);p=field.origin+np.c_[ix,iy]*field.h
        p=p[(p[:,0]>=-1.05)&(p[:,0]<=9.05)&(p[:,1]>=-1.55)&(p[:,1]<=1.55)]
        data['snapshot_cache'][file]=p
    return data['snapshot_cache'][file]

def first_box_map(data):
    if not data['spawn']:return None
    target=data['record'].get('first_depth_map_observed_s')
    if target is None:return None
    return next((u for u in data['updates'] if abs(u['sim_s']-target)<1e-12),None)

def frame_map(data,t):
    # Latest map actually published by floor(t), not a future capture with that timestamp.
    horizon=math.floor(t);rr=[]
    for u in data['updates']:
        published=(u['publication_monotonic_ns']-data['epoch_ns'])/1e9
        if published<=horizon and u['sim_s']<=horizon:rr.append(u)
    return rr[-1] if rr else None

def walls(ax):
    ax.axhline(1.5,c='.35',lw=1);ax.axhline(-1.5,c='.35',lw=1)
    ax.axvline(-1,c='.35',lw=1);ax.axvline(9,c='.35',lw=1)
    ax.set_xlim(-1.1,9.1);ax.set_ylim(-1.65,1.65);ax.set_aspect('equal')
    ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)')

def draw_box(ax,box,**kw):
    x,y=box['center_xy_m'];w,h=box['size_xyz_m'][:2]
    patch=Rectangle((x-w/2,y-h/2),w,h,**kw);ax.add_patch(patch);return patch

def scene_levels(out):
    p=protocol();manifest=json.loads(Path(p['SO']['topomap']).read_text());nodes=np.array([n['world_pose'] for n in manifest['nodes']])
    fig,axes=plt.subplots(1,1,figsize=(12,4),constrained_layout=True)
    for ax,level in zip([axes],('L2',)):
        if level=='L1':box=dict(center_xy_m=[2+.09+1.2+.175,-.15],size_xyz_m=[.35,.35,.8])
        else:box=place(runtime_config('M1_ROTATE',95,level=level),[2,0,0])['obstacle']
        walls(ax);draw_box(ax,box,color='purple',alpha=.3)
        ax.plot(nodes[:,0],nodes[:,1],'.--',c='.6',ms=3,label='Frozen RGB Topomap nodes')
        ax.scatter([0,8],[0,0],marker='*',s=90,c=['green','red'],label='Start / goal')
        ax.scatter(2,0,marker='D',c='gold',edgecolors='black',s=45,label='Canonical spawn pose')
        gaps=[1.5-box['center_xy_m'][1]-box['size_xyz_m'][1]/2,1.5+box['center_xy_m'][1]+(-box['size_xyz_m'][1]/2)]
        ax.set_title(f"{level}: box {box['size_xyz_m'][0]:.2f} × {box['size_xyz_m'][1]:.2f}m; gaps {gaps[0]:.2f}/{gaps[1]:.2f}m",fontsize=10)
        ax.legend(loc='upper right',fontsize=7,ncol=3)
    fig.suptitle('Canonical B=(2,0), even-seed placement; actual per-run boxes are shown separately. Required safe gap=0.23m.',fontsize=10)
    fig.savefig(out/'scene_levels.png',dpi=140);plt.close(fig)

def pair_plot(level,seed,data,out):
    if not any(data.get(m) for m in COLORS):return False
    fig,axes=plt.subplots(1,2,figsize=(16,5.4),constrained_layout=True)
    maximum=max((d['t'][-1] for d in data.values() if d),default=90.);norm=Normalize(0,maximum)
    for ax,method in zip(axes,COLORS):
        walls(ax);d=data.get(method)
        if d is None:blank_panel(ax,method);continue
        cloud=occupancy(d,first_box_map(d))
        if len(cloud):ax.scatter(cloud[:,0],cloud[:,1],s=1,c='.65',alpha=.45,label='First map showing box')
        initial_cells=[r['cells_world'] for u in d['updates'] for r in u.get('new_component_records',[])]
        if initial_cells:
            cells=np.concatenate(initial_cells);ax.scatter(cells[:,0],cells[:,1],s=3,c='#541277',alpha=.8,label='New component: first recognition')
        if d['spawn']:
            draw_box(ax,d['spawn']['obstacle'],facecolor='purple',edgecolor='purple',alpha=.24)
            ax.scatter(*d['spawn']['pose'][:2],marker='D',c='gold',edgecolors='k',s=48,label='Box spawn')
        segments=np.stack([d['poses'][:-1,:2],d['poses'][1:,:2]],axis=1)
        for gap in d['record'].get('publication_gaps',[]):
            mask=(d['t'][1:]>=gap['start_s'])&(d['t'][1:]<=gap['end_s'])
            ax.add_collection(LineCollection(segments[mask],colors='.6',linewidth=6,alpha=.65))
        lc=LineCollection(segments,cmap='viridis',norm=norm,linewidth=2);lc.set_array(d['t'][1:]);ax.add_collection(lc)
        marks={}
        for e in d['events']:
            if e.get('phase16',{}).get('selection',{}).get('all_unsafe'):marks.setdefault('ALL_UNSAFE',[]).append(e['agent_pose_at_switch'][:2])
        for r in d['recovery']:
            if r['event']=='START':marks.setdefault('Recovery start',[]).append(r['pose'][:2])
        for r in d['repairs']:
            if r['event']=='PATH_APPLIED':
                if r['alignment']:marks.setdefault('Start alignment',[]).append(r['pose'][:2])
                if r['kind']=='REPAIR':
                    marks.setdefault('Repair applied',[]).append(r['pose'][:2]);q=np.array(r['path_world']);ax.plot(q[:,0],q[:,1],'--',c='magenta',lw=1)
            if r['event']=='RESULT' and r['disposition'] in ('REJECTED','TIMEOUT','WAYPOINT_TIMEOUT'):
                marks.setdefault('Repair rejected/timeout',[]).append(r['pose_at_result'][:2])
        for r in d['detours']:
            if r['event']=='TRIGGER' and r['trigger']=='B':marks.setdefault('NO_PROGRESS',[]).append(r['B'][:2])
            if r['event']=='APPLIED':
                q=np.array(r['path']);ax.plot(q[:,0],q[:,1],'--',c='darkorange',lw=1.4,label='Applied detour' if not any(x.get_label()=='Applied detour' for x in ax.lines) else None)
        denied=[r['pose'][:2] for r in d['detours'] if r['event']=='NEW_OBSTACLE_CONDITION' and r['reason']=='NO_NEW_OBSTACLE_AHEAD']
        if denied:
            q=np.array(denied);ax.scatter(q[:,0],q[:,1],marker='D',s=15,facecolors='none',edgecolors='.5',linewidths=.6,label='NO_NEW_OBSTACLE_AHEAD')
        for r in d['detours']:
            if r['event']=='END':
                ax.scatter(*r['pose'][:2],marker='s',s=32,facecolors='none',edgecolors='brown')
                ax.annotate(r['reason'],r['pose'][:2],xytext=(4,-14),textcoords='offset points',fontsize=6,color='brown',bbox=dict(facecolor='white',alpha=.8,edgecolor='none'))
        symbols={'NO_PROGRESS':('D','darkorange'),'ALL_UNSAFE':('x','red'),'Recovery start':('$↻$','darkorange'),'Repair applied':('*','magenta'),
                 'Repair rejected/timeout':('o','purple'),'Start alignment':('^','black')}
        for label,points in marks.items():
            q=np.array(points);marker,color=symbols[label]
            ax.scatter(q[:,0],q[:,1],marker=marker,s=48,color=color,facecolors='none' if marker=='o' else color,label=label)
        r=d['record'];fmt=lambda x:'—' if x is None else f'{x:.1f}s'
        ax.set_title(f"{method} · {r.get('classification','unavailable')}\ngoal {fmt(r.get('goal_time_s'))}, box pass {fmt(r.get('box_passage_time_s'))}\nALL_UNSAFE {r.get('all_unsafe',0)} · repair {r.get('repair_attempts',0)}/{r.get('repair_accepted',0)} applied · rotate {r.get('recovery_count',0)} · detour {r.get('detour_applied',0)}",fontsize=9)
        ax.legend(fontsize=6,loc='upper left',ncol=2)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='viridis'),ax=axes,orientation='horizontal',fraction=.06,label='Simulation time (s)')
    role='Excluded smoke / technical check' if any(d and d['record'].get('excluded') for d in data.values()) else 'Pilot main run'
    fig.suptitle(f'{role} · {level}, seed {seed}: each panel uses only its own box and depth observations',fontsize=10)
    fig.savefig(out/f'drive_{level}_{seed}.png',dpi=140);plt.close(fig)

def pair_gif(level,seed,data,out):
    if not any(data.get(m) for m in COLORS):return False
    fig,axes=plt.subplots(1,2,figsize=(12,3.4),dpi=90,constrained_layout=True);artists={}
    for ax,method in zip(axes,COLORS):
        walls(ax);d=data.get(method)
        if d is None:blank_panel(ax,method);continue
        cloud=ax.scatter([],[],s=1,c='.65',alpha=.4);route,=ax.plot([],[],'--',c='purple',lw=1);trail,=ax.plot([],[],c=COLORS[method],lw=1)
        circle=Circle(d['poses'][0,:2],.09,color=COLORS[method],alpha=.65);ax.add_patch(circle)
        arrow=FancyArrowPatch((0,0),(.2,0),arrowstyle='->',mutation_scale=12,color='black');ax.add_patch(arrow)
        box=draw_box(ax,d['spawn']['obstacle'],color='purple',alpha=.3) if d['spawn'] else None
        if box:box.set_visible(False)
        label=ax.text(.02,.02,'',transform=ax.transAxes,fontsize=7)
        trigger_marks=ax.scatter([],[],marker='D',c='darkorange',s=35)
        gap_lines=LineCollection([],colors='.6',linewidth=5,alpha=.7);ax.add_collection(gap_lines)
        blocked_marks=ax.scatter([],[],marker='D',s=15,facecolors='none',edgecolors='.5',linewidths=.6)
        new_cells=ax.scatter([],[],s=3,c='#541277');end_marks=ax.scatter([],[],marker='s',s=30,facecolors='none',edgecolors='brown')
        artists[method]=(cloud,route,trail,circle,arrow,box,label,trigger_marks,gap_lines,blocked_marks,new_cells,end_marks)
    maximum=min(150.,max((d['t'][-1] for d in data.values() if d),default=0.));frames=[]
    for t in np.arange(0,maximum+1e-10,1.)[:150]:
        for ax,method in zip(axes,COLORS):
            d=data.get(method)
            if d is None:continue
            cloud,route,trail,circle,arrow,box,label,trigger_marks,gap_lines,blocked_marks,new_cells,end_marks=artists[method];tick=min(round(t*72),len(d['poses'])-1);p=d['poses'][tick]
            circle.center=p[:2];arrow.set_positions(p[:2],p[:2]+.23*np.array([np.cos(p[2]),np.sin(p[2])]))
            marks=[r['B'][:2] for r in d['detours'] if r['event']=='TRIGGER' and r['trigger']=='B' and r['simulation_time_s']<=t]
            points=[r['cells_world'] for u in d['updates'] if (u['publication_monotonic_ns']-d['epoch_ns'])/1e9<=t for r in u.get('new_component_records',[])]
            new_cells.set_offsets(np.concatenate(points) if points else np.empty((0,2)))
            endings=[r for r in d['detours'] if r['event']=='END' and r['simulation_time_s']<=t]
            end_marks.set_offsets(np.array([r['pose'][:2] for r in endings]).reshape(-1,2))
            denied=[r['pose'][:2] for r in d['detours'] if r['event']=='NEW_OBSTACLE_CONDITION' and r['reason']=='NO_NEW_OBSTACLE_AHEAD' and r['simulation_time_s']<=t]
            blocked_marks.set_offsets(np.array(denied).reshape(-1,2))
            trigger_marks.set_offsets(np.array(marks).reshape(-1,2));segments=np.stack([d['poses'][:tick,:2],d['poses'][1:tick+1,:2]],axis=1);mask=np.zeros(tick,dtype=bool)
            for gap in d['record'].get('publication_gaps',[]):mask|=(d['t'][1:tick+1]>=gap['start_s'])&(d['t'][1:tick+1]<=gap['end_s'])
            gap_lines.set_segments(segments[mask])
            trail.set_data(d['poses'][:tick+1,0],d['poses'][:tick+1,1]);cloud.set_offsets(occupancy(d,frame_map(d,min(t,d['t'][-1]))))
            if box:box.set_visible(t>=d['spawn']['simulation_time_s'])
            controls=[c for c in d['commands'] if c['time_s']<=min(t,d['t'][-1])];control=controls[-1] if controls else None
            paths=[r for r in d['repairs'] if r['event']=='PATH_APPLIED' and r['simulation_time_s']<=min(t,d['t'][-1])]
            inactive=not control or control.get('path_source_id') is None or control['source'] in ('STOP_WAIT','REPAIR_WAIT','DETOUR_WAIT','RECOVER_ROTATE','WAIT_FRESH','WAYPOINT_TIMEOUT','ENDPOINT')
            if paths and not inactive:
                q=np.array(paths[-1]['path_world']);route.set_data(q[:,0],q[:,1]);route.set_color('darkorange' if paths[-1]['kind']=='DETOUR' else 'purple')
            else:route.set_data([],[])
            ax.set_title(f"{method} · {level}/{seed} · t={min(t,d['t'][-1]):.1f}s",fontsize=9)
            label.set_text((control['source'] if control else 'initial')+(' · last end: '+endings[-1]['reason'] if endings else '')+(' · terminated (pose held)' if t>d['t'][-1] else ''))
        role='Excluded smoke' if any(d and d['record'].get('excluded') for d in data.values()) else 'Pilot main run'
        fig.suptitle(role+' · saved SE(2) replay · 10× · depth uses only already-published snapshots',fontsize=9)
        fig.canvas.draw();frame=Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:,:,:3].copy()).convert('P',palette=Image.Palette.ADAPTIVE,colors=128);frames.append(frame)
    if frames:frames[0].save(out/f'drive_{level}_{seed}.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,optimize=False)
    plt.close(fig)

def rgb_strip(level,seed,data,out):
    if not any(data.get(m) for m in COLORS):return False
    fig,axes=plt.subplots(2,6,figsize=(13,4.8),constrained_layout=True)
    for row,method in enumerate(COLORS):
        d=data.get(method)
        for k,ax in enumerate(axes[row]):
            ax.axis('off')
            if d is None:blank_panel(ax,method);continue
            if not d['spawn']:ax.set_title(f'{method}\nno spawn/frame',fontsize=7);continue
            target=d['spawn']['simulation_time_s']+2*k
            o=next((o for o in d['observations'] if o['observation_sim_s']>=target-1e-12),None)
            if o:
                with Image.open(d['run']/o['rgb_file']) as im:ax.imshow(np.array(im))
                ax.set_title(f"{method}\n{ o['observation_sim_s']:.2f}s (+{o['observation_sim_s']-d['spawn']['simulation_time_s']:.2f}s)",fontsize=7)
            else:ax.set_title(f'{method}\nframe unavailable',fontsize=7)
    role='Excluded smoke' if any(d and d['record'].get('excluded') for d in data.values()) else 'Pilot main run'
    fig.suptitle(f'{role} · {level}/{seed}: RGB at/after spawn + 0,2,4,6,8,10s',fontsize=10)
    fig.savefig(out/f'rgb_strip_{level}_{seed}.png',dpi=140);plt.close(fig)

def generate(records,out,cases=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);scene_levels(out)
    cases=cases or [(l,i) for l in ('L2',) for i in range(95,101)]
    status=[]
    for level,seed in cases:
        issues=[];matched={r['method']:r for r in records if r['scene']==level and r['index']==seed}
        selected={m:load(matched[m],issues) if m in matched else None for m in COLORS}
        for m in COLORS:
            if m not in matched:issues.append(dict(method=m,reason='No run record'))
        skipped=not any(selected.values());status.append(dict(scene=level,index=seed,skipped=skipped,missing=issues))
        if skipped:
            # Remove only managed, derived images from an earlier partial report.
            for name in (f'drive_{level}_{seed}.png',f'drive_{level}_{seed}.gif',f'rgb_strip_{level}_{seed}.png'):(out/name).unlink(missing_ok=True)
            print(f'[figures] {level}/{seed} skipped: both runs have no usable data',flush=True);continue
        pair_plot(level,seed,selected,out);pair_gif(level,seed,selected,out);rgb_strip(level,seed,selected,out)
        print(f'[figures] {level}/{seed} png/gif/rgb done',flush=True)
    (out/'visualization_status.json').write_text(json.dumps(status,indent=2)+'\n')
    return status


def passage_summary(pairs,out):
    fig,axes=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
    for ax,key,title in zip(axes,('passage_s','goal_s'),('Box passage time from spawn','Goal arrival time')):
        for row in pairs:
            a,b=row['M1_'+key],row['M3_'+key];color=plt.cm.tab10((row['index']-95)%10)
            if a is not None and b is not None:ax.plot([0,1],[a,b],'.-',c=color,label=str(row['index']))
            else:
                for x,value in enumerate((a,b)):
                    if value is not None:ax.scatter(x,value,c=[color],marker='o')
                    else:ax.text(x,-.06-.035*(row['index']-95),f"{row['index']}: missing",ha='center',transform=ax.get_xaxis_transform(),color=color,fontsize=7)
        ax.set_xticks([0,1],['M1 ROTATE','M3 DETOUR']);ax.set_xlim(-.25,1.25);ax.set_ylabel('Seconds');ax.set_title(title)
        if ax.lines:ax.legend(title='Seed',fontsize=8)
    fig.suptitle('Same-seed paired times; missing outcomes are not imputed')
    fig.savefig(Path(out)/'passage_summary.png',dpi=140);plt.close(fig)


def cumulative_plot(records,out):
    fig,axes=plt.subplots(2,1,figsize=(14,7),constrained_layout=True)
    for method in COLORS:
        rr=sorted([r for r in records if r['method']==method],key=lambda r:r['index'])
        for r in rr:
            valid=r.get('technical_validation')=='PASS';color=COLORS[method];dx=-.12 if method=='M1_ROTATE' else .12;x=r['index']+dx
            if valid and r.get('passed_box'):axes[0].scatter(x,r['box_passage_time_s'],c=color,s=28)
            else:axes[0].scatter(x,0,edgecolors=color,facecolors='none',s=28)
            axes[1].scatter(x,int(valid and r.get('success',False)),c=color if valid else 'none',edgecolors=color,s=28)
        axes[0].plot([],[],'.',c=COLORS[method],label=method)
    phases=[('20D',[86,87,88]),('20E',list(range(89,95))),('20F',list(range(95,101)))]
    for name,indices in phases:
        for ax in axes:ax.axvspan(min(indices)-.45,max(indices)+.45,color='.5',alpha=.06 if name!='20E' else .15)
        axes[0].text(np.mean(indices),1.01,name,transform=axes[0].get_xaxis_transform(),ha='center')
    axes[0].set_ylabel('Box passage seconds (open at0: missing)');axes[0].legend();axes[1].set_ylabel('Goal reached');axes[1].set_yticks([0,1],['No','Yes']);axes[1].set_xlabel('Seed index');axes[1].set_xticks(range(86,101))
    fig.suptitle('L2 descriptive cumulative15 seeds: method definitions changed across20D /20E /20F')
    fig.savefig(Path(out)/'cumulative_L2.png',dpi=140);plt.close(fig)
