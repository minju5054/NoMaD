"""Audit-only recovery of first attempts; never launches a run or chooses by outcome."""
import argparse,json,shutil
from datetime import datetime,timezone
from pathlib import Path
from nomad_isaac.common import sha256_file
from nomad_phase26.storage import atomic_json
from nomad_phase0.s0_batch import exclusive_batch
from .config import ROOT,HERE,OUT,RUN_ROOT,protocol,verify

REVISION='STARTUP_MISSING_AUDIT_V1'
ORIGINAL_PROTOCOL='57838e8042c9d156c728313a61432c2e3eccb000530f20ef654b2045978a57c4'
OVERRIDES=('config.py','metrics.py','campaign.py','report.py')
ADDED=('resume.py','test_resume.py')
REASON='REDUNDANT_RETRY_AFTER_STARTUP_AUDIT_DEFECT; user selects completed attempt1 regardless of navigation outcome'

def read(path,default=None):return json.loads(Path(path).read_text()) if Path(path).exists() else default

def planned(root):
    from nomad_phase26.campaign import jobs
    from types import FunctionType
    return FunctionType(jobs.__code__,dict(jobs.__globals__,protocol=protocol),jobs.__name__)(Path(root),False)

def revision():return read(HERE/'audit_revision.json')
def backup_root(root):return Path(root)/'audit_recovery'/REVISION/'before'

def original_record(root,key,attempt):
    relative=Path('attempt_metrics')/f'{key}_{attempt}.json'
    saved=backup_root(root)/relative
    return read(saved) if saved.exists() else read(Path(root)/relative)

def eligible(job,root):
    dest=Path(job['outputs'][0]);record=original_record(root,job['key'],1)
    complete=read(dest/'launch_complete.json',{})
    return bool(record and record.get('attempt')==1 and record.get('exit_code')==0
        and record.get('technical_validation')=='FAIL' and record.get('error')=='AssertionError()'
        and complete.get('exit_code')==0 and (dest/'summary.json').is_file() and not (dest/'FAILED.json').exists())

def register_revision():
    assert sha256_file(HERE/'protocol.json')==ORIGINAL_PROTOCOL,'Never refreeze the running experiment'
    existing=revision();plan=planned(RUN_ROOT)
    keys=[j['key'] for j in plan if eligible(j,RUN_ROOT)]
    assert keys,'No eligible audit-only recovery inputs'
    if existing:assert keys==existing['required_attempt1_keys'],'Recovery scope changed; inspect before any writes'
    value=dict(revision=REVISION,registered_at_utc=(existing or {}).get('registered_at_utc',datetime.now(timezone.utc).isoformat()),
        base_protocol_sha256=ORIGINAL_PROTOCOL,original_commit='bfe19d0',required_attempt1_keys=keys,
        authorization='User: restore all completed exit0 attempt1 with only this audit defect,including discovered seventh H1 GRAPH-REC;exclude all attempt2 regardless of outcomes',
        scope='Only audit/reporting/resume guard/source verification;method,solver,controller,scenario,seed,order,protocol unchanged',
        audit='Pre-first-chunk missing source WAYPOINT_TIMEOUT allowed;new_timeout anywhere or WAYPOINT_TIMEOUT after first chunk still fails',
        overridden_source_sha256={str((HERE/f).relative_to(ROOT)):sha256_file(HERE/f) for f in OVERRIDES},
        added_source_sha256={str((HERE/f).relative_to(ROOT)):sha256_file(HERE/f) for f in ADDED})
    atomic_json(HERE/'audit_revision.json',value);verify();return value

def raw_inventory(plan):
    result={}
    for job in plan:
        for output in job['outputs']:
            directory=Path(output)
            if not directory.exists():continue
            for f in sorted(directory.rglob('*')):
                if f.is_file():
                    st=f.stat();result[str(f)]=[st.st_size,st.st_mtime_ns]
    return result

