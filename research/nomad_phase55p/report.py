"""Automatic tables only; frozen historical aggregates, never old-run replay."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,verify,split
FIELDS=('classification','success','collision','wrong_stop','timeout_without_declaration','box_passage','box_passage_from_spawn_s','goal_time_s','stopped_s','align_rotate_s',
        'graph_adoption_rate','graph_solve_p50_s','graph_solve_p95_s','graph_left_right_switches','all_path_left_right_switches')
def generate(root=RUN_ROOT,output=OUT,document=None):
    p=verify();root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    keys=[(r['scene'],r['index'],r['method']) for r in runs];expected={(x['scene'],x['index'],x['method']) for x in p['main_order']}
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    baseline=json.loads((OUT/'preparation/baselines.json').read_text());pairs=[];by={(r['scene'],r['index']):r for r in runs}
    for job in p['main_order']:
        r=by.get((job['scene'],job['index']));s,d=split(job['scene'])
        row=dict(scene=s,condition=d,seed=job['index'],status=r['technical_validation'] if r else 'NOT_RUN')
        row.update({'U_'+k:r.get(k) if r else None for k in FIELDS})
        for phase,method in [('Phase53','CUT'),('Phase52','CUT-HOLD')]:
            b=next((x for x in baseline if x['phase']==phase and x['scene']==job['scene'] and x['index']==job['index']),{})
            row.update({phase+'_'+method+'_'+k:b.get(k) for k in FIELDS})
        pairs.append(row)
    summary=[]
    for d in ('D075','D150'):
        rr=[r for r in runs if split(r['scene'])[1]==d and r['technical_validation']=='PASS']
        summary.append(dict(condition=d,completed=len(rr),**{k:sum(bool(r.get(k)) for r in rr) for k in ('success','collision','wrong_stop','timeout_without_declaration','box_passage')},
            **{k+'_median':median([r[k] for r in rr if r.get(k) is not None]) for k in ('goal_time_s','stopped_s','align_rotate_s','graph_adoption_rate','graph_solve_p50_s','graph_solve_p95_s')},
            left_right_switches=sum(r.get('graph_left_right_switches',0) for r in rr)))
    status=dict(status='COMPLETE' if len(runs)==24 else 'PARTIAL' if runs else 'PREPARED_NOT_RUN',planned=24,completed=len(runs),
        protocol_sha256=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest())
    states=[dict(scene=r['scene'],seed=r['index'],state=k,seconds=v) for r in runs for k,v in r.get('command_state_seconds',{}).items()]
    save(output/'runs.json',runs);save(output/'status.json',status)
    for name,data in [('summary',summary),('paired',pairs),('command_states',states)]:csvout(output/(name+'.csv'),data)
    doc=Path(document) if document else ROOT/'docs/PHASE55P_RESULTS.md'
    doc.write_text('# Phase55-P U-Graph 폐루프 파일럿\n\n'+table([status])+'\n\n'+
        'PP+SP가 Graph XY를 추종하며 Graph v/ω 계획을 직접 실행하지 않는다. 결과 없음은 —로 표시한다. 역사 비교는 다른 날짜의 같은 scene·조건·seed이며 H1-v2 비교군은 없다. Phase53 CUT은 1s 만료+EC-tail, Phase52 CUT-HOLD는 HOLD+기존 EC이므로 실행 정책 차이가 있다.\n\n'+
        table(summary)+'\n\n'+table([{k:('—' if v is None else v) for k,v in row.items()} for row in pairs])+'\n\n'+table(states or [dict(status='NOT_RUN')])+'\n')
    return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate()
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase55-P U-Graph XY HOLD pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
