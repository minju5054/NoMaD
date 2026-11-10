"""Freeze three protocols and publish preparation before any smoke begins."""
import argparse,copy,json,hashlib,os,subprocess,re,shutil
from datetime import datetime,timezone
from nomad_isaac.common import sha256_file
from nomad_phase31p.report import table
from .config import ROOT,HERE,QUEUE_ROOT,RESULTS,DEFS,BASE_SCENES,ORDER_SEED,registered_order,verify

def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def freeze():
    assert not (QUEUE_ROOT/'smoke').exists() and not (QUEUE_ROOT/'state.json').exists(),'No source refreeze after a smoke/main run'
    from nomad_phase53p.config import verify as old_verify
    from nomad_h1v2.scene import load_spec
    from nomad_phase38.scenes import registered_jitter
    old=old_verify();h1=load_spec();h1hashes={}
    for f in (ROOT/'research/nomad_h1v2').glob('*'):
        if f.suffix not in ('.py','.json'):continue
        raw=subprocess.check_output(['git','show','65556be:'+str(f.relative_to(ROOT))],cwd=ROOT)
        assert hashlib.sha256(raw).hexdigest()==sha256_file(f)
        h1hashes[str(f.relative_to(ROOT))]=sha256_file(f)
    placements={f'{s}_{i}':registered_jitter(s,i) for s in ('L2','H1','H2') for i in (95,225,226)}
    for e,d in DEFS.items():
        p=copy.deepcopy(old);p.update(phase=d['phase'],experiment=e,status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),
            main_order=registered_order(e),methods=d['methods'],indices=d['indices'],order_seed=ORDER_SEED,placements=placements,
            scenes={s:copy.deepcopy(old['scenes'][s.replace('H1-v2','H1')]) for s in d['scenes']},
            smoke=dict(enabled=True,maximum_attempts=1,**d['smoke'],reason='Shortest reference LC5.693m,tied with H1/H1-v2;newest code method;technical audit only'),
            report_document=f'NIGHT_{e}_20261111_RESULTS.md',prep_document=f'NIGHT_{e}_20261111_PREP.md',
            queue_policy=dict(priority=['E1','E2','E3'],maximum_seconds=21600,no_new_run_after_deadline=True,technical_retries=1,smoke_retries=0,
                smoke_failure='SKIPPED;no code repair',shared_seed=[225,226],all_scenes=list(BASE_SCENES),launch='single nohup;one start receipt;no subsequent polling'))
        p['environment_overrides']={'H1-v2':dict(source_commit='65556be',scene_spec='research/nomad_h1v2/scene.json',scene_sha256=sha256_file(ROOT/'research/nomad_h1v2/scene.json'),box=h1['box'],spawn=h1['spawn'],jitter=False)}
        p['method_definitions']={
            'CUT':'Frozen Phase53 CUT,1s expiry,HMM,official stop,EC braking tail',
            'GRAPH-HO':'Frozen Phase53 GRAPH-HO,1s expiry,HMM,official stop,EC braking tail',
            'OURS-R3':'Frozen Phase38 OURS R2+R3/triggers/handover/RECOVER restored on Phase47 HMM;only EC predicate changed to registered braking tail;1s expiry',
            'CUT-HOLD':'Phase53 CUT + receipt does not expire;keep current path to endpoint if latest periodic EC-tail passes,including<.25m remainder',
            'GRAPH-HOLD':'CUT-HOLD + Phase53 Graph-HO;only start boundary curvature hard equality omitted when abs(v)<.02 or abs(w/v)>8;all costs,inequalities,certificate,solver options unchanged'}
        p['analysis']=(dict(primary='box passage;exact two-sided McNemar OURS-R3 vs CUT and vs GRAPH-HO',
            pairing='same scene,seed,both completed technical PASS;static SLW/LC have no box and are N/A;12run blocks,8box blocks',
            secondary='spawn-to-passage time only both pass;goal,wrong stop,collision(all must be0)',
            candidate='OURS-R3 only-pass pairs minus CUT only-pass pairs>=3;report this rule and collision-free condition separately;never hide safety failures') if e!='E2' else
            dict(primary='D15012pairs:graph adoption,paired ALIGN_ROTATE and both-arrival time deltas,goal descriptive noninferiority',
                noninferiority='GRAPH-HOLD goals minus CUT-HOLD goals>=-1;pilot descriptive rule,NOT statistical noninferiority test;report discordant pairs',
                margin_runs=-1,expected_pairs_per_condition=12,delay_comparison='D150 vs D075 differences,matched complete4-run blocks;no imputation'))
        p['report_definitions']={'scope':'No historical/new tuning;run figures top-down only;state trajectory,R3 blue solid,R2 purple dotted,Graph handoff orange dashed,CUT gray dotted,raw8 candidates faint,EC rejects redx',
            'comparisons':'Completed technicalPASS pairs only;all unrun/failed rows marked;partial counts and denominators explicit',
            'executor':'C0-NA PP/SP >90deg alignment,depth/HMM/official goal frozen;EC-tail at endpoint/2s then frozen stop_command to rest;36tick rechecks'}
        p['frozen_sources']={**old['frozen_sources'],**old['source_sha256'],**h1hashes,
            'research/nomad_phase53p/protocol.json':sha256_file(ROOT/'research/nomad_phase53p/protocol.json')}
        for relative in ('nomad_phase52p/runtime.py','nomad_phase35/runtime.py','nomad_phase35/worker.py','nomad_phase35/graph_pool.py','nomad_h1v2_trial/figures.py','nomad_run_plots.py'):
            f=ROOT/'research'/relative;p['frozen_sources'][str(f.relative_to(ROOT))]=sha256_file(f)
        p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')}
        save(HERE/f'protocol_{e}.json',p);verify(e)

