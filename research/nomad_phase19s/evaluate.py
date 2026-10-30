"""One saved-input pass; reconstruct paths, pair SP/SRG, report and publish."""
import argparse
import csv
import json
import subprocess
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT, sha256_file
from nomad_phase18d.diagnose import Inputs as ChunkInputs, CLR
from nomad_phase19r.evaluate import Inputs as RepairInputs, clean, dump, csv_write, rows
from nomad_phase12.methods import hermite_splice
from .srg import rollout

HERE=ROOT/'research/nomad_phase19s'
OUT=ROOT/'research/results/phase19s'
PATHS=('FRESHEST-SAFE','HERMITE','CLR')
LARGE=('poses','commands','speeds','omegas','phases','events','pivots')


def csv_rows(path):
    def parse(v):
        if v=='':return None
        if v in ('True','False'):return v=='True'
        try:return json.loads(v)
        except (ValueError,TypeError):return v
    with Path(path).open() as f:return [{k:parse(v) for k,v in r.items()} for r in csv.DictReader(f)]


def inventory():
    ci=ChunkInputs();ri=RepairInputs();cases=[];excluded=[]
    old=csv_rows(ci.track(ROOT/'research/results/phase18d/combos.csv'))
    records=json.loads(ci.track(ROOT/'research/results/phase18/runs.json').read_text())
    byrun={r['key']:r for r in records}
    source=[]
    for r in old:
        if r['speed']!='SP' or r['path_type'] not in PATHS:continue
        if not r['available']:
            excluded.append({k:r[k] for k in ('run','scene','fresh_id','path_type','availability')});continue
        source.append(r)
        d=ci.load(byrun[r['run']]);event=d['events_by_id'][r['fresh_id']];job=d['jobs_by_id'][r['fresh_id']]
        B=np.array(r['B']);np.testing.assert_array_equal(B,job['boundary'])
        raw=ci.native(d,event)
        np.testing.assert_allclose(raw,job['world_xy'],atol=1e-12,rtol=0)
        if r['path_type']=='FRESHEST-SAFE':path=raw
        elif r['path_type']=='HERMITE':path=hermite_splice(raw,B)[0]
        else:
            saved=d['results'][job['job_id']];assert saved['accepted'];path=np.array(saved['poses'])[:,:2]
        ident=dict(dataset='D1' if r['scene']=='SLW' else 'D2',event_id=f"{r['run']}:F{r['fresh_id']}",
                   run=r['run'],scene=r['scene'],index=r['index'],fresh_id=r['fresh_id'],path_type=r['path_type'],
                   common=r['common_eligible'],B=B.tolist(),previous_v=job['previous_command'][0])
        cases.append(dict(identity=ident,path=np.asarray(path),config=d['config'],legacy=r))
    counts=Counter((c['identity']['dataset'],c['identity']['path_type'],c['identity']['common']) for c in cases)
    for dataset,n in [('D1',85),('D2',166)]:
        for name in PATHS:assert counts[dataset,name,True]==n
    repairs={}
    for split,dataset,n in [('eval','D3',90),('dev','D4',755)]:
        es=csv_rows(ri.track(ROOT/f'research/results/phase19r/events_{split}.csv'))
        selected=[e for e in es if e['repair_success']];assert len(selected)==n
        for e in selected:repairs[split,e['event_id'],e['selected_sample']]=(dataset,e)
    journal=ri.track(ROOT/'research/results/phase19r/repair_journal.jsonl')
    restored={}
    with journal.open() as f:
        for line in f:
            r=json.loads(line);key=(r['split'],r['event_id'],r['sample'])
            if key in repairs:
                assert r['accepted'];assert key not in restored;restored[key]=r
    assert len(restored)==845
    for key,(dataset,e) in repairs.items():
        d=ri.load(e['output']);tick=e['tick'];np.testing.assert_allclose(e['B'],d['poses'][tick],atol=1e-12,rtol=0)
        assert e['previous_actual_v_m_s']==float(d['trace'][tick]['v_m_s'])
        ident=dict(dataset=dataset,event_id=e['event_id'],run=e['run'],scene=e['scene'],index=e['index'],fresh_id=e['fresh_id'],
                   path_type='REPAIR',common=True,B=e['B'],previous_v=e['previous_actual_v_m_s'],cause=e['cause'],selected_sample=e['selected_sample'])
        legacy=dict(minimum_clearance_m=e['rollout_minimum_clearance_m'],overlap=e['rollout_overlap'],distance_m=e['rollout_progress_m'],duration_s=e['rollout_duration_s'])
        cases.append(dict(identity=ident,path=np.array(restored[key]['path']),config=d['config'],legacy=legacy))
    # Figure choices use only previously published labels, before new rollouts.
    failures=csv_rows(ci.track(ROOT/'research/results/phase18d/slw_failures.csv'))
    first=next(r for r in failures if r['row_type']=='FINAL_CAUSE' and r['label']=='UNDERTURN_EXECUTION')
    d=ci.load(byrun[first['run']]);e=d['events_by_id'][first['source_id']];tick=round(e['application_sim_s']*72)
    slw=dict(identity=dict(dataset='EXAMPLE_ONLY',event_id=f"{first['run']}:F{first['source_id']}",run=first['run'],
                          scene='SLW',index=first['index'],fresh_id=first['source_id'],path_type=first['path_kind'],common=False,
                          B=first['B'],previous_v=d['v'][tick]),path=np.array(first['path']),config=d['config'])
    repair_example=next(c for c in cases if c['identity']['dataset']=='D3' and c['legacy']['overlap'])
    example_ids=dict(slw=slw['identity'],repair=repair_example['identity'])
    hashes={**ci.hashes,**ri.hashes}
    meta=dict(case_count=len(cases),expected_rollouts=len(cases)*2,examples=example_ids,
              dataset_path_counts=dict(Counter(c['identity']['dataset'] for c in cases)),
              common_event_counts={'D1':85,'D2':166},unavailable_path_rows=len(excluded),
              slw_example_scope='First Phase18D FINAL_CAUSE UNDERTURN_EXECUTION row; supplemental saved active path, not added to denominators',
              repair_example_scope='First Phase19R evaluation success with saved 1.5s SP overlap, event order fixed before new execution')
    return cases,slw,repair_example,meta,excluded,hashes


