import argparse,copy,json,os,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,INDICES,verify


def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def freeze():
    assert not RUN_ROOT.exists()
    from .nodes import node_errors
    parent=json.loads((ROOT/'research/nomad_phase41/protocol.json').read_text());p=copy.deepcopy(parent)
    p.update(phase='43-P',frozen_at_utc=datetime.now(timezone.utc).isoformat(),methods=['OURS-DETOUR+HMM'],
        main_order=[dict(scene=s,index=i,method='OURS-DETOUR+HMM') for i in INDICES for s in SCENES],
        localization=dict(filter='Frozen nomad_phase42l.filter.WindowHMM',initial_closest=0,
            window='Official candidate_range(previous HMM MAP,goal,4),inclusive H-4..H+5',
            transition='K=min(N-1,max(1,ceil(odometry_distance/median_positive_adjacent_node_spacing)))',
            odometry='Recorded72Hz cumulative XY path length at observation tick; delta between accepted inference inputs,first delta0',
            emission='42-L exp(-NoMaD distance),unit temperature,forward only,no tuning',
            subgoal='min(H+int(distance[H]<3),candidate_end_inclusive)',
            neural='Frozen encoder,one selected-condition DDPM,unchanged weights/noise/seeds'),
        decision=dict(LOC_OK='wrong_stop<=3 AND success_0p5>=8',baseline41_success=4,required_gain=4,planned=15))
    refs=dict(p['reference_hashes'])
    for name in ('research/nomad_phase41/protocol.json','research/results/phase41/runs.json','research/nomad_phase42l/filter.py'):
        refs[name]=sha256_file(ROOT/name)
    baselines=[]
    for cohort,file in (('Phase38',ROOT/'research/results/phase41/preparation/baselines.json'),('Phase41',ROOT/'research/results/phase41/runs.json')):
        refs[str(file)]=sha256_file(file)
        for r in json.loads(file.read_text()):
            summary=Path(r['output'])/'summary.json';refs[str(summary)]=sha256_file(summary)
            s=json.loads(summary.read_text());is_stop=bool(r.get('declared_arrival')) if cohort=='Phase41' else bool(s['goal_entry'])
            inf=Path(r['output'])/'model/inference.jsonl';refs[str(inf)]=sha256_file(inf)
            cfg=Path(r['output'])/'scenario.json';refs[str(cfg)]=sha256_file(cfg)
            baselines.append(dict(r,cohort=cohort,final_pose=s['final_pose'],stop_pose=s['final_pose'] if is_stop else None,
                node_errors=node_errors(r['output'],cohort)))
    assert len(baselines)==30 and sum(r['success'] for r in baselines if r['cohort']=='Phase41')==4
    save(OUT/'preparation/baselines.json',baselines)
    refs['research/results/phase43p/preparation/baselines.json']=sha256_file(OUT/'preparation/baselines.json')
    p['reference_hashes']=refs
    p['frozen_sources']={**parent['frozen_sources'],**parent['source_sha256'],
        **{str(f.relative_to(ROOT)):sha256_file(f) for f in (ROOT/'research/nomad_phase42l').glob('*.py')},
        'research/nomad_isaac/worker.py':sha256_file(ROOT/'research/nomad_isaac/worker.py'),
        'research/nomad_isaac/topomap_inference.py':sha256_file(ROOT/'research/nomad_isaac/topomap_inference.py')}
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')}
    save(HERE/'protocol.json',p);verify()


def validate():
    verify();folder=OUT/'preparation';env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase43p.test_phase43p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-3500:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase43p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==15 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_phase43p.launch,nomad_phase43p.campaign,nomad_phase43p.worker;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    import re
    v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=15,smoke=False,simulations_started=0,new_nomad_inferences=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',v)
    prefix=f'cd {ROOT} && '
    cmd=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase43p.campaign > ../artifacts/isaac6/phase43p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase43p.campaign --status'
    save(folder/'commands.json',dict(campaign=cmd,status=status,executed=False))
    fields=[('등록','FROZEN'),('방법','Phase41 OURS-DETOUR +42-L forward HMM'),('본 실행','5장면×217,219,220=15회;Phase41 jitter 동일'),
        ('후보 창','직전 HMM MAP 기준 공식 candidate_range(radius4),양끝포함 H−4..H+5'),('closest / subgoal','HMM MAP /공식 거리<3이면 다음node,창끝 clamp'),
        ('K','42-L 동일;관측tick의72Hz누적이동거리 차이/인접node 양의간격 중앙값'),('동결','공식정지·D750·실행기·EC·회복·필터·지도·신경망/RNG'),
        ('LOC_OK','잘못된정지≤3/15 AND 성공0.5m≥8'),('비교','Phase41·Phase38 같은15쌍,과거 실행일'),
        ('노드 오차','영상관측 pose 최근접Topomap XY node;평가 전용'),('검증',f"최소테스트{v['tests']}개 PASS;15조합 dry-run PASS"),
        ('주행/추론','0회;smoke생략'),('Protocol SHA256',v['protocol_sha256'])]
    (ROOT/'docs/PHASE43P_PREP.md').write_text('| 항목 | 결과 |\n|---|---|\n'+''.join(f'| {a} | {b} |\n' for a,b in fields))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()


if __name__=='__main__':main()
