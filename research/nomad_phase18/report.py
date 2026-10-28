"""Frozen confirmatory tables, clustered confidence intervals, plots and publish."""
import argparse,csv,json,subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase17.report import table
from nomad_phase12.report import wilson
from .config import METHODS,SCENES,PROPOSED,protocol,scene,verify_sources
from .statistics import counts,decisions,valid
from .campaign import read,write

OUT=ROOT/'research/results/phase18';DOC=ROOT/'docs/PHASE18_CONFIRMATORY.md'

def csv_write(path,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,keys);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})

def stat(x):
    x=[v for v in x if v is not None]
    return dict(n=len(x),median=float(np.median(x)) if x else None,p95=float(np.quantile(x,.95)) if x else None)

def summaries(records):
    result=[]
    for sc in (None,*SCENES):
        for method in METHODS:
            rr=[r for r in records if valid(r) and r['method']==method and (sc is None or r['scene']==sc)]
            g=counts(records,method,sc)
            for key in ('goal_time_s','checkpoint_time_s','checkpoint_mean_speed_m_s','minimum_oracle_clearance_m','minimum_obstacle_clearance_m','minimum_wall_clearance_m','curv_slow_fraction','endpoint_clamp_fraction','recovery_time_fraction'):
                g[key]=stat([r.get(key) for r in rr])
            g.update(success_wilson95=wilson(g['success'],g['valid']),
                recovery_count=sum(r.get('recovery_count',0) for r in rr),
                recovery_limit_runs=sum(r.get('recovery_count',0)>=12 for r in rr),
                recovery_safe_outcomes=sum(r.get('recovery_safe_outcomes',0) for r in rr),
                recovery_observed_outcomes=sum(r.get('recovery_observed_outcomes',0) for r in rr),
                no_detour_success=sum(bool(r.get('no_detour_success')) for r in rr),
                keep_active_count=sum(r.get('fallback_events',{}).get('KEEP_ACTIVE',0) for r in rr),
                stop_wait_count=sum(r.get('fallback_events',{}).get('STOP_WAIT',0) for r in rr),
                keep_active_fraction=stat([r.get('fallback_time_fraction',{}).get('KEEP_ACTIVE') for r in rr]),
                stop_wait_fraction=stat([r.get('fallback_time_fraction',{}).get('STOP_WAIT') for r in rr]),
                graph_calls=sum(r.get('graph_calls',0) for r in rr),graph_accepted=sum(r.get('graph_accepted',0) for r in rr),
                graph_initialization_rejected=sum(r.get('graph_initialization_rejected',0) for r in rr),
                graph_solve_s=stat([x for r in rr for x in r.get('graph_solve_samples_s',[])]),
                inference_ms=stat([x for r in rr for x in r.get('inference_samples_ms',[])]),
                rtc_d0_count=sum(r.get('rtc_d0_count') or 0 for r in rr),rtc_inference_count=sum(r.get('rtc_inference_count') or 0 for r in rr),
                rtc_prefix_run_median_m=stat([r.get('rtc_prefix_error_m',{}).get('median') for r in rr if r.get('rtc_prefix_error_m')]),
                rtc_prefix_max_m=max((r['rtc_prefix_error_max_m'] for r in rr if r.get('rtc_prefix_error_max_m') is not None),default=None))
            g['graph_acceptance']=g['graph_accepted']/g['graph_calls'] if g['graph_calls'] else None
            result.append(g)
    return result

