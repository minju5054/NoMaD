"""Reporting-only final audit. Never changes methods, protocol or predicates."""
import csv,hashlib,json,shutil,statistics,subprocess,time
from collections import Counter
from pathlib import Path
import numpy as np
from .config import ROOT,HERE,OUT,RUN_ROOT,verify
from .report import read,save,table,confirm_decision,dev_gate,baselines,publish

def csv_write(path,rows):
    if not rows:path.write_text('');return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as stream:
        w=csv.DictWriter(stream,keys);w.writeheader();w.writerows(rows)

def main():
    p=verify();state=read(RUN_ROOT/'state.json');d=read(OUT/'decision.json')
    assert state['status'] in ('COMPLETE','STOP_DEV_FAIL','STOP_BLOCKED','PARTIAL')
    rows=[read(f) for f in sorted((RUN_ROOT/'metrics').glob('*.json'))]
    conf=[r for r in rows if r['stage']=='confirm'];dev=[r for r in rows if r['stage']=='dev']
    assert dev_gate(dev,baselines())==d['dev_gate']
    totals=[];enriched=[];checks=[]
    if state['status']=='COMPLETE' and len(conf)==60 and all(r['technical_validation']=='PASS' for r in conf):
        assert len(conf)==60 and all(r['technical_validation']=='PASS' for r in conf)
        expected={(r['scene'],r['index'],r['method']) for r in p['confirm']}
        assert {(r['scene'],r['index'],r['method']) for r in conf}==expected
        recomputed=confirm_decision(conf)
        for key in ('label','checks','sm_clearance_median_m','sm_goal_time_median_s','c0_goal_time_median_s'):assert d[key]==recomputed[key]
        groups={m:{(r['scene'],r['index']):r for r in conf if r['method']==m} for m in ('C0','C0-NA','SM','G18')}
        for m,g in groups.items():totals.append(dict(method=m,n=len(g),goal=sum(r['success'] for r in g.values()),collision=sum(r['collision'] for r in g.values())))
        for other in ('C0','C0-NA','SM'):
            for key,g in groups['G18'].items():
                b=groups[other][key]
                enriched.append(dict(scene=key[0],index=key[1],comparison='G18-'+other,g18_success=g['success'],baseline_success=b['success'],
                    goal_difference=int(g['success'])-int(b['success']),collision_difference=int(g['collision'])-int(b['collision']),
                    minimum_clearance_difference_m=g['minimum_clearance_m']-b['minimum_clearance_m'],
                    goal_time_difference_s=g['goal_time_s']-b['goal_time_s'] if g['success'] and b['success'] else None,
                    mean_speed_difference_m_s=g['mean_speed_m_s']-b['mean_speed_m_s'],
                    stop_fraction_difference=g['stopped_fraction']-b['stopped_fraction'],
                    omega_saturation_difference=g['omega_saturation_fraction']-b['omega_saturation_fraction']))
        vals=lambda name,key:[r[key] for r in enriched if r['comparison']=='G18-'+name and r[key] is not None]
        sm_clear=statistics.median(vals('SM','minimum_clearance_difference_m'))
        sm_t=vals('SM','goal_time_difference_s');c_t=vals('C0','goal_time_difference_s')
        counts={r['method']:r for r in totals};g=counts['G18'];na=counts['C0-NA'];sm=counts['SM'];c=counts['C0']
        a=g['collision']<na['collision'] and g['goal']>=na['goal']
        b=sm_clear>0 and g['collision']<=sm['collision'] and bool(sm_t) and statistics.median(sm_t)<=3
        cc=bool(c_t) and statistics.median(c_t)<0 and g['collision']<=c['collision']
        assert dict(a=a,b=b,c=cc)==d['checks']
        assert sm_clear==d['sm_clearance_median_m']
        checks=[dict(condition='a',passed=a,evidence=f"collision {g['collision']} < {na['collision']}; goal {g['goal']} >= {na['goal']}"),
            dict(condition='b',passed=b,evidence=f"clearance median {sm_clear:.6f}m >0 (n=15); collision {g['collision']} <= {sm['collision']}; goal-time median {statistics.median(sm_t) if sm_t else None}s <=3 (n={len(sm_t)})"),
            dict(condition='c',passed=cc,evidence=f"goal-time median {statistics.median(c_t) if c_t else None}s <0 (n={len(c_t)}); collision {g['collision']} <= {c['collision']}")]
    attempts=[read(f) for f in (RUN_ROOT/'attempt_metrics').glob('*.json')]
    technical_attempts=sum(r['technical_validation']!='PASS' for r in attempts)
    cleanup=[];workers=[];timing=[];all_reasons={}
    for r in rows:
        root=Path(r['output']);cfg=read(root/'scenario.json')
        if r['technical_validation']!='PASS':continue
        assert cfg['timeout_sim_s']==90 and cfg['goal_tolerance_m']==.3 and cfg['seed_offset']==10000*r['index']
        clean=read(root/'phase28_cleanup.json');assert clean['enabled'] and clean['processes_finished']
        assert not (root/'portable/cache').exists() and not (root/'pycache').exists();cleanup.append(str(root))
        if r['method']=='G18':
            w=read(root/'phase29_worker_provenance.json');assert w['affinity']['passed'] and w['affinity']['actual']==[7];workers.append(str(root))
            events=[json.loads(s) for s in (root/'phase29_paths.jsonl').read_text().splitlines()]
            results=[e for e in events if e['event']=='RESULT'];assert sum(e['event']=='SUBMIT' for e in events)==r['path_jobs']
            assert sum(e['applied'] for e in results)==r['path_applied']
            for e in results:json.dumps(e)
            times=[e['wall_s'] for e in results];full=[e['dispatch_to_result_s'] for e in results if e.get('dispatch_to_result_s') is not None]
            timing.append(dict(stage=r['stage'],scene=r['scene'],index=r['index'],jobs=len(results),worker_p50_s=float(np.median(times)) if times else None,worker_p95_s=float(np.quantile(times,.95)) if times else None,
                dispatch_to_result_n=len(full),dispatch_to_result_p50_s=float(np.median(full)) if full else None,dispatch_to_result_p95_s=float(np.quantile(full,.95)) if full else None))
            counter=all_reasons.setdefault(r['stage'],Counter());counter.update(e['disposition'] for e in results)
    changed=subprocess.check_output(['git','diff','8b5aed3','--name-only'],cwd=ROOT,text=True).splitlines()
    assert all(f.startswith(('research/nomad_phase29/','research/results/phase29/','docs/PHASE29_GOAL_REPORT.md')) for f in changed),changed
    audit=dict(label=d['label'],counts=totals,criterion_audit=checks,technical_attempt_failures=technical_attempts,
        retries=sum(r['attempt']==2 for r in attempts),completed=Counter(r['stage'] for r in rows),cleanup_verified=len(cleanup),cpu7_workers_verified=len(workers),
        free_bytes=shutil.disk_usage(ROOT).free,elapsed_minutes=(time.time()-p['goal_start_epoch'])/60,
        runtime_sources_unchanged=True,prior_tracked_files_unchanged=True,reporting_only_finalizer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    save(OUT/'final_audit.json',audit);csv_write(OUT/'summary.csv',read(OUT/'summary.json'));csv_write(OUT/'paired.csv',enriched);csv_write(OUT/'graph_timing.csv',timing)
    save(OUT/'rejection_totals.json',{s:dict(v) for s,v in all_reasons.items()})
    d['final_audit']=dict(file='final_audit.json',technical_attempt_failures=technical_attempts,dev_gate_verified=True,confirmation_criteria_verified=bool(checks),counts=totals)
    save(OUT/'decision.json',d)
    if totals:
        core='; '.join(f"{r['method']} 도착 {r['goal']}/15·충돌 {r['collision']}" for r in totals)
        number=lambda x,fmt:'NA' if x is None else format(x,fmt)
        pairs=f"G18−SM 여유 {number(d['sm_clearance_median_m'],'+.4f')}m, 도착시간 {number(d['sm_goal_time_median_s'],'+.3f')}s; G18−C0 도착시간 {number(d['c0_goal_time_median_s'],'+.3f')}s"
    else:core='dev gate: '+json.dumps(d['dev_gate'],ensure_ascii=False);pairs='불완전 확인 단계는 최종 가설 판정에 대체/합산하지 않음.'
    morning=[f"1. 최종 라벨: **{d['label']}**",f"2. 완료: {dict(audit['completed'])}; 기술 실패 {technical_attempts}, 재시도 {audit['retries']}",f'3. {core}',f'4. {pairs}',f"5. 종료 단계: {state['stage']} — {state.get('reason','')}; 경과 {audit['elapsed_minutes']:.1f}분, 여유 {audit['free_bytes']/1e9:.1f}GB."]
    doc=ROOT/'docs/PHASE29_GOAL_REPORT.md';body=doc.read_text().split('\n',5)[5]
    addition='\n\n## 확인 판정 독립 검산\n\n'+table(checks)+'\n\n'+table(totals)+'\n\n도착시간 및 그 짝 차이는 둘 다 도착한 짝만 사용한다. 최소여유·평균속도·정지비율·ω 포화는 실패를 포함한 모든 기술 유효 run을 사용한다. `paired.csv`에는 짝별 도착/충돌 차이와 연속 지표 차이를 함께 기록했다. dev 및 smoke는 확인 판정에 포함하지 않았다.\n\nG18 적용은 유효 결과를 NORMAL 실행기의 경로로 설치한 사건이다. CPU7 고정, cache 정리, seed/90s/goal radius 및 원 소스 보존을 final_audit.json으로 검증했다. 계산시간은 worker 처리와 dispatch→결과 수신을 구분해 graph_timing.csv에 기록했다(terminal-unapplied의 수신 총시간이 없는 행은 후자에서 제외, n 별도).\n\nPhase29 protocol의 과거 Phase28 R1 항목은 재사용한 등록 틀의 이력이다. G18은 실제로 동결 graph_v4_protocol와 ClearanceGraph를 사용하며, H의 시간 매개 궤적/속도·0.15s 수치 budget은 사용하지 않는다. SM은 Phase22 P3의 기하 연산을 평소 suffix에 적용한다. 실행 중 수치·방법·판정의 수정 및 튜닝은 없었다.\n'
    doc.write_text('\n'.join(morning)+'\n'+body+addition)
    save(OUT/'morning_summary.json',morning);publish('final report audit and morning summary')
    print(json.dumps(audit,ensure_ascii=False))
if __name__=='__main__':main()
