"""Tables only:15 new runs and the identical15 frozen Phase38 blocks."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,verify


def generate(root=RUN_ROOT,output=OUT,document=None,baseline=None):
    p=verify();output=Path(output);root=Path(root)
    old=baseline if baseline is not None else json.loads((OUT/'preparation/baselines.json').read_text())
    new=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    keys={(r['scene'],r['index']) for r in p['main_order']}
    assert len(new)==len({(r['scene'],r['index']) for r in new}) and all((r['scene'],r['index']) in keys for r in new)
    assert {(r['scene'],r['index']) for r in old}==keys
    summary=[]
    for scene in (*SCENES,'ALL'):
        for group,rows in (('Phase38 existing',old),('Phase41 declared',new)):
            g=[r for r in rows if scene=='ALL' or r['scene']==scene];valid=[r for r in g if r.get('technical_validation')=='PASS']
            summary.append(dict(group=group,scene=scene,method='OURS-DETOUR',completed=len(g),valid=len(valid),technical_failures=len(g)-len(valid),
                success=sum(r['success'] for r in valid),collision=sum(r['collision'] for r in valid),
                success_0p3=sum(r['success_0p3'] for r in valid),success_1p0=sum(r['success_1p0'] for r in valid),
                wrong_stop=sum(r['wrong_stop'] for r in valid) if group=='Phase41 declared' else None,
                timeout_without_arrival=sum(r['timeout_without_declaration'] for r in valid),
                stop_distance_median_m=median([r['stop_distance_m'] for r in valid if r.get('stop_distance_m') is not None])))
    pairs=[]
    for x in new:
        y=next(r for r in old if (r['scene'],r['index'])==(x['scene'],x['index']))
        valid=x.get('technical_validation')==y.get('technical_validation')=='PASS'
        pairs.append(dict(scene=x['scene'],index=x['index'],paired_valid=valid,
            phase38_success=y['success'],phase41_success=x.get('success') if valid else None,
            success_delta=int(x['success'])-int(y['success']) if valid else None,
            success_0p3_delta=int(x['success_0p3'])-int(y['success_0p3']) if valid else None,
            collision_delta=int(x['collision'])-int(y['collision']) if valid else None,
            phase38_stop_distance_m=y.get('stop_distance_m'),phase41_stop_distance_m=x.get('stop_distance_m'),
            phase38_final_distance_m=y.get('final_goal_distance_m'),phase41_final_distance_m=x.get('final_goal_distance_m'),
            phase38_termination=y['termination'],phase41_termination=x.get('termination',x.get('classification'))))
    valid=[x for x in pairs if x['paired_valid']]
    change=[dict(n=len(valid),success_delta=sum(x['success_delta'] for x in valid),
        success_0p3_delta=sum(x['success_0p3_delta'] for x in valid),collision_delta=sum(x['collision_delta'] for x in valid),
        phase41_only=sum(x['phase41_success'] and not x['phase38_success'] for x in valid),
        phase38_only=sum(x['phase38_success'] and not x['phase41_success'] for x in valid))]
    definitions=[dict(metric='Phase41 main',definition='declared arrival AND goal distance<=0.5m AND no collision'),
        dict(metric='Phase41 auxiliary',definition='same declaration; distance<=0.3m / <=1.0m'),
        dict(metric='Phase38 existing',definition='frozen geometric0.3m arrival outcome; different execution day'),
        dict(metric='wrong stop',definition='Phase41 declaration at>0.5m; not applicable to Phase38 geometric-stop rule'),
        dict(metric='timeout',definition='simulation/navigation wall timeout without terminal arrival; collision/corridor stops counted separately')]
    output.mkdir(parents=True,exist_ok=True);save(output/'runs.json',new);save(output/'baselines.json',old)
    state=dict(status='COMPLETE' if len(new)==15 else 'PARTIAL',completed=len(new),paired_valid=len(valid),planned=15,
               protocol_sha256=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest())
    save(output/'analysis.json',state)
    for name,rows in [('summary',summary),('paired',pairs),('changes',change)]:csvout(output/(name+'.csv'),rows)
    doc=Path(document) if document else ROOT/'docs/PHASE41_RESULTS.md'
    doc.write_text('\n\n'.join(table(rows) for rows in ([state],definitions,summary,change,pairs))+'\n')
    return doc


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    assert a.run_root.resolve()==RUN_ROOT.resolve();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))]
        subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase41 declared-arrival pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)


if __name__=='__main__':main()
