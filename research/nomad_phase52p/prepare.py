import argparse,copy,json,os,re,shutil,subprocess
from pathlib import Path
from datetime import datetime,timezone
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,BASE_SCENES,INDICES,CONDITIONS,ORDER_SEED,registered_order,split,verify

def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def freeze():
    assert not RUN_ROOT.exists()
    from .metrics import extra
    old=json.loads((ROOT/'research/nomad_phase47c/protocol.json').read_text());p=copy.deepcopy(old);baseline=[];hashes={}
    for phase in ('phase47c','phase51p'):
        source=ROOT/f'research/results/{phase}/runs.json';hashes[str(source.relative_to(ROOT))]=sha256_file(source)
        for r in json.loads(source.read_text()):
            if r['index'] not in INDICES or r['method']!='OURS-DETOUR+HMM':continue
            assert r['technical_validation']=='PASS'
            x={k:v for k,v in r.items() if k not in ('attempts','node_errors')};x.update(extra(r['output']))
            x['historical_group']='Phase47_D075' if phase=='phase47c' else 'Phase51_'+r['condition'];x.setdefault('condition','D075');x.setdefault('base_scene',r['scene']);baseline.append(x)
            for name in ('summary.json','agent_trajectory.csv','repair.jsonl','phase20_commands.jsonl','model/inference.jsonl','events.jsonl','exec_cert.jsonl'):
                file=Path(r['output'])/name;hashes[str(file)]=sha256_file(file)
    assert len(baseline)==30;save(OUT/'preparation/baselines.json',baseline)
    p.update(phase='52-P',status='FROZEN',experiment='HANDOFF_PILOT',frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        methods=list(METHODS),indices=list(INDICES),main_order=registered_order(),smoke=dict(enabled=False),order_seed=ORDER_SEED,
        scenes={level:copy.deepcopy(old['scenes'][split(level)[0]]) for level in SCENES})
    for name in ('blocks','primary_tests','analysis'):p.pop(name,None)
    p['conditions']={'D075':.75,'D150':1.5}
    p['method_definitions']={
        'CUT-HOLD':'Frozen Phase47-C OURS-DETOUR+HMM:remove1s expiry;full-path KEEP if latest continuation EC passes,without0.25m remaining minimum',
        'GRAPH-REC':'Same immediate CUT-HOLD install/control;each arriving FRESH dispatches8 unfiltered NoMaD R2 reconstructions in4-process pool;only extra cost is old-path factor'}
    p['reconstruction']=dict(solver='Phase35 graph_pool R2 branch = nomad_phase20.repair.RepairGraphR2 + Phase19R.initialize',
        points=8,variables_xy=14,maxiter=100,ftol=1e-8,workers=4,prior_sigma_m=.10,smoothness_sigma_m=.02,heading_sigma_rad=3.141592653589793/6,
        safety_m=.025,maximum_abs_curvature_m_inv=8.,trust_region_m=.75,source_constraints_and_certificate='inherited unchanged,including NEGATIVE_DEPTH_AT_B and SHORT_REMAINING',
        old_factor='0.5 sum_i w_i ||p_i-old(s_i)||²;w=max(0,1-s_i/0.5);s_i fixed by this initialization cumulative arclength;no added sigma',
        old_scope='previous installation before immediate CUT replacement;project predicted B onto old path;use only available suffix up to0.5m;no extrapolated endpoint weight',
        b='Frozen Phase40-P schedule.predict(current CUT controller,state,command):apply_tick=ceil((dispatch_tick+54)/8)*8;dispatch after current tick control',
        apply='Only that tick;actual pose/current velocity/latest EC map;lowest objective among all R2-accepted and EC-passing candidates,tie sample index',
        superseded='Any newer FRESH before or at target tick discards old job. Late/missing/EC failure keeps CUT path;no Graph wait stop',
        recovery='Phase47 recovery unchanged;FRESH received during active recovery retains original deferred handling;Graph cannot replace during recovery',
        queue='One4-process broker,per-FRESH FIFO transport;late jobs logged/discarded without extra navigation attempts',
        map='Same latest base snapshot as EC at dispatch;latest map again at application;no strict R3 map,no oracle')
    p['shared_hold']=dict(waypoint_expiry=False,keep_remaining_minimum_m=None,periodic_ec_ticks=36,
        exhausted='Before STOP on unavailable/rejected fresh candidates,continue active follower only if latest continuation EC passes,including suffix shorter0.25m',
        terminal='Existing path endpoint,official declared arrival,run90s timeout and evaluation collision stops remain;RECOVER remains last resort',
        physical='Frozen C0-NA PP/SP,90degree rotation policy,v<=.3,w<=.4,a<=.5 unchanged')
    p['report_definitions']={
        'outcomes':'Phase47 official stop;success=declared arrival distance<=0.5m and no collision,wrong stop>0.5m;90s limit unchanged',
        'speed':'Success/timeout,arrival time(success pairs only),distance/duration mean speed,actual72Hz stop duration,command-state interval totals',
        'passage':'Frozen box passage and spawn-to-passage duration;H2 all-box status and per-box spawn observations. Oracle remains evaluation-only',
        'spawn_path':'Installation before spawn tick,with active follower command state;original chunk observation time compared to spawn,missing/cleared path=>NA',
        'tracking':'72Hz position cross-track to installed polyline only while NORMAL/KEEP/ALIGN/REPAIR/ENDPOINT follower states. p50/p95,count;recovery/no path excluded',
        'heading':'At each replacement pose:old/new projected suffix direction over next0.05m,wrapped absolute difference;p50/p95. Not physical heading jump',
        'raw_distance':'Mean72Hz position distance to the original selected NoMaD candidate of the currently installed path;EC alternative sample identity retained;missing/degenerate samples reported via count',
        'graph':'Actual applied/FRESH-dispatched rate,pool whole8-solve p50/p95,late/discard/replacement counts,prediction position+heading errors;all terminal/late results retained',
        'hold':'Explicit HOLD_REJECTED START/END,including recovery-independent original path continuation;total and longest episode until replacement/EC fail/endpoint',
        'historical':'Adjacent same scene/seed Phase47 D075,Phase51 L150 and Phase51 WIDE. Separate execution dates;WIDE different geometry,not pooled/matched causal evidence',
        'wide_analysis':'docs/PHASE51P_WIDE_ANALYSIS.md:214 inference-box events,1712 candidates,3 byte-identical saved RGB images;no new inference/render',
        'execution':'40 serial runs,one technical retry,storagev2/cache cleanup,disk30GB stop;preparation only,no simulation or smoke'}
    p['frozen_sources']={**old['frozen_sources'],**old['source_sha256']}
    for file in (ROOT/'research/nomad_phase40p/schedule.py',ROOT/'research/nomad_phase51p/runtime.py'):
        p['frozen_sources'][str(file.relative_to(ROOT))]=sha256_file(file)
    p['reference_hashes']={**old['reference_hashes'],**hashes,'research/nomad_phase47c/protocol.json':sha256_file(ROOT/'research/nomad_phase47c/protocol.json'),
        str((OUT/'preparation/baselines.json').relative_to(ROOT)):sha256_file(OUT/'preparation/baselines.json')}
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')};save(HERE/'protocol.json',p);verify()

