"""Saved installation geometry and run-level ALIGN_ROTATE association only."""
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.stats import pearsonr,spearmanr
from nomad_isaac.common import ROOT,local_to_world
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .inputs import read,lines,HASHES

OUT=ROOT/'research/results/phase52ec/chunks';DOC=ROOT/'docs/PHASE47_51_52_CHUNK_GEOMETRY.md'

def geometry(native,B):
    try:p=XYPath(native)
    except ValueError:return dict(valid=False,reason='DEGENERATE_NATIVE')
    s,offset=p.project(np.asarray(B)[:2]);remaining=float(p.s[-1]-s)
    ahead=next((point for arclength,point in zip(p.s,p.points) if arclength>s+1e-12),None)
    geometric_heading=None
    if ahead is not None:
        d=ahead-p.at(s)
        geometric_heading=float(abs((np.arctan2(d[1],d[0])-B[2]+np.pi)%(2*np.pi)-np.pi)*180/np.pi)
    first=next((point for arclength,point in zip(p.s,p.points) if arclength>=s+.05),None)
    heading=None
    if first is not None:
        d=first-np.asarray(B)[:2];heading=float(abs((np.arctan2(d[1],d[0])-B[2]+np.pi)%(2*np.pi)-np.pi)*180/np.pi)
    tangent=(p.points[-1]-p.points[-2])/p.lengths[-1]
    signed=float((np.asarray(B)[:2]-p.points[-1])@tangent)
    return dict(valid=True,native_length_m=float(p.s[-1]),projected_s_m=float(s),remaining_m=remaining,cross_track_m=float(offset),
        geometric_suffix_heading_error_deg=geometric_heading,geometric_heading_defined=ahead is not None,
        suffix_heading_error_deg=heading,heading_defined=first is not None,remaining_lt_5cm=bool(remaining<.05),
        beyond_endpoint_tangent=bool(s>=p.s[-1]-1e-9 and signed>0),endpoint_forward_overshoot_m=signed)

