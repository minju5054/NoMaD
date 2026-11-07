"""Preregistered unique installation cohort, with original solver inputs."""
import hashlib,json
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase32o.evaluate import save

OUT=ROOT/'research/results/phase33p'
SEED=20261108

def read(path):return json.loads(Path(path).read_text())
def lines(path):return [json.loads(s) for s in Path(path).read_text().splitlines() if s] if Path(path).exists() else []
def path_key(path):return hashlib.sha256(np.asarray(path,dtype=np.float64).tobytes()).hexdigest()

def population():
    runs=sorted((r for r in read(ROOT/'research/results/phase32/runs.json') if r['method']=='G18+EC'),key=lambda r:(r['scene'],r['index']))
    cases=[]
    for r in runs:
        root=Path(r['output']);repairs=lines(root/'repair.jsonl');paths=lines(root/'phase29_paths.jsonl');detours=lines(root/'detour.jsonl');ec=lines(root/'exec_cert.jsonl')
        apps=[x for x in repairs if x['event']=='PATH_APPLIED'];installs=[x for x in ec if x['event']=='INSTALL'];assert len(apps)==len(installs)
        checks=[x for x in ec if x['event']=='CHECK'];normal={};prior=None;priors=[]
        for x in paths:
            if x['event']=='SUBMIT':normal[x['job_id']]=dict(x,previous_xy=prior)
            elif x['event']=='RESULT' and x.get('applied'):
                prior=np.asarray(x['poses'])[:,:2].tolist();priors.append((x['simulation_time_s'],prior))
        for ordinal,(app,installed) in enumerate(zip(apps,installs)):
            assert app['tick']==installed['apply_tick'] and app['kind']==installed['kind'] and app['id']==installed['id']
            kind='R2' if app['kind']=='REPAIR' else 'R3' if app['kind']=='DETOUR' else 'NORMAL';key=path_key(app['path_world'])
            matching=[x for x in checks if x['check_tick']==app['tick'] and x['generation']==installed['generation']-1 and x['path_sha256']==key and x['passed'] and x.get('speed_cap_m_s')==installed.get('speed_cap_m_s')]
            assert matching,(r['key'],ordinal,'missing exact installation EC context')
            check=matching[-1]
            case=dict(event_key=f"{r['key']}:{ordinal}",run_key=r['key'],output=str(root),scene=r['scene'],index=r['index'],state=kind,
                      event_ordinal=ordinal,application=app,installation=installed,ec_context=check)
            if kind=='NORMAL':
                matching=[x for x in normal.values() if x['id']==app['id'] and x['simulation_time_s']<=app['simulation_time_s']+1e-9]
                if matching:
                    job=max(matching,key=lambda x:x['job_id']);case['input_source']='RECORDED_NORMAL_SUBMIT'
                else:
                    assert app['kind']=='SAFE','Missing originating GRAPH18 input must not be replaced by an optimized path'
                    before=[p for t,p in priors if t<app['simulation_time_s']]
                    job=dict(job_id=-1,id=app['id'],path=app['path_world'],boundary=app['pose'],previous_vw=check['actual_vw'],previous_xy=before[-1] if before else None,snapshot=check['snapshot'])
                    case['input_source']='RECORDED_SAFE_INSTALL_STATE_NO_ORIGIN_JOB'
                case.update(job=job,snapshot_file=job['snapshot']['file'])
            else:
                if kind=='R3':
                    matches=[x for x in detours if x['event']=='APPLIED' and round(x['simulation_time_s']*72)==app['tick'] and path_key(x['path'])==key]
                else:
                    matches=[]
                    for x in repairs:
                        if x['event']!='RESULT' or x.get('disposition')!='ACCEPTED' or round(x['simulation_time_s']*72)!=app['tick']:continue
                        result=x['numeric_result'];i=result.get('selected_sample')
                        if i is not None and path_key(result['results'][i]['path'])==key:matches.append(x)
                assert len(matches)==1,(r['key'],ordinal,kind,len(matches))
                job_id=matches[0]['job_id'];job=read(root/'repair_jobs'/f'transport_{job_id:04d}.json');assert job['kind']==kind
                case.update(job=job,snapshot_file=job['snapshot_file'],input_source='RECORDED_POOL_TRANSPORT')
            assert Path(case['snapshot_file']).exists(),case['snapshot_file']
            assert Path(check['snapshot']['file']).exists(),check['snapshot']['file']
            cases.append(case)
    return cases

def select():
    dest=OUT/'cohort.json'
    if dest.exists():return read(dest)
    all_cases=population();counts=Counter(x['state'] for x in all_cases);assert counts==dict(NORMAL=1419,R2=7,R3=40),counts
    rng=np.random.default_rng(SEED);normal=[x for x in all_cases if x['state']=='NORMAL']
    chosen=[normal[int(i)] for i in rng.choice(len(normal),200,replace=False)]+[x for x in all_cases if x['state'] in ('R2','R3')]
    chosen=sorted(chosen,key=lambda x:({'NORMAL':0,'R2':1,'R3':2}[x['state']],x['run_key'],x['event_ordinal']))
    for i,x in enumerate(chosen):x['case_id']=f'E{i:04d}'
    assert len(chosen)==247 and len({x['event_key'] for x in chosen})==247
    save(dest,chosen);save(OUT/'sampling.json',dict(seed=SEED,algorithm='numpy.default_rng.choice(replace=False); sorted population and deterministic case order',
        population=dict(counts),selected=dict(Counter(x['state'] for x in chosen)),unique_events=247,
        input_sources=dict(Counter(x['input_source'] for x in chosen)),R2_small_n_note='R2 n=7; descriptive only, not a standalone reliability estimate'))
    return chosen

if __name__=='__main__':
    cases=select();print(json.dumps(dict(events=len(cases),states=dict(Counter(x['state'] for x in cases)),input_sources=dict(Counter(x['input_source'] for x in cases)))))