def validate():
    p=verify();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase52p.test_phase52p','nomad_phase52p.test_wide','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-6000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase52p.campaign','--dry-run'],cwd=ROOT,env=env,text=True));assert dry['planned']==40 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_phase52p.launch,nomad_phase52p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    result=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=40,simulations_started=0,new_nomad_inferences=0,renders=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free);save(folder/'validation.json',result)
    from nomad_phase31p.report import table
    from .report import generate
    generate();prefix=f'cd {ROOT} && '
    command=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase52p.campaign > ../artifacts/isaac6/phase52p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase52p.campaign --status';save(folder/'commands.json',dict(campaign=command,status=status,executed=False))
    tables=[dict(item=k,value=v) for k,v in p['reconstruction'].items()]+[dict(item=k,value=v) for k,v in p['shared_hold'].items()]
    (ROOT/'docs/PHASE52P_PREP.md').write_text('# Phase52-P 준비\n\n'+table([dict(status='FROZEN_PREPARED_NOT_RUN',runs=40,methods='CUT-HOLD / GRAPH-REC',conditions='D075 / D150',seeds='221,222',scenes=','.join(BASE_SCENES))])+'\n\n'+table(tables)+'\n\n'+table([result])+'\n\n[Phase51-P WIDE 저장 후보 분석](PHASE51P_WIDE_ANALYSIS.md)\n\n진행 확인: `'+status+'`\n\n실행 명령(미실행):\n\n`'+command+'`\n')
    print(json.dumps(result))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
if __name__=='__main__':main()
