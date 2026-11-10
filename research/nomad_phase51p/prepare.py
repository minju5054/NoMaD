"""Dry-run registration only: no simulation, model inference or renders."""
import argparse,copy,json,os,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,BASE_SCENES,INDICES,CONDITIONS,ORDER_SEED,registered_order,split,verify

def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def freeze():
    assert not RUN_ROOT.exists()
    from nomad_phase47c.config import runtime_config as old_config
    from .geometry import spec
    from .metrics import saved_times
    old=json.loads((ROOT/'research/nomad_phase47c/protocol.json').read_text());p=copy.deepcopy(old)
    source=ROOT/'research/results/phase47c/runs.json';baseline=[r for r in json.loads(source.read_text()) if r['method']==METHODS[0] and r['index'] in INDICES]
    assert len(baseline)==10 and all(r['technical_validation']=='PASS' for r in baseline)
    hashes={str(source.relative_to(ROOT)):sha256_file(source)};reused=[]
    for r in baseline:
        root=Path(r['output']);record={k:v for k,v in r.items() if k!='attempts'};record.update(saved_times(root,r['duration_s']));reused.append(record)
        for name in ('agent_trajectory.csv','exec_cert.jsonl','summary.json'):
            f=root/name;hashes[str(f)]=sha256_file(f)
    save(OUT/'preparation/baselines.json',reused)
    p.update(phase='51-P',status='FROZEN',experiment='ENVIRONMENT_STRESS_PILOT',frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        methods=list(METHODS),indices=list(INDICES),main_order=registered_order(),smoke=dict(enabled=False),order_seed=ORDER_SEED,
        scenes={level:copy.deepcopy(old['scenes'][split(level)[0]]) for level in SCENES},
        wide={s:spec(old_config(METHODS[0],221,90,s)) for s in BASE_SCENES})
    for name in ('blocks','primary_tests','analysis'):p.pop(name,None)
    p['conditions']={'L150':dict(additional_delivery_delay_s=1.5,all_geometry='Phase47 same seed incl jitter'),
        'WIDE':dict(additional_delivery_delay_s=.75,lateral_jitter_m=0,center='Static free corridor cross-section midpoint',requested_width_multiplier=1.5,minimum_side_gap_m=.33)}
    p['method_definitions']={METHODS[0]:'Phase47-C OURS-DETOUR+HMM frozen;NO graph/R2/R3,SAFE+EC+RECOVER,C0-NA PP/SP,HMM,official declared stop'}
    p['report_definitions']={
        'success':'Phase47 success: declared arrival at distance<=0.5m AND no collision;wrong arrival>0.5m;timeout without declaration unchanged',
        'delay':'Same post-inference IPC hold as D750: packet received -> release,changed only to1.5s in L150;actual network inference time is additional,not normalized',
        'WIDE':'Only sudden-box lateral width and center/jitter change. Thickness/height/trigger/forward-surface offset frozen;H2 both boxes centered. SLW/LC have no sudden boxes and are unchanged',
        'passage':'At least one full geometric side gap>=0.33m;inside corridor/no static overlap. H1 inner-corner wall included;maximum multiplier<=1.5 frozen before runs',
        'stop_time':'Saved72Hz actual |v|<0.01,integrated by interval;includes first inference wait,recovery/alignment and other stops',
        'EC_all_rejected':'Logged NORMAL_NO_EC_SAFE_CANDIDATE => no available path survives frozen full-speed then0.1m/s fallback;duration held from that decision to next EC PASS INSTALL or run end,merged across repeated rejects',
        'EC_scope':'Available install candidates,not necessarily all8 NoMaD samples (depth-unsafe samples were already filtered). Held last-decision state,not continuous new validation;recovery time included;no runtime change',
        'EC_report':'Per-run total held duration and longest continuous interval;physical-stop intersection also saved. Same reconstruction on historical Phase47 logs',
        'comparison':'Same scene/seed Phase47-C OURS-DETOUR+HMM adjacent columns;different execution day,no claim of isolated random effect;missing/new technical failures not zero-filled',
        'summary':'Counts for outcomes;medians for arrival time(successes only),stop and EC durations;per-run values also reported',
        'execution':'Preparation only,dry-run20,zero simulation/render/inference;main serial/one technical retry/storagev2/cache cleanup/disk30GB stop,automatic report+commit+push'}
    p['frozen_sources']={**old['frozen_sources'],**old['source_sha256']};p['reference_hashes']={**old['reference_hashes'],**hashes,
        'research/nomad_phase47c/protocol.json':sha256_file(ROOT/'research/nomad_phase47c/protocol.json'),
        str((OUT/'preparation/baselines.json').relative_to(ROOT)):sha256_file(OUT/'preparation/baselines.json')}
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')}
    save(HERE/'protocol.json',p);verify()

def validate():
    p=verify();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase51p.test_phase51p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-5000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase51p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==20 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_phase51p.launch,nomad_phase51p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    result=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=20,simulations_started=0,renders=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',result)
    from nomad_phase31p.report import table
    from .report import generate
    generate()
    prefix=f'cd {ROOT} && '
    command=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase51p.campaign > ../artifacts/isaac6/phase51p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase51p.campaign --status'
    save(folder/'commands.json',dict(campaign=command,status=status,executed=False))
    definitions=[dict(item=k,value=v) for k,v in p['report_definitions'].items()]
    (ROOT/'docs/PHASE51P_PREP.md').write_text('# Phase51-P 준비\n\n'+table([dict(status='FROZEN_PREPARED_NOT_RUN',method=METHODS[0],conditions='L150/WIDE',scenes=','.join(BASE_SCENES),seeds='221,222',runs=20)])+'\n\n'+table(list(p['wide'].values()))+'\n\n'+table(definitions)+'\n\n'+table([result])+'\n\n진행 확인: `'+status+'`\n\n실행 명령(미실행):\n\n`'+command+'`\n')
    print(json.dumps(result))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()

if __name__=='__main__':main()
