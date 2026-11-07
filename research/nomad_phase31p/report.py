"""Phase31-P-only decision; historical tables are explicitly descriptive."""
import argparse,csv,json,subprocess
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_phase26.metrics import audit as original_audit
from nomad_phase29.metrics import audit as graph_audit
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,verify

def read(p):return json.loads(Path(p).read_text())
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def median(xs):return float(np.median(xs)) if xs else None
def table(rows):
    if not rows:return '자료 없음'
    keys=list(rows[0]);fmt=lambda x:'—' if x is None else f'{x:.5g}' if isinstance(x,float) else str(x).replace('|','/')
    return '\n'.join(['| '+' | '.join(keys)+' |','|'+'|'.join(['---']*len(keys))+'|']+['| '+' | '.join(fmt(r.get(k)) for k in keys)+' |' for r in rows])
def csv_write(p,rows):
    if not rows:p.write_text('');return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='') as f:w=csv.DictWriter(f,keys,lineterminator='\n');w.writeheader();w.writerows(rows)

def audit(root):
    cfg=read(Path(root)/'scenario.json');method=cfg['phase31p_method']
    r=graph_audit(root) if method=='G18-R' else original_audit(root)
    r.update(method=method,study='Phase31-P',mean_speed_m_s=r['distance_m']/r['duration_s'])
    return r

def decide(rows):
    expected={(s,i,m) for s in SCENES for i in INDICES for m in METHODS}
    keys=[(r['scene'],r['index'],r['method']) for r in rows]
    complete=len(rows)==30 and len(set(keys))==30 and set(keys)==expected
    valid=complete and all(r['technical_validation']=='PASS' and r.get('collision') is not None for r in rows)
    count={m:dict(n=sum(r['method']==m for r in rows),goal=sum(bool(r.get('success')) for r in rows if r['method']==m),
                  collision=sum(bool(r.get('collision')) for r in rows if r['method']==m)) for m in METHODS}
    g,na,c=count['G18-R'],count['C0-NA'],count['C0']
    checks=dict(goal_gt_na=g['goal']>na['goal'],collision_le_na=g['collision']<=na['collision'],
                goal_ge_c0=g['goal']>=c['goal'],collision_le_c0=g['collision']<=c['collision'])
    return dict(label='EXPAND' if valid and all(checks.values()) else 'HOLD',evidence_valid=valid,checks=checks,
        phase31p_only_counts=count,complete_blocks=sum(all(any((r['scene'],r['index'],r['method'])==(s,i,m) and r['technical_validation']=='PASS' for r in rows) for m in METHODS) for s in SCENES for i in INDICES),
        reason='All four registered conditions pass' if valid and all(checks.values()) else 'Registered conditions not all satisfied' if valid else 'Incomplete or technically invalid10-pair evidence; no EXPAND claim',
        historical_used=False,auxiliary_metrics_used=False)

def paired(rows):
    result=[]
    for scene in SCENES:
        for index in INDICES:
            block={r['method']:r for r in rows if (r['scene'],r['index'])==(scene,index) and r['technical_validation']=='PASS'}
            if 'G18-R' not in block:continue
            g=block['G18-R']
            for method in ('C0','C0-NA'):
                if method not in block:continue
                b=block[method]
                result.append(dict(scene=scene,index=index,comparison='G18-R minus '+method,
                    g_goal=g['success'],baseline_goal=b['success'],goal_difference=int(g['success'])-int(b['success']),
                    collision_difference=int(g['collision'])-int(b['collision']),
                    goal_time_difference_s=g['goal_time_s']-b['goal_time_s'] if g['success'] and b['success'] else None,
                    **{k+'_difference':g[k]-b[k] for k in ('mean_speed_m_s','stopped_fraction','minimum_clearance_m')}))
    return result

def historical():
    # Do not double-count reused Phase27-R/28 rows inside Phase29 runs.json,
    # and do not relabel the old 0.15m G18 as G18-R.
    old29=[dict(r,study='Phase29 confirm') for r in read(ROOT/'research/results/phase29/runs.json') if r.get('stage')=='confirm' and r['method'] in ('C0','C0-NA')]
    old30=[dict(r,study='Phase30-R') for r in read(ROOT/'research/results/phase30r/runs.json') if r['method']=='G18-R']
    return old29+old30

