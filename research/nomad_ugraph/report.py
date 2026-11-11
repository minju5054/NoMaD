"""Read completed caches; report only, no optimization inside this command."""
import argparse,csv,json,subprocess
from collections import Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Polygon,Rectangle
from nomad_run_plots import obstacle_corners
from nomad_phase31p.report import table
from .inputs import HERE,OUT,RUN_ROOT,SCENES,materialize
from .evaluate import verify,atomic
from nomad_isaac.common import ROOT,sha256_file

def quantile(values,q):return float(np.quantile(values,q)) if values else None

def summarize(cases,by,after=False):
    rows=[]
    for scene in (*SCENES,'ALL'):
        selected=[c for c in cases if (scene=='ALL' or c['scene']==scene) and (not after or c['after_box_spawn'])]
        available=[c for c in selected if c['status']=='READY'];completed=[by[c['case_id']] for c in available if c['case_id'] in by]
        good=[r for r in completed if r['found']];times=[r['wall_s'] for r in completed];solve=[r['solve_job_wall_s'] for r in completed if 'solve_job_wall_s' in r]
        rows.append(dict(scope='AFTER_BOX_SPAWN' if after else 'ALL_SELECTED',scene=scene,selected=len(selected),map_available=len(available),completed=len(completed),
            EC_valid_solutions=len(good),solution_rate=len(good)/len(completed) if completed else None,job_wall_p50_s=quantile(times,.5),job_wall_p95_s=quantile(times,.95),job_wall_max_s=max(times) if times else None,
            solve_11starts_p50_s=quantile(solve,.5),solve_11starts_p95_s=quantile(solve,.95),
            fixed_start_infeasible=sum(r['reason']=='FIXED_INITIAL_STATE_HARD_INFEASIBLE' for r in completed),
            reverse_in_solution=sum(r.get('reverse_included',False) for r in good),feasible_but_nonconverged=sum(not r.get('solver_converged',True) for r in good)))
    return rows

def reversal(cases,by,after=False):
    both=ours=actual=0;previous=None
    for c in cases:
        r=by.get(c['case_id'])
        if previous:
            pc,pr=previous
            valid=(c['uid']==pc['uid'] and r is not None and pr is not None and r['found'] and pr['found'] and (not after or (c['after_box_spawn'] and pc['after_box_spawn'])))
            if valid and all(s in ('LEFT','RIGHT','CENTER') for s in (r['side'],pr['side'],r['actual_side'],pr['actual_side'])):
                both+=1;ours+=int({r['side'],pr['side']}=={'LEFT','RIGHT'});actual+=int({r['actual_side'],pr['actual_side']}=={'LEFT','RIGHT'})
        previous=(c,r)
    return dict(scope='AFTER_BOX_SPAWN' if after else 'ALL',common_adjacent_pairs=both,U_flips=ours,actual_flips=actual,U_rate=ours/both if both else None,actual_rate=actual/both if both else None)