def figures(records,d,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from nomad_phase0.chunk_report import trace
    from nomad_phase16.geometry import rect
    labels=['SAFE','+HERMITE','+TE','+RTC-hard','+GRAPH-depth','+CLR']
    colors=plt.get_cmap('tab10').colors
    fig,axs=plt.subplots(1,3,figsize=(15,5))
    for ax,sc in zip(axs,SCENES):
        vv=[r.get('checkpoint_time_s') for r in records if r['scene']==sc and valid(r) and r.get('checkpoint_time_s') is not None]
        band=max(vv,default=30)+5
        for j,m in enumerate(METHODS):
            rr=sorted([r for r in records if r['scene']==sc and r['method']==m],key=lambda r:r['index']);actual=[]
            for k,r in enumerate(rr):
                t=r.get('checkpoint_time_s') if valid(r) else None
                if t is not None:actual.append(t)
                ax.scatter(j+(k-(len(rr)-1)/2)*.045,t if t is not None else band,edgecolor=colors[j],
                    facecolor=colors[j] if r.get('success') and t is not None else 'none',s=30)
            if actual:ax.plot([j-.18,j+.18],[np.median(actual)]*2,color=colors[j],lw=3)
        ax.axhline(band,color='.8',ls=':');ax.set_title(sc);ax.set_xticks(range(6),labels,rotation=45,ha='right');ax.set_ylabel('Checkpoint time (s)')
        ax.text(.01,.99,'Top band: no checkpoint (not imputed)\nOpen circles: non-success / missing',transform=ax.transAxes,va='top',fontsize=7)
    fig.tight_layout();fig.savefig(out/'checkpoint_by_method.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5))
    for j,p in enumerate(d['primary']):
        for k,v in enumerate(p['pairs']):ax.scatter(v['difference'],j+(k-(p['n']-1)/2)*.012,color=colors[SCENES.index(v['scene'])],s=18,alpha=.6)
        if p['ci'] is not None:
            ax.plot(p['ci'],[j,j],c='k',lw=3);ax.scatter(p['mean_difference'],j,c='k',marker='D',s=35)
    ax.axvline(0,color='.5',ls='--');ax.set_yticks(range(3),['CLR − HERMITE','CLR − TE','CLR − RTC-hard']);ax.set_xlabel('Paired checkpoint difference (s); Bonferroni 98.333% CI')
    fig.tight_layout();fig.savefig(out/'paired_diff.png',dpi=150);plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(15,4))
    for ax,sc in zip(axs,SCENES):
        for j,m in enumerate(METHODS):
            x=[r['minimum_oracle_clearance_m'] for r in records if r['scene']==sc and r['method']==m and valid(r)]
            if x:ax.scatter(j+np.linspace(-.15,.15,len(x)),x,color=colors[j],s=20);ax.plot([j-.2,j+.2],[np.median(x)]*2,color=colors[j],lw=3)
        ax.axhline(0,color='.5');ax.axhline(.025,color='.7',ls='--');ax.set_xticks(range(6),labels,rotation=45,ha='right');ax.set_title(sc);ax.set_ylabel('Minimum footprint oracle clearance (m)')
    fig.tight_layout();fig.savefig(out/'clearance_by_method.png',dpi=150);plt.close(fig)
    def paths(rr,sc,file):
        fig,ax=plt.subplots(figsize=(10,6));c=scene(sc)
        for r in rr:
            p=Path(r['output'])/'agent_trajectory.csv'
            if not p.exists():continue
            _,xy=trace(p.parent);j=METHODS.index(r['method']);ax.plot(xy[:,0],xy[:,1],color=colors[j],label=labels[j]);ax.scatter(*xy[-1,:2],marker='x',color=colors[j])
        for b in c['obstacles']:
            x,y=b['center_xy_m'];w,h=b['size_xyz_m'][:2];ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,color='.6',alpha=.45))
        xmin,xmax,ymin,ymax=rect(c);ax.add_patch(Rectangle((xmin,ymin),xmax-xmin,ymax-ymin,fill=False,color='black'))
        ax.set_aspect('equal');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.set_title(f'{sc}: recorded execution; oracle geometry for evaluation only')
        if ax.get_legend_handles_labels()[0]:ax.legend(fontsize=8)
        fig.tight_layout();fig.savefig(file,dpi=150);plt.close(fig)
    for sc in SCENES:paths([r for r in records if r['scene']==sc and r['index']==66],sc,out/f'paths_{sc}.png')
    for r in records:
        if not r.get('success') and (Path(r['output'])/'agent_trajectory.csv').exists():paths([r],r['scene'],out/f"failure_{r['scene']}_{r['method']}_{r['index']}.png")

