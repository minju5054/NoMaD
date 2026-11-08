"""Replay original B and PROV on exactly Phase37's 4,915 common opportunities."""
import json,time,csv,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase24r import trigger as legacy
from nomad_phase32o.evaluate import save,csvout,clean
from nomad_phase37.evaluate import load_run
from nomad_phase37.geometry import classify
from nomad_phase37 import audit as prior_audit
from .evidence import OUT,HASHES,read,lines,snapshot,register,common_rows
from .rules import evaluate,outcome_envelope

HERE=Path(__file__).parent
LABELS=('BOX_AHEAD','STATIC_AHEAD','PASSED_BOX','NOTHING_AHEAD')

def verify():
    p=json.loads((HERE/'protocol.json').read_text());assert p['status']=='FROZEN_OFFLINE'
    for f,h in p['source_hashes'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,f
    return p

def masks(proof,shape):
    confirmed=np.zeros(np.prod(shape),bool);possible=confirmed.copy()
    confirmed[proof['indices']]=proof['confirmed'];possible[proof['indices']]=proof['confirmed']|proof['unknown']
    return confirmed.reshape(shape),possible.reshape(shape)

def history_rows(row,field,proof,old,boxes,miss_status):
    """Point-level history of current occupied box cells and original selector.

    Cell-square intersection with physical box AABBs is analysis-only. Also
    preserve all selected-component cells so a geometrically BOX_AHEAD event
    whose trigger actually refers to a neighbouring static object is visible.
    """
    iy,ix=np.nonzero(field.occupied&field.observed);xy=field.origin+np.c_[ix,iy]*field.h
    indices=iy*field.occupied.shape[1]+ix;lookup={int(k):j for j,k in enumerate(proof['indices'])}
    selected=set()
    if old['component']:
        pts=old['sets'][old['component']['component_id']]
        cells=np.rint((pts-field.origin)/field.h).astype(int);selected=set((cells[:,1]*field.occupied.shape[1]+cells[:,0]).tolist())
    result=[];time_s=float(row['time_s'])
    active=[b for b in boxes if b['spawn_s']<=time_s]
    for k,(y,x,point,index) in enumerate(zip(iy,ix,xy,indices)):
        box_ids=[b['id'] for b in active if np.all(point>=b['polygon'].min(axis=0)-field.h/2-1e-12) and np.all(point<=b['polygon'].max(axis=0)+field.h/2+1e-12)]
        if not box_ids and int(index) not in selected:continue
        j=lookup.get(int(index));ff=int(field.first_free_tick[y,x]);fo=int(field.first_occupied_tick[y,x]);cf=int(proof['first_confirmed_free_tick'][j]) if j is not None else -1
        status='CONFIRMED' if j is not None and proof['confirmed'][j] else 'MISSING_HISTORY' if j is not None and proof['unknown'][j] else 'NO_VALID_PUBLISHED_FREE' if j is not None else 'NOT_ORIGINAL_CANDIDATE'
        result.append(dict(event_key=row['event_key'],phase=row['phase'],scene=row['scene'],index=row['index'],time_s=time_s,
            missed_status=miss_status,box_ids=box_ids,selected_component_cell=int(index) in selected,grid_x=int(x),grid_y=int(y),world_x_m=float(point[0]),world_y_m=float(point[1]),
            first_ray_free_tick=ff if ff>=0 else None,first_ray_free_s=ff/72 if ff>=0 else None,
            first_confirmed_observed_free_tick=cf if cf>=0 else None,first_confirmed_observed_free_s=cf/72 if cf>=0 else None,
            first_occupied_tick=fo if fo>=0 else None,first_occupied_s=fo/72 if fo>=0 else None,
            first_ray_free_observed=(int(proof['first_free_observed'][j]) if j is not None else None),
            missing_frames_before_occupied=int(proof['missing_frames_before_occupied'][j]) if j is not None else None,provenance_status=status))
    return result

def gate(rows):
    positive=[r for r in rows if r['original_fire'] and r['original_label']=='BOX_AHEAD'];n=len(positive)
    lower=sum(r['PROV_fire_lower'] for r in positive);upper=sum(r['PROV_fire_upper'] for r in positive)
    strict=sum(r['PROV_confirmed_fire'] for r in positive)
    old_other=sum(r['original_fire'] and r['original_label']!='BOX_AHEAD' for r in rows)
    low_other=sum(r['PROV_nonbox_lower'] for r in rows);high_other=sum(r['PROV_nonbox_upper'] for r in rows)
    strict_other=sum(r['PROV_confirmed_fire'] and r['PROV_confirmed_label']!='BOX_AHEAD' for r in rows)
    recall_ok=bool(n and lower/n>=.95);reduction_ok=high_other<=.5*old_other
    impossible=bool(n and upper/n<.95) or low_other>.5*old_other
    label='PROV_OK' if recall_ok and reduction_ok else 'PROV_FAIL' if impossible else 'PROV_NOT_ESTABLISHED_MISSING_HISTORY'
    return dict(label=label,BOX_AHEAD_original=n,BOX_retained_confirmed_history=strict,
        BOX_retained_lower=lower,BOX_retained_upper=upper,recall_confirmed_history=strict/n if n else None,
        recall_lower=lower/n if n else None,recall_upper=upper/n if n else None,
        nonbox_original=old_other,nonbox_confirmed_history=strict_other,nonbox_lower=low_other,nonbox_upper=high_other,
        checks=dict(box_retention_guaranteed=recall_ok,nonbox_reduction_guaranteed=reduction_ok),
        ray_timestamp_only_would_be_identical_to_original=True,simulation_runs=0,navigation_prepared=False)

def main():
    verify();grouped=common_rows();all_rows=[];misses=[];cells=[];start=time.monotonic();regressions=0;source_candidate_checks=0
    run_records=[dict(r,phase='32') for r in read(ROOT/'research/results/phase32/runs.json') if r['method']=='C0-NA+EC']
    run_records += [dict(r,phase='35') for r in read(ROOT/'research/results/phase35/runs.json') if r['method']=='OURS']
    by_run={r['output']:r for r in run_records}
    for run_number,(directory,source_rows) in enumerate(sorted(grouped.items()),1):
        r=by_run[directory];root,cfg,poses,reference,static,boxes=load_run(r);key=f"{r['phase']}_{r['scene']}_{r['index']}"
        with np.load(register(OUT/'evidence'/f'{key}.npz')) as z:proof={k:z[k].copy() for k in z.files}
        confirmed,possible=masks(proof,tuple(proof['shape']));last=None;field=None;local=[];envelopes=[]
        for source in source_rows:
            file=source['snapshot_file'];tick=int(source['tick'])
            if file!=last:field=snapshot(file);last=file
            old=evaluate(field,np.ones(field.occupied.shape,bool),poses,tick)
            old_label,old_objects=classify(poses[tick],old['u_ref'],tick/72,static,boxes)
            assert old['fire']==(source['original_fire']=='True') and old_label==source['original_label']
            np.testing.assert_allclose(old['u_ref'],json.loads(source['original_u_ref']),atol=1e-12,rtol=0);regressions+=1
            candidate=field.occupied&field.observed&(field.new_component_ids>0)
            assert np.all((field.first_free_tick[candidate]>=0)&(field.first_free_tick[candidate]<field.first_occupied_tick[candidate]));source_candidate_checks+=int(candidate.sum())
            known=evaluate(field,confirmed,poses,tick);full=evaluate(field,possible,poses,tick)
            known_label,known_objects=classify(poses[tick],known['u_ref'],tick/72,static,boxes)
            full_label,full_objects=classify(poses[tick],full['u_ref'],tick/72,static,boxes)
            options=outcome_envelope(field,confirmed,possible,poses,tick)
            for item in options:
                item['label']=classify(poses[tick],item['u_ref'],tick/72,static,boxes)[0] if item['component_id'] is not None else 'NO_CANDIDATE'
            outcome_set={(x['fire'],x['component_id']) for x in options}
            for value in (known,full):
                assert (value['fire'],value['component']['component_id'] if value['component'] else None) in outcome_set
            row=dict(event_key=f'{key}:{tick}',phase=r['phase'],scene=r['scene'],index=r['index'],method=r['method'],tick=tick,time_s=tick/72,
                snapshot_file=file,original_fire=old['fire'],original_label=old_label,original_component=old['component']['component_id'] if old['component'] else None,
                original_t_new_tick=old['component']['t_new_tick'] if old['component'] else None,original_u_ref=old['u_ref'].tolist(),
                PROV_confirmed_fire=known['fire'],PROV_confirmed_label=known_label,PROV_confirmed_component=known['component']['component_id'] if known['component'] else None,
                PROV_confirmed_t_new_tick=known['component']['t_new_tick'] if known['component'] else None,PROV_confirmed_u_ref=known['u_ref'].tolist(),
                PROV_possible_all_fire=full['fire'],PROV_possible_all_label=full_label,
                PROV_fire_lower=all(x['fire'] for x in options),PROV_fire_upper=any(x['fire'] for x in options),
                PROV_nonbox_lower=all(x['fire'] and x['label'] in LABELS[1:] for x in options),
                PROV_nonbox_upper=any(x['fire'] and x['label'] in LABELS[1:] for x in options),
                exact_outcome=len({(x['fire'],x['label'] if x['fire'] else None) for x in options})==1,
                current_candidate_cells=int(candidate.sum()),confirmed_candidate_cells=int((candidate&confirmed).sum()),
                unmeasured_candidate_cells=int((candidate&possible&~confirmed).sum()),
                rejected_candidate_cells=int((candidate&~possible).sum()),original_objects=old_objects,PROV_objects=known_objects)
            for name in LABELS:
                row['PROV_'+name+'_lower']=all(x['fire'] and x['label']==name for x in options)
                row['PROV_'+name+'_upper']=any(x['fire'] and x['label']==name for x in options)
            local.append(row);envelopes.append(dict(event_key=row['event_key'],options=options))
            if old['fire'] and old_label=='BOX_AHEAD' and not known['fire']:
                state='DEFINITE_MISS' if not row['PROV_fire_upper'] else 'UNMEASURED_HISTORY_SENSITIVE'
                details=history_rows(row,field,proof,old,boxes,state);cells.extend(details)
                def span(name):
                    a=[x[name] for x in details if x[name] is not None and x['box_ids']];return [min(a),max(a)] if a else None
                misses.append(dict(event_key=row['event_key'],phase=r['phase'],scene=r['scene'],index=r['index'],time_s=tick/72,status=state,
                    original_component=row['original_component'],PROV_component=row['PROV_confirmed_component'],
                    box_occupied_cells=sum(bool(x['box_ids']) for x in details),selected_component_cells=sum(x['selected_component_cell'] for x in details),
                    box_first_ray_free_s_range=span('first_ray_free_s'),box_first_confirmed_free_s_range=span('first_confirmed_observed_free_s'),
                    box_first_occupied_s_range=span('first_occupied_s'),
                    selected_history_status=dict(Counter(x['provenance_status'] for x in details if x['selected_component_cell']))))
        save(OUT/'per_run'/f'{key}.json',dict(events=local,envelopes=envelopes));all_rows.extend(local)
        save(OUT/'status.json',dict(status='RUNNING',runs_done=run_number,runs_total=30,elapsed_s=time.monotonic()-start))
        print('[PROV]',run_number,'/30',key,flush=True)
    summaries=[]
    for scene in ('SLW','LC','L2','H1','H2','ALL'):
        rows=[r for r in all_rows if scene=='ALL' or r['scene']==scene]
        for name in LABELS:
            summaries.append(dict(scene=scene,label=name,original=sum(r['original_fire'] and r['original_label']==name for r in rows),
                PROV_confirmed_history=sum(r['PROV_confirmed_fire'] and r['PROV_confirmed_label']==name for r in rows),
                PROV_lower=sum(r['PROV_'+name+'_lower'] for r in rows),PROV_upper=sum(r['PROV_'+name+'_upper'] for r in rows)))
    decision=gate(all_rows);save(OUT/'decision.json',decision);csvout(OUT/'events.csv',all_rows);csvout(OUT/'summary.csv',summaries)
    if misses:csvout(OUT/'missed_BOX_AHEAD.csv',misses)
    else:(OUT/'missed_BOX_AHEAD.csv').write_text('event_key,phase,scene,index,time_s,status\n')
    if cells:csvout(OUT/'missed_box_cell_history.csv',cells)
    else:(OUT/'missed_box_cell_history.csv').write_text('event_key,world_x_m,world_y_m,first_ray_free_s,first_confirmed_observed_free_s,first_occupied_s\n')
    merged=dict(prior_audit.HASHES);merged.update(HASHES);save(OUT/'evaluation_input_hashes.json',merged)
    save(OUT/'verification.json',dict(common_opportunities=len(all_rows),original_regression_exact=regressions,
        original_candidate_cell_appearances_all_have_ray_evidence=source_candidate_checks,
        exact_PROV_event_outcomes=sum(r['exact_outcome'] for r in all_rows),missed_box_events_confirmed_history=len(misses),
        no_simulation=True,no_navigation_preparation=True,elapsed_s=time.monotonic()-start))
    save(OUT/'status.json',dict(status='COMPLETE',runs_done=30,runs_total=30,elapsed_s=time.monotonic()-start,label=decision['label']))
    print(json.dumps(decision))

if __name__=='__main__':main()
