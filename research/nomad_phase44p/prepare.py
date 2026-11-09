import argparse,copy,json,os,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,INDICES,METHODS,verify


def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def freeze():
    assert not RUN_ROOT.exists()
    from .appearance import build_assets
    assets=build_assets();parent=json.loads((ROOT/'research/nomad_phase43p/protocol.json').read_text());p=copy.deepcopy(parent)
    p.update(phase='44-P',frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        main_order=[dict(scene=s,index=i,method=METHODS[0]) for i in INDICES for s in SCENES],
        decision=dict(mode='DESCRIPTIVE_ONLY',planned=6,no_new_threshold=True),
        appearance=dict(panels='Each existing14 Panel cube has a unique hue and deterministic stripe/bit texture,including hidden panels',
            floor='20 hue/tone bands over unchanged Floor cube UVs',static_boxes='distinct materials; L2/H2 have0 static boxes,none added',
            sudden_box='Frozen magenta retained,all static textures non-magenta; frozen visibility mask unchanged',
            geometry='No prim shape/position/scale/visibility/camera/light edits in appearance adapter; UV/material only',
            geometry_gate='USD geometry signature equality; paired example depth finite masks equal and max error<=1e-6m',
            examples='Original/changed RTX views at seed217 first-box canonical pose; two images each containing L2 and H2',
            material_api='https://openusd.org/dev/user_guides/render_user_guide.html',
            cube_uv_source='https://github.com/PixarAnimationStudios/OpenUSD/blob/release/pxr/imaging/geomUtil/cuboidMeshGenerator.cpp'),
        topomap_generation=dict(mode='Sensor-only replay,zero NoMaD inference/navigation',
            reference='Identical original21 node poses,IDs,timestamps,spacing; all sudden boxes hidden',
            freeze='Generation specification frozen now; rendered manifest/image hashes sealed before first main run',
            render_retries=0,incomplete_attempt='Preserve and stop for inspection; complete maps reused on resume'))
    p['scenes']={s:dict(parent['scenes'][s],original_topomap=parent['scenes'][s]['topomap'],
        original_topomap_sha256=parent['scenes'][s]['topomap_sha256'],
        topomap=str(RUN_ROOT/'topomap'/s/'topomap/manifest.json'),topomap_sha256=None) for s in SCENES}
    p['frozen_sources']={**parent['frozen_sources'],**parent['source_sha256'],
        'research/nomad_phase26/rendering.py':sha256_file(ROOT/'research/nomad_phase26/rendering.py'),
        'research/nomad_isaac/simulator.py':sha256_file(ROOT/'research/nomad_isaac/simulator.py')}
    for name in ('research/nomad_phase43p/protocol.json','research/results/phase43p/runs.json'):p['reference_hashes'][name]=sha256_file(ROOT/name)
    for name,digest in assets.items():p['reference_hashes'][str((HERE/'textures'/name).relative_to(ROOT))]=digest
    rows=json.loads((ROOT/'research/results/phase43p/runs.json').read_text());baseline=[r for r in rows if r['scene'] in SCENES and r['index'] in INDICES]
    assert len(baseline)==6;save(OUT/'preparation/baselines.json',baseline)
    p['reference_hashes']['research/results/phase44p/preparation/baselines.json']=sha256_file(OUT/'preparation/baselines.json')
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')}
    save(HERE/'protocol.json',p);verify()


def validate():
    verify();folder=OUT/'preparation';env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase44p.test_phase44p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-3500:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase44p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==6 and dry['render_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_phase44p.launch,nomad_phase44p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    import re
    v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=6,render_started=0,simulations_started=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',v)
    prefix=f'cd {ROOT} && '
    cmd=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase44p.campaign > ../artifacts/isaac6/phase44p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase44p.campaign --status'
    save(folder/'commands.json',dict(campaign=cmd,status=status,executed=False))
    fields=[('등록','FROZEN;새 Topomap RGB hash는 생성 후 본 주행 전 별도 seal'),('단계','L2/H2 동일 reference pose RGB 재생성→6회→표+렌더예시2장 report'),
        ('run','L2,H2 ×217,219,220;Phase43-P 같은 jitter'),('동결','HMM·공식정지·실행기·EC·회복·기하·배치·카메라·조명'),
        ('외관','기존14패널 전부 고유색/무늬,바닥20색조구간,정적상자0개 유지;돌발상자 자주색 유지'),
        ('geometry 검증','material/UV 외 USD 속성 동일;기존/변경 예시 depth차≤1e−6m'),
        ('Topomap','기존21 node의 위치·자세·시각·간격 동일;돌발상자 숨김;기존파일 보존'),
        ('USD API','[OpenUSD material/primvar](https://openusd.org/dev/user_guides/render_user_guide.html)'),
        ('검증',f"최소테스트{v['tests']}개 PASS,6조합 dry-run PASS"),('렌더/주행','0회;사용자 명령에서만 생성·실행'),
        ('보고','Phase43-P 같은6쌍 성공·잘못된정지·노드오차;original/changed 실제RTX예시 각1장'),
        ('Protocol SHA256',v['protocol_sha256'])]
    (ROOT/'docs/PHASE44P_PREP.md').write_text('| 항목 | 결과 |\n|---|---|\n'+''.join(f'| {a} | {b} |\n' for a,b in fields))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()


if __name__=='__main__':main()