def summary(rows,scope):
    output=[]
    for scene in (*SCENES,'ALL'):
        for method in METHODS:
            allrows=[r for r in rows if r['method']==method and (scene=='ALL' or r['scene']==scene)]
            valid=[r for r in allrows if r['technical_validation']=='PASS']
            if not allrows:continue
            output.append(dict(scope=scope,scene=scene,method=method,n=len(allrows),valid=len(valid),goal=sum(r['success'] for r in valid),collision=sum(r['collision'] for r in valid),
                goal_time_s=median([r['goal_time_s'] for r in valid if r['success']]),
                **{k:median([r[k] for r in valid if r.get(k) is not None]) for k in ('mean_speed_m_s','stopped_fraction','minimum_clearance_m')}))
    return output

def generate(root):
    p=verify();rows=[dict(read(f),study='Phase31-P') for f in sorted((root/'metrics').glob('*.json'))]
    for r in rows:
        assert r['method'] in METHODS and r['index'] in INDICES and r['scene'] in SCENES
        assert Path(r['output']).resolve().is_relative_to(RUN_ROOT.resolve()/'main')
    decision=decide(rows);pairs=paired(rows);stats=summary(rows,'Phase31-P primary')
    times=[r['goal_time_difference_s'] for r in pairs if r['comparison']=='G18-R minus C0' and r['goal_time_difference_s'] is not None]
    auxiliary=dict(c0_both_success_pairs=len(times),c0_goal_time_difference_median_s=median(times))
    graph=[dict(scene=r['scene'],index=r['index'],technical=r['technical_validation'],jobs=r.get('path_jobs',0),applied=r.get('path_applied',0),
                application_rate=r.get('path_applied',0)/r['path_jobs'] if r.get('path_jobs') else None,rejections=r.get('path_reasons',{})) for r in rows if r['method']=='G18-R']
    prior=historical();historical_sections=[]
    for source in ('Phase29 confirm','Phase30-R','Phase31-P'):
        historical_sections.extend(summary([r for r in prior+rows if r['study']==source],source+' descriptive'))
    pooled=summary(prior+rows,'Pooled historical+Phase31-P descriptive ONLY')
    OUT.mkdir(parents=True,exist_ok=True)
    save(OUT/'runs.json',rows);save(OUT/'decision.json',dict(decision,auxiliary=auxiliary));csv_write(OUT/'summary.csv',stats);csv_write(OUT/'paired.csv',pairs)
    save(OUT/'graph_statistics.json',graph);save(OUT/'historical_runs.json',prior)
    csv_write(OUT/'historical_by_source.csv',historical_sections);csv_write(OUT/'historical_combined.csv',pooled)
    technical=[dict(scene=r['scene'],index=r['index'],method=r['method'],error=r.get('error'),attempt_count=r.get('attempt_count')) for r in rows if r['technical_validation']!='PASS']
    save(OUT/'technical_failures.json',technical)
    from nomad_isaac.common import sha256_file
    doc=ROOT/'docs/PHASE31P_RESULTS.md'
    doc.write_text('# Phase31-P 동결 방법 비교\n\n**'+decision['label']+'** — Phase31-P seed206/207만 판정에 사용. protocol SHA256 `'+sha256_file(HERE/'protocol.json')+'`.\n\n'+table([dict(method=m,**v) for m,v in decision['phase31p_only_counts'].items()])+'\n\n'+json.dumps(decision,ensure_ascii=False,indent=2)+'\n\n## 주 실험\n\n'+table(stats)+'\n\n'+table(pairs)+'\n\n## 보조 지표 — 판정 미사용\n\n'+table([auxiliary])+'\n\n'+table(graph)+'\n\n도착시간 짝 차이는 둘 다 도착한 동일 scene×seed만 사용한다. 평균속도·정지비율·최소여유는 기술 유효 run 전체이며 최소여유는 참고다. G18-R 적용은 동결 실행기의 경로 설치 사건이며, 거절 사유는 기존 로그 정의를 따른다. 기술 실패는1회 재시도 후에도 유효하지 않으면 원 자료를 보존하고 HOLD(근거 불완전)로 보고한다.\n\n## 과거 자료를 합친 표 — 판정 미사용\n\nPhase29의 실제 confirm C0/C0-NA만 사용하고 그 파일에 중복 저장된 reused/dev/smoke 행은 제외했다. Phase30-R에서는 실제 G18-R 행만 사용했다. Phase29 G18(0.15m)은 다른 방법이므로 합치지 않는다. seed·실행 시점·방법별 n이 달라 아래 표는 서술용이며 EXPAND/HOLD 계산 함수에 전달하지 않는다.\n\n'+table(historical_sections)+'\n\n'+table(pooled)+'\n\n## 기술 실패\n\n'+table(technical)+'\n')
    return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    root=a.run_root.resolve();assert root==RUN_ROOT.resolve();doc=generate(root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase31-P frozen-method pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