def summarize(data):
    out=[]
    for dataset in ('D1','D2','D3','D4'):
        names=PATHS if dataset in ('D1','D2') else ('REPAIR',)
        for scope in (('COMMON','AVAILABLE') if dataset in ('D1','D2') else ('ALL',)):
            for name in names:
                for rule in ('SP','SRG'):
                    rr=[r for r in data if r['dataset']==dataset and r['path_type']==name and r['rule']==rule and (scope!='COMMON' or r['common'])]
                    done=[r for r in rr if r['completed']]
                    out.append(dict(dataset=dataset,scope=scope,path_type=name,rule=rule,n=len(rr),
                        overlaps=sum(r['overlap'] for r in rr),negative_witnesses=sum(r['geometric_negative_witness'] for r in rr),
                        margin_violations=sum(r['margin_violation'] for r in rr),completions=len(done),safe_completions=sum(r['safe_completion'] for r in rr),
                        completion_time_median_s=float(np.median([r['completion_time_s'] for r in done])) if done else None,
                        completion_mean_speed_m_s=float(np.mean([r['completion_average_speed_m_s'] for r in done])) if done else None,
                        distance_mean_m=float(np.mean([r['distance_m'] for r in rr])) if rr else None,
                        rotation_time_mean_s=float(np.mean([r['rotation_time_s'] for r in rr])) if rr else None,
                        trigger_events=sum(r['trigger_any'] for r in rr),trigger_fraction=sum(r['trigger_any'] for r in rr)/len(rr) if rr else None,
                        trigger_S=sum(r['trigger_S'] for r in rr),trigger_P=sum(r['trigger_P'] for r in rr),
                        omega_saturation_mean=float(np.mean([r['omega_saturation_fraction'] for r in rr])) if rr else None,
                        max_cross_track_m=float(np.max([r['max_cross_track_m'] for r in rr])) if rr else None,
                        incomplete_reasons=dict(Counter(r['incomplete_reason'] for r in rr if not r['completed']))))
    return out