def figure(case,result):
    root=Path(case['run']);cfg=json.loads((root/'scenario.json').read_text());summary=json.loads((root/'summary.json').read_text());samples=materialize(case)
    with (root/'agent_trajectory.csv').open() as f:rows=list(csv.DictReader(f))
    trace=np.array([[float(r['simulation_time_s']),float(r['x_m']),float(r['y_m'])] for r in rows]);future=trace[(trace[:,0]>=case['time_s']-1e-9)&(trace[:,0]<=case['time_s']+2.5+1e-9)]
    fig,ax=plt.subplots(figsize=(9,7));fig.subplots_adjust(left=.1,right=.96,top=.86,bottom=.16)
    bounds=cfg['corridor'];x0,x1=bounds['xmin'],bounds['xmax'];y0,y1=bounds.get('ymin',-bounds['half_width']),bounds.get('ymax',bounds['half_width'])
    ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec='#777777',lw=2))
    for box in cfg.get('obstacles',[]):ax.add_patch(Polygon(obstacle_corners(box),fc='#D0D0D0',ec='#777777',lw=.8))
    dyn=summary.get('dynamic_obstacle') or {}
    for b in dyn.get('boxes',[dyn] if dyn.get('spawn') else []):
        if b['spawn']['simulation_time_s']<=case['time_s']+1e-9:ax.add_patch(Polygon(obstacle_corners(b['spawn']['obstacle']),fc='#A481B8',alpha=.5,ec='#765089'))
    ax.add_collection(LineCollection(samples,colors='#999999',linewidths=1.,alpha=.35,label='8world-fixed NoMaD candidates'))
    if len(future):ax.plot(future[:,1],future[:,2],color='#222222',lw=2,label=f"saved next {future[-1,0]-case['time_s']:.2f}s")
    if result['found']:
        state=np.asarray(result['states']);ax.plot(*state[:,:2].T,color='#0072B2',marker='.',ms=3,lw=1.6,label='U-Graph selected2.5s trajectory')
        length=.22;ax.arrow(*state[-1,:2],length*np.cos(state[-1,2]),length*np.sin(state[-1,2]),width=.012,color='#0072B2',length_includes_head=True)
        ec=result['ec'].get('trace',{}).get('poses')
        if ec is not None:ax.plot(*np.asarray(ec)[:,:2].T,color='#CC79A7',ls='--',lw=1,label='independent frozen EC PP/SP trace')
    else:ax.text(.02,.93,'NO EC-VALID SOLUTION: '+result['reason'],transform=ax.transAxes,fontsize=9,color='#A83E3E')
    ax.scatter(*case['pose'][:2],marker='o',s=60,fc='white',ec='black',zorder=10,label='stored actual initial pose')
    ax.set(xlim=(x0-.15,x1+.15),ylim=(y0-.15,y1+.15),xlabel='x(m)',ylabel='y(m)');ax.set_aspect('equal');ax.grid(alpha=.15)
    fig.suptitle(f"{case['scene']} | {case['case_id']} | t={case['time_s']:.2f}s | {result.get('type',result['reason'])}",fontsize=12)
    fig.legend(loc='lower center',bbox_to_anchor=(.5,.02),ncol=2,frameon=False,fontsize=9)
    target=ROOT/f"docs/figures/ugraph_{case['scene']}.png";fig.savefig(target,dpi=150);plt.close(fig);return target