def correlations(rows,groups):
    buckets=defaultdict(list)
    for r in rows:buckets[tuple(r[k] for k in groups)].append(r)
    result=[]
    for key,rs in sorted(buckets.items()):
        for metric in ('end_lt_5cm_fraction','mean_geometric_heading_error_deg','mean_heading_error_deg','remaining_median_m','projection_fraction_mean'):
            available=[r for r in rs if r.get(metric) is not None];x=[r[metric] for r in available];y=[r['align_rotate_s'] for r in available]
            okay=len(x)>=3 and np.std(x)>1e-12 and np.std(y)>1e-12
            result.append(dict(zip(groups,key),predictor=metric,response='ALIGN_ROTATE seconds',n=len(x),
                pearson_r=float(pearsonr(x,y).statistic) if okay else None,spearman_rho=float(spearmanr(x,y).statistic) if okay else None,
                note='descriptive/repeated seeds,not independent causal evidence' if okay else 'insufficient n or zero variance'))
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True);events=[];runrows=[];coverage=[]
    for phase in ('phase47c','phase51p','phase52p'):
        for r in read(ROOT/f'research/results/{phase}/runs.json'):
            root=Path(r['output']);s=read(root/'summary.json');c=read(root/'scenario.json');uid=f"{phase}/{r['scene']}/{r['index']}/{r['method']}"
            delay=float(s['delivery_delay']['configured_additional_s']);condition=r.get('condition','D075');scene=c['phase16_scene']
            installs=[e for e in lines(root/'repair.jsonl') if e['event']=='PATH_APPLIED'];ec=[e for e in lines(root/'exec_cert.jsonl') if e['event']=='INSTALL']
            metas=[e for e in lines(root/'reconstruction.jsonl') if e['event']=='INSTALL_META'];received={e['id']:e for e in lines(root/'received.jsonl')}
            commands=lines(root/'phase20_commands.jsonl');align=0.
            for i,e in enumerate(commands):
                end=commands[i+1]['time_s'] if i+1<len(commands) else s['simulation_duration_s']
                if e['source']=='ALIGN_ROTATE':align+=max(0.,end-e['time_s'])
            used=set();these=[]
            for app_index,a in enumerate(installs):
                meta=next((e for e in metas if e['tick']==a['tick'] and e['id']==a['id']),None)
                match=next((e for e in ec if e['apply_tick']==a['tick'] and e['id']==a['id'] and e['kind']==a['kind']),None)
                sample=meta['sample'] if meta is not None else match.get('selected_sample') if match is not None else 0 if r['method']=='NOMAD_RAW' else None
                source=received.get(a['id']);native=None;provenance=None
                if meta is not None and meta.get('original_candidate_world') is not None:native=np.asarray(meta['original_candidate_world']);provenance='STORED_NATIVE_WORLD'
                elif source is not None and sample is not None and source.get('overnight_metric_samples') is not None:
                    native=local_to_world(source['overnight_metric_samples'][sample],source['observation_pose']);provenance='STORED_LOCAL_CANDIDATE_PLUS_OBSERVATION_POSE'
                first=a['id'] not in used;used.add(a['id'])
                row=dict(uid=uid,phase=phase,condition=condition,delay_s=delay,scene=scene,method=r['method'],seed=r['index'],application_index=app_index,
                    tick=a['tick'],time_s=a['simulation_time_s'],chunk_id=a['id'],sample=sample,kind=a['kind'],B=a['pose'],first_install_of_chunk=first,
                    observation_age_s=a['simulation_time_s']-source['observation_sim_s'] if source else None,coordinate_source=provenance)
                row.update(geometry(native,a['pose']) if native is not None else dict(valid=False,reason='NO_NATIVE_IDENTITY'))
                events.append(row);these.append(row)
            valid=[e for e in these if e['valid']]
            for scope,subset in (('ALL_INSTALLATIONS',valid),('FIRST_INSTALL_PER_CHUNK',[e for e in valid if e['first_install_of_chunk']])):
                heads=[e['suffix_heading_error_deg'] for e in subset if e['heading_defined']]
                geometric=[e['geometric_suffix_heading_error_deg'] for e in subset if e['geometric_heading_defined']]
                runrows.append(dict(uid=uid,phase=phase,condition=condition,delay_s=delay,scene=scene,method=r['method'],seed=r['index'],scope=scope,
                    installations=len(subset),align_rotate_s=align,align_rotate_fraction=align/s['simulation_duration_s'],
                    end_lt_5cm_fraction=sum(e['remaining_lt_5cm'] for e in subset)/len(subset) if subset else None,
                    remaining_median_m=median([e['remaining_m'] for e in subset]),mean_heading_error_deg=float(np.mean(heads)) if heads else None,
                    mean_geometric_heading_error_deg=float(np.mean(geometric)) if geometric else None,
                    heading_defined_n=len(heads),projection_fraction_mean=float(np.mean([e['projected_s_m']/e['native_length_m'] for e in subset])) if subset else None))
            coverage.append(dict(uid=uid,installations=len(these),valid=len(valid),excluded=len(these)-len(valid)))
    summary=[]
    for grouping in (('scope','delay_s'),('scope','phase','condition','delay_s'),('scope','phase','condition','delay_s','method','scene')):
        buckets=defaultdict(list)
        for r in runrows:buckets[tuple(r[k] for k in grouping)].append(r)
        for key,rr in sorted(buckets.items()):
            scope=key[0];uids={r['uid'] for r in rr};ee=[e for e in events if e['uid'] in uids and e['valid'] and (scope=='ALL_INSTALLATIONS' or e['first_install_of_chunk'])]
            heads=[e['suffix_heading_error_deg'] for e in ee if e['heading_defined']]
            geometric=[e['geometric_suffix_heading_error_deg'] for e in ee if e['geometric_heading_defined']]
            summary.append(dict(zip(grouping,key),grouping='/'.join(grouping),runs=len(rr),n=len(ee),
                native_length_median_m=median([e['native_length_m'] for e in ee]),projected_s_median_m=median([e['projected_s_m'] for e in ee]),
                remaining_median_m=median([e['remaining_m'] for e in ee]),remaining_p10_m=float(np.quantile([e['remaining_m'] for e in ee],.1)) if ee else None,
                heading_error_median_deg=median(heads),heading_error_p95_deg=float(np.quantile(heads,.95)) if heads else None,heading_defined_n=len(heads),
                suffix_direction_median_deg=median(geometric),suffix_direction_p95_deg=float(np.quantile(geometric,.95)) if geometric else None,suffix_direction_defined_n=len(geometric),
                remaining_lt_5cm=sum(e['remaining_lt_5cm'] for e in ee),remaining_lt_5cm_fraction=sum(e['remaining_lt_5cm'] for e in ee)/len(ee) if ee else None,
                true_endpoint_overshoot=sum(e['beyond_endpoint_tangent'] for e in ee),align_rotate_run_median_s=median([r['align_rotate_s'] for r in rr])))
    corr=correlations(runrows,('scope','delay_s'))+correlations(runrows,('scope','phase','condition','delay_s'))
    for name,data in [('applications',events),('runs',runrows),('coverage',coverage),('summary',summary),('correlations',corr)]:csvout(OUT/(name+'.csv'),data)
    save(OUT/'input_hashes.json',HASHES);save(OUT/'analysis.json',dict(runs=len(coverage),applications=len(events),valid=sum(e['valid'] for e in events),simulations=0,new_inference=0))
    definitions=[dict(item='범위',value='Phase47-C60+Phase51-P20+Phase52-P40=120 selected analysis runs; excluded retry attempts not used'),
        dict(item='원 chunk',value='선택된 원 NoMaD8개 waypoint polyline,observation world frame. 관측 원점이나 B를 앞에 덧붙이지 않음. GRAPH_REC도 실행 보정 경로가 아니라 선택한 원 후보를 사용'),
        dict(item='B와 투영',value='PATH_APPLIED의 실제 적용 pose B;가장 가까운 polyline 투영s_B∈[0,L],잔여=L-s_B'),
        dict(item='잔여 첫 방향',value='geometric_suffix/suffix_direction: 투영점에서 다음 원 waypoint로 향하는 첫 suffix 선분과 로봇heading의 wrapped 절댓값. 잔여가0이면NA'),
        dict(item='실행기 정렬 방향',value='suffix_heading/heading_error/mean_heading: 동결 정렬 규칙의 s_B+0.05m 이상 첫 원 waypoint로 실제 B에서 향하는 방향. 해당 점이 없으면NA. 기하학적 suffix 방향과 별도 기록하며 두 방향 모두 ALIGN_ROTATE와 상관 계산'),
        dict(item='끝 초과 지표',value='사용자 지정 잔여<0.05m 비율은 끝 근처/짧은 잔여도 포함하므로 실제 초과와 구분. 마지막 구간 tangent에 대한B-end 전진 투영>0인 진짜 끝 초과 수를 별도 열'),
        dict(item='설치 중복',value='모든 PATH_APPLIED와 chunk id별 첫 설치 두 범위;Graph 교체·주기EC 대체가 같은chunk를 재설치할 수 있음'),
        dict(item='상관',value='run별 잔여<5cm비율/잔여중앙값/방향오차평균/투영진행비율 vs실제 ALIGN_ROTATE 상태 지속시간. Pearson와Spearman,상수변수/작은n은NA. 지연·방법·장면·날짜가 교란되어 인과 해석 불가'),
        dict(item='WIDE',value='Phase51 WIDE는지연0.75이지만상자기하가다름. 조건별 표를 함께 보며 합산 지연표만으로 효과를 주장하지 않음')]
    compact=[r for r in summary if r['grouping'] in ('scope/delay_s','scope/phase/condition/delay_s')]
    DOC.write_text('# Chunk 적용 위치·잔여 길이와 정렬 회전\n\n'+table(definitions)+'\n\n'+table(compact)+'\n\n'+table(corr)+'\n\n'+table(runrows)+'\n\n전체 적용 시점: [applications.csv](../research/results/phase52ec/chunks/applications.csv). 방법·장면별 상세 표: [summary.csv](../research/results/phase52ec/chunks/summary.csv).\n')
    print(json.dumps(dict(runs=len(coverage),applications=len(events),excluded=sum(not e['valid'] for e in events))))

if __name__=='__main__':main()
