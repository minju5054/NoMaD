"""Four-arm tables with historical V0/VE and unchanged R2 reuse."""
import json
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from nomad_phase39o2.report import grouped_rates
from nomad_isaac.common import sha256_file
from .data import ROOT,HERE,OUT,read

METHODS=('V0','VE','VN','VU')

def decision(rows,metadata):
    grouped={v:[r for r in rows if r['variant']==v] for v in METHODS};ids={m['case_id'] for m in metadata}
    complete=bool(ids) and all(len(g)==len(ids) and {r['case_id'] for r in g}==ids for g in grouped.values())
    base=sum(r['success'] for r in grouped['V0'])/len(ids) if complete else None;verdicts=[]
    for v in ('VN','VU'):
        g=grouped[v];rate=sum(r['success'] for r in g)/len(ids) if complete else None
        timing=float(np.quantile([r['job_wall_s'] for r in g],.95)) if g else None;bad=sum(r['certificate_failures'] for r in g)
        checks=dict(success_plus_30pp=complete and rate>=base+.3-1e-12,p95_le_1s=timing is not None and timing<=1.,certificate_failures_zero=bad==0)
        verdicts.append(dict(variant=v,label='GO' if complete and all(checks.values()) else 'NO_GO' if complete else 'NOT_EVALUATED',n=len(g),
            baseline_success_rate=base,success_rate=rate,p95_s=timing,certificate_failures=bad,checks=checks))
    chosen=next((r['variant'] for r in verdicts if r['label']=='GO'),None)
    return dict(label='GO' if chosen else 'NO_GO' if complete else 'NOT_EVALUATED',selected_variant=chosen,complete=complete,selection_order=['VN','VU'],variants=verdicts)

def summary(rows):
    result=[]
    for kind in ('R2','R3','ALL'):
        for band in ('<0','0<=cB<0.03125','>=0.03125','ALL'):
            for method in METHODS:
                g=[r for r in rows if r['variant']==method and (kind=='ALL' or r['kind']==kind) and (band=='ALL' or r['cB_bin']==band)]
                if not g:continue
                result.append(dict(kind=kind,cB_bin=band,variant=method,n=len(g),accepted_jobs=sum(r['success'] for r in g),success_rate=sum(r['success'] for r in g)/len(g),
                    p50_s=median([r['job_wall_s'] for r in g]),p95_s=float(np.quantile([r['job_wall_s'] for r in g],.95)),certificate_failures=sum(r['certificate_failures'] for r in g),
                    selected_unknown_median=median([r['unknown_fraction_all'] for r in g if r.get('unknown_fraction_all') is not None]),
                    selected_unknown_within_0p6_median=median([r['unknown_fraction_within_0p6'] for r in g if r.get('unknown_fraction_within_0p6') is not None]),
                    selected_base_exact_median_m=median([r['selected_base_exact_m'] for r in g if r.get('selected_base_exact_m') is not None])))
    return result