def paired_times(data):
    pairs=[];lookup={(r['dataset'],str(r['event_id']),r['path_type'],r['rule']):r for r in data}
    for r in data:
        if r['dataset']!='D2' or r['rule']!='SP':continue
        s=lookup['D2',str(r['event_id']),r['path_type'],'SRG']
        paired=r['completed'] and s['completed'] and r['completion_time_s']>0
        pairs.append(dict(event_id=r['event_id'],path_type=r['path_type'],common=r['common'],
                          sp_complete=r['completed'],srg_complete=s['completed'],both_complete=paired,
                          both_safe=r['safe_completion'] and s['safe_completion'],trigger=s['trigger_any'],
                          SP_s=r['completion_time_s'],SRG_s=s['completion_time_s'],
                          ratio=s['completion_time_s']/r['completion_time_s'] if paired else None))
    summaries=[]
    for scope in ('COMMON','AVAILABLE'):
        for name in ('ALL',)+PATHS:
            for safe in (False,True):
                rr=[r for r in pairs if (scope!='COMMON' or r['common']) and (name=='ALL' or r['path_type']==name)]
                valid=[r['ratio'] for r in rr if r['both_complete'] and (not safe or r['both_safe'])]
                summaries.append(dict(scope=scope,path_type=name,require_both_safe=safe,candidates=len(rr),pairs=len(valid),
                                      median=float(np.median(valid)) if valid else None,p90=float(np.quantile(valid,.9)) if valid else None,
                                      trigger_fraction=sum(r['trigger'] for r in rr)/len(rr) if rr else None,
                                      SP_only_complete=sum(r['sp_complete'] and not r['srg_complete'] for r in rr),
                                      SRG_only_complete=sum(r['srg_complete'] and not r['sp_complete'] for r in rr)))
    return pairs,summaries


def decide(summary,times):
    find=lambda dataset,scope,name,rule:next(r for r in summary if (r['dataset'],r['scope'],r['path_type'],r['rule'])==(dataset,scope,name,rule))
    d3=find('D3','ALL','REPAIR','SRG');sp=find('D3','ALL','REPAIR','SP')
    violations=[]
    for scope in ('COMMON','AVAILABLE'):
        for name in PATHS:
            a=find('D1',scope,name,'SP');b=find('D1',scope,name,'SRG')
            if b['overlaps']>a['overlaps']:violations.append(dict(scope=scope,path=name,SP=a['overlaps'],SRG=b['overlaps']))
    time=next(r for r in times if r['scope']=='COMMON' and r['path_type']=='ALL' and not r['require_both_safe'])
    safe=d3['overlaps']/d3['n']<=.01 and not violations
    if not safe:label='SRG_NOT_ENOUGH'
    elif time['median'] is None:label='INCONCLUSIVE_NO_COMPLETION_PAIRS'
    elif time['median']>1.10:label='SRG_SAFE_BUT_SLOW'
    else:label='SRG_FIXES_EXECUTION'
    return dict(label=label,D3_SP_overlaps=sp['overlaps'],D3_SRG_overlaps=d3['overlaps'],D3_n=d3['n'],
                D3_SRG_overlap_fraction=d3['overlaps']/d3['n'],D1_safety_violations=violations,safety_pass=safe,
                D2_primary_time=time,decision_scope='D1 safety: common AND method-available; D2 timing: common 166, pooled three paths, paired completions only',
                historical_D3_SP_1p5s_overlaps=10,post_hoc=True,closed_loop_claim=False)