def documents():
    from .config import protocol
    selection=json.loads((RESULTS/'smoke_selection.json').read_text()) if (RESULTS/'smoke_selection.json').exists() else {}
    for e,d in DEFS.items():
        p=protocol(e);validation=json.loads((RESULTS/e/'preparation/validation.json').read_text()) if (RESULTS/e/'preparation/validation.json').exists() else {}
        parts=['# '+p['phase']+' 준비',table([dict(experiment=e,status='FROZEN',runs=len(p['main_order']),scenes=','.join(BASE_SCENES),seeds='225,226',
            protocol_sha256=sha256_file(HERE/f'protocol_{e}.json'))]),
            '최신 사용자 확정: 초기5장면/기존 seed 설계를 대체해 모든 실험을6장면×신규 seed225·226으로 고정. E1·E3는각12블록/36run,E2는각지연12블록/총48run. 방법 순서는 블록 내부에서 seed20261117로 무작위화. H1-v2는65556be;기존5장면과Topomap 불변. 새 seed jitter는 동결Phase38 알고리즘으로 생성해 세 실험/방법이 공유한다.',
            table([dict(method=m,definition=p['method_definitions'][m]) for m in d['methods']]),table([dict(item=k,value=v) for k,v in p['analysis'].items()]),
            table([p['smoke']]),table([validation or dict(status='PENDING')]),table([selection.get(e,dict(status='SMOKE_NOT_RUN'))]),
            'PREP·코드 commit/push 후 등록 smoke1회만 실행한다. audit 실패 시 수정·재시도하지 않고 SKIPPED. PASS 실험만 E1→E2→E3 단일 대기열. 총6시간 종료선 이후에는 다음run/재시도를 시작하지 않고 진행 중run만 마친다. 저장v2·portable/cache/pycache정리·30GB 여유·기술실패1회재시도. 실험 종료/시간제한 시 완료된짝만 report하고 미완료표시,자동commit/push.',
            'E2 boundary equality 제외는 낮은v/과대w/v에서만 적용한다. 기존 초기화의 해당 곡률정의 사전거부도 그 경우에만 건너뛰며, 시작heading 소프트항·Menger hard·진전/여유/이전prior·solver옵션은 동일하다. HOLD에서 활성경로가EC-tail통과면 짧은잔여도 유지;새chunk우선설치·정렬·RECOVER는그대로다.' if e=='E2' else
            'OURS-R3라는 이름에도 R2와R3를 모두 사용한다(요청정의). 상자 통과 검정은상자있는8블록,목표도착/충돌은전체12블록. statics의상자통과를실패로대체하지 않는다.']
        (ROOT/'docs'/p['prep_document']).write_text('\n\n'.join(parts)+'\n')
    status=f'cd {ROOT} && PYTHONPATH=research /usr/bin/python3 -m nomad_night20261111.queue --status'
    start=f'cd {ROOT} && env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m nomad_night20261111.queue --start'
    (ROOT/'docs/NIGHT_QUEUE_20261111.md').write_text('# 20261111 밤샘 대기열\n\n'+table([dict(priority=i+1,experiment=e,planned=len(protocol(e)['main_order']),smoke=selection.get(e,{}).get('status','NOT_RUN'),prep=protocol(e)['prep_document'],report=protocol(e)['report_document']) for i,e in enumerate(DEFS)])+
        '\n\n최신 확정6장면(SLW,LC,L2,H1,H2,H1-v2),seed225·226. 총120run. Smoke3회는본결과제외,실패실험은수정없이SKIPPED. 통과실험만순차실행한다. 대기열시작부터6시간경과시새run/재시도를금지하고진행중run만완료한다. 미완료짝은표시하되비교에서제외한다. 실험마다report·PNG·commit·push.\n\n`--start`는nohup프로세스를정확히하나생성하고첫launcher PID의시작영수증을pipe로한번확인한뒤반환한다. 주행완료를기다리거나poll하지않는다. 재실행중복은pid/lock으로거부한다. 기존deadline은재개해도연장하지않는다.\n\n진행 확인: `'+status+'`\n\n전체로그: `../artifacts/isaac6/night_queue_20261111_01.log`\n\nSmoke로그: `../artifacts/isaac6/night_queue_20261111_smoke.log`\n\n개별로그·상태: `../artifacts/isaac6/night_queue_20261111_01/{E1,E2,E3}/` (smoke는`smoke/{E1,E2,E3}/`).\n\n시작명령(내부nohup1회): `'+start+'`\n')

def validate():
    for e in DEFS:verify(e)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/nomad-night-mpl')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_night20261111.test_night','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (RESULTS/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-6000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_night20261111.queue','--dry-run'],cwd=ROOT,env=env,text=True));save(RESULTS/'dry_run.json',dry)
    assert sum(d['planned'] for d in dry['experiments'].values())==120
    for e in DEFS:
        subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_night20261111.launch;assert 'scipy' not in sys.modules and 'torch' not in sys.modules"],cwd=ROOT,env=dict(env,NOMAD_NIGHT_EXPERIMENT=e),check=True)
        v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=dry['experiments'][e]['planned'],simulations_started=0,
            protocol_sha256=sha256_file(HERE/f'protocol_{e}.json'),free_bytes=shutil.disk_usage(ROOT).free)
        save(RESULTS/e/'preparation/validation.json',v)
    documents();print(json.dumps(dict(tests=v['tests'],dry_runs=120,smokes_planned=3,simulations_started=0,free_bytes=v['free_bytes'])))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');ap.add_argument('--documents',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
    if a.documents:documents()
if __name__=='__main__':main()