def raw_hashes(plan):
    result={}
    names=('summary.json','scenario.json','launch_complete.json','controller.jsonl','received.jsonl',
           'agent_trajectory.csv','events.jsonl','repair.jsonl','reconstruction.jsonl','model/inference.jsonl','exec_cert.jsonl')
    for job in plan:
        for output in job['outputs']:
            for name in names:
                f=Path(output)/name
                if f.exists():result[str(f)]=sha256_file(f)
    return result

def backup(root,relative):
    source=Path(root)/relative;dest=backup_root(root)/relative
    if source.exists() and not dest.exists():
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        assert sha256_file(source)==sha256_file(dest)
    return str(dest) if dest.exists() else None

def repair(root=RUN_ROOT,audit_fn=None):
    root=Path(root);verify();rev=revision();plan=planned(root);keys=rev['required_attempt1_keys']
    targets=[j for j in plan if j['key'] in keys];assert [j['key'] for j in targets]==keys
    assert all(eligible(j,root) for j in targets),'Not solely the registered startup audit error'
    before=raw_inventory(targets);inputs=raw_hashes(targets)
    if audit_fn is None:
        from .metrics import audit as audit_fn
    verified=[]
    # Complete all audits before changing even one final metric. No success,
    # collision, path length or other outcome is involved in eligibility.
    for j in targets:
        result=audit_fn(Path(j['outputs'][0]));assert result['technical_validation']=='PASS',j['key']
        verified.append((j,result))
    assert raw_inventory(targets)==before and raw_hashes(targets)==inputs,'Saved run changed while auditing; stop'
    backup(root,Path('state.json'));manifest=[]
    for j,result in verified:
        key=j['key'];a1=Path('attempt_metrics')/f'{key}_1.json';a2=Path('attempt_metrics')/f'{key}_2.json';final=Path('metrics')/f'{key}.json'
        snapshots={str(p):backup(root,p) for p in (a1,a2,final)}
        recovered=dict(j,attempt=1,exit_code=0);recovered.update(result)
        recovered.update(output=j['outputs'][0],included_in_analysis=True,selected_attempt=1,audit_revision=REVISION,
            audit_recovery=dict(reason='STARTUP_MISSING_IS_NOT_EXPIRY',original_error='AssertionError()',original_record=snapshots[str(a1)]))
        attempts=[recovered];excluded=None
        if Path(j['outputs'][1]).exists() or (root/a2).exists():
            old=original_record(root,key,2)
            excluded=dict(old or dict(j,attempt=2,output=j['outputs'][1],exit_code=None),
                included_in_analysis=False,selected_for_analysis=False,exclusion_reason=REASON,audit_revision=REVISION,
                navigation_reaudited=False,raw_output_preserved=True)
            # Preserve the original technical verdict, even though it was
            # produced by the defective audit. An interrupted attempt2 with
            # no prior metric receives no invented outcome.
            if old is None:excluded.update(technical_validation='NOT_AUDITED',classification='EXCLUDED_INTERRUPTED_ATTEMPT',
                launch_complete=(Path(j['outputs'][1])/'launch_complete.json').exists())
            atomic_json(root/a2,excluded);attempts.append(excluded)
        atomic_json(root/a1,recovered)
        selected=dict(recovered,attempt_count=len(attempts),analysis_attempt_count=1,attempts=attempts,
            selection_reason='First completed attempt; corrected startup audit;attempt2 excluded without outcome review')
        atomic_json(root/final,selected)
        manifest.append(dict(key=key,attempt=1,output=j['outputs'][0],technical_validation='PASS',
            reason='exit0 + complete summary + original startup-only audit AssertionError; corrected audit PASS',
            initial_wait_s=result['initial_wait_s'],first_chunk_received_s=result['first_chunk_received_s'],
            startup_missing_timeout_rows=result['startup_missing_timeout_rows'],post_chunk_waypoint_timeout_rows=result['post_chunk_waypoint_timeout_rows'],
            new_timeout_count=result['new_timeout_count'],excluded_attempt2=excluded['output'] if excluded else None,excluded_reason=REASON if excluded else None,
            previous_metric_backups=snapshots))
    assert raw_inventory(targets)==before and raw_hashes(targets)==inputs
    remaining=[j['key'] for j in plan if not (root/'metrics'/f"{j['key']}.json").exists()]
    info=dict(revision=REVISION,status='PASS',recovered=len(manifest),items=manifest,remaining=len(remaining),next_key=remaining[0] if remaining else None,
        simulations_started=0,attempt2_used=0,raw_files_unchanged=len(before),input_sha256=inputs,
        protocol_sha256=sha256_file(HERE/'protocol.json'),audit_revision_sha256=sha256_file(HERE/'audit_revision.json'))
    atomic_json(root/'audit_recovery'/REVISION/'manifest.json',info);atomic_json(OUT/'audit_fix/recovery.json',info)
    state=read(root/'state.json',{});previous_error=state.pop('error',None)
    state.update(status='AUDIT_REPAIRED_READY_TO_RESUME',pid=None,current=None,
        audit_recovery=dict(revision=REVISION,recovered_keys=keys,remaining=len(remaining),previous_interrupt_error=previous_error))
    atomic_json(root/'state.json',state)
    return info

