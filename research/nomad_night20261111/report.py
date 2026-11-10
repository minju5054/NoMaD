"""Preregistered complete-pair reports and automatic commit/push."""
import argparse,json,math,subprocess
from pathlib import Path
import numpy as np
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,EXP,OUT,RUN_ROOT,DEFS,verify
from .figures import generate as plots

def exact(wins,losses):
    n=wins+losses
    return min(1.,2*sum(math.comb(n,k) for k in range(min(wins,losses)+1))/2**n) if n else 1.

def pairs(runs,a,b):
    good={(r['scene'],r['index'],r['method']):r for r in runs if r['technical_validation']=='PASS'};out=[]
    for scene,index in sorted({(r['scene'],r['index']) for r in runs}):
        if (scene,index,a) not in good or (scene,index,b) not in good:continue
        x,y=good[(scene,index,a)],good[(scene,index,b)]
        out.append(dict(scene=scene,index=index,a=x,b=y))
    return out

def decide(e,runs):
    if e in ('E1','E3'):
        result=[];detail=[]
        for method in ('CUT','GRAPH-HO'):
            pp=pairs(runs,'OURS-R3',method);box=[p for p in pp if p['a'].get('expected_boxes',0)>0]
            w=sum(p['a']['box_passage'] and not p['b']['box_passage'] for p in box);l=sum(p['b']['box_passage'] and not p['a']['box_passage'] for p in box)
            times=[p['a']['box_passage_from_spawn_s']-p['b']['box_passage_from_spawn_s'] for p in box if p['a']['box_passage'] and p['b']['box_passage']]
            collisions=sum(p['a']['collision'] for p in pp)
            result.append(dict(comparison='OURS-R3 minus '+method,complete_run_pairs=len(pp),box_pairs=len(box),static_NA_pairs=len(pp)-len(box),
                ours_only_pass=w,baseline_only_pass=l,passage_gain=w-l,exact_mcnemar_p=exact(w,l),both_passage_n=len(times),passage_time_delta_median_s=median(times),
                ours_goal=sum(p['a']['success'] for p in pp),baseline_goal=sum(p['b']['success'] for p in pp),ours_collision=collisions,
                collision_free_required=collisions==0,candidate_by_passage_rule=(w-l>=3) if method=='CUT' else None))
            for p in pp:detail.append(dict(scene=p['scene'],index=p['index'],comparison='OURS-R3 minus '+method,box_applicable=p['a'].get('expected_boxes',0)>0,
                ours_pass=p['a']['box_passage'],baseline_pass=p['b']['box_passage'],ours_goal=p['a']['success'],baseline_goal=p['b']['success']))
        return dict(primary=result,paired=detail)
    pp=pairs(runs,'GRAPH-HOLD','CUT-HOLD');summary=[];detail=[]
    for condition in ('D075','D150'):
        subset=[p for p in pp if p['scene'].endswith(condition)]
        wins=sum(p['a']['success'] and not p['b']['success'] for p in subset);losses=sum(p['b']['success'] and not p['a']['success'] for p in subset)
        aligned=[p['a']['align_rotate_s']-p['b']['align_rotate_s'] for p in subset]
        times=[p['a']['goal_time_s']-p['b']['goal_time_s'] for p in subset if p['a']['success'] and p['b']['success']]
        attempted=sum(p['a']['graph_attempts'] for p in subset);adopted=sum(p['a']['graph_applied'] for p in subset)
        summary.append(dict(condition=condition,primary=condition=='D150',complete_pairs=len(subset),graph_attempts=attempted,graph_applied=adopted,graph_adoption_rate=adopted/attempted if attempted else None,
            align_delta_median_s=median(aligned),both_arrival_n=len(times),arrival_delta_median_s=median(times),graph_only_goal=wins,cut_only_goal=losses,goal_delta=wins-losses,
            descriptive_noninferior=(wins-losses>=-1) if subset else None,margin_runs=-1,not_statistical_test=True,incomplete=len(subset)<12))
        for p in subset:detail.append(dict(scene=p['scene'],index=p['index'],condition=condition,align_delta_s=p['a']['align_rotate_s']-p['b']['align_rotate_s'],
            arrival_delta_s=p['a']['goal_time_s']-p['b']['goal_time_s'] if p['a']['success'] and p['b']['success'] else None,goal_delta=int(p['a']['success'])-int(p['b']['success'])))
    contrast=[];by={(r['scene'].rsplit('_',1)[0],r['index'],r['condition']):r for r in detail}
    for scene,index in sorted({(k[0],k[1]) for k in by}):
        a=by.get((scene,index,'D150'));b=by.get((scene,index,'D075'))
        if a and b:contrast.append(dict(scene=scene,index=index,align_delta150_minus_delta075_s=a['align_delta_s']-b['align_delta_s'],
            arrival_delta150_minus_delta075_s=a['arrival_delta_s']-b['arrival_delta_s'] if a['arrival_delta_s'] is not None and b['arrival_delta_s'] is not None else None))
    return dict(primary=summary,paired=detail,delay_gain_comparison=contrast)

