"""Registration and dry-run only; smoke is an explicit separate operation."""
import argparse,copy,json,os,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
from nomad_isaac.common import sha256_file
from nomad_phase31p.report import table
from .config import ROOT,HERE,OUT,RUN_ROOT,SMOKE_ROOT,METHODS,SCENES,BASE_SCENES,INDICES,CONDITIONS,ORDER_SEED,registered_order,split,verify

def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def freeze():
    assert not RUN_ROOT.exists()
    old=json.loads((ROOT/'research/nomad_phase47c/protocol.json').read_text());p=copy.deepcopy(old)
    baselines=[];hashes={}
    # Reuse existing published summaries only. No re-audit, old logs, numerical
    # replay or solver input is read during this preparation.
    source=ROOT/'research/results/phase52p/preparation/baselines.json'
    existing=json.loads(source.read_text());hashes[str(source.relative_to(ROOT))]=sha256_file(source)
    for r in existing:
        b={k:v for k,v in r.items() if k not in ('attempts','node_errors','ec_exhausted_intervals')}
        b['base_scene']=b.get('base_scene',b['scene']);baselines.append(b)
    source=ROOT/'research/results/phase52p/runs.json';hashes[str(source.relative_to(ROOT))]=sha256_file(source)
    for r in json.loads(source.read_text()):
        b={k:v for k,v in r.items() if k not in ('attempts','node_errors','ec_exhausted_intervals')}
        b['base_scene']=b.get('base_scene',split(b['scene'])[0]);b['historical_group']='Phase52_'+b['condition'];baselines.append(b)
    for b in baselines:
        b['heading_discontinuity_p50_deg']=b.get('chunk_heading_jump_p50_deg');b['heading_discontinuity_p95_deg']=b.get('chunk_heading_jump_p95_deg')
        b['align_rotate_s']=b.get('command_state_seconds',{}).get('ALIGN_ROTATE');b['graph_adoption_rate']=b.get('graph_acceptance_rate')
    save(OUT/'preparation/baselines.json',baselines)
    p.update(phase='53-P',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),methods=list(METHODS),indices=list(INDICES),
        main_order=registered_order(),order_seed=ORDER_SEED,scenes={s:copy.deepcopy(old['scenes'][split(s)[0]]) for s in SCENES},
        smoke=dict(enabled=True,maximum_attempts=1,scene='LC_D075',method='GRAPH-HO',index=95,timeout_s=90,
            reason='Shortest reference length5.69336m (tie H1); LC excludes dynamic obstruction; audit only;main excluded'),
        conditions=dict(D075=.75,D150=1.5))
    for k in ('blocks','primary_tests','analysis'):p.pop(k,None)
    p['method_definitions']={'CUT':'Phase47 OURS-DETOUR+HMM native FRESHEST-SAFE handoff; original1s expiry; only common EC tail changed',
        'GRAPH-HO':'Same CUT EC selection and fallback; final chunk installation synchronously reconstructs selected native8-waypoint path with unmodified Phase17/18 ClearanceGraph; current actual pose and actual command; accept only solver feasible/certificate AND tail EC;otherwise identical CUT path'}
    p['report_definitions']={
        'frozen':'Phase47 HMM/official declared arrival,geometry/jitter/controller/SAFE/filter/RECOVER; no R2/R3;original1s receipt-age expiry. No Phase52 HOLD or predictedB dispatch.',
        'tail':'At earlier path endpoint/2s request frozen stop_command until v=0 at72Hz;omega also frozen stop_command. Swept depth footprint>=.025. Periodic continuation respects original9Hz phase (36tick checks).',
        'graph':'Direct nomad_phase17.graph.ClearanceGraph (Phase18 same implementation), native8SE2poses/24variables, SLSQP maxiter100 ftol1e-8 analytic Jacobians; no factor/weight/option changes;previous prior last actually installed acceptedGraph; no new init or resampling.',
        'heading_curvature':'Start heading SOFT sigma10deg at interpolated entry E; boundary position sigma.01m. Hard boundary tangent-circle curvature kappa_before=w/v plus Menger abs<=8. Not hard fixed B pose. v=0 undefined curvature and abs(w/v)>8 retain frozen initialization rejection and CUT fallback.',
        'synchronous':'One external system-Python persistent RPC, caller waits synchronously at installation actual pose; no predicted pose or delayed result reuse. RPC30s watchdog is technical error,not solver tuning. Solver compute time and wholeRPC logged.',
        'install_scope':'Final EC-selected native CUT chunk installation,including alternative SAFE candidates selected by unchanged fallback. On periodic replacement refine the corresponding native candidate rather than recursively refine Graph XY. EC-tail rechecks Graph with latest map;failed/no-convergence uses the same already-passed CUT candidate.',
        'success':'Frozen official declared stop, distance<=.5m and no collision;wrong stop>.5m; timeout without declaration unchanged.',
        'heading_discontinuity':'At actual installation B: wrapped direction difference between previous and installed XY suffixes projected at B,first .05m; p50/p95 degrees;undefined endpoint directions excluded/count recorded.',
        'time':'Actual72Hz |v|<.01 stop duration; command-state intervals include ALIGN_ROTATE;arrival median only successes.',
        'graph_rate':'Actually installed Graph / synchronous Graph attempts;also attempts,installations,reasons,solve p50/p95. No Graph in CUT.',
        'historical':'Same seed published Phase47/51/52 aggregates reused without extra analysis. Different days;Phase51 WIDE geometry differs;Phase52 HOLD differs. Historical missing fields remain empty,not zero-filled.',
        'execution':'40main serial,one technical retry,global lock,resume completed runs,storagev2,cache cleanup,30GB reserve,automatic systemPython report+commit+push. One LC smoke only;no main in preparation.'}
    p['frozen_sources']={**old['frozen_sources'],**old['source_sha256']}
    for name in ('nomad_phase17/graph.py','nomad_phase15b/graph.py','nomad_phase12/graph_gf.py','nomad_phase5/graph.py','nomad_phase0/graph_v4.py','nomad_phase0/graph_v4_protocol.json','nomad_phase52ec/rollout.py','nomad_phase32o/exec_cert.py','nomad_phase32/policy.py','nomad_phase16/execution.py','nomad_phase38/ec_normal.py','nomad_phase47c/runtime.py','nomad_phase51p/runtime.py'):
        f=ROOT/'research'/name;p['frozen_sources'][str(f.relative_to(ROOT))]=sha256_file(f)
    p['reference_hashes']={**old['reference_hashes'],**hashes,'research/nomad_phase47c/protocol.json':sha256_file(ROOT/'research/nomad_phase47c/protocol.json'),
        str((OUT/'preparation/baselines.json').relative_to(ROOT)):sha256_file(OUT/'preparation/baselines.json')}
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')}
    save(HERE/'protocol.json',p);verify()

