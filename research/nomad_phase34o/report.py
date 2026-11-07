"""Saved-input EC comparison, uncertainty bounds and reproducible offline report."""
import argparse, hashlib, json, time
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase15b.depth import Snapshot
from nomad_phase33p.storage import install
from nomad_phase32o.exec_cert import certify
from nomad_phase32o.evaluate import save, csvout
from .inputs import OUT
from .evaluate import read, sha, verify


def lines(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines() if x] if Path(p).exists() else []


def quantile(values, q):
    values=[v for v in values if v is not None]
    return float(np.quantile(values,q)) if values else None


def summary(rows):
    n=len(rows); solved=sum(r['solution'] for r in rows)
    passed=sum(r['ec_pass'] is True for r in rows)
    missing=sum(r['solution'] and r['ec_pass'] is None for r in rows)
    return dict(n=n, solutions=solved, solution_rate=solved/n, ec_pass=passed,
        ec_missing_solutions=missing, ec_observed_solutions=solved-missing,
        ec_conditional_observed=passed/(solved-missing) if solved>missing else None,
        ec_conditional_lower=passed/solved if solved else None,
        ec_conditional_upper=(passed+missing)/solved if solved else None,
        joint_EC_lower=passed/n, joint_EC_upper=(passed+missing)/n,
        plan_clearance_p10_m=quantile([r['plan_clearance_m'] for r in rows],.1),
        plan_clearance_p50_m=quantile([r['plan_clearance_m'] for r in rows],.5),
        plan_clearance_p90_m=quantile([r['plan_clearance_m'] for r in rows],.9),
        plan_clearance_min_m=min((r['plan_clearance_m'] for r in rows if r['plan_clearance_m'] is not None),default=None),
        pool_p50_s=quantile([r['pool_wall_s'] for r in rows],.5),
        pool_p95_s=quantile([r['pool_wall_s'] for r in rows],.95))


def gate(base, clr):
    a=clr['solution_rate'] >= base['solution_rate']-.05-1e-12
    low=clr['joint_EC_lower']-base['joint_EC_upper']
    high=clr['joint_EC_upper']-base['joint_EC_lower']
    c=True if low>=.20-1e-12 else False if high<.20-1e-12 else None
    ratio=clr['pool_p95_s']/base['pool_p95_s']
    timing=ratio<=1.3+1e-12
    label='OFFLINE_FAIL' if False in (a,c,timing) else 'OFFLINE_OK' if all(x is True for x in (a,c,timing)) else 'INDETERMINATE_MISSING_EC'
    return dict(label=label,criteria=dict(a_solution_rate=a,c_joint_EC_increase=c,e_time=timing),
        solution_rate_difference_pp=100*(clr['solution_rate']-base['solution_rate']),
        joint_EC_difference_lower_pp=100*low,joint_EC_difference_upper_pp=100*high,
        pool_p95_ratio=ratio, missing_EC_cannot_reach_gate=high<.20-1e-12,
        navigation_prepared=False,simulation_runs=0)


def previous_archive_context(case):
    """Strictly descriptive proxy only; never enters the gate."""
    p=ROOT/'research/results/phase32o/per_run'/f"{case['uid']}.json"
    if not p.exists() or not case['actual_install']:
        return None
    rows=read(p)['events']; tick=case['actual_install']['tick']
    rows=[r for r in rows if round(r['install_s']*72)==tick and r['kind']=='REPAIR']
    if not rows:return None
    r=rows[0]
    if r['exact_install_map']:return None
    return dict(file=r['snapshot_file'],extra_age_s=r['extra_archive_staleness_s'])


