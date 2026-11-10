"""Offline tests and protocol registration only. Never launch Kit/NoMaD."""
import argparse,copy,json,os,re,shutil,subprocess
from datetime import datetime,timezone
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,RANDOM_SEED,condition,registered_order,verify
from nomad_isaac.common import sha256_file

def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def freeze():
    assert not RUN_ROOT.exists(),'No refreeze after campaign begins'
    from nomad_phase47c.config import runtime_config
    from .motion import placement,geometry_check
    frozen=json.loads((ROOT/'research/nomad_phase47c/protocol.json').read_text());p=copy.deepcopy(frozen)
    p.update(phase='50-P',status='FROZEN',experiment='DESCRIPTIVE_PILOT',frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        methods=list(METHODS),indices=list(INDICES),main_order=registered_order(),order_seed=RANDOM_SEED,smoke=dict(enabled=False),
        scenes={level:copy.deepcopy(frozen['scenes'][condition(level)[0]]) for level in SCENES},placements={})
    checks=[]
    for index in INDICES:
        for scene in ('H1','L2'):
            c=runtime_config(METHODS[0],index,90,scene);spec=placement(c,index);check=geometry_check(c,spec);assert check['passed']
            p['placements'][f'{scene}_{index}']=spec;checks.append(dict(scene=scene,index=index,**check))
    for name in ('blocks','primary_tests','analysis'):p.pop(name,None)
    p['method_definitions']={METHODS[0]:'Unmodified Phase47-C OURS-DETOUR+HMM, D750, C0-NA PP/SP, SAFE/EC/RECOVER, Phase43 HMM, declared-arrival stop'}
    p['scenario_change']=dict(shape='vertical cylinder',diameter_m=.4,height_m=1.7,speeds_m_s=[.5,1.],
        crossing={'L2':'x=3.5,perpendicular to straight reference','H1':'y=2.7,across corner-exit corridor'},
        spawn='First 72Hz tick at reference-projected remaining arclength <= Uniform(1.5,2.5)m; distance fixed per scene/seed',
        lateral='Start center inset0.35m + Uniform(-0.1,0.1)m from chosen wall; odd seed low->high,even high->low; same draw both speeds',
        endpoint='Opposite wall center inset0.25m => cylinder surface gap0.05m; remove at exact crossing duration,one crossing,no reappearance',
        removal_log='Exact simulation time and person pose;robot pose interpolated by frozen integrate_se2 within containing72Hz tick;center and footprint distances',
        no_static_changes=True,no_topomap_regeneration=True,no_method_changes=True,no_dynamic_velocity_to_controller=True,
        person_color=[.65,.04,.65],renderer='Frozen Phase26 static renderer + UsdGeom.Cylinder,linear time-sampled position',
        collision='Continuous relative moving circle vs frozen robot unicycle arc;chord/sagitta certified bounds and contact-stop convention',
        post_removal='Frozen depth update only;no deletion/mask/oracle clearing;passive snapshot observation at72Hz deduplicated by published frame_id')
    p['measurement_definitions']={
        'success':'Declared arrival with actual distance<=0.5m AND no person/static/wall collision;Phase47 stop unchanged',
        'distance':'Report robot-person center distance and surface clearance=center distance-0.09-0.20;only while person exists;N/A if not spawned',
        'collision':'Frozen static/wall evaluation,plus certified relative-motion circle sweep at72Hz;conservative contact stops distinguished from witnessed overlap',
        'stop_s':'Time-weighted actual |v|<0.01m/s;full run and person-present interval',
        'slow_s':'Time-weighted actual 0.01<=v<0.3m/s;separately decreasing-v duration and EC0.1 cap duration;not a causal attribution',
        'EC':'All EC records in [first contact-2s,first contact],including CHECK result and periodic application;no invented record if no check',
        'removal':'One crossing;surface within0.05m of opposite wall,then hidden and removed from collision monitor;exact removal time/position/robot distance',
        'ghosts':'Per retained live publication after removal through+5s: occupied cells intersecting removed disk and swept capsule;also exclude pre-spawn occupied baseline;no map writes',
        'ghost_time':'Bin by depth capture simulation time;log sampling and publication times. If run ends early or no map is available,report coverage/missing,never zero-fill',
        'ghost_attribution':'Geometric residual-occupancy counts,not semantic proof of person cells;noise/mapping remain frozen',
        'scope':'12 descriptive runs;no hypothesis gate,smoke,simulation,inference or render during preparation;static geometry/materials and reference hashes frozen'}
    p['frozen_sources']={**frozen['frozen_sources'],**frozen['source_sha256']}
    p['reference_hashes']={**frozen['reference_hashes'],'research/nomad_phase47c/protocol.json':sha256_file(ROOT/'research/nomad_phase47c/protocol.json')}
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')}
    save(HERE/'protocol.json',p);verify();save(OUT/'preparation/geometry.json',checks)

def validate():
    p=verify();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase50p.test_phase50p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-5000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase50p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==12 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_phase50p.launch,nomad_phase50p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    result=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=12,simulations_started=0,
        renders=0,protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',result)
    prefix=f'cd {ROOT} && '
    command=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase50p.campaign > ../artifacts/isaac6/phase50p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase50p.campaign --status'
    save(folder/'commands.json',dict(campaign=command,status=status,executed=False))
    from nomad_phase31p.report import table
    from .report import generate
    generate()  # Empty tables, never fabricated run results.
    defs=[dict(item=k,value=v) for k,v in p['scenario_change'].items()]
    (ROOT/'docs/PHASE50P_PREP.md').write_text('\n\n'.join(table(x) for x in ([dict(phase='50-P',runs=12,method=METHODS[0],scenes='H1,L2',speeds='.5,1.0',seeds='221,222,223',status='PREPARED_NOT_RUN')],defs,
        json.loads((folder/'geometry.json').read_text()),[result],[dict(campaign=command,status=status)]))+'\n')
    print(json.dumps(result))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()

if __name__=='__main__':main()