def render(records,out,doc,metadata):
    expected={(s,i,m) for s in SCENES for i in range(66,74) for m in METHODS}
    assert len(records)==144 and {(r['scene'],r['index'],r['method']) for r in records}==expected
    out.mkdir(parents=True,exist_ok=True);doc.parent.mkdir(parents=True,exist_ok=True)
    if (out/'runs.json').exists():assert read(out/'runs.json')==records,'Existing different results preserved'
    p=protocol();d=decisions(records,p['statistics']['technical_failure_rule']);gs=summaries(records)
    write(out/'runs.json',records);write(out/'decisions.json',d);write(out/'provenance.json',metadata)
    csv_write(out/'summary.csv',gs);csv_write(out/'paired.csv',d['primary']+d['auxiliary']+d['scene_descriptive']);figures(records,d,out)
    cols=['comparator','n','seed_clusters','mean_difference','ci','H1','CLR_success','comparator_success','CLR_safety_failures','comparator_safety_failures','H2','safety','combined']
    text='# 사전 등록 확인 실험 — Phase 18\n\n'
    text+=f"Protocol SHA256: `{metadata['protocol_sha256']}`  \n실행 Git SHA: `{metadata['execution_git_sha']}`\n\n"
    text+='SLW·LC·CL의 Phase17 scene/reference/Topomap 및 성공한 게이트 6회를 hash 검증 후 재사용했다. 새로운 게이트/Topomap 주행은 없다. 여섯 방법 모두 동일 depth 선택·fallback·회복을 사용한다. NoMaD 입력은 RGB이며 depth는 noisy V1 지도에만 사용한다. 시뮬레이터 pose 사용으로 odometry 오차가 없다고 가정한다. Oracle은 사후 평가에만 사용한다. SE(2) kinematic Isaac Sim 결과이며 실제 로봇/PhysX 동역학 검증이 아니다.\n\n'
    text+='## 주 판정\n\n'+table(d['primary'],cols)+'\n\n'
    if d['overall']:text+='전체 결론: **ALL_CONFIRMED**\n\n'
    text+='20,000회 paired seed-cluster bootstrap, seed 20261030. 같은 seed의 scene들을 함께 재표집한다. 세 비교에 Bonferroni α=.05/3, 정확한 CI 수준 98.333333%를 적용한다. checkpoint 결측은 대체하지 않고 양쪽 유효 checkpoint가 있는 쌍만 사용한다. FASTER/SLOWER에는 n≥12가 필요하다. H2는 사용자 고정 count 기준(성공 −3, 안전 실패 +1)이며 통계적 비열등성 검정으로 확대 해석하지 않는다.\n\n'
    text+=f"기술 실패 처리: `{d['technical_failure_rule']}`. 기술 실패를 장애물 충돌·벽 침범으로 세지 않는다.\n\n"
    text+='## 보조 판정 (95% CI, 무보정)\n\n'+table(d['auxiliary'],['comparator','metric','n','mean_difference','ci','label'])+'\n\n'
    text+=table([g for g in gs if g['scene']=='ALL'],['method','planned','valid','technical_failures','success','safety_failures','collision','corridor','timeout','no_detour_success','goal_time_s','checkpoint_time_s','minimum_oracle_clearance_m','minimum_obstacle_clearance_m','recovery_count','stop_wait_count'])+'\n\n'
    text+='## Scene별 서술용 판정 지표\n\n'+table(d['scene_descriptive'],['scene','comparator','n','mean_difference','ci','CLR_counts','comparator_counts'])+'\n\n'
    text+=table([g for g in gs if g['scene']!='ALL'],['scene','method','valid','success','safety_failures','timeout','goal_time_s','checkpoint_time_s','minimum_oracle_clearance_m'])+'\n\n'
    text+='## Seed × scene × 방법\n\n'+table(records,['index','scene','method','classification','checkpoint_time_s','goal_time_s','minimum_oracle_clearance_m'])+'\n\n'
    text+='## RTC·회복·fallback·Graph\n\n'+table([g for g in gs if g['scene']=='ALL'],['method','inference_ms','rtc_inference_count','rtc_d0_count','rtc_prefix_run_median_m','rtc_prefix_max_m','recovery_count','recovery_limit_runs','recovery_time_fraction','recovery_safe_outcomes','recovery_observed_outcomes','keep_active_count','keep_active_fraction','stop_wait_count','stop_wait_fraction','graph_calls','graph_acceptance','graph_initialization_rejected','graph_solve_s'])+'\n\n'
    text+='RTC는 **RTC hard-masking ablation (DDPM adaptation)**: 보호된 Phase8 β=5/RePaint 코드 그대로이며 원 논문의 flow-policy RTC와 동일한 구현이라고 주장하지 않는다. 관측 순간 active OLD로 Y를 구성하고 T_est=0.888536777s 규칙을 유지했다. d=0은 기존 soft-guidance(W≠0) 또는 무-guidance(W=0) 분기를 그대로 따른다. 추론 추가 비용을 빼거나 보정하지 않았다. RTC prefix error는 모든 sample의 d-prefix point와 Y local point의 위치 오차이며 기존 rtc_prefix_error 정의를 유지한다.\n\n'
    text+='최소 oracle clearance는 상자와 외곽 벽의 footprint clearance 최솟값이며 상자만의 값도 별도 기록한다. 안전 실패는 충돌 또는 벽 침범 run의 합집합이다. 중단 run의 최소 거리는 실행된 구간만 평가하므로 경로 길이가 다를 수 있다. Scene별 지표는 서술용이며 추가 주 가설 검정을 만들지 않는다.\n\n'
    text+='## 기술 실패\n\n'+table([r for r in records if not valid(r)],['scene','index','method','error'])+'\n\n'
    for f in sorted(out.glob('*.png')):text+=f'![{f.stem}](../research/results/phase18/{f.name})\n\n'
    doc.write_text(text)
    return d