def analyze():
    p=verify(); assert p['status']=='FROZEN' and p['ec_policy']['no_result']=='UNMEASURED'
    install(); cases=read(OUT/'inputs.json'); rows=[];samples=[]; regressions=[]; extra_hashes={}
    original_logs={}; available=0
    for ordinal,c in enumerate(cases):
        data=read(OUT/'numeric'/f"{c['case_id']}.json")
        context=c['ec_context']; field=Snapshot.load(context['snapshot_file']) if context and context['snapshot_file'] else None
        proxy_context=previous_archive_context(c) if context and field is None else None
        proxy=Snapshot.load(proxy_context['file']) if proxy_context else None
        if proxy_context:extra_hashes[proxy_context['file']]=sha(proxy_context['file'])
        checks={}
        for variant in ('R2','R2_CLR'):
            numeric=data['variants'][variant]; selected=numeric['selected_sample']
            solution=numeric['results'][selected] if selected is not None else None
            assert solution is None or solution['accepted']
            check=(certify(context['pose'],context['actual_vw'],solution['path'],field,speed_cap=context['speed_cap_m_s'])
                if solution and field is not None else None)
            proxy_check=(certify(context['pose'],context['actual_vw'],solution['path'],proxy,speed_cap=context['speed_cap_m_s'])
                if solution and proxy is not None else None)
            checks[variant]=dict(selected=selected,EC=check,older_archive_proxy=proxy_check,proxy_context=proxy_context)
            row=dict(case_id=c['case_id'],uid=c['uid'],root=c['root'],stage=c['stage'],scene=c['scene'],index=c['index'],
                source_method=c['method'],job_id=c['job_id'],variant=variant,solution=solution is not None,
                selected_sample=selected,ec_context=context['source'] if context else 'NO_RESULT',
                ec_map_status=context['map_status'] if context else 'NO_RESULT',
                ec_pass=bool(check['passed']) if check else (False if solution is None else None),
                ec_reason=check['reason'] if check else 'NO_SOLUTION' if solution is None else 'UNMEASURED',
                ec_clearance_m=check.get('clearance_m') if check else None,
                plan_clearance_m=solution['depth_clearance_m'] if solution else None,
                mean_edit_m=solution['mean_edit_m'] if solution else None,
                pool_wall_s=numeric['pool_wall_s'],
                accepted_samples=sum(r['accepted'] for r in numeric['results']),
                old_proxy_ec_pass=proxy_check['passed'] if proxy_check else None,
                old_proxy_extra_age_s=proxy_context['extra_age_s'] if proxy_context else None,
                collision_uid=c['collision_uid'])
            rows.append(row)
            for i,r in enumerate(numeric['results']):
                costs=r.get('factor_costs',{})
                extra=(r['objective']-sum(costs.values())) if variant=='R2_CLR' and 'objective' in r else 0.
                samples.append(dict(case_id=c['case_id'],variant=variant,sample=i,accepted=r['accepted'],
                    disposition=r['disposition'],selected=i==selected,iterations=r.get('iterations'),
                    objective=r.get('objective'),clearance_soft_cost=extra,depth_clearance_m=r.get('depth_clearance_m'),
                    constraint_violation=r.get('constraint_violation'),mean_edit_m=r.get('mean_edit_m'),
                    attempt_wall_s=r['attempt_wall_s']))
        # Reference-only actual installed path, without feeding it into either
        # solver or selecting a candidate after EC.
        app=c['actual_install']
        if app and field is not None:
            checks['PATH_APPLIED']=certify(context['pose'],context['actual_vw'],app['path_world'],field,speed_cap=context['speed_cap_m_s'])
        save(OUT/'ec'/f"{c['case_id']}.json",checks)
        # Reproduction check of the original numerical job, before online EC.
        if c['run'] not in original_logs:
            file=Path(c['run'])/'repair_pool_jobs.jsonl';extra_hashes[str(file)]=sha(file)
            original_logs[c['run']]={x['job_id']:x for x in lines(file) if x.get('kind')=='R2'}
        logged=original_logs[c['run']].get(c['job_id']); replay=data['variants']['R2']
        if logged and len(logged.get('results',[]))==8:
            errors=[]; matches=[]
            for saved,new in zip(logged['results'],replay['results']):
                matches.append(saved['disposition']==new['disposition'] and saved['accepted']==new['accepted'])
                if saved.get('path') is not None and new.get('path') is not None:
                    errors.append(float(np.max(np.abs(np.asarray(saved['path'])-np.asarray(new['path'])))))
            regressions.append(dict(case_id=c['case_id'],available=True,
                all_dispositions_match=all(matches),dispositions_matched=sum(matches),
                selected_index_match=logged['selected_sample']==replay['selected_sample'],
                maximum_path_coordinate_difference_m=max(errors,default=0.),
                paths_within_1e6=all(e<=1e-6 for e in errors),paths_compared=len(errors)))
        else:regressions.append(dict(case_id=c['case_id'],available=False))
        if ordinal%50==0:print(f'[EC] {ordinal+1}/{len(cases)}',flush=True)
    csvout(OUT/'jobs.csv',rows);csvout(OUT/'samples.csv',samples);csvout(OUT/'regression.csv',regressions)
    save(OUT/'additional_input_hashes.json',extra_hashes)
    summaries=[]
    groups=[('ALL',lambda r:True),('ACTUAL_INSTALL',lambda r:r['ec_context']=='ACTUAL_INSTALL'),
            ('RESULT_DECISION_COUNTERFACTUAL',lambda r:r['ec_context']=='RESULT_DECISION_COUNTERFACTUAL')]
    groups += [(root,lambda r,root=root:r['root']==root) for root in sorted({r['root'] for r in rows})]
    for group,predicate in groups:
        for variant in ('R2','R2_CLR'):
            subset=[r for r in rows if r['variant']==variant and predicate(r)]
            summaries.append(dict(group=group,variant=variant,**summary(subset)))
    decision=gate(summaries[0],summaries[1]);decision['summaries']=summaries[:2]
    decision['EC_policy']=p['ec_policy'];decision['protocol_sha256']=sha(Path(__file__).with_name('protocol.json'))
    csvout(OUT/'summary.csv',summaries);save(OUT/'decision.json',decision)
    failures=Counter((r['variant'],r['disposition']) for r in samples)
    csvout(OUT/'sample_dispositions.csv',[dict(variant=v,disposition=d,count=n) for (v,d),n in sorted(failures.items())])
    paired=[];collisions=[]
    for c in cases:
        pair={r['variant']:r for r in rows if r['case_id']==c['case_id']};a,b=pair['R2'],pair['R2_CLR']
        paired.append(dict(case_id=c['case_id'],scene=c['scene'],source_method=c['method'],
            R2_solution=a['solution'],CLR_solution=b['solution'],R2_EC=a['ec_pass'],CLR_EC=b['ec_pass'],
            plan_clearance_difference_m=b['plan_clearance_m']-a['plan_clearance_m'] if a['solution'] and b['solution'] else None,
            pool_time_difference_s=b['pool_wall_s']-a['pool_wall_s']))
        if c['collision_uid']:
            checks=read(OUT/'ec'/f"{c['case_id']}.json")
            collisions.append(dict(case_id=c['case_id'],uid=c['collision_uid'],scene=c['scene'],method=c['method'],
                job_id=c['job_id'],install_s=c['ec_context']['simulation_time_s'],
                latest_map_status=c['ec_context']['map_status'],
                R2_solution=a['solution'],R2_EC=a['ec_pass'],R2_plan_clearance_m=a['plan_clearance_m'],
                CLR_solution=b['solution'],CLR_EC=b['ec_pass'],CLR_plan_clearance_m=b['plan_clearance_m'],
                actual_path_EC=checks.get('PATH_APPLIED',{}).get('passed'),
                CLR_old_proxy_EC=b['old_proxy_ec_pass'],proxy_extra_age_s=b['old_proxy_extra_age_s']))
    csvout(OUT/'paired.csv',paired);csvout(OUT/'collisions.csv',collisions)
    save(OUT/'analysis.json',dict(rows=rows,summaries=summaries,collisions=collisions,regression=regressions))
    return decision


