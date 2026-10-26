"""One frozen A2 campaign from saved depth, with scoped report commit/push."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import subprocess
import time
import numpy as np
from nomad_isaac.common import ROOT, local_to_world, sha256_file, write_json
from nomad_isaac.clearance import configured_obstacles, obstacle_bounds, single_obstacle_config, point_clearance
from nomad_phase0.graph_v4 import SignedDistanceField
from nomad_phase4.report import write_csv
from .depth_sdf import bounds_from_config
from .evaluate import available, choose, decision, distribution, oracle_clearance, sample_path, suffix
from .occupancy import make_field, ray_kernel, kernel_provenance
from .replay_render import jsonl, git_sha
from .report import table, f

HERE=Path(__file__).parent
OLD=ROOT/'research/results/phase15a'
OUT=ROOT/'research/results/phase15a2'
DOC=ROOT/'docs/PHASE15A2_OCCUPANCY.md'
PROTOCOL=HERE/'occupancy_protocol.json'
VARIANTS=('V0','V1','V2','V3','V4')
NOISES=('none','gaussian')


def csv_rows(path):
    with Path(path).open() as file:return list(csv.DictReader(file))


def key(row):return row['run'],row['noise'],int(row['fresh_id']),int(row['sample'])


def rng_for(name,frame):
    digest=int(hashlib.sha256(name.encode()).hexdigest()[:8],16)
    return np.random.default_rng(np.random.SeedSequence([20261026,digest,frame['observation_id']]))


def unknown_mask(field,queries):
    cells,ok=field.cells(queries);unknown=np.ones(len(queries),dtype=bool)
    x,y=cells[ok].T;unknown[ok]=~field.observed[y,x]
    return unknown


def exact_point_values(points,config):
    boxes=[obstacle_bounds(single_obstacle_config(config,b)) for b in configured_obstacles(config)]
    c=config['corridor'];radius=config['agent_radius_m']
    return np.array([min(*(point_clearance(q,lo,hi,radius) for lo,hi in boxes),
        q[0]-c['xmin']-radius,c['xmax']-q[0]-radius,c['half_width']-abs(q[1])-radius) for q in points])


def oracle_grid(config):
    field=SignedDistanceField(config,.01,2.)
    xx,yy=np.meshgrid(field.origin[0]+np.arange(field.values.shape[1])*field.h,
                      field.origin[1]+np.arange(field.values.shape[0])*field.h)
    c=config['corridor'];r=config['agent_radius_m']
    walls=np.minimum.reduce([xx-c['xmin'],c['xmax']-xx,c['half_width']-np.abs(yy)])-r
    return np.minimum(field.values,walls)


def load_run(root,source,archive_info):
    name=source['key'];run=Path(source['output']);config=source['scenario']
    archive=root/name/'depth.npz';metadata=root/name/'frames.json'
    assert sha256_file(archive)==archive_info['sha256']
    assert sha256_file(metadata)==archive_info['metadata_sha256']
    frames=json.loads(metadata.read_text())
    assert len(frames)==len(source['frames'])
    assert all(all(fr[k]==old[k] for k in old) for fr,old in zip(frames,source['frames']))
    with np.load(archive) as saved:depth=saved['depth'];transforms=saved['camera_to_world']
    assert depth.dtype==np.float16 and depth.shape==(len(frames),240,320)
    for frame,image in zip(frames,depth):assert hashlib.sha256(image.tobytes()).hexdigest()==frame['depth_sha256']
    events=jsonl(run/'events.jsonl');cache={}
    for event in events:
        with np.load(run/f"model/derived/{event['id']:04d}.npz") as native:metric=native['metric']
        assert metric.shape==(8,8,2)
        samples=[]
        for sample in metric:
            world=local_to_world(sample,event['observation_pose'])
            path,length=suffix(world,event['agent_pose_at_switch']);queries,ds=sample_path(path)
            samples.append(dict(queries=queries,step=ds,length=length,oracle=oracle_clearance(path,config),
                                oracle_points=exact_point_values(queries,config)))
        cache[event['id']]=samples
    active=None
    if source['method']=='FRESHEST+GRAPH-GF' and source['index'] in (39,45):
        active=jsonl(run/'phase6_applications.jsonl')[-1]['id']
    snapshot_id=next((e['id'] for e in events if e['agent_pose_at_switch'][0]>=1.),None)
    return dict(frames=frames,depth=depth,transforms=transforms,events=events,cache=cache,active=active,
                snapshot_id=snapshot_id,oracle=oracle_grid(config))


def check_v0_sample(row,reference):
    exact=('depth_clearance_m','oracle_clearance_m','clearance_error_m','remaining_length_m',
           'path_unknown_fraction','unknown_grid_fraction')
    for column in exact:assert float(reference[column])==row[column],(key(row),column,reference[column],row[column])
    for column in ('confusion',):assert reference[column]==row[column],(key(row),column)
    for column in ('depth_safe','oracle_safe','same'):
        assert (reference[column]=='True')==row[column],(key(row),column)
    for column in ('depth_selected','oracle_selected'):
        assert (None if reference[column]=='' else int(reference[column]))==row[column],(key(row),column)


def evaluate_variant(source,data,k,variant,noise,split,old_rows,old_updates,selected,snapshots):
    field=make_field(bounds_from_config(source['scenario']),variant)
    name=source['key'];frames=data['frames'];rows=[];updates=[];phantoms=[];collisions=[];cursor=0

    def update_one(i):
        result=field.update(data['depth'][i],k,data['transforms'][i],noise=='gaussian',rng_for(name,frames[i]))
        row=dict(run=name,variant=variant,noise=noise,split=split,observation_id=frames[i]['observation_id'],**result)
        if variant=='V0':
            previous=old_updates[name,noise,frames[i]['observation_id']]
            for column in ('points','obstacle_points','occupied_cells','unknown_fraction'):
                assert result[column]==float(previous[column]),(name,noise,i,column)
        updates.append(row)
        if noise=='gaussian':
            ph=int(np.count_nonzero(field.occupied & (data['oracle']>.20)))
            phantoms.append(dict(run=name,variant=variant,noise=noise,split=split,
                observation_id=frames[i]['observation_id'],sim_s=frames[i]['sim_s'],occupied_cells=result['occupied_cells'],
                phantom_cells=ph,final_observation=i==len(frames)-1))

    for event in data['events']:
        while cursor<len(frames) and available(frames[cursor],event):update_one(cursor);cursor+=1
        assert cursor>0
        cache=data['cache'][event['id']];local=[]
        for sample,entry in enumerate(cache):
            queries=entry['queries'];dval=float(field.query(queries)[0].min())-field.error_bound-entry['step']/2
            oval=entry['oracle'];dsafe=dval>=.025;osafe=oval>=.025
            category='both_safe' if dsafe and osafe else 'both_unsafe' if not dsafe and not osafe else 'depth_only_safe' if dsafe else 'depth_only_unsafe'
            unknown=unknown_mask(field,queries)
            local.append(dict(run=name,method=source['method'],index=source['index'],variant=variant,noise=noise,split=split,
                fresh_id=event['id'],sample=sample,switch_sim_s=event['application_sim_s'],depth_clearance_m=dval,
                oracle_clearance_m=oval,clearance_error_m=dval-oval,depth_safe=bool(dsafe),oracle_safe=bool(osafe),
                confusion=category,remaining_length_m=entry['length'],unknown_query_count=int(unknown.sum()),
                query_count=len(queries),unknown_unsafe_query_count=int(np.count_nonzero(unknown & (entry['oracle_points']<.025))),
                path_unknown_fraction=float(unknown.mean()),unknown_grid_fraction=float((~field.observed).mean())))
        di=choose([r['depth_clearance_m'] for r in local],[r['remaining_length_m'] for r in local])
        oi=choose([r['oracle_clearance_m'] for r in local],[r['remaining_length_m'] for r in local])
        for row in local:
            row.update(depth_selected=di,oracle_selected=oi,same=di==oi)
            if variant=='V0':check_v0_sample(row,old_rows[key(row)])
        rows.extend(local)
        if event['id']==data['active']:
            collisions.append(dict(run=name,index=source['index'],variant=variant,noise=noise,fresh_id=event['id'],
                depth_selected=di,oracle_selected=oi,depth_selection_oracle_clearance_m=None if di is None else local[di]['oracle_clearance_m'],
                depth_all_unsafe=di is None))
        if (split=='judgment' and source['index']==35 and event['id']==data['snapshot_id'] and
            noise=='gaussian' and variant in ('V0',selected)):
            snapshots[variant]=dict(values=field.values.copy(),unknown=~field.observed.copy(),oracle=data['oracle'],
                origin=field.origin.copy(),h=field.h,run=name,fresh_id=event['id'],boundary=event['agent_pose_at_switch'])
    while cursor<len(frames):update_one(cursor);cursor+=1
    return rows,updates,phantoms,collisions


def aggregate(rows,updates):
    out=[]
    for variant in VARIANTS:
        for noise in NOISES:
            for split in ('selection','judgment','all'):
                rr=[r for r in rows if r['variant']==variant and r['noise']==noise and (split=='all' or r['split']==split)]
                tt=[t for t in updates if t['variant']==variant and t['noise']==noise and (split=='all' or t['split']==split)]
                if not rr:continue
                counts=Counter(r['confusion'] for r in rr);n=len(rr);ss=[r for r in rr if r['sample']==0]
                errors=distribution([r['clearance_error_m'] for r in rr])
                item=dict(variant=variant,noise=noise,split=split,runs=len({r['run'] for r in rr}),samples=n,switches=len(ss),
                    agreement_fraction=(counts['both_safe']+counts['both_unsafe'])/n,
                    dangerous_fraction=counts['depth_only_safe']/n,conservative_fraction=counts['depth_only_unsafe']/n,
                    clearance_error_median_m=errors['median'],clearance_error_p5_m=errors['p5'],clearance_error_p95_m=errors['p95'],
                    selection_agreement_fraction=sum(r['same'] for r in ss)/len(ss),
                    selection_both_null=sum(r['depth_selected'] is None and r['oracle_selected'] is None for r in ss),
                    unknown_queries=sum(r['unknown_query_count'] for r in rr),unknown_unsafe_queries=sum(r['unknown_unsafe_query_count'] for r in rr),
                    query_count=sum(r['query_count'] for r in rr),**{c:counts[c] for c in ('both_safe','both_unsafe','depth_only_safe','depth_only_unsafe')})
                for part in ('update_ms','pointcloud_ms','accumulate_ms','sdf_ms'):
                    stat=distribution([t[part] for t in tt]);item[part+'_median']=stat['median'];item[part+'_p95']=stat['p95']
                out.append(item)
    return out


def select_variant(summaries):
    candidates=[dict(r,eligible=r['dangerous_fraction']<=.02 and r['update_ms_p95']<=50)
        for r in summaries if r['split']=='selection' and r['noise']=='gaussian']
    eligible=[r for r in candidates if r['eligible']]
    winner=min(eligible,key=lambda r:(r['conservative_fraction'],int(r['variant'][1:])))['variant'] if eligible else None
    return dict(candidates=candidates,selected_variant=winner,selected_before_held_out=True,
        rule='dangerous<=2%, update p95<=50ms, minimum conservative fraction then lower variant number')


def verify_inputs():
    old=json.loads((OLD/'summary.json').read_text());root=Path(old['render_root'])
    for path,digest in json.loads((OLD/'complete.json').read_text())['output_hashes'].items():
        assert sha256_file(ROOT/path)==digest,path
    for path,digest in old['input_hashes'].items():assert sha256_file(path)==digest,path
    for path,digest in old['producer_hashes'].items():assert sha256_file(ROOT/path)==digest,path
    complete=json.loads((root/'render_complete.json').read_text());plan=json.loads((root/'plan.json').read_text())
    assert sha256_file(root/'render_complete.json')==old['render_complete_sha256']
    assert sha256_file(root/'plan.json')==complete['plan_sha256']
    assert sha256_file(root/'camera.json')==complete['camera_sha256']
    assert len(plan['runs'])==24
    return old,root,complete,plan


def run():
    if OUT.exists() or DOC.exists():raise FileExistsError('A2 results already exist; refusing recomputation/overwrite')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip():
        raise RuntimeError('Commit frozen implementation/protocol before evaluation')
    old,root,complete,plan=verify_inputs();protocol=json.loads(PROTOCOL.read_text())
    assert protocol['next_navigation_default']['variant'] is None
    OUT.mkdir();write_json(OUT/'registration.json',dict(protocol=protocol,execution_git_sha=git_sha(),
        protocol_sha256=sha256_file(PROTOCOL),baseline_summary_sha256=sha256_file(OLD/'summary.json'),
        input_provenance=old['input_hashes'],producer_hashes={str(p.relative_to(ROOT)):sha256_file(p) for p in
            (HERE/'occupancy.py',HERE/'occupancy_rays.c',HERE/'occupancy_report.py',HERE/'test_occupancy.py')}))
    start=time.perf_counter();ray_kernel();kernel=kernel_provenance();kernel['startup_s']=time.perf_counter()-start
    k=np.array(json.loads((root/'camera.json').read_text())['intrinsics'])
    archives={r['key']:r for r in complete['runs']}
    old_rows={key(r):r for r in csv_rows(OLD/'switches.csv')}
    old_updates={(r['run'],r['noise'],int(r['observation_id'])):r for r in csv_rows(OLD/'updates.csv')}
    all_rows=[];all_updates=[];phantoms=[];collisions=[];snapshots={};selection=None;selected=None
    for split,method in (('selection','FRESHEST'),('judgment','FRESHEST+GRAPH-GF')):
        sources=sorted([r for r in plan['runs'] if r['method']==method],key=lambda r:r['index'])
        assert len(sources)==12
        for j,source in enumerate(sources):
            data=load_run(root,source,archives[source['key']]);begin=time.perf_counter()
            for variant in VARIANTS:
                for noise in NOISES:
                    rr,tt,pp,cc=evaluate_variant(source,data,k,variant,noise,split,old_rows,old_updates,selected,snapshots)
                    all_rows.extend(rr);all_updates.extend(tt);phantoms.extend(pp);collisions.extend(cc)
            with (OUT/'progress.jsonl').open('a') as file:
                file.write(json.dumps(dict(split=split,completed=j+1,run=source['key'],wall_s=time.perf_counter()-begin))+'\n')
            print(f'{split} {j+1}/12 {source["key"]} complete',flush=True)
        if split=='selection':
            selection=select_variant(aggregate(all_rows,all_updates));selected=selection['selected_variant']
            write_json(OUT/'selection_frozen.json',selection)
            print(f'SELECTION_FROZEN {selected or "NO_VARIANT"}',flush=True)
    variants=aggregate(all_rows,all_updates)
    # Full V0 regression: all non-clock sample/map checks above plus pooled metrics.
    for noise in NOISES:
        v=next(r for r in variants if r['variant']=='V0' and r['noise']==noise and r['split']=='all');b=old['conditions'][noise]
        for column in ('dangerous_fraction','conservative_fraction','agreement_fraction','selection_agreement_fraction'):
            assert v[column]==b[column],column
        assert v['samples']==b['samples'] and v['switches']==b['switches']
    judged=next((r for r in variants if r['variant']==selected and r['noise']=='gaussian' and r['split']=='judgment'),None)
    label=decision(judged['dangerous_fraction'],judged['conservative_fraction'],judged['update_ms_p95']) if judged else 'NO_VARIANT'
    summary=dict(**selection,final_label=label,judgment=judged,kernel=kernel,baseline_conditions=old['conditions'],
        execution_git_sha=git_sha(),v0_regression=dict(status='EXACT_NON_CLOCK_MATCH',samples_checked=sum(r['variant']=='V0' for r in all_rows),
            updates_checked=sum(r['variant']=='V0' for r in all_updates),timing='Remeasured; not asserted equal to historic wall-clock times'),
        held_out_nonselected='Descriptive only; never used to change frozen choice',collisions=collisions)
    write_csv(OUT/'variants.csv',variants);write_json(OUT/'selection.json',summary)
    write_csv(OUT/'phantom.csv',phantoms)
    write_csv(OUT/'unknown_risk.csv',[{k:r[k] for k in ('run','variant','noise','split','fresh_id','sample','query_count',
        'unknown_query_count','unknown_unsafe_query_count','path_unknown_fraction','oracle_clearance_m','depth_clearance_m')} for r in all_rows])
    write_csv(OUT/'collision_selections.csv',collisions);write_csv(OUT/'updates.csv',all_updates)
    figures(all_rows,snapshots,selected)
    with DOC.open('x') as file:file.write(document(summary,variants,phantoms))
    protocol['next_navigation_default']=dict(variant=selected,status=label,scope='Offline selection only; no new navigation performed or authorized')
    # New A2 protocol only; Phase15-A protocol/results are immutable.
    PROTOCOL.write_text(json.dumps(protocol,indent=2,ensure_ascii=False)+'\n')
    hashes={str(p.relative_to(ROOT)):sha256_file(p) for p in OUT.iterdir() if p.is_file()}
    hashes[str(DOC.relative_to(ROOT))]=sha256_file(DOC);hashes[str(PROTOCOL.relative_to(ROOT))]=sha256_file(PROTOCOL)
    write_json(OUT/'complete.json',dict(output_hashes=hashes))
    return summary


def figures(rows,snapshots,selected):
    if selected is None:return  # NO_VARIANT: tables only, no invented winner.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    raw=snapshots['V0'];chosen=snapshots[selected]
    assert (raw['run'],raw['fresh_id'])==(chosen['run'],chosen['fresh_id'])
    h=raw['h'];ny,nx=raw['values'].shape;o=raw['origin']
    extent=[o[0],o[0]+(nx-1)*h,o[1],o[1]+(ny-1)*h]
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    for ax,values,title in zip(axes,[raw['values'],chosen['values'],raw['oracle']],['V0 noisy',selected+' noisy','Oracle (evaluation only)']):
        im=ax.imshow(values,extent=extent,origin='lower',vmin=-.1,vmax=.5,cmap='viridis',interpolation='nearest')
        ax.plot(*raw['boundary'][:2],'r+',ms=8)
        ax.set(xlim=(-.5,5),ylim=(-1.8,1.8),title=title,xlabel='World x (m)',ylabel='World y (m)')
        fig.colorbar(im,ax=ax,shrink=.7,label='Footprint clearance (m)')
    fig.suptitle(f"{raw['run']} F{raw['fresh_id']} — same Phase15-A pose, gaussian noise")
    fig.savefig(OUT/'sdf_compare_noisy.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,5),layout='constrained')
    for ax,noise in zip(axes,NOISES):
        rr=[r for r in rows if r['variant']==selected and r['noise']==noise and r['split']=='judgment']
        x=np.array([r['oracle_clearance_m'] for r in rr]);y=np.array([r['depth_clearance_m'] for r in rr])
        dangerous=np.array([r['confusion']=='depth_only_safe' for r in rr])
        ax.scatter(x[~dangerous],y[~dangerous],s=5,alpha=.25)
        ax.scatter(x[dangerous],y[dangerous],s=6,c='red',alpha=.5,label='Depth only safe')
        lo=min(x.min(),y.min())-.02;hi=max(x.max(),y.max())+.02
        ax.plot([lo,hi],[lo,hi],'k:',lw=1);ax.axvline(.025,c='orange');ax.axhline(.025,c='orange')
        ax.set(title=f'{selected}, {noise}, held-out GF runs',xlabel='Oracle clearance (m)',ylabel='Depth clearance (m)');ax.legend()
    fig.savefig(OUT/'clearance_scatter.png',dpi=160);plt.close(fig)


def document(summary,variants,phantoms):
    selected=summary['selected_variant'];label=summary['final_label']
    text=['# Phase 15-A2 — Occupancy accumulation comparison','',
        f"Selected variant: **{selected or 'none'}**. Decision: **{label}**. Execution SHA `{summary['execution_git_sha']}`.",'',
        'Saved Phase15-A depth/poses and existing predictions only; no rendering, navigation, inference or Graph solve. The original Phase15-A files and code are unchanged.',
        '', '## Frozen selection','',
        'Twelve FRESHEST runs select on noisy data; twelve FRESHEST+GRAPH-GF runs supply the held-out decision. The choice was saved before held-out metrics were computed. Nonselected held-out variants below are descriptive only.',
        '',table(['Variant','Dangerous %','Conservative %','Update p95 ms','Eligible'],[
            [r['variant'],f(100*r['dangerous_fraction']),f(100*r['conservative_fraction']),f(r['update_ms_p95']),r['eligible']]
            for r in summary['candidates']]),'',
        'Eligibility: dangerous ≤2%, update p95 ≤50ms. Lowest conservative fraction wins; lower variant number breaks ties. No parameter tuning/retries.',
        '', '## All variants: descriptive table','',
        table(['Variant','Noise','Split','Samples','Agreement %','Dangerous %','Conservative %','Error median / p5 / p95 m','Selection match %','Update median / p95 ms'],[
            [r['variant'],r['noise'],r['split'],r['samples'],f(100*r['agreement_fraction']),f(100*r['dangerous_fraction']),
             f(100*r['conservative_fraction']),' / '.join(f(r[k]) for k in ('clearance_error_median_m','clearance_error_p5_m','clearance_error_p95_m')),
             f(100*r['selection_agreement_fraction']),f(r['update_ms_median'])+' / '+f(r['update_ms_p95'])] for r in variants]),'',
        'Fractions pool sample decisions; timing pools observation updates, including all warmup/late frames. Selection match includes both-null; its count is stored separately in variants.csv.',
        '', '## V0 regression','',
        f"{summary['v0_regression']['status']}: {summary['v0_regression']['samples_checked']} sample rows and {summary['v0_regression']['updates_checked']} observation updates checked. All non-clock values match exactly. Re-executed wall-clock times cannot equal historic timings and are not asserted to do so.",
        '',table(['Noise','Original V0 update median / p95 ms','A2 V0 update median / p95 ms'],[
            [noise,f(summary['baseline_conditions'][noise]['timing']['update_ms']['median'])+' / '+f(summary['baseline_conditions'][noise]['timing']['update_ms']['p95']),
             f(next(r for r in variants if r['variant']=='V0' and r['noise']==noise and r['split']=='all')['update_ms_median'])+' / '+
             f(next(r for r in variants if r['variant']=='V0' and r['noise']==noise and r['split']=='all')['update_ms_p95'])] for noise in NOISES]),'',
        '## Phantom occupancy (gaussian noise)','',
        'A phantom is an occupied lattice cell whose oracle footprint clearance is >0.20m. Counts are per independent run map; sums do not represent distinct physical locations. Full observation series is in phantom.csv.',
        '',table(['Variant','Split','Final phantom cells sum','Mean final per run','Peak per observation'],[
            [v,split,sum(p['phantom_cells'] for p in phantoms if p['variant']==v and (split=='all' or p['split']==split) and p['final_observation']),
             f(np.mean([p['phantom_cells'] for p in phantoms if p['variant']==v and (split=='all' or p['split']==split) and p['final_observation']]),1),
             max(p['phantom_cells'] for p in phantoms if p['variant']==v and (split=='all' or p['split']==split))]
            for v in VARIANTS for split in ('selection','judgment','all')]),'',
        '## Unknown-risk diagnostic','',
        'Query counts use the unchanged 5mm path sampling, including duplicate segment vertices. Unknown points with exact oracle footprint clearance <0.025m are counted; these counts do not enter selection or the decision.',
        '',table(['Variant','Noise','Split','Unknown / all queries','Unknown and oracle unsafe queries'],[
            [r['variant'],r['noise'],r['split'],str(r['unknown_queries'])+' / '+str(r['query_count']),r['unknown_unsafe_queries']] for r in variants]),'',
        '## P13 collision-run counterfactual selections','',
        'The rows use the originating FRESH switch of the active path at collision, matching Phase15-A. Null means ALL_UNSAFE, not execution of a fallback. Counterfactual sample safety is not proof of collision prevention.',
        '',table(['Index','Variant','Noise','FRESH','Depth pick','Oracle pick','Depth pick oracle clearance m'],[
            [r['index'],r['variant'],r['noise'],r['fresh_id'],r['depth_selected'],r['oracle_selected'],f(r['depth_selection_oracle_clearance_m'])]
            for r in summary['collisions']]),'',
        '## Implementation and limits','',
        'V1–V4 update each cell once per captured frame, with occupied precedence over free. V2 counts distinct occupied frames. Log-odds uses exact integer hundredths (+85/−40, clipped −200..350, occupied >85). These fixed evidence semantics avoid treating correlated pixels in one image as independent confirmations.',
        '', 'Bresenham uses a serial C kernel; duplicate endpoint/type rays are removed without changing the union of traversed cells. Height/range filtering, noise realizations, grid allocation, EDT, radius, interpolation and path-clearance bound remain those of Phase15-A. V0 is the original class without changes. The map has no oracle obstacle/half-plane input.',
        '', 'V1–V4 unknown means no ray has visited a cell. V0 retains its original camera-height visibility coverage for exact regression. Endpoints outside the 2m occupied range but within 3m are observed, with free interior and no endpoint evidence update. Free rays are not extrapolated beyond measured endpoints.',
        '', f"Kernel: `{summary['kernel']['compiler']}`, one CPU thread; compile/load startup {f(summary['kernel']['startup_s'])}s excluded from update timing. Oracle diagnostics and disk I/O are outside mapping timings. No timing samples are discarded.",
        '', 'Simulator pose is exact (no odometry noise). Surface occupancy does not fill unseen interiors. Unknown is not occupied. h/√2 is an interpolation bound, not a sensing/occlusion error bound. The held-out split is by controller on the same scene, not cross-scene generalization.',
        '', '## Selected-variant timing breakdown',''
    ]
    if selected is not None:
        rr=[r for r in variants if r['variant']==selected and r['split']=='judgment']
        text+=[table(['Noise','Component','Median ms','p95 ms'],[
            [r['noise'],part,f(r[part+'_median']),f(r[part+'_p95'])] for r in rr
            for part in ('pointcloud_ms','accumulate_ms','sdf_ms','update_ms')]),'',
            '![Noisy SDF comparison](../research/results/phase15a2/sdf_compare_noisy.png)','',
            '![Selected-variant clearance](../research/results/phase15a2/clearance_scatter.png)','',
            f'`occupancy_protocol.json` records {selected} as the next navigation default. This task performs no navigation; the held-out label and unknown-risk limitations remain applicable.','']
    else:text+=['NO_VARIANT: no eligible variant; no default or held-out decision is fabricated. Tables only.','']
    if label=='TIMING_NOT_READY':text+=['Accuracy passed. Optimize implementation and remeasure timing only in a subsequent task.','']
    text+=[label,'']
    return '\n'.join(text)


def publish():
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    if branch!='research/phase0-infrastructure':raise RuntimeError('Wrong publication branch')
    paths=[str(DOC.relative_to(ROOT)),str(OUT.relative_to(ROOT)),str(PROTOCOL.relative_to(ROOT))]
    staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines()
    if staged:raise RuntimeError('Unrelated staged work must not be included')
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    for image in OUT.glob('*.png'):subprocess.run(['git','add','-f','--',str(image.relative_to(ROOT))],cwd=ROOT,check=True)
    subprocess.run(['git','-c','core.whitespace=cr-at-eol','diff','--cached','--check'],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():
        subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m',
                        'Record frozen Phase 15-A2 occupancy comparison'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin',branch],cwd=ROOT,check=True)


def protocol_snapshot():
    """Publish the user's confirmed measurement semantics, no re-evaluation."""
    statement=('Each cell is updated at most once per depth frame: any eligible occupied endpoint gives +0.85; '
        'otherwise a traversing free ray gives -0.40. Occupied wins within a frame. V2 counts three distinct '
        'occupied frames. V3/V4 apply their occupied distance limit to each point before frame aggregation. '
        'V0 does not use these rules and remains the unmodified Phase15-A implementation.')
    snapshot=dict(json.loads(PROTOCOL.read_text()),confirmed_measurement_rules=statement)
    target=OUT/'protocol.json'
    if target.exists():assert json.loads(target.read_text())==snapshot
    else:write_json(target,snapshot)
    text=DOC.read_text()
    if statement not in text:
        text=text.replace('## Implementation and limits\n','## Implementation and limits\n\n'+statement+'\n')
        DOC.write_text(text)
    manifest=OUT/'complete.json';complete=json.loads(manifest.read_text())
    for path in (target,DOC):complete['output_hashes'][str(path.relative_to(ROOT))]=sha256_file(path)
    manifest.write_text(json.dumps(complete,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    if (OUT/'complete.json').exists():
        for path,digest in json.loads((OUT/'complete.json').read_text())['output_hashes'].items():
            assert sha256_file(ROOT/path)==digest,path
        summary=json.loads((OUT/'selection.json').read_text())
    else:summary=run()
    protocol_snapshot()
    if args.publish:publish()
    judgment=summary['judgment']
    print(json.dumps(dict(selected=summary['selected_variant'],label=summary['final_label'],
        dangerous=None if not judgment else judgment['dangerous_fraction'],
        conservative=None if not judgment else judgment['conservative_fraction'],
        update_p95_ms=None if not judgment else judgment['update_ms_p95'])),flush=True)


if __name__=='__main__':main()