def publish(out,doc):
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    paths=[str(doc.relative_to(ROOT)),str(out.relative_to(ROOT))]
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    png=list(out.glob('*.png'))
    if png:subprocess.run(['git','add','-f','--',*[str(f.relative_to(ROOT)) for f in png]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():
        subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase18 preregistered confirmatory experiment'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

def main():
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True);g.add_argument('--run-root',type=Path);g.add_argument('--runs-json',type=Path)
    ap.add_argument('--out',type=Path,default=OUT);ap.add_argument('--doc',type=Path,default=DOC);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    assert not (a.runs_json and a.publish),'Synthetic report cannot be published'
    if a.run_root:
        verify_sources();root=a.run_root.resolve();assert read(root/'complete.json')['main_expected']==144
        plan=read(root/'plan.json');assert plan['protocol']==protocol()
        records=[read(f) for f in sorted((root/'metrics').glob('main_*.json'))]
        metadata=dict(protocol_sha256=sha256_file(Path(__file__).with_name('protocol.json')),execution_git_sha=plan['git_sha'],run_root=str(root))
    else:
        records=read(a.runs_json);metadata=dict(protocol_sha256=sha256_file(Path(__file__).with_name('protocol.json')),execution_git_sha='SYNTHETIC_TEST_ONLY')
    d=render(records,a.out,a.doc,metadata)
    if a.publish:publish(a.out,a.doc)
    print(json.dumps(dict(overall=d['overall'],comparisons={r['comparator']:r['combined'] for r in d['primary']})))


if __name__=='__main__':main()