def run(out):
    assert not out.exists(),'Preserve results: no overwrite or implicit restart'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).strip(),'Commit code and protocol before data rollouts'
    proto=json.loads((HERE/'protocol.json').read_text());sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for file,h in proto['protected_sha256'].items():assert sha256_file(ROOT/file)==h,file
    cases,slw,repair_example,meta,excluded,hashes=inventory()
    for file in HERE.glob('*'):
        if file.is_file():hashes[str(file)]=sha256_file(file)
    out.mkdir(parents=True);dump(out/'protocol.json',proto);dump(out/'inventory.json',meta)
    dump(out/'input_manifest.json',dict(git_sha=sha,sha256=hashes));csv_write(out/'unavailable.csv',excluded)
    print(f"[inventory] {meta['dataset_path_counts']}; {meta['expected_rollouts']} paired-rollout rows; examples fixed",flush=True)
    data=[];audits=[];examples={};maximum_dv=maximum_w=0.
    with (out/'rollouts.jsonl').open('x') as log:
        for i,c in enumerate(cases):
            ident=c['identity'];pair={}
            for rule in ('SP','SRG'):
                result=rollout(ident['B'],c['path'],ident['previous_v'],rule,c['config'])
                vv=np.r_[ident['previous_v'],[x['v'] for x in result['commands']]]
                dv=float(np.max(np.abs(np.diff(vv)))) if len(vv)>1 else 0.
                ww=max((abs(x['w']) for x in result['commands']),default=0.)
                assert dv<=.5/9+1e-12 and ww<=.4+1e-12
                maximum_dv=max(maximum_dv,dv);maximum_w=max(maximum_w,ww)
                row={**ident,'rule':rule,**{k:v for k,v in result.items() if k not in LARGE}}
                data.append(row);log.write(json.dumps(clean(row),allow_nan=False)+'\n');log.flush();pair[rule]=result
                if rule=='SP':
                    current=result['legacy_1p5s_prefix'];old=c['legacy']
                    errors={k:abs(current[k]-old[k]) for k in ('minimum_clearance_m','distance_m','duration_s')}
                    passed=max(errors.values())<=1e-10 and current['overlap']==old['overlap']
                    audits.append({**ident,**errors,'overlap_match':current['overlap']==old['overlap'],'PASS':passed})
                    assert passed,('SP prefix regression mismatch',ident,errors)
            if c is repair_example:examples['repair']=dict(identity=ident,path=c['path'],config=c['config'],results=pair)
            if (i+1)%50==0:print(f'[offline] {i+1}/{len(cases)} saved paths, SP+SRG recorded',flush=True)
    examples['slw']=dict(identity=slw['identity'],path=slw['path'],config=slw['config'],
                         results={r:rollout(slw['identity']['B'],slw['path'],slw['identity']['previous_v'],r,slw['config']) for r in ('SP','SRG')})
    summary=summarize(data);pairs,times=paired_times(data);decision=decide(summary,times)
    csv_write(out/'rollouts.csv',data);csv_write(out/'summary.csv',summary);csv_write(out/'time_pairs.csv',pairs)
    csv_write(out/'time_summary.csv',times);csv_write(out/'prefix_regression.csv',audits)
    dump(out/'decision.json',decision);dump(out/'examples.json',examples)
    verify=dict(tests=5,prefix_regressions=len(audits),prefix_pass=sum(r['PASS'] for r in audits),
                max_prefix_clearance_error_m=max(r['minimum_clearance_m'] for r in audits),maximum_command_dv=maximum_dv,maximum_abs_w=maximum_w)
    dump(out/'verification.json',verify)
    from .report import render
    render(out,data,summary,pairs,times,decision,examples,proto,sha,verify)
    for file,h in hashes.items():assert sha256_file(file)==h,file
    for file,h in proto['protected_sha256'].items():assert sha256_file(ROOT/file)==h,file
    dump(out/'complete.json',dict(git_sha=sha,rollouts=len(data),supplemental_example_rollouts=2,
                                 protected_and_input_hashes_unchanged=True,Isaac_navigation=0,NoMaD_inference=0,Graph_solves=0,
                                 label=decision['label']))
    print(json.dumps(decision),flush=True)


def publish(out):
    assert (out/'complete.json').exists()
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','add','--','research/nomad_phase19s',str(out.relative_to(ROOT)),'docs/PHASE19S_STOP_ROTATE_GO.md'],cwd=ROOT,check=True)
    subprocess.run(['git','add','-f','--',*[str(p.relative_to(ROOT)) for p in out.glob('*.png')]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():
        subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase19S fixed-path stop rotate go offline validation'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');ap.add_argument('--report-only',action='store_true');args=ap.parse_args()
    if args.report_only:
        from .report import render
        render(OUT,csv_rows(OUT/'rollouts.csv'),csv_rows(OUT/'summary.csv'),csv_rows(OUT/'time_pairs.csv'),csv_rows(OUT/'time_summary.csv'),
               json.loads((OUT/'decision.json').read_text()),json.loads((OUT/'examples.json').read_text()),json.loads((OUT/'protocol.json').read_text()),
               json.loads((OUT/'complete.json').read_text())['git_sha'],json.loads((OUT/'verification.json').read_text()),replace=True)
    elif OUT.exists():assert (OUT/'complete.json').exists(),'Partial output preserved; no automatic restart'
    else:run(OUT)
    if args.publish:publish(OUT)


if __name__=='__main__':main()
