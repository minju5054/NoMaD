import argparse,copy,json,os,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,INDICES,METHODS,verify


def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def freeze():
    assert not RUN_ROOT.exists()
    from .metrics import detour_windows
    from nomad_phase32.report import lines
    source=ROOT/'research/nomad_phase43p/protocol.json';parent=json.loads(source.read_text());p=copy.deepcopy(parent)
    p.update(phase='45-P',frozen_at_utc=datetime.now(timezone.utc).isoformat(),methods=list(METHODS),
        main_order=[dict(scene=s,index=i,method=METHODS[0]) for i in INDICES for s in SCENES],
        planner='Phase38 OURS frozen R2/R3,conservative maps,certificate,EC,blocking waits; no Phase39/40 changes',
        appearance='Original Phase38/43 appearance and Topomap; no Phase44 materials or regenerated maps',
        decision=dict(mode='DESCRIPTIVE_ONLY',planned=15),
        post_detour=dict(primary='END of applied R3 through min(END+10s,run termination)',
            supplementary='APPLIED through min(APPLIED+10s,run termination)',
            clock='Inference image observation time',truth='nearest Topomap XY node; evaluation only',
            overlapping='Per-run/scope union of inference IDs; episode windows also saved',
            missing='n0 and NA for no completed detour/no observations; active-at-termination counted'))
    refs=dict(parent['reference_hashes'])
    for name in ('research/nomad_phase38/protocol.json','research/nomad_phase43p/protocol.json','research/results/phase43p/runs.json'):
        refs[name]=sha256_file(ROOT/name)
    baseline=json.loads((ROOT/'research/results/phase43p/runs.json').read_text());assert len(baseline)==15
    for r in baseline:
        root=Path(r['output'])
        for name in ('detour.jsonl','repair.jsonl'):
            f=root/name;refs[str(f)]=sha256_file(f)
        apps=[e for e in lines(root/'repair.jsonl') if e['event']=='PATH_APPLIED']
        r['r2_installations']=sum(e['kind']=='REPAIR' for e in apps);r['r3_installations']=sum(e['kind']=='DETOUR' for e in apps)
        assert r['r2_installations']==r['r3_installations']==0
        r['post_detour']=detour_windows(lines(root/'detour.jsonl'),r['node_errors'],r['duration_s'])
    save(OUT/'preparation/baselines.json',baseline)
    refs['research/results/phase45p/preparation/baselines.json']=sha256_file(OUT/'preparation/baselines.json')
    p['reference_hashes']=refs;p['frozen_sources']={**parent['frozen_sources'],**parent['source_sha256']}
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')}
    save(HERE/'protocol.json',p);verify()


def validate():
    verify();folder=OUT/'preparation';env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase45p.test_phase45p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-3000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase45p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==15 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_phase45p.launch,nomad_phase45p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    import re
    v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=15,smoke=False,simulations_started=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',v)
    prefix=f'cd {ROOT} && '
    cmd=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase45p.campaign > ../artifacts/isaac6/phase45p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase45p.campaign --status'
    save(folder/'commands.json',dict(campaign=cmd,status=status,executed=False))
    fields=[('등록','FROZEN'),('방법','Phase38 OURS +Phase43-P HMM·공식정지;OURS+HMM'),
        ('동결','Phase38 R2/R3·기다림·EC·트리거·지도·실행기;Phase43 HMM·정지 그대로'),
        ('장면','원래 외관·Topomap;SLW,LC,L2,H1,H2 ×217,219,220 =15회'),('배치','Phase43 같은 seed·jitter'),
        ('성공','declared arrival 목표거리≤0.5m AND 충돌없음'),('보고','Phase43 같은15쌍 대비 성공·잘못된정지·충돌·짝차이·R2/R3 설치'),
        ('우회 후 오차','실제 적용된 R3 종료 뒤10초;설치 뒤10초 별도;관측시점 기준;중복구간은 inference ID 합집합'),
        ('미측정','관측없음/종료미발생은 n0·NA;진행중 종료 건수 기록'),
        ('검증',f"최소테스트{v['tests']}개 PASS /15조합 dry-run PASS"),('주행·추론','0회;smoke생략'),
        ('Protocol SHA256',v['protocol_sha256'])]
    (ROOT/'docs/PHASE45P_PREP.md').write_text('| 항목 | 결과 |\n|---|---|\n'+''.join(f'| {a} | {b} |\n' for a,b in fields))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()


if __name__=='__main__':main()
