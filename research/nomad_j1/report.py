import argparse
import json
import subprocess
from pathlib import Path
from nomad_j0.report import stats,csv_write
from nomad_phase18.report import table
from nomad_phase26.storage import atomic_json
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,METHODS,verify
from .statistics import primary,completed_seeds

def generate(root=RUN_ROOT,out=OUT,document=None,include_exploratory=True):
    p=verify();root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rr=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    expected={(j['scene'],j['index'],j['method']) for j in p['main_order']};keys=[(r['scene'],r['index'],r['method']) for r in rr]
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    artifact_count=len(rr);complete=completed_seeds(rr)
    rr=[r for r in rr if r['index'] in complete]
    result=primary(rr);result.update(protocol_sha256=sha256_file(HERE/'protocol.json'),completed_runs=len(rr),planned_runs=195,
        artifact_run_records=artifact_count,incomplete_block_records_excluded=artifact_count-len(rr))
    summary=[]
    for scene in (*SCENES,'ALL'):
        for method in METHODS:
            allrows=[r for r in rr if r['method']==method and (scene=='ALL' or r['scene']==scene)];valid=[r for r in allrows if r['technical_validation']=='PASS']
            arrival=stats([r.get('goal_time_s') for r in valid]);cp=stats([r.get('checkpoint_time_s') for r in valid]);solve=stats([v for r in valid for v in r.get('solve_times_s',[])])
            summary.append(dict(scene=scene,method=method,planned=39 if scene=='ALL' else 13,completed=len(allrows),technical_failures=len(allrows)-len(valid),
                success=sum(r['success'] for r in valid),collision=sum(r['collision'] for r in valid),wall_intrusion=sum(r['wall_intrusion'] for r in valid),
                timeout=sum(r['timeout'] for r in valid),arrival_n=arrival['n'],arrival_median_s=arrival['median'],arrival_p95_s=arrival['p95'],
                checkpoint_n=cp['n'],checkpoint_median_s=cp['median'],checkpoint_p95_s=cp['p95'],
                graph_applied=sum(r['graph_applied'] for r in valid),ec_checks=sum(r.get('ec_checks',0) for r in valid),ec_rejected=sum(r.get('ec_rejected',0) for r in valid),
                solve_median_s=solve['median'],solve_p95_s=solve['p95']))
    atomic_json(out/'runs.json',rr);atomic_json(out/'decision.json',result);csv_write(out/'summary.csv',summary)
    csv_write(out/'paired.csv',result['checkpoint_pairs']);csv_write(out/'primary.csv',result['primary'])
    doc=Path(document) if document else ROOT/'docs/J1_REPORT.md'
    display=lambda rows:[{k:('N/A' if v is None else v) for k,v in row.items()} for row in rows]
    primary_keys=['comparison','metric','pairs','seed_clusters','mean_difference_s','ci95_s',
                  'OURS_only_failure','noEC_only_failure','p_raw','p_holm','decision']
    primary_rows=[{k:r.get(k,'N/A') for k in primary_keys} for r in result['primary']]
    lines=['# J1',f"**{result['label']}**",table([{k:v for k,v in result.items() if k not in ('primary','checkpoint_pairs')}]),
        '종료 판정은 Phase18과 동일(0.3m). 공식 NoMaD argmin closest/subgoal,1s 만료,관측pose world고정/현재B 투영,PP+CURV,depth V1,SDF 등록fix,ENDPOINT latch를 공통 사용한다. 회복·STOP_WAIT 특수처리·HMM/NET 없음.',
        'J0 선별에서 LC는 통과했고 H1-v3·SLW-v2는 미달했지만 각각 돌발 장애물·좁은 통로 평가를 위해 사용자 사전 결정으로 포함했다. seed231–243,195회,seed별15회 고정RNG 섞기. 5.5h가 지난 뒤 새seed블록은 시작하지 않고 완료된 블록까지 중간 보고하며 동일 명령으로 재개한다.',
        '52-P 대비: 제동꼬리 적분·swept certificate·설치/36tick 검사는 동일하며, controller만 공통 Phase18 PP/CURV를 전달하고 사용자 지시대로 다음후보/0.1/STOP_WAIT 대체를 제거해 설치거절은 KEEP,주기거절은 같은 경로+stop_command 감속으로 처리한다.',
        'OURS-noEC는 J0 실행 객체를 그대로 사용한다. RAW는 Phase18-RAW에 공통 ENDPOINT latch만 추가한다. RTC-hard는 Phase18 생성/SAFE 규칙이며 공통 제거사항을 적용한다. OURS는 SAFE 원경로 설치와 비동기Graph 보정을 각각EC로 인증한다. 원경로EC거절도 SAFE후보의Graph 시도를 막지 않으며 새chunk/STALE/만료 폐기는 동결 규칙이다.',
        table(display(summary)),table(display(primary_rows)),
        '주 비교는 완료seed블록의 기술PASS·관측된 짝만 사용한다. checkpoint 결측은 대체하지 않으며 n을 표시한다. 차이=OURS−RTC,seed cluster bootstrap20,000회(seed20261030),양측95% CI,귀무가설 중심화 bootstrap p=(1+|boot−mean|≥|mean| 횟수)/(B+1). 안전실패=충돌OR벽침범,정확McNemar 양측검정. 두 p의 가족에Holm α=.05. 중간값은 탐색적으로 제시하며 전체13seed 완료 전 판정은 보류한다.',
        table([dict(scene=s,**p['scenes'][s]['checkpoint']) for s in SCENES]),
        'RTC-hard의 hard-mask 검증은 전체 OLD suffix(H_old)가 아닌 앞 d개만 양쪽에서 비교한다. d=0 prefix 오차와 미정의 solve/비율은 N/A다. 공통 성공·안전실패·timeout·checkpoint 계산식과 주 비교 함수는 변경하지 않았다.']
    revision=out/'reassessment.json'
    if revision.exists():
        r=json.loads(revision.read_text())
        lines.extend(['## 검증 재판정 기록',table([dict(completed_seed_blocks=r['completed_seeds'],RTC_reassessed=r['rtc_reassessed'],
            RTC_PASS=r['rtc_pass'],non_RTC_metrics_unchanged=r['non_rtc_unchanged'],protocol_unchanged=r['protocol_unchanged'],
            original_failure_archive=r['archive_directory'])]),
            '원 실패 canonical metrics와 모든 attempt_metrics는 보존했다. 같은 저장 artifacts에 검증만 다시 적용했으며 재주행·추론·solver 실행은 없다. 재개 후 RTC run도 수정된 같은 audit를 호출한다.'])
    if include_exploratory:
        from .interim_analysis import generate as explore
        extra=explore(rr,out)
        checkpoint_cols=['scene','method','valid_runs','checkpoint_runs','checkpoint_mean_speed_m_s_median',
            'checkpoint_curvature_slow_fraction_active_median','checkpoint_stop_s_median','checkpoint_distance_m_median']
        full_cols=['scene','method','valid_runs','full_mean_speed_m_s_median','full_curvature_slow_fraction_active_median',
                   'full_stop_s_median','full_distance_m_median']
        lines.extend(['## 탐색적 분석 — 주 판정과 분리',
            '아래는 저장 로그의 서술적 비교이며 주 가설·Holm 판정에 사용하지 않는다. 평균속도는 주행거리/경과시간(정지 포함), 정지는 |실제v|<1e−12의72Hz 구간이다. 곡률 감속은 활성 PP 중 0<v_target<0.3인 시간 비율이며 가속 제한만으로 낮은 명령과 EC_BRAKE는 제외한다. 먼저 checkpoint까지, 이어서 미도달 run도 포함하는 전체 주행을 별도 제시한다. 각 칸은 run별 값의 중앙값이며 미관측은 N/A다.',
            table(display([{k:r[k] for k in checkpoint_cols} for r in extra['summary']])),
            table(display([{k:r[k] for k in full_cols} for r in extra['summary']])),
            'OURS−비교법의 같은scene·seed 짝 차이(추가 p검정 없음):',table(display(extra['paired_summary'])),
            'OURS EC 검사·거절(scope별; 주 판정 미사용):',table(display(extra['ours_ec'])),
            'H1-v3 OURS timeout의 종료 위치와 마지막 정지 위치(종료 때 움직였으면 stationary_at_end=False):',table(display(extra['h1v3_timeout_positions'])),
            'H1-v3 top-down 그림은 사전 요청 범위 seed231–238의 OURS·OURS-noGRAPH·NOMAD_RAW만 표시한다.'])
        for fig in extra['figures']:lines.append(f"![saved trajectory]({Path(fig['file']).relative_to('docs')})")
        if extra['data_errors']:lines.extend(['저장 로그 가용성 제한:',table(extra['data_errors'])])
    doc.write_text('\n\n'.join(lines)+'\n');return doc

def publish_report(doc):
    paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    figure_manifest=OUT/'exploratory.json'
    images=[r['file'] for r in json.loads(figure_manifest.read_text()).get('figures',[])] if figure_manifest.exists() else []
    if images:subprocess.run(['git','add','-f','--',*images],cwd=ROOT,check=True);paths+=images
    if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
        subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report J1 completed seed blocks and preregistered comparisons','--',*paths],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate(a.run_root)
    if a.publish:publish_report(doc)

if __name__=='__main__':main()
