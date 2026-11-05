"""Enumerate all saved C0 R3 jobs and the registered 16 pre-passage cases."""
import copy, json
from pathlib import Path
from nomad_isaac.common import ROOT, sha256_file
from nomad_phase23o3.diagnose import input_stage

HERE=Path(__file__).parent
OUT=ROOT/'research/results/phase25'


def read(path):
    return json.loads(Path(path).read_text())


def build():
    cases=[];sources={};groups={}
    for phase in ('phase21','phase24r','phase24r2'):
        file=ROOT/'research/results'/phase/'runs.json'
        sources[str(file)]=sha256_file(file)
        runs=[r for r in read(file) if r['method']==('M3_GRAPH' if phase=='phase21' else 'C0')]
        count=0
        for run_record in sorted(runs,key=lambda r:(r['scene'],r['index'])):
            run=Path(run_record['output'])
            for f in sorted((run/'repair_jobs').glob('transport_*.json')):
                j=read(f)
                if j['kind']!='R3':continue
                assert Path(j['snapshot_file']).is_file(),j['snapshot_file']
                cfg=copy.deepcopy(read(run/'scenario.json'))
                spawn=read(run/'dynamic/spawn.json') if (run/'dynamic/spawn.json').exists() else None
                active=spawn is not None and int(j['evaluation_tick'])>=spawn['tick']
                cfg['obstacles']=list(cfg.get('obstacles',[]))
                if active:cfg['obstacles'].append(spawn['obstacle'])
                c=dict(case_id=f'{phase}_{count:03d}',source=phase,run=str(run),scene=run_record['scene'],
                    index=run_record['index'],job_id=j['job_id'],source_job=str(f),
                    snapshot_file=j['snapshot_file'],tick=int(j['evaluation_tick']),B=j['B'],u_ref=j['u_ref'],
                    trigger=j.get('trigger'),oracle_config=cfg,spawn=spawn,group='sudden' if spawn else 'static',
                    appearance_available=active)
                c['input_stage']=input_stage(c) if spawn else 'STATIC'
                cases.append(c);count+=1
                for path in (f,run/'scenario.json',run/'dynamic/spawn.json'):
                    if path.is_file():sources[str(path)]=sha256_file(path)
        groups[phase]=count
    file=ROOT/'research/results/phase23o3/manifest.json';sources[str(file)]=sha256_file(file)
    extra=[c for c in read(file)['training'] if c['group']=='sudden' and input_stage(c)=='PRE_PASSAGE']
    assert len(extra)==16
    for old in extra:
        cases.append(dict(case_id='D3_'+old['case_id'],source='phase23o3_pre16',run=old['run'],scene=old['scene'],
            index=old['index'],job_id=None,source_job=None,snapshot_file=old['snapshot_file'],tick=old['tick'],
            B=old['B'],u_ref=old['baseline_u_ref'],u_ref_source=old['baseline_u_source'],trigger=old['trigger'],
            oracle_config=old['oracle_config'],spawn=old['spawn'],group='sudden',appearance_available=True,input_stage='PRE_PASSAGE'))
    groups['phase23o3_pre16']=len(extra)
    keys=[(c['run'],c['tick'],tuple(c['B'])) for c in cases]
    assert len(set(keys))==len(keys),'Duplicate event; do not silently reweight it'
    for c in cases:
        file=Path(c['snapshot_file']);assert file.is_file(),file
        if str(file) not in sources:sources[str(file)]=sha256_file(file)
        c['snapshot_sha256']=sources[str(file)]
    examples=[]
    for predicate in (lambda c:c['scene']=='L2A' and c['index']==111,
                      lambda c:c['scene']=='SLW',lambda c:c['source']=='phase23o3_pre16'):
        examples.append(next(c['case_id'] for c in cases if predicate(c) and c['case_id'] not in examples))
    return dict(cases=cases,counts=groups,examples=examples,input_sha256=sources,
                duplicate_events=0,selection='all saved R3 transports from registered source runs plus fixed pre16; examples selected before new solves')


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    assert not (OUT/'manifest.json').exists()
    m=build();(OUT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    print(json.dumps(dict(counts=m['counts'],total=len(m['cases']),examples=m['examples'])))
