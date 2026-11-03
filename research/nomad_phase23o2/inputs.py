"""Run-disjoint training, truly unused static snapshots, seen sudden cases."""
import json,hashlib
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,local_to_world,sha256_file

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase23o2';OLD=ROOT/'research/results/phase23o'
def read(p):return json.loads(Path(p).read_text())
def write(p,x):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(x,indent=2)+'\n')
def key(c):return (c['run'],int(c['tick']))
def histories(cases,hashes):
    for run in sorted({c['run'] for c in cases}):
        file=Path(run)/'events.jsonl';hashes[str(file)]=sha256_file(file)
        with file.open() as stream:events=[json.loads(s) for s in stream if 'overnight_metric_samples' in s]
        events=[e for e in events if 'overnight_metric_samples' in e and e.get('received_sim_s',e.get('application_sim_s')) is not None]
        arrival=lambda e:float(e.get('received_sim_s',e.get('application_sim_s')))
        events=sorted(events,key=lambda e:(arrival(e),e['id']));by_id={e['id']:e for e in events}
        for c in [c for c in cases if c['run']==run]:
            now=c['tick']/72;current=by_id[c['fresh_id']];received=arrival(current);assert received<=now+1e-8
            prior=[e for e in events if e['id']!=current['id'] and arrival(e)<received and 0<=now-arrival(e)<=2.+1e-9]
            # Latest seven delivered previous native sets, plus the current set.
            prior=sorted(prior,key=lambda e:(arrival(e),e['id']),reverse=True)[:7]
            c['current_input_age_s']=max(0.,now-received);c['current_arrival_s']=received;c['memory_sets']=[]
            for e in prior:
                native=np.array([local_to_world(np.asarray(p),e['observation_pose']) for p in e['overnight_metric_samples']]);assert native.shape==(8,8,2)
                c['memory_sets'].append(dict(kind='NATIVE_NOMAD',fresh_id=e['id'],arrival_s=arrival(e),age_s=now-arrival(e),samples_world=native.tolist(),observation_pose=e['observation_pose']))
            c['memory_provenance']='Only saved native overnight_metric_samples; applied OLD/repair/A* paths never enter historical components'
    return cases

def prepare():
    assert not (OUT/'manifest.json').exists(),'Do not replace a registered dataset'
    m=read(OLD/'manifest.json');full=read(OLD/'registration_history/4eb8f7c_manifest.json');context=read(OLD/'input_context_050.json')['contexts']
    hashes={};files=[OLD/'manifest.json',OLD/'registration_history/4eb8f7c_manifest.json',OLD/'input_context_050.json',ROOT/'research/nomad_phase23/protocol.json']
    hashes.update({str(f):sha256_file(f) for f in files});used={key(c) for c in m['evaluation']}
    training=[dict(c,**context[c['case_id']],origin_phase23_case_id=c['case_id']) for c in m['training']]
    evaluation=[];examples=[]
    for c in full['evaluation']:
        if c['group']!='static' or key(c) in used:continue
        # Static source logs have no SPAlignment mode; the frozen23-O context
        # resumes the installed OLD in GO, with current actual speed.
        assert not (Path(c['run'])/'phase20_commands.jsonl').exists()
        evaluation.append(dict(c,case_id=f'H{len(evaluation):04d}',origin_full_case_id=c['case_id'],stratum='HELDOUT_STATIC',
            executing_path=c.get('baseline_old_path',c.get('old_path')),executing_state=dict(mode='GO',source='OLD already installed; no new alignment trigger')))
    for c in m['evaluation']:
        if c['group']!='sudden':continue
        file=OLD/'evaluation'/f"{c['case_id']}.json";hashes[str(file)]=sha256_file(file)
        evaluation.append(dict(c,**context[c['case_id']],case_id=f'S{len(evaluation):04d}',origin_phase23_case_id=c['case_id'],stratum='SEEN_SUDDEN',baseline_record=str(file)))
    for old_id in ('ES0078','ES0172'):
        c=next(c for c in m['evaluation'] if c['case_id']==old_id);file=OLD/'evaluation'/f'{old_id}.json';hashes[str(file)]=sha256_file(file)
        examples.append(dict(c,**context[c['case_id']],case_id='X_'+old_id,origin_phase23_case_id=old_id,stratum='SEEN_EXAMPLE_ONLY',baseline_record=str(file)))
    histories(training+evaluation+examples,hashes)
    for c in training+evaluation+examples:hashes[c['snapshot_file']]=sha256_file(c['snapshot_file'])
    assert len(training)==242 and len(evaluation)==558 and len(examples)==2
    assert not {key(c) for c in evaluation if c['group']=='static'}&used
    assert not {c['run'] for c in training}&{c['run'] for c in evaluation+examples}
    first=next(c['case_id'] for c in evaluation if c.get('origin_phase23_case_id')=='ED0473')
    extra=[c['case_id'] for c in evaluation if c['group']=='sudden' and c['case_id']!=first][:2]
    output=dict(training=training,evaluation=evaluation,examples_only=examples,figures=['X_ES0078',first,'X_ES0172']+extra,input_hashes=hashes,
        sampling=dict(full_static=795,previously_evaluated_static=454,overlap=271,unused_static=524,seen_sudden=34,
          explanation='Uniform5was selected from raw events, not as a subset of uniform10; actual run/tick set difference is524, not829-488=341. No evaluated static snapshot enters the new held-out denominator.'),
        split_disjoint=True,history_window_s=2.,history_max_sets_including_current=8,arrival_clock='post-delay received_sim_s, application_sim_s only if receipt is absent',
        age_clock='snapshot dispatch time; current component actual arrival age retained; no future0.5s information')
    write(OUT/'manifest.json',output)
    print(json.dumps(dict(training=len(training),heldout_static=524,seen_sudden=34,examples_only=2,max_sets=max(1+len(c['memory_sets']) for c in training+evaluation))))
    return output
if __name__=='__main__':prepare()