def audit_gate(root=RUN_ROOT,audit_fn=None):
    root=Path(root);verify();rev=revision();plan=planned(root);targets=[j for j in plan if j['key'] in rev['required_attempt1_keys']]
    if audit_fn is None:
        from .metrics import audit as audit_fn
    before=raw_inventory(targets);checked=[]
    try:
        assert len(targets)==len(rev['required_attempt1_keys'])
        for j in targets:
            chosen=read(root/'metrics'/f"{j['key']}.json",{})
            assert chosen.get('technical_validation')=='PASS' and chosen.get('attempt')==1 and chosen.get('selected_attempt')==1,j['key']
            assert chosen.get('output')==j['outputs'][0] and chosen.get('audit_revision')==REVISION,j['key']
            assert eligible(j,root),j['key']
            again=audit_fn(Path(j['outputs'][0]));assert again['technical_validation']=='PASS',j['key']
            for key in ('initial_wait_s','startup_missing_timeout_rows','new_timeout_count','post_chunk_waypoint_timeout_rows'):
                assert again[key]==chosen[key],(j['key'],key)
            excluded=read(root/'attempt_metrics'/f"{j['key']}_2.json",{})
            if Path(j['outputs'][1]).exists():assert excluded.get('included_in_analysis') is False and excluded.get('exclusion_reason')==REASON
            checked.append(j['key'])
        assert raw_inventory(targets)==before
        result=dict(status='PASS',revision=REVISION,checked=checked,checked_count=len(checked),simulations_started=0,
            checked_at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha256_file(HERE/'protocol.json'))
        atomic_json(root/'audit_gate.json',result);print(f'[audit] saved attempt1 {len(checked)}/{len(targets)} PASS; no smoke/navigation',flush=True);return result
    except BaseException as exc:
        atomic_json(root/'audit_gate.json',dict(status='FAIL',revision=REVISION,checked=checked,error=repr(exc),simulations_started=0))
        state=read(root/'state.json',{});state.update(status='AUDIT_GATE_FAILED',pid=None,current=None,error=repr(exc));atomic_json(root/'state.json',state)
        raise

def main():
    ap=argparse.ArgumentParser();group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--register-revision',action='store_true');group.add_argument('--repair',action='store_true');group.add_argument('--audit-only',action='store_true');a=ap.parse_args()
    with exclusive_batch():
        if a.register_revision:r=register_revision();print(json.dumps(dict(revision=r['revision'],eligible=len(r['required_attempt1_keys']))))
        elif a.repair:
            r=repair();print(json.dumps({k:r[k] for k in ('status','recovered','remaining','next_key','simulations_started')}))
        else:audit_gate()
if __name__=='__main__':main()