def generate(make_figures=True):
    p=verify();inventory=json.loads((RUN_ROOT/'inventory.json').read_text());cases=inventory['cases'];expected={c['case_id']:c for c in cases};h=sha256_file(HERE/'protocol.json')
    by={}
    for f in sorted((RUN_ROOT/'cache').glob('*.json')):
        r=json.loads(f.read_text());assert r['protocol_sha256']==h and r['case_id'] in expected
        if r['found']:assert r['ec']['passed'] and next(x for x in r['results'] if x['start_index']==r['selected'])['hard_feasible']
        by[r['case_id']]=r
    summary=summarize(cases,by)+summarize(cases,by,True)
    types=Counter();cross=Counter()
    for case in cases:
        r=by.get(case['case_id'])
        if r and r['found']:
            for scope in ('ALL','AFTER_BOX_SPAWN') if case['after_box_spawn'] else ('ALL',):
                types[(scope,r['type'])]+=1;cross[(scope,r['actual_command_state'],r['type'])]+=1
    distributions=[dict(scope=s,type=t,n=n) for (s,t),n in sorted(types.items())]
    crosses=[dict(scope=s,actual_state=a,U_type=t,n=n) for (s,a,t),n in sorted(cross.items())]
    reversals=[reversal(cases,by),reversal(cases,by,True)]
    details=[]
    for c in cases:
        r=by.get(c['case_id']);details.append(dict(case_id=c['case_id'],scene=c['scene'],uid=c['uid'],source_state=c['actual_command_state'],after_box_spawn=c['after_box_spawn'],
            availability=c['status'],status=r['reason'] if r else 'NOT_RUN',found=r['found'] if r else None,type=r.get('type') if r else None,wall_s=r.get('wall_s') if r else None))
    figs=[]
    for scene,ident in inventory['examples'].items():
        if ident in by and make_figures:figs.append(figure(expected[ident],by[ident]))
    state=dict(status='COMPLETE' if len(by)==len(cases) else 'PARTIAL' if by else 'PREPARED_NOT_RUN',selected=len(cases),completed=len(by),map_available=sum(c['status']=='READY' for c in cases),
        protocol_sha256=h,solver=p['solver'],implementation_interpretations=p['implementation_interpretations'])
    OUT.mkdir(exist_ok=True,parents=True);atomic(OUT/'summary.json',dict(state=state,summary=summary,types=distributions,cross_table=crosses,reversal=reversals))
    with (OUT/'cases.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,list(details[0]));writer.writeheader();writer.writerows(details)
    definitions=[dict(item=k,value=v) for k,v in p['implementation_interpretations'].items()]
    doc=ROOT/'docs/UGRAPH_OFFLINE.md';doc.write_text('\n\n'.join(['# U-Graph 오프라인 타당성 검증',table([dict(status=state['status'],selected=len(cases),completed=len(by),map_available=state['map_available'],protocol_sha256=h)]),
        '실제 개발 입력 풀이 전에는 해 존재율을 보고하지 않는다. 아래 표의 미실행 값은—이다. 기존 동결 코드·원 로그·실험 결과는 수정하지 않는다.',
        table(definitions),'## 입력 및 해 존재율 / 시간',table(summary),
        '해 존재=hard 제약 허용오차1e−7 이내인 최종iterate 중 독립 EC-tail PASS가 하나 이상. 수렴상태는 별도 기록하며 수렴 실패여도 실제 hard+EC를 통과한 최종iterate는 유효한 feasible 해다. 입력자료 누락은 planner 실패로 세지 않는다. 시간은 SDF 로드·11starts의4worker wall·EC재검증을 포함하는 전체 job이며 solver stage wall도 따로 기록한다. 초기 상태 자체가 hard SDF/속도 한계를 위반하면 즉시 불가능으로 기록한다.',
        '## 채택 해 유형 / 실제 동작 교차표',table(distributions),table(crosses),
        '유형: 계획 이동거리≤1mm이면 총회전>1mrad일 때 제자리회전, 아니면 정지. 이동 해는 첫 제어 a0·v0<−1e−7이면 감속, 나머지는 전진/이동이다. |v| 제약은 후진도 허용하므로 음의속도 포함수는 별도로 보여 전진으로 오인하지 않게 한다. 표는 채택된 해만 대상으로 한다.',
        '## 좌우 번복',table(reversals),
        '각 상태의 현재 heading 기준 endpoint 횡변위>1cm=LEFT,<−1cm=RIGHT,그 사이는CENTER. 직전 추출 입력과현재 입력 모두 채택되고 실제 설치경로도 있는 공통쌍에서 LEFT↔RIGHT를 센다. 균등 추출한 상태의 번복이며 전체4Hz 정책의 번복률은 아니다. 직전 U해는 실제 실행되지 않았으므로 일관성 factor는 순차 오프라인 반사실이다.',
        '## 고정 대표 입력6개',table([dict(scene=s,case_id=i,status=by[i]['reason'] if i in by else 'NOT_RUN') for s,i in inventory['examples'].items()]),
        *[f'![{f.stem}](figures/{f.name})' for f in figs],
        '한계: 최신 보존 SDF를 고정한2.5초 단일계획이다. 다음 NoMaD 추론·depth 갱신·3D 물리는 반영하지 않는다. EC는 Graph XY를 동결 PP/SP로 실행하므로 Graph v·ω를 그대로 추종한 안전 증명이 아니다. 정지·제자리회전의 정확히 고정된 중심은 원형footprint 불변성을 사용해 같은 EC 함수의 종료점 제동 경로로 검증한다. 주행 실험 결과나 성공률을 대신하지 않는다.'])+'\n')
    return doc,figs

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc,figs=generate()
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        images=[str(f.relative_to(ROOT)) for f in figs]
        if images:subprocess.run(['git','add','-f','--',*images],cwd=ROOT,check=True)
        tracked=paths+images
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*tracked],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report saved-log U-Graph offline feasibility','--',*tracked],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
