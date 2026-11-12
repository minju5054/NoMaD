"""After exit only: preserve RTC failures, re-audit completed blocks, publish."""
import argparse
import json
import os
import time
from datetime import datetime,timezone
from pathlib import Path
from nomad_isaac.common import sha256_file
from nomad_phase26.storage import atomic_json
from .config import ROOT,HERE,OUT,RUN_ROOT,verify
from .statistics import completed_seeds
from .validation_revision import REVISION
from .postprocess_guard import ORIGINAL,assert_stopped,locked

def metric_hashes(root,non_rtc=False):
    result={}
    for f in sorted((Path(root)/'metrics').glob('*.json')):
        r=json.loads(f.read_text())
        if non_rtc and r['method']=='RTC-hard':continue
        result[str(f)]=sha256_file(f)
    return result

def process(root,publish=True):
    from .metrics import audit
    root=Path(root);verify();out=OUT;out.mkdir(parents=True,exist_ok=True)
    files=sorted((root/'metrics').glob('*.json'));allrows=[json.loads(f.read_text()) for f in files];seeds=completed_seeds(allrows)
    assert seeds,'No completed seed blocks'
    before_other=metric_hashes(root,True);attempt_before={str(f):sha256_file(f) for f in (root/'attempt_metrics').glob('*.json')}
    protocol_hash=sha256_file(HERE/'protocol.json');p=verify()
    # Strictly check every method/executor/statistics file against the original
    # frozen protocol; only the separate evaluation/report overlay may differ.
    untouched={f:h for f,h in p['source_sha256'].items() if f not in __import__('nomad_j1.validation_revision',fromlist=['ALLOWED']).ALLOWED}
    assert all(sha256_file(ROOT/f)==h for f,h in untouched.items())
    archive=root/'audit_revisions'/REVISION/'original_metrics';archive.mkdir(parents=True,exist_ok=True)
    entries=[];failures=[]
    for file,old in zip(files,allrows):
        if old['method']!='RTC-hard' or old['index'] not in seeds:continue
        backup=archive/file.name
        if old.get('audit_revision',{}).get('revision')==REVISION:
            assert backup.exists() and sha256_file(backup)==old['audit_revision']['original_sha256']
            entries.append(dict(key=old['key'],original_sha256=sha256_file(backup),revised_sha256=sha256_file(file),
                                technical_validation=old['technical_validation'],reused=True));continue
        raw=file.read_bytes();old_hash=sha256_file(file)
        if backup.exists():assert backup.read_bytes()==raw,'Original archive mismatch; stop without replacement'
        else:
            with backup.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        run=Path(old['output']);new=dict(old)
        try:
            assert (run/'launch_complete.json').exists() and json.loads((run/'launch_complete.json').read_text())['exit_code']==0
            assert (run/'summary.json').exists(),'Saved run incomplete; no re-execution allowed'
            new=audit(run)
            for k in ('scene','index','method','delay','key','output','attempt'):
                if k in old:new[k]=old[k]
            new['audit_revision']=dict(revision=REVISION,original_sha256=old_hash,original_classification=old['classification'],
                original_technical_validation=old['technical_validation'],original_error=old.get('error'),
                timestamp_utc=datetime.now(timezone.utc).isoformat(),simulation_rerun=False,protocol_sha256=protocol_hash)
            atomic_json(file,new)
        except Exception as e:
            failures.append(dict(key=old['key'],error=repr(e),action='original canonical metric retained'))
        entries.append(dict(key=old['key'],original_sha256=old_hash,revised_sha256=sha256_file(file),technical_validation=new.get('technical_validation'),reused=False))
        print(json.dumps(dict(event='RTC_REAUDIT',key=old['key'],technical_validation=new.get('technical_validation'))),flush=True)
    after_other=metric_hashes(root,True);assert before_other==after_other,'Non-RTC metrics changed'
    assert attempt_before=={str(f):sha256_file(f) for f in (root/'attempt_metrics').glob('*.json')},'Original attempt metrics changed'
    assert sha256_file(HERE/'protocol.json')==protocol_hash
    state_file=root/'state.json';state=json.loads(state_file.read_text()) if state_file.exists() else {}
    historical=dict(state_before_postprocess=state,report_log_exists=(root/'report.log').exists(),
        note='At initial request campaign was still before5.5h inside seed239; absent report then was not evidence of failure. This snapshot is captured only after exit.')
    for name in ('report.log','../j1_01.log'):
        f=root/name
        if f.exists():
            with f.open('rb') as stream:
                stream.seek(max(0,f.stat().st_size-12000));historical[name]=stream.read().decode(errors='replace')
    historical['assessment']='REPORT_ALREADY_COMPLETED' if state.get('stage')=='DONE' else 'REPORT_NOT_COMPLETED_SEE_PRESERVED_EXIT_LOG'
    atomic_json(out/'report_exit_diagnosis.json',historical)
    result=dict(revision=REVISION,completed_seeds=seeds,rtc_reassessed=len(entries),rtc_pass=sum(e['technical_validation']=='PASS' for e in entries),
        non_rtc_unchanged=True,non_rtc_files=len(before_other),non_rtc_before=before_other,non_rtc_after=after_other,
        attempt_metrics_unchanged=True,protocol_unchanged=True,protocol_sha256=protocol_hash,
        runtime_source_hashes_unchanged=untouched,archive_directory=str(archive),entries=entries,failures=failures,
        simulations_started=0,solver_runs=0)
    atomic_json(out/'reassessment.json',result)
    if failures:raise RuntimeError(f'{len(failures)} RTC re-audits failed; details preserved; no simulation was run')
    from .report import generate,publish_report
    doc=generate(root)
    if publish:publish_report(doc)
    if state:
        state.update(stage='DONE',report_status='PUBLISHED' if publish else 'GENERATED',report_validation_revision=REVISION)
        state.pop('report_error',None);atomic_json(state_file,state)
    print(json.dumps(dict(completed_seeds=seeds,RTC_PASS=f"{result['rtc_pass']}/{len(entries)}",non_RTC_unchanged=True,published=publish)),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    assert ROOT==ORIGINAL,'Apply and process only in original repository after campaign exit'
    assert_stopped()
    with locked(a.run_root):process(a.run_root,a.publish)

if __name__=='__main__':main()
