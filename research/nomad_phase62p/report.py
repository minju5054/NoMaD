"""UG-GOAL and same-seed Phase61 tables, plus all saved-run PNGs."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from nomad_isaac.common import sha256_file
from nomad_phase60p.report import stage_report
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,verify
FIELDS=('classification','success','collision','wrong_stop','timeout_without_declaration','box_passage','box_passage_from_spawn_s','goal_time_s','stopped_s',
        'u_adoption_rate','u_solution_length_median_m','u_goal_distance_at_solve_median_m')
BASELINE=ROOT/'research/results/phase61p/runs.json'

def generate(root=RUN_ROOT,output=OUT,document=None):
    p=verify();root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))];baseline=json.loads(BASELINE.read_text())
    expected={(j['scene'],j['index'],j['method']) for j in p['main_order']};keys=[(r['scene'],r['index'],r['method']) for r in runs]
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    summary=[]
    for phase,source,methods in [('Phase62',runs,('UG-GOAL',)),('Phase61',baseline,('CUT','CONS','CONS+G18'))]:
        for method in methods:
            for scene in (*SCENES,'ALL'):
                rr=[r for r in source if r['method']==method and (scene=='ALL' or r['scene']==scene)];good=[r for r in rr if r['technical_validation']=='PASS']
                row=dict(phase=phase,method=method,scene=scene,n=len(rr),valid=len(good))
                for k in ('success','collision','wrong_stop','timeout_without_declaration','box_passage'):
                    row[k]=sum(bool(r[k]) for r in good) if good else None
                for k in ('goal_time_s','stopped_s','box_passage_from_spawn_s'):
                    row[k+'_median']=median([r[k] for r in good if r.get(k) is not None])
                attempts=sum(r.get('u_attempts',0) for r in good);applied=sum(r.get('u_applied',0) for r in good)
                row.update(u_attempts=attempts if phase=='Phase62' else None,u_applied=applied if phase=='Phase62' else None,
                    u_adoption_rate=applied/attempts if attempts else None,
                    u_solution_length_median_m=median([x for r in good for x in r.get('u_install_lengths_m',[])]),
                    u_goal_distance_at_solve_median_m=median([x for r in good for x in r.get('u_goal_distances_at_solve_m',[])]))
                summary.append(row)
    by={(r['scene'],r['index']):r for r in runs};pairs=[]
    for j in p['main_order']:
        r=by.get((j['scene'],j['index']),{});row=dict(j,status=r.get('technical_validation','NOT_RUN'));row.update({k:r.get(k) for k in FIELDS})
        for method in ('CUT','CONS','CONS+G18'):
            b=next((e for e in baseline if e['scene']==j['scene'] and e['index']==j['index'] and e['method']==method),{})
            row['P61_'+method+'_status']=b.get('technical_validation','NOT_AVAILABLE');row.update({'P61_'+method+'_'+k:b.get(k) for k in FIELDS[:9]})
        pairs.append(row)
    status=dict(status='COMPLETE' if len(runs)==6 else 'PARTIAL' if runs else 'PREPARED_NOT_RUN',planned=6,completed=len(runs),oracle_analysis_only=True,
        protocol_sha256=sha256_file(HERE/'protocol.json'),phase61_results_sha256=sha256_file(BASELINE))
    save(output/'runs.json',runs);save(output/'status.json',status);csvout(output/'summary.csv',summary);csvout(output/'paired.csv',pairs)
    from .figures import generate as figures
    files=figures(runs,output/'figures');save(output/'figures.json',dict(files=files,count=len(files),force_stage_png=True))
    doc=Path(document) if document else ROOT/'docs/PHASE62P_RESULTS.md'
    shown=lambda rr:table([{k:('—' if v is None else v) for k,v in r.items()} for r in rr])
    text=['# Phase62-P UG-GOAL — oracle 위치추정 분석용 조건',table([status]),
        'Phase61-P의 oracle 위치추정·D075·ENDPOINT latch·1s 만료·PP/SP·EC 제동꼬리·CUT fallback을 유지한다. U-Graph는 Phase55-P의0≤v≤0.3 solver에 r_goal=(p_N−target_xy)/0.3m 한 항만 더했다. 나머지 factor·초기값11개·4process·solver 옵션은 동결이다.',
        '목표는 최근 도착 chunk의 관측 시점 oracle 노드+2(마지막 노드 clamp)이며 다음 chunk 전까지0.5초 주기 재풀이에서도 고정한다. 실제 풀이 시작점은 그때의 실제 pose/v/ω다. Graph XY를 동결 PP/SP로 실행하며 Graph v/ω를 직접 실행하지 않는다.',
        'U 채택률은 실제 설치된 U 해/풀이 시도다. 해 길이는 실제 채택된 U XY 호장(정지 해0 포함)의 중앙값이다. 풀이 pose–목표 거리는 모든 풀이 시점 실제 pose와 고정 목표 노드 사이 거리의 run별 중앙값이며,ALL은 풀이 사건을 합쳐 구한 중앙값이다. Phase61 같은 scene·seed 결과는 기존 발표값을 옆 열에 그대로 둔다.',
        shown(summary),shown(pairs)]
    for file in files:
        f=Path(file);text.append(f'![{f.stem}](../{f.relative_to(ROOT)})' if f.is_relative_to(ROOT) else f'![{f.stem}]({f})')
    doc.write_text('\n\n'.join(text)+'\n');return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate()
    if a.publish:
        paths=stage_report(doc,OUT)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase62-P U-Graph goal pilot with Phase61 comparisons and figures','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