def text_table(rows,columns):
    def value(v):
        if v is None:return '미측정/해 없음'
        if isinstance(v,bool):return 'PASS' if v else 'FAIL'
        if isinstance(v,float):return f'{v:.6f}'
        return str(v)
    return '\n'.join(['| '+' | '.join(title for key,title in columns)+' |',
        '| '+' | '.join('---' for _ in columns)+' |']+
        ['| '+' | '.join(value(r.get(key)) for key,title in columns)+' |' for r in rows])


def figures(analysis):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rows=analysis['rows'];fig,axes=plt.subplots(1,2,figsize=(10,3.6))
    for ax,key,label in zip(axes,['plan_clearance_m','pool_wall_s'],['Selected path clearance (m)','Whole 8-sample / 4-process job (s)']):
        values=[[r[key] for r in rows if r['variant']==v and r[key] is not None] for v in ('R2','R2_CLR')]
        ax.boxplot(values,labels=['R2','R2+CLR'],showfliers=False);ax.set_ylabel(label);ax.grid(axis='y',alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'clearance_time.png',dpi=170);plt.close(fig)


def document():
    a=read(OUT/'analysis.json');d=read(OUT/'decision.json');p=read(Path(__file__).with_name('protocol.json'));audit=read(OUT/'input_audit.json')
    base,clr=d['summaries'];r=[x for x in a['regression'] if x['available']]
    gate_rows=[dict(criterion='(a) 해 있음: 기준 대비 −5%p 이내',result=d['criteria']['a_solution_rate'],evidence=f"{100*base['solution_rate']:.2f}% → {100*clr['solution_rate']:.2f}%"),
        dict(criterion='(c) 전체 job 대비 solve+EC: +20%p 이상',result=d['criteria']['c_joint_EC_increase'],evidence=f"CLR−R2 범위 {d['joint_EC_difference_lower_pp']:+.2f}~{d['joint_EC_difference_upper_pp']:+.2f}%p"),
        dict(criterion='(e) 전체 job p95 ≤ 기준 ×1.3',result=d['criteria']['e_time'],evidence=f"{base['pool_p95_s']:.6f}s → {clr['pool_p95_s']:.6f}s (×{d['pool_p95_ratio']:.3f})")]
    main_columns=[('variant','방법'),('n','job'),('solutions','해 있음'),('solution_rate','(a) 비율'),
        ('ec_pass','EC PASS'),('ec_missing_solutions','해 있음/EC 미측정'),
        ('ec_conditional_lower','(b) 하한'),('ec_conditional_upper','(b) 상한'),
        ('joint_EC_lower','(c) 하한'),('joint_EC_upper','(c) 상한'),('pool_p50_s','(e) p50 s'),('pool_p95_s','p95 s')]
    text=f'''# Phase34-O: R2+CLR 오프라인 확인

판정: **{d['label']}**. Phase28~32의 실험 run 87개에서 R2 job 411개(8 sample/job)를 원본과 CLR로 각각 한 번씩 재풀이했다. Phase34-P의 44건을 모두 포함한다. 주행 준비와 시뮬레이션은 하지 않았다.

해 있음 {base['solutions']}/411 → {clr['solutions']}/411, 확인된 solve+EC PASS {base['ec_pass']}/411 → {clr['ec_pass']}/411. 최신 지도/시점 누락을 포함한 차이 범위는 {d['joint_EC_difference_lower_pp']:+.2f}~{d['joint_EC_difference_upper_pp']:+.2f}%p이며, 요구치는 +20%p이다. 전체 job 시간 p95는 {base['pool_p95_s']:.6f}s → {clr['pool_p95_s']:.6f}s이다.

## 변경 범위와 재현

새 모듈 `nomad_phase34o.repair.RepairGraphCLR`은 `RepairGraphR2`의 residual/Jacobian만 확장한다. 기존 intent(σ=0.10m), smoothness(σ=0.02m), heading(σ=30°), 신뢰영역 ±0.75m, 곡률 ≤8m⁻¹, 길이 보존, 초기화, 시작 0.30m 완화, 정확 certificate, SLSQP(maxiter=100, ftol=1e−8)는 그대로다.

추가 residual은 각 구간의 9개 검사점에서 `r_CLR(q)=max(0,0.15−d_depth(q))/0.05`; 목적함수는 원본과 같이 `0.5 Σr²`이다. 경계점 중복도 R3와 동일하게 유지한다. 활성 구간 Jacobian은 `−∇d(q)·dq/dp / 0.05`, 비활성 구간은 0이다. R2는 7구간/63점이다. oracle은 solver·선택·EC 입력에 사용하지 않았다.

수락은 원본의 solver 성공 + hard 위반≤1e−7 + 원본 certificate이며, 8개 중 평균 수정량이 가장 작은 수락 해를 선택한다(동률 sample index). EC로 후보를 다시 고르지 않는다. 해가 없으면 EC 실패로 센다. 계산시간은 기존 `evaluate_job.pool_wall_s`: 미리 기동한 4-process pool의 8개 풀이·map 복원·IPC·선택을 포함하며 EC 시간은 제외한다. 원본/CLR 실행 순서는 job별로 교대했다. 원본 runtime의 1초 대기 초과와 별개인 수치 해 유무를 (a)로 보고하며 시간은 (e)에 모두 포함한다.

Protocol SHA256: `{d['protocol_sha256']}`. 동결 소스·신규 solver hash는 `research/nomad_phase34o/protocol.json`, 입력 현재 hash는 `input_hashes.json`에 기록했다. 압축 snapshot은 STORAGE_RETROFIT 복원 로더를 사용했다. 기존 코드·raw·결과 문서는 변경하지 않았다.

원본 수치 job 회귀: 저장 결과가 남은 {len(r)}/411건 중 sample disposition 전부 일치 {sum(x['all_dispositions_match'] for x in r)}건, 선택 index 일치 {sum(x['selected_index_match'] for x in r)}건, 경로 좌표 1e−6m 이내 {sum(x['paths_within_1e6'] for x in r)}건. 세부는 `regression.csv`; 수치 환경 차이가 있는 job도 제외하지 않고 표시했다.

## EC 평가 시점과 누락 자료

실제 설치 172건은 PATH_APPLIED tick의 실제 pose·(v,ω), 그때 가장 최근 발행된 depth를 사용한다. 미설치 237건은 **저장 RESULT 결정 tick을 가상 설치 시점**으로 사용한다. 이는 실제 주행 설치나 새로운 완료 시점 예측이 아니다. 원본과 CLR에 같은 상태·map을 사용한다. RESULT 없는 2건은 설치 시점을 만들어내지 않고 EC 미측정이다. 해당 규약은 EC 검사 전에 고정했으며 원래 요청의 '실제 설치'가 존재하지 않는 입력에 대한 분석상 가정이다.

최신 지도 파일/동일 frame 사본이 없는 실제 설치 14건은 EC 미측정으로 남겼다. 최신 map을 확보한 job은 395건이다. solve 실패는 map 누락과 무관하게 (c)의 실패이며, 해는 있으나 EC가 미측정인 경우만 통과율의 하한(모두 실패)·상한(모두 통과)을 만든다. (b)의 분모는 해가 있는 job 전체, (c)의 분모는 411이다. `ec_conditional_observed` 열에는 측정 가능 해만의 참고 비율도 기록한다. gate 차이 범위는 CLR 하한−원본 상한부터 CLR 상한−원본 하한까지의 보수적 범위다. 이전 보존 지도 proxy는 별도 참고열에만 있으며 gate에서 제외한다.

고정 경로를 72Hz의 C0-NA PP/SP로 최대 2초 적분하는 EXEC-CERT만 재사용했다. 후속 NoMaD·지도 갱신·실제 재주행 반응은 재현하지 않는다. EC PASS는 실제 충돌 방지의 주행 검증이 아니다.

## 전체 및 출처별 결과

{text_table(a['summaries'][:2],main_columns)}

아래 값은 비율(0–1)이며 누락이 있는 경우 하한·상한을 함께 표시한다.

{text_table(a['summaries'][2:],[('group','입력 그룹')]+main_columns)}

## 선택 해의 최소 계획 여유 (footprint 포함, planning depth map)

{text_table(a['summaries'][:2],[('variant','방법'),('solutions','선택 해 수'),('plan_clearance_min_m','최솟값 m'),('plan_clearance_p10_m','p10 m'),('plan_clearance_p50_m','median m'),('plan_clearance_p90_m','p90 m')])}

![계획 여유 및 전체 job 시간](../research/results/phase34o/clearance_time.png)

## Phase31-E R2 충돌 8건

이 표의 입력은 각 사고 직전 R2 job과 실제 설치 상태이다. `FAIL`은 해 없음 또는 EC REJECT, `미측정`은 최신 지도 부재이다. 과거 지도 proxy를 실제 최신 지도 검사로 해석하지 않는다.

{text_table(a['collisions'],[('uid','충돌 run'),('job_id','job'),('R2_solution','R2 해'),('R2_EC','R2 EC'),('CLR_solution','CLR 해'),('CLR_EC','CLR EC'),('CLR_plan_clearance_m','CLR 계획 여유 m'),('latest_map_status','map'),('CLR_old_proxy_EC','옛 지도 CLR EC'),('proxy_extra_age_s','추가 stale s')])}

## 게이트

{text_table(gate_rows,[('criterion','조건'),('result','판정'),('evidence','근거')])}

**{d['label']}**. 최신 지도 누락의 가능한 결과 범위를 명시해 판정했으며, 어떤 경우에도 주행 준비를 하지 않는다. 같은 저장 자료를 사용한 경로 수준 반사실 비교로서 이후 행동의 인과 효과를 확정하지 않는다.

재생성: `env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m nomad_phase34o.report`
'''
    (ROOT/'docs/PHASE34O_R2CLR.md').write_text(text)
    figures(a)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--document-only',action='store_true');args=ap.parse_args()
    if not args.document_only:analyze()
    document()
    print(json.dumps(read(OUT/'decision.json')['label']))


if __name__=='__main__':main()