def document():
    p=verify();v=json.loads((OUT/'preparation/validation.json').read_text());smoke=json.loads((OUT/'preparation/smoke.json').read_text()) if (OUT/'preparation/smoke.json').exists() else None
    prefix=f'cd {ROOT} && '
    command=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase53p.campaign > ../artifacts/isaac6/phase53p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase53p.campaign --status'
    save(OUT/'preparation/commands.json',dict(campaign=command,status=status,main_executed=False))
    smoke_row=dict(status='NOT_RUN') if not smoke else {k:smoke.get(k) for k in ('technical_validation','graph_attempts','graph_applied','graph_reasons','ec_checks','ec_rejects','new_timeout_count')}
    lengths=[dict(scene=s,reference_m=json.loads((ROOT/p['scenes'][s+'_D075']['scenario']).read_text()).get('reference_length_m','~7.7 (straight reference)')) for s in BASE_SCENES]
    lines=['# Phase53-P 준비',table([dict(status='FROZEN; MAIN_NOT_RUN',runs=40,conditions='D075/D150',seeds='221,222',methods='CUT/GRAPH-HO',protocol_sha256=sha256_file(HERE/'protocol.json'))]),
        table([dict(method=k,definition=v) for k,v in p['method_definitions'].items()]),table([dict(item=k,value=v) for k,v in p['report_definitions'].items()]),
        'LC GRAPH-HO seed95 smoke 1회만 허용(본 결과 제외). reference 최단 LC/H1 동률 중 LC 선택. 추가 분석·오프라인 재풀이 없음.',table(lengths),table([v]),table([smoke_row]),
        'smoke는 기술 audit만 평가한다. 수치 성과로 method/parameter를 바꾸지 않는다. 본 실행은 사용자가 수행한다.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/phase53p_01.log`','본 실행 명령(미실행):','`'+command+'`']
    (ROOT/'docs/PHASE53P_PREP.md').write_text('\n\n'.join(lines)+'\n')

def validate():
    verify();folder=OUT/'preparation';env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase53p.test_phase53p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-4000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase53p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==40 and not dry['simulations_started'];save(folder/'dry_run.json',dry)
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_phase53p.launch,nomad_phase53p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    result=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=40,main_started=0,offline_resolves=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',result)
    from .report import generate
    generate();document();print(json.dumps(result))

def finalize_smoke():
    """Associate the single saved PASS with the final prep manifest, not rerun it.

    Only this documentation/registration tool may differ from the smoke commit;
    all runtime/test/report sources and every numerical protocol field must match.
    Both protocol hashes are retained, so the raw run provenance is never rewritten.
    """
    p=verify();metrics=list((SMOKE_ROOT/'metrics').glob('*.json'));assert len(metrics)==1
    r=json.loads(metrics[0].read_text());assert r['technical_validation']=='PASS' and r['attempt_count']==1
    provenance=json.loads((Path(r['output'])/'provenance.json').read_text())
    assert provenance['smoke_excluded'] and provenance['index']==95 and provenance['method']=='GRAPH-HO'
    ignore={'frozen_at_utc','source_sha256'}
    assert {k:v for k,v in p.items() if k not in ignore}=={k:v for k,v in provenance['protocol'].items() if k not in ignore}
    exempt=str((HERE/'prepare.py').relative_to(ROOT));verified={}
    for f,h in provenance['source_sha256'].items():
        if f==exempt:continue
        assert sha256_file(ROOT/f)==h,f
        verified[f]=h
    count=0
    for f in (Path(r['output'])/x for x in ('controller.jsonl','phase20_commands.jsonl','graph_ho.jsonl','exec_cert.jsonl')):
        for line in f.read_text().splitlines():
            if line.strip():json.dumps(json.loads(line),allow_nan=False);count+=1
    save(OUT/'preparation/smoke.json',dict(r,excluded_from_main=True,
        protocol_sha256=sha256_file(HERE/'protocol.json'),smoke_execution_protocol_sha256=provenance['protocol_sha256'],
        runtime_source_equivalence=verified,preparation_only_change='Reference-length documentation reads scenario metadata;final smoke registration utility only',
        standard_json_records_validated=count,simulations_started=1))
    print(json.dumps(dict(smoke='PASS',runtime_sources_identical=len(verified),json_records=count,main_started=0)))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');ap.add_argument('--document',action='store_true');ap.add_argument('--finalize-smoke',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
    if a.finalize_smoke:finalize_smoke()
    if a.document:document()
if __name__=='__main__':main()