def preparation_text(p):
    soft='CLR soft 조회 지도는 기존 VE(base 첫0.3m/strict 이후) 그대로다.' if not p['soft_policy_map'] else 'CLR soft 조회도 새 지도로 통일하되 비용 가중치는 그대로다.'
    return f'''# Phase39-O3 — unknown 지도 정책 비교 준비

실데이터 재풀이·시뮬레이션0회. V0/VE209건씩은 저장 결과만 재사용하며 solver 진입을 금지한다. R2는 VE와 동일해72건의 결과·시간을 VN/VU에서도 재사용한다. 새 재풀이는 R3 137건×VN/VU=274건,4프로세스다. A*·경로 검색·슬랙은 사용하지 않는다.

| 변형 | R3 hard 제약 / certificate / VO 기하 초기값 지도 |
|---|---|
| VU | 원 base occupied만; unknown=free |
| VN | occupied OR (~observed AND 셀 중심이 B에서0.6m 이내); 바깥 unknown=free |

지도는 첫0.3m를 포함한 전체 경로에 적용한다. {soft} c_B와 보고 구간은 항상 원 base의 `d(B)−h/√2`로 유지한다. B행 제외·낮은 c_B 탈출·s_esc certificate·초기값 생성/선택·곡률/길이/반경·SLSQP 설정은 VE 그대로다. 기하 초기값은39-O2의 동일 함수다.

실제39-O2 strict 구현은 shadow.py의 occupied|~observed뿐 아니라 **last_free<0 또는 관측 후2초 초과**도 차단하는 recent.py의 build_cache다. 새 hard/certificate/기하 지도는 위 표의 mask만 쓰므로 이 추가 recency 차단을 포함하지 않는다. 이 차이를 숨기지 않고 기록한다.

보고는 V0/VE/VN/VU의 c_B(<0 / 0~0.03125 / ≥0.03125)×R2/R3 표와SLSQP 메시지,기하 초기값 생성률·선택 비율,위치 중복 그룹/run 표다. 선택 경로는 전체 호길이5mm 이하 균등 표본이 놓인 **원 observed=false 칸** 비율과 그중 B반경0.6m 내의 조건부 비율을 기록한다. 같은 job의 모든 수락 해에 **원 base 지도 exact clearance**와≥0.025 여부를 기록하고 선택 해를 표시한다. 이는 EC와 같은 지도의 경로 검사이며,PP/SP 실행 궤적을 검사하는 EC PASS를 의미하지 않는다. EC·oracle은 실행하지 않는다.

전체209 job 성공률이 저장 V0보다≥30%p 증가 AND p95≤1s AND certificate 실패0이면 GO. 둘 다 통과하면 더 보수적인 VN→VU 순으로 선택한다. p95에는 동일한 R2의 과거 VE시간과 새 R3 job시간이 함께 들어가며,R3 단독 시간도 표에 표시한다. 미완료 자료는 판정하지 않는다. 새 job시간에는 map/cache·기하 생성·IPC·선택이 포함되며,기존 경로의 추가 측정/audit는 제외한다.

Protocol SHA256 `{sha256_file(HERE/'protocol.json')}`. 예상 약{p['estimated_minutes']:.1f}분(저장 VE R3 시간의 보수적 계수와추가 측정 여유 기반 계획 추정).55분 후 새 job을 시작하지 않고 현재 job 완료 후 PARTIAL로 저장하며 같은 명령으로 재개한다. 원본 입력·V0·VE hash를 검증하고 수정하지 않는다.

```bash
cd {ROOT} && nohup env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase39o3.run > ../artifacts/isaac6/phase39o3_01.log 2>&1 < /dev/null &
```

진행 확인: `PYTHONPATH=research /usr/bin/python3 -m nomad_phase39o3.run --status`. 완료 후 이 문서와 `research/results/phase39o3/` 표를 자동 생성한다. 온라인 준비는 하지 않는다.
'''

