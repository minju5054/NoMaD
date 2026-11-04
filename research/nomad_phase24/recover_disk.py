"""One authorized disk-incident repair; never launches navigation or redoes results."""
import argparse,json,os,shutil,time,zipfile
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase0.s0_batch import exclusive_batch
from .storage import read,atomic_json,ensure_reserve,has_disk_error,capacity
from .campaign import jobs

COMPLETE=('L2_131_C0','L2_131_C1','L2_131_G','SLW_131_C0')
def snapshot_metadata(root,backup):
    backup.mkdir(parents=True,exist_ok=True)
    for f in [*root.glob('state*'),root/'plan.json',root/'journal.jsonl',*sorted((root/'metrics').glob('*.json'))]:
        if not f.is_file():continue
        rel=f.relative_to(root);to=backup/rel;to.parent.mkdir(parents=True,exist_ok=True)
        if not to.exists():shutil.copy2(f,to)

def repair(root):
    root=Path(root).resolve();folder=root/'recovery'/'disk_full_20261104';marker=folder/'recovery.json'
    if marker.exists() and read(marker).get('complete'):return read(marker)
    state=read(root/'state.json');plan=read(root/'plan.json');assert state['protocol']==plan['protocol']
    if state.get('pid'):
        path=Path(f"/proc/{state['pid']}/stat")
        assert not path.exists() or path.read_text().split()[21]!=state.get('process_token'),'Campaign still running'
    snapshot_metadata(root,folder/'original_metadata');ensure_reserve(root)
    from .online_metrics import audit
    integrity=[];preserved={}
    for key in COMPLETE:
        run=root/'main'/key;metric=root/'metrics'/(key+'.json');stored=read(metric);assert stored['technical_validation']=='PASS'
        assert read(run/'launch_complete.json')['exit_code']==0
        checked=audit(run)
        for field in ('classification','success','collision','corridor','goal_time_s','distance_m','seed_offset','command_pose_error_m'):assert checked[field]==stored[field],(key,field)
        for f in (metric,run/'summary.json',run/'launch_complete.json',run/'provenance.json'):
            preserved[str(f)]=sha256_file(f)
        integrity.append(dict(key=key,summary_valid=True,metric_matches_reaudit=True,command_pose_error_m=checked['command_pose_error_m']))
    retries=[]
    for key,reason in [('SLW_131_C1','DISK_FULL_TECHNICAL_FAILURE'),('SLW_131_G','DISK_FULL_STARTUP_NO_RUN')]:
        archive=root/'attempts'/key/'disk_full_attempt_01';dest=root/'main'/key;metric=root/'metrics'/(key+'.json');log=root/'logs'/(key+'.log')
        if not (archive/'run').exists():
            if key.endswith('C1'):assert has_disk_error(dest,log),'No disk-full evidence'
            else:assert not (dest/'requests.jsonl').exists() and not (dest/'agent_trajectory.csv').exists(),'G was more than an unstarted attempt'
            assert not (dest/'summary.json').exists() and not (dest/'launch_complete.json').exists()
            archive.mkdir(parents=True,exist_ok=True);os.rename(dest,archive/'run')
        if metric.exists():os.rename(metric,archive/'metric.json')
        if log.exists():os.rename(log,archive/'launcher.log')
        entry=dict(key=key,reason=reason,classification='TECHNICAL_FAILURE' if key.endswith('C1') else 'NOT_STARTED',seed_index=131,seed_offset=1310000,
            preserved_attempt=str(archive),rerun_authorization='User explicitly requested disk recovery and same-seed retry; no outcome-based retry',max_additional_attempts=1)
        atomic_json(archive/'incident.json',entry);retries.append(entry);state['jobs'].pop(key,None)
    if (root/'state.tmp').exists():os.rename(root/'state.tmp',folder/'interrupted_state.tmp')
    for f,h in preserved.items():assert sha256_file(f)==h,f
    state.update(status='READY_TO_RESUME',pid=None,current=None,disk_recovery=str(marker),authorized_disk_retries=retries)
    atomic_json(root/'state.json',state,backup=True)
    estimate=capacity(root,jobs(root));atomic_json(root/'capacity.json',estimate)
    result=dict(complete=True,restored_ns=time.time_ns(),state_json_was_valid=True,empty_tmp_preserved=True,integrity=integrity,preserved_sha256=preserved,retries=retries,
        completed_runs_preserved=4,remaining_runs=20,capacity=estimate,new_navigation_started=0)
    atomic_json(marker,result)
    out=ROOT/'research/results/phase24_online/disk_recovery.json';atomic_json(out,result)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);a=ap.parse_args()
    with exclusive_batch():r=repair(a.run_root)
    print(json.dumps(dict(completed_preserved=r['completed_runs_preserved'],pending=r['remaining_runs'],enough_space=r['capacity']['enough'],new_navigation_started=0)))
if __name__=='__main__':main()
