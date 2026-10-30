"""Read-only publication gaps, frame ages, backlog estimates and worker overlap."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase20.metrics import rows,stats
from nomad_phase19r.evaluate import dump,csv_write

OUT=ROOT/'research/results/phase20d_diagnosis'

def diagnose():
    assert not OUT.exists(),'Preserve diagnosis; no overwrite'
    sources=[];hashes={}
    def track(p):p=Path(p).resolve();hashes[str(p)]=sha256_file(p);return p
    for phase in ('phase20','phase20b'):
        rr=json.loads(track(ROOT/f'research/results/{phase}/runs.json').read_text())
        for r in rr:
            if phase=='phase20b' and r['scene']=='L1':continue
            sources.append((phase,r))
    intervals=[];summaries=[];unavailable=[];per_update=[];ages=[]
    for phase,r in sources:
        run=Path(r['output'])
        if not (run/'summary.json').exists() or not (run/'depth/updates.jsonl').exists():
            unavailable.append(dict(phase=phase,run=r['key'],reason='Missing summary or depth updates'));continue
        summary=json.loads(track(run/'summary.json').read_text());epoch=summary['epoch_monotonic_ns']
        updates=rows(track(run/'depth/updates.jsonl'));obs=rows(track(run/'observations.jsonl'));ctrl=rows(track(run/'controller.jsonl'))
        commands=rows(track(run/'phase20_commands.jsonl'));repair=rows(track(run/'repair.jsonl'))
        captures=[o for o in obs if 'capture_end_monotonic_ns' in o and o.get('status')!='terminal_capture_no_request' and 'observation_id' in o]
        times=np.array([(o['capture_end_monotonic_ns']-epoch)/1e9 for o in captures]);ctimes=np.array([(c['monotonic_ns']-epoch)/1e9 for c in ctrl])
        end=float(summary['navigation_wall_seconds']);pub=np.array([(u['publication_monotonic_ns']-epoch)/1e9 for u in updates])
        active=[]
        pool=run/'repair_pool_jobs.jsonl'
        result_rows=rows(track(pool)) if pool.exists() else [x.get('numeric_result',x) for x in repair if x['event'] in ('RESULT','LATE_RESULT')]
        for x in result_rows:
            if x and 'start_ns' in x and 'end_ns' in x:active.append(((x['start_ns']-epoch)/1e9,(x['end_ns']-epoch)/1e9,x.get('job_id')))
        ids={u['frame_id'] for u in updates};capture_ids={o['observation_id'] for o in captures}
        missing=sorted(capture_ids-ids);extra=sorted(ids-capture_ids)
        # Queue is explicitly unbounded in the frozen producer; there is no drop branch.
        max_age=0.;run_ages=[];qlags=[]
        for i,u in enumerate(updates):
            publication=pub[i];capture=(u['capture_end_monotonic_ns']-epoch)/1e9
            service=(u['update_ms']+u['snapshot_and_persist_ms'])/1000
            wait=max(0.,publication-capture-service);qlags.append(wait)
            per_update.append(dict(phase=phase,run=r['key'],method=r['method'],frame=u['frame_id'],capture_sim_s=u['sim_s'],
                publication_s=publication,capture_to_publication_s=publication-capture,update_ms=u['update_ms'],
                snapshot_and_persist_ms=u['snapshot_and_persist_ms'],estimated_queue_wait_s=wait,
                inferred_unpublished_frames=max(0,int(np.searchsorted(times,publication,side='right'))-(i+1))))
        for c,t in zip(ctrl,ctimes):
            i=int(np.searchsorted(pub,t,side='right')-1)
            age=c['simulation_time_s']-(updates[i]['sim_s'] if i>=0 else 0.)
            max_age=max(max_age,age);run_ages.append(age)
            if age>.5:ages.append(dict(phase=phase,run=r['key'],method=r['method'],simulation_time_s=c['simulation_time_s'],snapshot_age_s=age,
                frame=updates[i]['frame_id'] if i>=0 else -1,source=c.get('phase20',{}).get('source')))
        valid_indices=np.flatnonzero((pub>=0)&(pub<=end));edges=[(0.,None)]+[(pub[i],int(i)) for i in valid_indices]+[(end,None)]
        local=[]
        for (start,_),(finish,j) in zip(edges,edges[1:]):
            length=finish-start
            if length<.5:continue
            overlapping=[k for a,b,k in active if a<finish and b>start]
            capture_count=int(np.sum((times>start)&(times<=finish)))
            state=Counter();n=0
            for c,t in zip(ctrl,ctimes):
                if start<=t<finish:state[c.get('phase20',{}).get('source','UNKNOWN')]+=1;n+=1
            u=updates[j] if j is not None else None
            prior_count=int(np.searchsorted(pub,start,side='right'));submitted=int(np.searchsorted(times,start,side='right'))
            backlog=max(0,submitted-prior_count)
            # PUBLISH_BUG requires dominant synchronous post-update work, not an
            # invented CPU-utilization reading. Timestamp is an estimate from logged durations.
            publish_wait=bool(u and u['snapshot_and_persist_ms']>u['update_ms'])
            label='CPU_CONTENTION' if overlapping else 'NO_CAPTURE' if capture_count==0 and backlog==0 else 'PUBLISH_BUG' if publish_wait else 'OTHER'
            row=dict(phase=phase,run=r['key'],method=r['method'],start_wall_s=start,end_wall_s=finish,length_s=length,
                label=label,state_tick_fractions={k:v/n for k,v in state.items()} if n else {},repair_jobs_overlapping=overlapping,
                depth_captures_completed=capture_count,recorded_queue_length=None,inferred_unpublished_backlog_at_start=backlog,
                recorded_dropped_frames=None,inferred_dropped_frames=0 if not missing and not extra else None,
                update_ms=u['update_ms'] if u else None,persist_ms=u['snapshot_and_persist_ms'] if u else None,
                estimated_processing_end_s=finish-u['snapshot_and_persist_ms']/1000 if u else None,cpu_utilization='NOT_RECORDED',
                evidence='repair interval overlap (not causal CPU proof)' if overlapping else 'source has synchronous compression/hash before publication' if publish_wait else 'capture/publication timestamps')
            intervals.append(row);local.append(row)
        # Include all actual control windows for stale-age fraction, not average frame ages.
        dt=np.maximum(0,np.r_[ctimes[1:],end]-ctimes) if len(ctimes) else np.array([])
        summaries.append(dict(phase=phase,run=r['key'],method=r['method'],original_classification=r['classification'],wall_duration_s=end,
            max_publication_gap_s=max((b[0]-a[0] for a,b in zip(edges,edges[1:])),default=0.),max_snapshot_age_s=max_age,
            gap_intervals=len(local),gap_full_time_fraction=sum(x['length_s'] for x in local)/end if end else None,
            no_update_after_0p5_fraction=sum(x['length_s']-.5 for x in local)/end if end else None,
            stale_snapshot_time_fraction=float(np.sum(dt*(np.array(run_ages)>.5))/end) if end else None,
            update_ms=stats([u['update_ms'] for u in updates]),persist_ms=stats([u['snapshot_and_persist_ms'] for u in updates]),
            queue_wait_s=stats(qlags),captures=len(captures),published=len(updates),missing_frame_ids=missing,extra_frame_ids=extra,
            interval_labels=dict(Counter(x['label'] for x in local))))
    OUT.mkdir(parents=True);csv_write(OUT/'gaps.csv',intervals);csv_write(OUT/'runs.csv',summaries);csv_write(OUT/'updates.csv',per_update);csv_write(OUT/'stale_controller_ticks.csv',ages)
    verdict=dict(runs=len(summaries),unavailable=unavailable,labels=dict(Counter(x['label'] for x in intervals)),
        maximum_publication_gap_s=max(r['max_publication_gap_s'] for r in summaries),maximum_snapshot_age_s=max(r['max_snapshot_age_s'] for r in summaries),
        total_missing_frames=sum(len(r['missing_frame_ids']) for r in summaries),queue_drop_evidence=False,
        source_findings=['Unbounded FIFO; no full-queue/drop code','Snapshot/raw compressed persistence and SHA hashing precede publication pointer','Recorded publication timestamp precedes hash/log/pointer update'],
        interpretation='Publication gap and capture-age/backlog are distinct; overlap label is not measured CPU causation; historical run classifications unchanged')
    dump(OUT/'diagnosis.json',verdict);dump(OUT/'input_hashes.json',hashes)
    print(json.dumps(verdict),flush=True)

if __name__=='__main__':diagnose()