def generate(output=OUT,document=None):
    output=Path(output);p=read(HERE/'protocol.json');metadata=read(OUT/'preparation/metadata.json');by={m['case_id']:m for m in metadata};records=[]
    for m in metadata:
        for v,file in (('V0',m['baseline_file']),('VE',m['ve_file'])):
            r=read(file);measure_file=output/'baseline_metrics'/f"{m['case_id']}_{v}.json"
            measurements=read(measure_file)['measurements'] if measure_file.exists() else None
            record=dict(r,variant=v,measurements=measurements,reused=True);records.append(record)
            if v=='VE' and m['kind']=='R2':records.extend(dict(record,variant=x,reused_from='VE_R2') for x in ('VN','VU'))
    records+=[read(f) for f in sorted((output/'jobs').glob('*.json'))]
    rows=[];solutions=[];clearance=[];seeds=[];messages=Counter()
    for record in records:
        m=by[record['case_id']];v=record['variant'];n=record['numeric'];a=record['certificate_audit'];measure=record.get('measurements') or {};selected=n['selected_sample']
        chosen=next((x['base_exact_clearance_m'] for x in measure.get('accepted_base_clearances',[]) if x['selected']),None)
        unknown=measure.get('selected_path_unknown') or {}
        source=n.get('selected_initialization_source')
        rows.append(dict(m,variant=v,reused=record.get('reused',False),success=any(r['accepted'] for r in n['results']),job_wall_s=n['pool_wall_s'],
            certificate_failures=sum(not x['certificate_pass'] for x in a),selected_source=source,selected_index=selected,
            selected_base_exact_m=chosen,unknown_fraction_all=unknown.get('unknown_fraction_all'),unknown_fraction_within_0p6=unknown.get('unknown_fraction_within_0p6')))
        for r in measure.get('accepted_base_clearances',[]):clearance.append(dict(case_id=m['case_id'],variant=v,kind=m['kind'],cB_bin=m['cB_bin'],**r))
        for i,r in enumerate(n['results']):
            message=r.get('message',r.get('error',r['disposition']));messages[(m['cB_bin'],m['kind'],v,message)]+=1
            solutions.append(dict(case_id=m['case_id'],variant=v,kind=m['kind'],cB_bin=m['cB_bin'],index=i,accepted=r['accepted'],disposition=r['disposition'],message=message))
        if n.get('geometry'):seeds.extend(dict(case_id=m['case_id'],variant=v,kind=m['kind'],**r) for r in n['geometry']['sides'])
    d=decision(rows,metadata);stats=summary(rows);groups,runs=grouped_rates(rows);geo=[];base_stats=[]
    for kind in ('R2','R3','ALL'):
        for band in ('<0','0<=cB<0.03125','>=0.03125','ALL'):
            for v in METHODS:
                cc=[x for x in clearance if x['variant']==v and (kind=='ALL' or x['kind']==kind) and (band=='ALL' or x['cB_bin']==band)]
                if cc:base_stats.append(dict(kind=kind,cB_bin=band,variant=v,accepted_paths=len(cc),base_exact_min_m=min(x['base_exact_clearance_m'] for x in cc),
                    base_exact_median_m=median([x['base_exact_clearance_m'] for x in cc]),base_exact_ge_0p025=sum(x['base_exact_ge_0p025'] for x in cc),
                    base_exact_ge_0p025_fraction=sum(x['base_exact_ge_0p025'] for x in cc)/len(cc)))
    for v in ('VE','VN','VU'):
        ss=[s for s in seeds if s['variant']==v];jj=[r for r in rows if r['variant']==v and r['kind']=='R3'];chosen=[r for r in jj if r['selected_index'] is not None]
        geo.append(dict(variant=v,r3_jobs=len(jj),attempted_sides=len(ss),generated_sides=sum(s['generated'] for s in ss),
            generation_rate=sum(s['generated'] for s in ss)/len(ss) if ss else None,
            jobs_with_extra=len({s['case_id'] for s in ss if s['generated']}),selected_paths=len(chosen),
            selected_geometric=sum(str(r['selected_source']).startswith('OBSTACLE_') for r in chosen),
            selected_geometric_fraction=sum(str(r['selected_source']).startswith('OBSTACLE_') for r in chosen)/len(chosen) if chosen else None,
            exclusion_reasons=dict(Counter(s['reason'] for s in ss if not s['generated']))))
    output.mkdir(parents=True,exist_ok=True)
    for name,data in (('jobs.csv',rows),('solutions.csv',solutions),('summary.csv',stats),('groups.csv',groups),('runs.csv',runs),('base_clearances.csv',clearance),('base_clearance_summary.csv',base_stats),
        ('geometry.csv',seeds),('geometry_summary.csv',geo),('messages.csv',[dict(cB_bin=b,kind=k,variant=v,message=msg,count=count) for (b,k,v,msg),count in sorted(messages.items())])):csvout(output/name,data)
    save(output/'decision.json',d)
    text=f"# Phase39-O3 — 지도 정책 재풀이 결과\n\n**{d['label']}**, 선택 {d['selected_variant']}. V0/VE 재풀이0회, R2는 저장 VE 재사용.\n\n{table(d['variants'])}\n\n{table(stats)}\n\n## 기하 초기값\n\n{table(geo)}\n\n## 수락 해의 base exact clearance\n\n{table([r for r in base_stats if r['cB_bin']=='ALL'])}\n\n## 위치 그룹/run\n\n{table(runs)}\n\n수락 해별 원 base exact clearance는 base_clearances.csv, 선택 경로의 미관측 비율은 jobs.csv에 있다.\n\n## 고정된 준비 기록\n"+preparation_text(p).split('\n',1)[1]
    doc=Path(document) if document else ROOT/'docs/PHASE39O3_RESOLVE.md';doc.write_text(text);return d
