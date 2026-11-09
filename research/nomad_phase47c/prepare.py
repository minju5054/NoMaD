import argparse,copy,json,os,shutil,subprocess
from datetime import datetime,timezone
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,INDICES,METHODS,ORDER_SEED,registered_order,verify


def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def freeze():
    assert not RUN_ROOT.exists()
    from nomad_phase38.scenes import registered_jitter
    original=json.loads((ROOT/'research/nomad_phase38/protocol.json').read_text())
    hmm=json.loads((ROOT/'research/nomad_phase43p/protocol.json').read_text())
    p=copy.deepcopy(original);blocks,order=registered_order()
    p.update(phase='47-C',status='FROZEN',experiment='CONFIRMATORY',frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        methods=list(METHODS),indices=list(INDICES),smoke=dict(enabled=False),main_order=order,blocks=blocks,order_seed=ORDER_SEED,
        placements={f'{s}_{i}':registered_jitter(s,i) for i in INDICES for s in SCENES},
        stop=copy.deepcopy(hmm['stop']),outcomes=copy.deepcopy(hmm['outcomes']),localization=copy.deepcopy(hmm['localization']),
        method_definitions={'NOMAD_RAW':'Phase38 RAW sample0,original argmin localization,+Phase41 declared stop; no depth/filter/EC/recovery',
            'OURS-DETOUR':'Phase38 frozen SAFE+EC/recovery,no detour,original argmin localization,+Phase41 declared stop',
            'OURS-DETOUR+HMM':'Phase43-P frozen method,HMM window/MAP and same declared stop'},
        primary_tests=[dict(name='PRIMARY1',left='OURS-DETOUR+HMM',right='OURS-DETOUR',outcome='success',favorable='higher'),
                       dict(name='PRIMARY2',left='OURS-DETOUR',right='NOMAD_RAW',outcome='collision',favorable='lower')],
        analysis=dict(test='Exact two-sided McNemar = binomtest(left-only,discordant,p0=.5)',
            multiplicity='Raw p and Holm adjusted p for the two primary tests',family_alpha=.05,
            rejection_display='Only a comparison with all20 valid pairs; incomplete comparisons show p and missing counts without rejection flag',
            discordant_zero='p=1 when at least one valid pair; no data=>NA',
            technical_failure='One retry,then pairwise exclusion per comparison,no imputation',
            auxiliary=['wrong stop','stop distance','per-inference absolute node error'],
            no_historical_pooling=True,no_composite_label=True),
        execution=dict(serial=True,technical_retries=1,cache_cleanup=True,disk_min_bytes=30_000_000_000,storage_version=2,full_frame_seed=221))
    p.pop('nights',None)
    p['frozen_sources']={**hmm['frozen_sources'],**hmm['source_sha256'],**original['source_sha256']}
    p['reference_hashes']={name:sha256_file(ROOT/name) for name in ('research/nomad_phase38/protocol.json','research/nomad_phase43p/protocol.json')}
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')}
    save(HERE/'protocol.json',p);verify()


def validate():
    verify();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase47c.test_phase47c','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-3500:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase47c.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==60 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_phase47c.launch,nomad_phase47c.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    import re
    v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=60,smoke=False,simulations_started=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',v)
    prefix=f'cd {ROOT} && '
    cmd=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase47c.campaign > ../artifacts/isaac6/phase47c_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase47c.campaign --status'
    save(folder/'commands.json',dict(campaign=cmd,status=status,executed=False))
    fields=[('등록','FROZEN / 확인 실험'),('본 실행','NOMAD_RAW,OURS-DETOUR,OURS-DETOUR+HMM ×5장면×221–224 =60회'),
        ('공통정지','Phase41 closest_node==goal_node 선언 시 v=ω=0;성공은 거리≤0.5m AND 충돌없음'),
        ('위치추정','방법1·2 원래 argmin;방법3 Phase43-P HMM 동결'),
        ('jitter','Phase38 생성식/SeedSequence20261111에 새 seed221–224;블록3방법 동일 배치'),
        ('순서','seed→scene;블록내3방법 RNG20261111 무작위 순열'),
        ('주1','3 vs2 성공 exact 양측 McNemar'),('주2','2 vs1 충돌 exact 양측 McNemar'),
        ('통계','원 p+주2검정 Holm 보정 p,α0.05;방향/discordant표;20유효짝에서만 기각표시;합성결론 없음'),
        ('기술 실패','1회 재시도 후 해당 비교의 짝만 제외,대체값 없음'),('보조','잘못된정지,정지거리,관측pose 기준 추론별노드오차'),
        ('기타','원래 외관/Topomap·D750·C0-NA·90s·저장v2 유지;첫seed221 전체프레임,cache정리,30GB 중단'),
        ('검증',f"최소테스트{v['tests']}개 PASS /60조합 dry-run PASS"),('실행','주행·추론0회;smoke생략'),
        ('Protocol SHA256',v['protocol_sha256'])]
    (ROOT/'docs/PHASE47C_PREP.md').write_text('| 항목 | 결과 |\n|---|---|\n'+''.join(f'| {a} | {b} |\n' for a,b in fields))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()


if __name__=='__main__':main()
