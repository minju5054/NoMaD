"""Freeze, minimum tests,20-job argument dry-run; no simulator execution."""
import argparse,copy,json,os,shutil,subprocess
from datetime import datetime,timezone
from .config import ROOT,HERE,OUT,RUN_ROOT,verify
from nomad_isaac.common import sha256_file


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def freeze():
    assert not RUN_ROOT.exists()
    source=ROOT/'research/nomad_phase40p/protocol.json'
    parent=json.loads(source.read_text());p=copy.deepcopy(parent)
    p.update(phase='40-R2',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),methods=['OURS-R2'],
        smoke=dict(enabled=False,reason='User explicitly omitted smoke'),
        planner='Frozen Phase40-P R2 only; no trigger B or R3',
        changes=['Disable trigger B','Disable every R3 dispatch','On R2 failure/EC rejection keep OURS-DETOUR alternative path behavior'],
        parent_protocol_sha256=sha256_file(source))
    p['main_order']=[dict(r,method='OURS-R2') for r in parent['main_order']]
    p['decision']['GRAPH_GAIN']=parent['decision']['GRAPH_GAIN'].replace('OURS-N','OURS-R2')
    p['reference_hashes']['research/nomad_phase40p/protocol.json']=sha256_file(source)
    p['frozen_sources']={**parent['frozen_sources'],**parent['source_sha256']}
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in sorted(HERE.glob('*.py'))}
    save(HERE/'protocol.json',p);verify()


def validate():
    p=verify();assert not RUN_ROOT.exists();out=OUT/'preparation';out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase40r2.test_phase40r2','-v'],cwd=ROOT,env=env,capture_output=True,text=True)
    (out/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-2500:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase40r2.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==20 and dry['simulations_started']==0 and not dry['smoke'];save(out/'dry_run.json',dry)
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_phase40r2.launch,nomad_phase40r2.campaign;assert 'scipy' not in sys.modules"],cwd=ROOT,env=env,check=True)
    import re
    v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=20,smoke=False,simulations_started=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(out/'validation.json',v)
    prefix=f'cd {ROOT} && '
    cmd=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase40r2.campaign > ../artifacts/isaac6/phase40r2_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase40r2.campaign --status'
    save(out/'commands.json',dict(campaign=cmd,status=status,executed=False))
    text='| 항목 | 결과 |\n|---|---|\n'
    for label,value in [('등록','FROZEN'),('방법','OURS-R2: OURS-N에서 트리거 B·R3만 제외'),
        ('R2 실패/EC 거절','OURS-DETOUR 대체 경로 유지'),('변경하지 않음','R2 VN·비차단·예측 B·탈출 EC·실행기·회복·평가기·jitter'),
        ('본 실행','SLW,LC,L2,H1,H2 × seed217–220 =20회'),('비교군','Phase38 OURS-DETOUR·OURS·ASTAR+EC 재사용'),
        ('PILOT_OK','도착≥14 AND 충돌≤1'),('GRAPH_GAIN','도착≥17 AND OURS-R2만 도착≥3쌍(vs OURS-DETOUR)'),
        ('검증',f"테스트{v['tests']}개 PASS /20조합 dry-run PASS"),('smoke','생략'),('실행 횟수',0),
        ('저장/재시도','v2 / 기술실패1회 / cache정리 /30GB 중단 / 잠금·재개'),
        ('디스크 여유',f"{v['disk_free_bytes']/1e9:.1f}GB"),('Protocol SHA256',v['protocol_sha256'])]:
        text+=f'| {label} | {value} |\n'
    (ROOT/'docs/PHASE40R2_PREP.md').write_text(text)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()


if __name__=='__main__':main()
