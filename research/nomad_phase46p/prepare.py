import argparse,copy,json,os,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,INDICES,METHODS,verify


def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def freeze():
    assert not RUN_ROOT.exists()
    from .metrics import augment
    parent=json.loads((ROOT/'research/nomad_phase45p/protocol.json').read_text());p=copy.deepcopy(parent)
    p.update(phase='46-P',frozen_at_utc=datetime.now(timezone.utc).isoformat(),methods=list(METHODS),
        main_order=[dict(scene=s,index=i,method=METHODS[0]) for i in INDICES for s in SCENES],
        planner='Phase45 frozen B->R3 only; A/R2 disabled; ALL_UNSAFE uses identical OURS-DETOUR fallback',
        decision=dict(B_ONLY_OK='success_0p5>=11 AND collision<=1 AND current_only_success-Phase43_only_success>=2',paired_n=15),
        trigger_analysis=dict(online='Depth-only component cell centers from exact field used by frozen B predicate; no oracle input',
            oracle='Report only:actual boxes spawned by trigger time; rotated XY box footprint',
            association='min cell-center-to-box distance<=0.3m (+1e-12 numerical tolerance)',
            categories=['BOX','NON_BOX','UNMEASURED'],no_spawned_box='NON_BOX',
            historical_missing='Only exact matching archived frame; never substitute or count missing as false',
            false_results='R3 disposition/installed/end reason and final run outcome; no causal attribution'))
    refs=dict(parent['reference_hashes']);baseline=[]
    for name in ('research/nomad_phase45p/protocol.json','research/results/phase43p/runs.json','research/results/phase45p/runs.json'):
        refs[name]=sha256_file(ROOT/name)
    for cohort,phase in (('Phase43-P','phase43p'),('Phase45-P','phase45p')):
        rows=json.loads((ROOT/f'research/results/{phase}/runs.json').read_text());assert len(rows)==15
        for r in rows:
            for name in ('summary.json','detour.jsonl','phase20_commands.jsonl'):
                f=Path(r['output'])/name;refs[str(f)]=sha256_file(f)
            r=augment(r);r['cohort']=cohort;baseline.append(r)
    save(OUT/'preparation/baselines.json',baseline)
    refs['research/results/phase46p/preparation/baselines.json']=sha256_file(OUT/'preparation/baselines.json')
    p['reference_hashes']=refs;p['frozen_sources']={**parent['frozen_sources'],**parent['source_sha256']}
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')}
    save(HERE/'protocol.json',p);verify()


def validate():
    verify();folder=OUT/'preparation';env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase46p.test_phase46p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-3500:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase46p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==15 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_phase46p.launch,nomad_phase46p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    import re
    v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=15,smoke=False,simulations_started=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',v)
    prefix=f'cd {ROOT} && '
    cmd=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase46p.campaign > ../artifacts/isaac6/phase46p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase46p.campaign --status'
    save(folder/'commands.json',dict(campaign=cmd,status=status,executed=False))
    fields=[('등록','FROZEN'),('방법','Phase45에서 A·R2만 OFF;B→R3 동결'),('ALL_UNSAFE','OURS-DETOUR와 동일 fallback;별도로 B가 충족하면 B→R3는 허용'),
        ('본 실행','SLW,LC,L2,H1,H2 ×217,219,220 =15회;같은 jitter·원래 외관'),('비교군','Phase43-P·45-P 같은15쌍 재사용'),
        ('B_ONLY_OK','성공0.5m≥11 AND 충돌≤1 AND (Phase43대비 Graph만성공−반대)≥2'),
        ('추가 분석','발동 component셀 중심→이미 출현한 실제상자 XY 경계 최소거리≤0.3m;oracle은 종료 후만 사용'),
        ('거짓 발동','NON_BOX 수·그 뒤 R3수락/설치/종료사유·최종 run결과;과거 지도누락은 UNMEASURED'),
        ('대기 시간','계산대기(REPAIR_WAIT+DETOUR_WAIT),STOP_WAIT,실제 정지 시간 분리'),
        ('검증',f"최소테스트{v['tests']}개 PASS /15조합 dry-run PASS"),('주행·추론','0회;smoke생략'),('Protocol SHA256',v['protocol_sha256'])]
    (ROOT/'docs/PHASE46P_PREP.md').write_text('| 항목 | 결과 |\n|---|---|\n'+''.join(f'| {a} | {b} |\n' for a,b in fields))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()


if __name__=='__main__':main()
