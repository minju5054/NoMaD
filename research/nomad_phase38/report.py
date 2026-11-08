"""Cumulative nightly saved-run report; no simulator or inference calls."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,SMOKE_ROOT,METHODS,SCENES,verify
from .statistics import analyze

def generate(output=OUT,document=None,roots=None):
    p=verify();roots=roots or [RUN_ROOT/'night1',RUN_ROOT/'night2'];output=Path(output)
    rows=[json.loads(f.read_text()) for root in roots for f in sorted((root/'metrics').glob('*.json'))]
    keys=[(r['scene'],r['index'],r['method']) for r in rows];assert len(keys)==len(set(keys))
    summary=[]
    for scene in (*SCENES,'ALL'):
        for m in METHODS:
            group=[r for r in rows if r['method']==m and (scene=='ALL' or r['scene']==scene)];good=[r for r in group if r.get('technical_validation')=='PASS']
            summary.append(dict(scene=scene,method=m,completed=len(group),valid=len(good),goal=sum(r['success'] for r in good),
                collision=sum(r['collision'] for r in good),arrival_median_s=median([r['goal_time_s'] for r in good if r['success']]),
                technical_failure=len(group)-len(good)))
    tests,paired,ni=analyze(rows,METHODS);output.mkdir(parents=True,exist_ok=True)
    save(output/'runs.json',rows);csvout(output/'summary.csv',summary);csvout(output/'mcnemar.csv',tests);csvout(output/'paired.csv',paired);csvout(output/'noninferiority.csv',ni)
    failed=[{k:r.get(k) for k in ('method','scene','index','error','output','attempt_count')} for r in rows if r.get('technical_validation')!='PASS']
    save(output/'technical_failures.json',failed)
    result=dict(stage='COMPLETE' if len(rows)==180 else 'NIGHT1_INTERIM' if len(rows)==90 and all(r['index']<=218 for r in rows) else 'PARTIAL',
        completed=len(rows),planned=180,protocol_sha256=sha256_file(HERE/'protocol.json'),noninferiority=ni,technical_failures=len(failed))
    save(output/'analysis.json',result)
    text=f'''# Phase38 누적 비교

**{result['stage']} — {len(rows)}/180회**. Protocol SHA256 `{result['protocol_sha256']}`. 방법/배치/분석은 실행 전에 동결했다. 이전 phase 결과는 합산하지 않는다.

## 방법×장면 도착·충돌·도착시간

{table(summary)}

도착시간은 도착 run만의 중앙값이다. 기술 실패는 아래 표에 보존하고 짝 분석에서 어느 한쪽이 실패하면 해당 비교의 scene×seed 짝을 제외한다. 미관측 충돌을0으로 대체하지 않는다.

## 짝 McNemar exact 및 Holm

{table(tests)}

두 결과(도착/충돌)×8비교=16검정을 한 family로 Holm 보정한다. left_only/right_only는 해당 결과가 왼쪽/오른쪽에만 있는 짝 수다. 밤1은 중간 기술 통계이며, 밤2는 누적 분석이다. 각 누적 report의 Holm 보정은 반복 열람 전체의 순차검정 오류율을 보장하지 않는다.

## 도착 비열등성: OURS−상대

{table(ni)}

짝 scene×seed를 장면 내 복원 추출하는20,000회 paired bootstrap(seed20261111), percentile95% CI다. CI 하한≥−10%p이면 NONINFERIOR, 상한<−10%p이면 INFERIOR, 그 외 INCONCLUSIVE. 적은 seed 수의 탐색적 비교로 해석한다. 비열등성 CI는 보정하지 않은 별도 요약이다.

## 짝 차이와 기술 실패

짝별 도착/충돌과 둘 다 도착한 경우 도착시간 차이는 `research/results/phase38/paired.csv`에 있다.

{table(failed)}

방법 차이·CARE/RTC 원문 차이와 동결 규칙은 [준비 문서](PHASE38_PREP.md)를 따른다. 저장v2,cache정리,30GB 중단,기술실패1회 재시도다.
'''
    doc=Path(document) if document else ROOT/'docs/PHASE38_RESULTS.md';doc.write_text(text);return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    assert a.run_root.resolve() in {RUN_ROOT.resolve(),(RUN_ROOT/'night1').resolve(),(RUN_ROOT/'night2').resolve()}
    doc=generate()
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report cumulative Phase38 night comparison','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
