"""Verify publication-time live flags against Phase37-B on two stored runs."""
import json,csv,hashlib,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase20f.history import HistorySnapshot
from nomad_phase33p.storage import load_snapshot
from nomad_phase37b.evidence import inventory,common_rows
from nomad_phase37b.rules import evaluate as offline_rule
from nomad_phase20c.detour_known import radial_reference
from nomad_phase32o.evaluate import save,csvout
from .provenance import PublishedFree,ProvenSnapshot
from .runtime import ProvenNoProgress
from .config import OUT

# Full archival history plus compact archival history with known positive B
# decisions. Selection covers both branches; it does not tune the method.
CASES=(('32','H1',201),('35','L2',212))

def field_from_saved(saved,tracker):
    values=dict(vars(saved));values['prov']=tracker
    values['history']=SimpleNamespace(**{k:getattr(saved,k) for k in ('first_free_tick','first_occupied_tick','new_component_ids')},births=dict(saved.component_births))
    return SimpleNamespace(**values)

def run():
    common=common_rows();summaries=[];events=[];hashes={};start=time.monotonic()
    for phase,scene,index in CASES:
        selected=[(root,rows) for root,rows in common.items() if (rows[0]['phase'],rows[0]['scene'],int(rows[0]['index']))==(phase,scene,index)]
        assert len(selected)==1;directory,rows=selected[0];root=Path(directory);key=f'{phase}_{scene}_{index}'
        with (root/'agent_trajectory.csv').open() as f:trace=list(csv.DictReader(f))
        poses=np.array([[float(x[k]) for k in ('x_m','y_m','yaw_rad')] for x in trace])
        evidence=ROOT/'research/results/phase37b/evidence'/f'{key}.npz'
        with np.load(evidence) as z:proof={k:z[k].copy() for k in z.files}
        expected={e['tick']:e for e in json.loads((ROOT/'research/results/phase37b/per_run'/f'{key}.json').read_text())['events']}
        by_frame={}
        for row in rows:by_frame.setdefault(int(row['frame']),[]).append(row) if 'frame' in row else None
        # Phase37 common CSV contains frame, while Phase37-B per-run output
        # repeats the same immutable snapshot path; no fresh map is invented.
        if not by_frame:
            from nomad_phase37.audit import metadata
            for row in rows:by_frame.setdefault(metadata(row['snapshot_file'])['frame_id'],[]).append(row)
        tracker=PublishedFree(tuple(proof['shape']));compared=0;flags_checked=0;fields_checked=0;frames=0
        for tick,path,meta in inventory(root):
            if path is None:continue
            saved=load_snapshot(HistorySnapshot,path);field=field_from_saved(saved,tracker)
            before={k:getattr(field,k).copy() for k in ('values','occupied','observed','last_free_tick','new_component_ids')}
            snap=ProvenSnapshot(field,dict(saved.metadata));frames+=1
            for name,value in before.items():np.testing.assert_array_equal(getattr(field,name),value)
            fields_checked+=1
            actual=snap.prov_first_confirmed_free_tick.ravel()[proof['indices']]
            full=proof['first_confirmed_free_tick'];want=np.where((full>=0)&(full<=tick),full,-1)
            np.testing.assert_array_equal(actual,want);flags_checked+=len(actual)
            assert not snap.prov_confirmed_free.flags.writeable and not snap.prov_first_confirmed_free_tick.flags.writeable
            for row in by_frame.get(meta['frame_id'],[]):
                query_tick=int(row['tick']);u,_=radial_reference(poses,query_tick)
                owner=SimpleNamespace(depth_maps=SimpleNamespace(snapshot=lambda:snap),suppress_trigger_tick=-1,records=[])
                owner.drecord=lambda event,**kw:owner.records.append(dict(event=event,**kw))
                live=ProvenNoProgress(owner);fire,progress,reason=live.check(poses,query_tick,u,blocked=False)
                offline=offline_rule(snap,snap.prov_confirmed_free,poses,query_tick);record=expected[query_tick]
                assert fire==offline['fire']==record['PROV_confirmed_fire']
                component=live.last_gate['component'] if live.last_gate else None
                component_id=component['component_id'] if component else None
                assert component_id==record['PROV_confirmed_component']
                actual_u=component['u_ref'] if component else u
                np.testing.assert_allclose(actual_u,record['PROV_confirmed_u_ref'],atol=1e-12,rtol=0)
                if component:assert component['t_new_tick']==record['PROV_confirmed_t_new_tick']
                json.dumps(owner.records,allow_nan=False)
                compared+=1;events.append(dict(case=key,tick=query_tick,time_s=query_tick/72,frame=meta['frame_id'],live_fire=bool(fire),offline_fire=offline['fire'],component_id=component_id,matched=True))
            hashes[str(path)]=sha256_file(Path(path))
        assert compared==len(rows)
        for p in (evidence,root/'agent_trajectory.csv',ROOT/'research/results/phase37b/per_run'/f'{key}.json'):hashes[str(p)]=sha256_file(p)
        summaries.append(dict(case=key,output=str(root),published_frames=len(inventory(root)),replayed_saved_frames=frames,
            common_decisions=compared,matched_decisions=compared,live_triggers=sum(e['live_fire'] for e in events if e['case']==key),
            offline_triggers=sum(e['offline_fire'] for e in events if e['case']==key),cell_timestamp_comparisons=flags_checked,
            immutable_map_comparisons=fields_checked,all_flags_equal=True,arrays_unchanged=True,
            caveat='Same saved-frame stream only; omitted historical frames are not reconstructed'))
        print('[replay]',key,compared,'decisions matched',flush=True)
    save(OUT/'preparation/replay.json',dict(passed=True,cases=summaries,elapsed_s=time.monotonic()-start,simulation_runs=0))
    csvout(OUT/'preparation/replay_events.csv',events);save(OUT/'preparation/replay_input_hashes.json',hashes)

if __name__=='__main__':run()
