"""Saved depth only; unchanged original frame/noise schedules and geometry metrics."""
import hashlib,json,subprocess,types
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase15 import occupancy_report as old
from nomad_phase15.depth_sdf import intrinsics
from nomad_phase15b.depth import Snapshot
from nomad_phase19r.evaluate import dump,csv_write,clean
from nomad_phase19s.evaluate import csv_rows
from .shadow import ShadowSDF


def verify_archives(inputs):
    previous=json.loads(inputs.track(ROOT/'research/results/phase15a/summary.json').read_text());root=Path(previous['render_root'])
    complete=json.loads(inputs.track(root/'render_complete.json').read_text());plan=json.loads(inputs.track(root/'plan.json').read_text())
    assert sha256_file(root/'render_complete.json')==previous['render_complete_sha256']
    assert sha256_file(root/'plan.json')==complete['plan_sha256']
    assert sha256_file(root/'camera.json')==complete['camera_sha256']
    producer=[]
    for file,h in previous['producer_hashes'].items():
        current=sha256_file(ROOT/file)
        if current!=h:
            data=subprocess.check_output(['git','show',previous['render_git_sha']+':'+file],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==h,file
            producer.append(dict(file=file,recorded_sha256=h,current_sha256=current,verified_historical_commit=previous['render_git_sha']))
    for file,h in previous['input_hashes'].items():assert sha256_file(inputs.track(file))==h,file
    assert len(plan['runs'])==24
    return root,complete,plan,producer


def accuracy(out,inputs):
    root,complete,plan,producer=verify_archives(inputs);dump(out/'historical_producer_verification.json',producer)
    k=np.array(json.loads(inputs.track(root/'camera.json').read_text())['intrinsics']);archives={x['key']:x for x in complete['runs']}
    evaluator=types.FunctionType(old.evaluate_variant.__code__,{**old.__dict__,'make_field':lambda bounds,_:ShadowSDF(bounds)})
    aggregator=types.FunctionType(old.aggregate.__code__,{**old.__dict__,'VARIANTS':('SHADOW',)})
    records=[];updates=[]
    for number,source in enumerate(plan['runs']):
        inputs.track(root/source['key']/'depth.npz');inputs.track(root/source['key']/'frames.json')
        data=old.load_run(root,source,archives[source['key']]);inputs.track(Path(source['output'])/'events.jsonl')
        for e in data['events']:inputs.track(Path(source['output'])/f"model/derived/{e['id']:04d}.npz")
        split='selection' if source['method']=='FRESHEST' else 'judgment'
        for noise in ('none','gaussian'):
            rr,uu,_,_=evaluator(source,data,k,'SHADOW',noise,split,{}, {},None,{})
            records.extend(rr);updates.extend(uu)
        print(f'[map accuracy] {number+1}/24 saved runs, both noise conditions',flush=True)
    summary=aggregator(records,updates)
    baseline=[r for r in csv_rows(inputs.track(ROOT/'research/results/phase15a2/variants.csv')) if r['variant']=='V1']
    comparison=[]
    for r in summary:
        b=next(x for x in baseline if x['noise']==r['noise'] and x['split']==r['split'])
        assert b['samples']==r['samples'] and b['runs']==r['runs']
        # Resetting a negative log-odds to zero can only increase subsequent
        # occupancy under the same evidence schedule; no new false-safe is expected.
        assert r['dangerous_fraction']<=b['dangerous_fraction']+1e-12
        assert r['conservative_fraction']>=b['conservative_fraction']-1e-12
        comparison.append(dict(noise=r['noise'],split=r['split'],runs=r['runs'],samples=r['samples'],
            old_dangerous_fraction=b['dangerous_fraction'],new_dangerous_fraction=r['dangerous_fraction'],
            old_conservative_fraction=b['conservative_fraction'],new_conservative_fraction=r['conservative_fraction'],
            dangerous_change_pp=100*(r['dangerous_fraction']-b['dangerous_fraction']),conservative_change_pp=100*(r['conservative_fraction']-b['conservative_fraction']),
            update_median_ms=r['update_ms_median'],update_p95_ms=r['update_ms_p95'],
            usage='common selection/R2/fallback view; unknown is not occupied'))
    csv_write(out/'map_samples.csv',records);csv_write(out/'map_updates.csv',updates);csv_write(out/'map_accuracy.csv',comparison)
    dump(out/'map_accuracy_complete.json',dict(runs=24,frames=complete['frames'],noise_conditions=2,sample_decisions=len(records),new_render=0,new_inference=0))
    return comparison


def rebuild_events(events,replay_root,inputs,out):
    replay_root.mkdir(parents=True,exist_ok=False);updates_log=[]
    source_protocol=json.loads(inputs.track(ROOT/'research/nomad_phase20b/protocol.json').read_text())
    bounds=source_protocol['depth']['allocation_bounds_m']
    for runname in dict.fromkeys(e['run'] for e in events):
        selected=[e for e in events if e['run']==runname];run=Path(selected[0]['output']);config=json.loads(inputs.track(run/'scenario.json').read_text())
        old_first=Snapshot.load(inputs.track(run/'depth/snapshot_initial.npz'))
        field=ShadowSDF(bounds,old_first.h,old_first.radius);k=intrinsics(config['camera'])
        assert field.values.shape==old_first.values.shape
        np.testing.assert_array_equal(field.origin,old_first.origin)
        dest=replay_root/runname;dest.mkdir();wanted={e['snapshot_file'] for e in selected};mapping={}
        initial=str((run/'depth/snapshot_initial.npz').resolve())
        if initial in wanted:
            path=dest/'snapshot_initial.npz';Snapshot(field,dict(sim_s=0.,frame_id=-1,file=str(path),source_snapshot=initial)).save(path);mapping[initial]=str(path)
        from nomad_phase20.metrics import rows
        updates=rows(inputs.track(run/'depth/updates.jsonl'))
        for u in updates:
            file=inputs.track(run/f"depth/depth_{u['frame_id']:04d}.npz")
            with np.load(file) as z:depth=z['depth'];transform=z['camera_to_world']
            rng=np.random.default_rng(np.random.SeedSequence([20261027,config['seed_offset'],u['frame_id']]))
            timing=field.update(depth,k,transform,True,rng)
            updates_log.append(dict(run=runname,frame=u['frame_id'],sim_s=u['sim_s'],**timing))
            old_file=str(Path(u['file']).resolve())
            if old_file in wanted:
                path=dest/f"snapshot_{u['frame_id']:04d}.npz"
                meta=dict(u,file=str(path),source_snapshot=old_file,shadow_rule='negative log-odds behind occupied endpoints reset to unknown over0.5m')
                Snapshot(field,meta).save(path);mapping[old_file]=str(path)
        assert set(mapping)==wanted,(runname,wanted-set(mapping))
        for e in selected:
            original=e['snapshot_file'];e['source_snapshot_file']=original;e['snapshot_file']=mapping[original]
            snap=Snapshot.load(e['snapshot_file']);e['source_B_depth_clearance_m']=e['B_depth_clearance_m']
            e['B_depth_clearance_m']=float(snap.query(np.array(e['B'])[None,:2])[0][0])-snap.error_bound
            e['rebuilt_snapshot_sha256']=sha256_file(e['snapshot_file'])
        print(f'[map replay] {runname}: {len(updates)} frames, {len(wanted)} trigger snapshots',flush=True)
    csv_write(out/'event_map_updates.csv',updates_log)