def generate(e=EXP,root=RUN_ROOT,output=OUT,make_plots=True):
    p=verify(e);root=Path(root);output=Path(output);runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    by={(r['scene'],r['index'],r['method']):r for r in runs};expected={(r['scene'],r['index'],r['method']) for r in p['main_order']}
    assert len(by)==len(runs) and set(by)<=expected
    d=decide(e,runs);state=dict(status='COMPLETE' if len(runs)==len(expected) else 'PARTIAL' if runs else 'NOT_STARTED',completed=len(runs),planned=len(expected),
        queue_state=json.loads((root/'state.json').read_text()).get('status') if (root/'state.json').exists() else None,protocol_sha256=__import__('hashlib').sha256((HERE/f'protocol_{e}.json').read_bytes()).hexdigest())
    rows=[]
    keys=('classification','success','collision','wrong_stop','box_passage','box_passage_from_spawn_s','goal_time_s','stopped_s','align_rotate_s','minimum_clearance_m','graph_adoption_rate','graph_rejection_reasons','detour_applied_count','boundary_curvature_dropped')
    for j in p['main_order']:
        r=by.get((j['scene'],j['index'],j['method']));rows.append(dict(**j,technical=r['technical_validation'] if r else 'NOT_RUN',**{k:r.get(k) if r and r['technical_validation']=='PASS' else None for k in keys}))
    images=plots(runs) if make_plots else dict(files=[])
    save(output/'runs.json',runs);save(output/'decision.json',dict(state=state,**d));save(output/'figures.json',images);csvout(output/'summary.csv',rows);csvout(output/'paired.csv',d['paired'])
    doc=ROOT/'docs'/p['report_document']
    content=['# '+p['phase']+' 밤샘 파일럿',table([state]),'완료되고 기술 audit PASS인 동일 장면·seed 짝만 비교한다. 미완료/기술 실패는 NOT_RUN/FAIL로 표시하고 대체하지 않는다. 정적 SLW·LC의 상자 통과는 N/A(12블록 중 돌발8블록만 통과 검정 대상). E2 성공 비열등은 성공 차이≥−1회의 파일럿 서술 기준이며 통계적 비열등 검정이 아니다.',table(d['primary'])]
    if e=='E2':content += ['아래는 네 run이 모두 완료된 장면·seed에서 (GRAPH−CUT) D150 − (GRAPH−CUT) D075이다. 도착시간은 네 run 모두 도착한 경우만 포함.',table(d['delay_gain_comparison'])]
    content += [table(rows),table(d['paired'])]
    content += [f"![{Path(f).stem}](figures/{Path(f).name})" for f in images['files']]
    doc.write_text('\n\n'.join(content)+'\n');return doc,images

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc,images=generate()
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        figs=[str(Path(f).relative_to(ROOT)) for f in images['files']]
        if figs:subprocess.run(['git','add','-f','--',*figs],cwd=ROOT,check=True)
        tracked=paths+figs
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*tracked],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m',f'Report night20261111 {EXP} complete pairs and partial runs','--',*tracked],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
