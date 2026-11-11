"""SIGN outcome tables versus Phase58/59; explicitly stage generated PNGs."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from nomad_isaac.common import sha256_file
from nomad_phase59p.report import FIELDS
from nomad_phase59p.metrics import localization_metrics
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,verify,load_model,MODEL_SHA256
BASELINES={phase:ROOT/f'research/results/{folder}/runs.json' for phase,folder in [('Phase58','phase58p'),('Phase59','phase59p')]}

def generate(root=RUN_ROOT,output=OUT,document=None,prepare_only=False):
    p=verify();model=load_model();root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    expected={(j['scene'],j['index'],j['method']) for j in p['main_order']};keys=[(r['scene'],r['index'],r['method']) for r in runs]
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    baselines={};baseline_hashes={}
    for phase,file in BASELINES.items():
        old=json.loads(file.read_text());baseline_hashes[phase]=sha256_file(file);baselines[phase]=[]
        for b in old:
            b=dict(b)
            if not prepare_only and b['technical_validation']=='PASS':
                b.update(localization_metrics(b['output'],b));b['supplementary_metrics_status']='SAVED_LOG_ONLY'
            else:b['supplementary_metrics_status']='NOT_COMPUTED_IN_PREPARATION' if prepare_only else 'TECHNICAL_FAILURE'
            baselines[phase].append(b)
    summary=[]
    sources={'Phase60 SIGN':runs,'Phase58 HMM0':baselines['Phase58'],'Phase59 NET':baselines['Phase59']}
    for phase,source in sources.items():
        for method in METHODS:
            for scene in (*SCENES,'ALL'):
                rr=[r for r in source if r['method']==method and (scene=='ALL' or r['scene']==scene)];good=[r for r in rr if r['technical_validation']=='PASS']
                row=dict(phase=phase,method=method,scene=scene,n=len(rr),valid=len(good))
                for k in ('success','collision','wrong_stop','timeout_without_declaration','reached_goal_0p7','arrived_without_declaration','arrived_0p5_without_declaration'):
                    row[k]=sum(bool(r[k]) for r in good) if good and all(k in r for r in good) else None
                row['false_goal_count']=sum(r['false_goal_count'] for r in good) if good and all('false_goal_count' in r for r in good) else None
                row['false_goal_runs']=sum(r['false_goal_count']>0 for r in good) if row['false_goal_count'] is not None else None
                for k in ('stop_distance_m','goal_time_s','stopped_s'):row[k+'_median']=median([r[k] for r in good if r.get(k) is not None])
                summary.append(row)
    by={(r['scene'],r['index'],r['method']):r for r in runs};oldby={phase:{(r['scene'],r['index'],r['method']):r for r in rr} for phase,rr in baselines.items()};pairs=[]
    for j in p['main_order']:
        key=(j['scene'],j['index'],j['method']);r=by.get(key,{});row=dict(j,status=r.get('technical_validation','NOT_RUN'))
        row.update({k:r.get(k) for k in FIELDS})
        for phase in BASELINES:
            b=oldby[phase].get(key,{});row[phase+'_status']=b.get('technical_validation','NOT_AVAILABLE');row.update({phase+'_'+k:b.get(k) for k in FIELDS})
        pairs.append(row)
    status=dict(status='COMPLETE' if len(runs)==18 else 'PARTIAL' if runs else 'PREPARED_NOT_RUN',planned=18,completed=len(runs),protocol_sha256=sha256_file(HERE/'protocol.json'),
        model_sha256=MODEL_SHA256,sigma2=model['sigma2'],baseline_hashes=baseline_hashes,baseline_enriched_from_saved_logs=not prepare_only)
    save(output/'runs.json',runs);save(output/'status.json',status);csvout(output/'summary.csv',summary);csvout(output/'paired.csv',pairs)
    save(output/'baseline_fields.json',[dict(phase=phase,**{k:r.get(k) for k in ('scene','index','method','output','supplementary_metrics_status',*FIELDS)}) for phase,rr in baselines.items() for r in rr])
    from .figures import generate as figures
    files=figures(runs,output/'figures');save(output/'figures.json',dict(files=files,count=len(files),force_stage_png=True))
    doc=Path(document) if document else ROOT/'docs/PHASE60P_RESULTS.md'
    shown=lambda rr:table([{k:('—' if v is None else v) for k,v in r.items()} for r in rr])
    text=['# Phase60-P SIGN 전이 파일럿',table([status]),
        f"동결 보정 파일의 σ²={model['sigma2']}를 직접 읽고 model_sha256 `{MODEL_SHA256}` 일치를 검사했다. 보정값 재추정·반올림 대체는 하지 않는다. 전이는 LOC_V2 Filter(SIGN) 그대로이며 정수 node offset에서 Gaussian 밀도를 평가해 전역 노드 범위로 행 정규화한다.",
        'Phase59-P와 방법·장면·jitter·seed·블록 순서·실행기·EC·Graph·latch·만료·방출·후보 창·부목표·도착 조건이 같다. 바뀐 것은 전이뿐이다. 직전 추론 MAP 노드의 동결 인접차 접선에 observation-tick odometry XY 증분을 투영한다. Topomap 노드 pose와 오도메트리가 같은 좌표계라는 가정이 필요하다. OBS/MEM은 쓰지 않는다.',
        '성공은 기존 선언 시 거리≤0.5m AND 충돌 없음이다. 실제 목표0.7m 도달은 선언과 무관한72Hz 저장 거리 최소≤0.7m이며,미선언은 그 조건을 만족하고 종료까지 선언이 없는 run이다. 0.5m 기준 미선언도 별도 열로 유지한다. 거짓 목표 판정은 추론 MAP==goal AND 관측 시점 true_node<goal−2의 건수로,거리 기준 잘못된 도착과 구별한다.',
        '선언 시 추정 노드는 선언 로그의 closest이고 실제 노드는 선언 순간 실제 pose에 최근접인 Topomap 노드다. Phase58-P·59-P 같은(scene,seed,method)를 옆 열에 둔다. 보조 항목은 report 실행 시 저장 로그에서만 읽으며 기존 결과를 수정하지 않는다. 준비 시점에는 미계산 비교 항목을 —로 둔다.',shown(summary),shown(pairs)]
    for file in files:
        f=Path(file);text.append(f'![{f.stem}](../{f.relative_to(ROOT)})' if f.is_relative_to(ROOT) else f'![{f.stem}]({f})')
    doc.write_text('\n\n'.join(text)+'\n');return doc

def stage_report(doc,output,root=ROOT):
    root=Path(root).resolve();doc=Path(doc).resolve();output=Path(output).resolve()
    paths=[str(doc.relative_to(root)),str(output.relative_to(root))]
    subprocess.run(['git','add','--',*paths],cwd=root,check=True)
    pngs=[str(f.relative_to(root)) for f in sorted((output/'figures').glob('*.png'))]
    if pngs:
        # Repository ignores *.png globally. Force only this phase's figures.
        subprocess.run(['git','add','-f','--',*pngs],cwd=root,check=True)
        tracked=set(subprocess.check_output(['git','ls-files','--cached','-z','--',*pngs],cwd=root).decode().split('\0'))
        assert set(pngs)<=tracked,'Generated report PNGs were not staged'
    return paths

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate()
    if a.publish:
        paths=stage_report(doc,OUT)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase60-P verified SIGN transition pilot with all trajectory figures','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
