"""Same-seed paired report using frozen Phase38 comparison results."""
import argparse,json,subprocess
from pathlib import Path
from scipy.stats import binomtest
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from nomad_phase38.statistics import paired
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,verify

COMPARATORS=('OURS-DETOUR','OURS','ASTAR+EC')


def analyze(rows):
    ours=[r for r in rows if r['method']=='OURS-N']
    valid=[r for r in ours if r.get('technical_validation')=='PASS']
    pairs,missing=paired(rows,'OURS-N','OURS-DETOUR')
    complete=len(ours)==20 and len(valid)==20 and len(pairs)==20
    goals=sum(r['success'] for r in valid);collisions=sum(r['collision'] for r in valid)
    only=sum(x['success'] and not y['success'] for x,y in pairs)
    decision=dict(complete=complete,n=len(valid),goals=goals,collisions=collisions,ours_only=only,
        pilot_label=('PILOT_OK' if collisions<=1 and goals>=14 else 'PILOT_NOT_OK') if complete else 'NOT_EVALUATED',
        graph_label=('GRAPH_GAIN' if goals>=17 and only>=3 else 'NO_GRAPH_GAIN') if complete else 'NOT_EVALUATED')
    tests=[];details=[]
    for other in COMPARATORS:
        pp,missing=paired(rows,'OURS-N',other)
        for metric in ('success','collision'):
            a=sum(bool(x[metric]) and not bool(y[metric]) for x,y in pp)
            b=sum(not bool(x[metric]) and bool(y[metric]) for x,y in pp)
            tests.append(dict(comparator=other,metric=metric,n=len(pp),ours_only=a,other_only=b,
                              p_exact=float(binomtest(a,a+b,.5).pvalue) if a+b else 1.))
        for x,y in pp:
            both=x['success'] and y['success']
            details.append(dict(scene=x['scene'],index=x['index'],comparator=other,ours_goal=x['success'],other_goal=y['success'],
                both_success=both,arrival_delta_s=x['goal_time_s']-y['goal_time_s'] if both else None,
                distance_delta_m=x['distance_m']-y['distance_m'] if both else None))
    return decision,tests,details


def generate(root=RUN_ROOT,output=OUT,document=None,baseline=None):
    verify();root=Path(root);output=Path(output)
    prior=baseline if baseline is not None else json.loads((ROOT/'research/results/phase38/runs.json').read_text())
    prior=[r for r in prior if r['method'] in COMPARATORS]
    ours=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    rows=prior+ours;d,tests,pairs=analyze(rows);summary=[]
    for scene in (*SCENES,'ALL'):
        for method in ('OURS-N',*COMPARATORS):
            g=[r for r in rows if r['method']==method and (scene=='ALL' or r['scene']==scene) and r.get('technical_validation')=='PASS']
            summary.append(dict(scene=scene,method=method,n=len(g),goal=sum(r['success'] for r in g),collision=sum(r['collision'] for r in g),
                                arrival_median_s=median([r['goal_time_s'] for r in g if r['success']])))
    telemetry=[dict(scene=r['scene'],index=r['index'],**{k:r.get(k) for k in ('planner_installations','escape_installations','consecutive_escape_installations',
        'escape_time_p50_s','escape_time_p95_s','escape_two_second_cap_installations','escape_two_second_cap_jobs',
        'escape_periodic_rejections','waiting_seconds','stopped_while_waiting_seconds','result_dispositions','compute_p50_s','compute_p95_s')}) for r in ours]
    escape_times=[dict(scene=r['scene'],index=r['index'],installation=i,t_escape_s=t) for r in ours for i,t in enumerate(r.get('escape_times_s',[]))]
    differences=[dict(comparator=m,n=sum(r['both_success'] for r in pairs if r['comparator']==m),
        arrival_delta_median_s=median([r['arrival_delta_s'] for r in pairs if r['comparator']==m and r['both_success']]),
        distance_delta_median_m=median([r['distance_delta_m'] for r in pairs if r['comparator']==m and r['both_success']])) for m in COMPARATORS]
    output.mkdir(parents=True,exist_ok=True);save(output/'runs.json',rows);save(output/'decision.json',d)
    for name,data in [('summary',summary),('mcnemar',tests),('paired',pairs),('paired_summary',differences),('telemetry',telemetry),('escape_times',escape_times)]:csvout(output/(name+'.csv'),data)
    doc=Path(document) if document else ROOT/'docs/PHASE40P_RESULTS.md'
    doc.write_text(f'# Phase40-P\n\n{d}\n\nPhase38 비교군은 같은 scene×seed의 과거 주행 재사용이며 실행일이 다르다. 누락·기술 실패 짝은 제외하고, 전체20짝이 갖춰져야 판정한다. McNemar는 기술 통계이며 판정에 사용하지 않는다.\n\n{table(summary)}\n\n{table(tests)}\n\n둘 다 도착한 짝, OURS-N−상대:\n\n{table(differences)}\n\n{table(telemetry)}\n\n탈출 t_esc 분포는 escape_times.csv에 설치 단위로 저장한다. 2초 상한은 설치 건수와 고유 job 수를 함께 보고하며, 같은 job의 재설치로 절대시각을 연장하지 않는다. 대기 중 정지는 EC 대안 없음·회복 등 실제 정지이며 계산 자체의 강제 정지 명령은 없다.\n')
    return doc


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    assert a.run_root.resolve()==RUN_ROOT.resolve();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))]
        subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase40-P pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)


if __name__=='__main__':main()
