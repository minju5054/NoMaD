"""Six frozen pairs, descriptive tables and two actual-render example images."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,verify


def examples(root,output):
    output.mkdir(exist_ok=True)
    for kind in ('original','changed'):
        canvas=Image.new('RGB',(640,272),'white');draw=ImageDraw.Draw(canvas)
        for i,scene in enumerate(SCENES):
            with Image.open(root/'topomap'/scene/f'render_{kind}.png') as im:
                assert im.size==(320,240);canvas.paste(im,(i*320,32))
            draw.text((i*320+10,10),f'{scene} - {kind} - seed217 first box',fill='black')
        canvas.save(output/f'render_{kind}.png',dpi=(150,150))


def generate(root=RUN_ROOT,output=OUT,document=None,baseline=None,render_examples=True):
    p=verify(require_maps=render_examples);root=Path(root);output=Path(output)
    old=baseline if baseline is not None else json.loads((OUT/'preparation/baselines.json').read_text())
    new=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    keys={(r['scene'],r['index']) for r in p['main_order']}
    assert len(new)==len({(r['scene'],r['index']) for r in new}) and all((r['scene'],r['index']) in keys for r in new)
    assert len(old)==6 and {(r['scene'],r['index']) for r in old}==keys
    all_rows=[dict(r,cohort='Phase43-P') for r in old]+[dict(r,cohort='Phase44-P') for r in new];summary=[]
    for scene in (*SCENES,'ALL'):
        for group in ('Phase43-P','Phase44-P'):
            rows=[r for r in all_rows if r['cohort']==group and (scene=='ALL' or r['scene']==scene)]
            valid=[r for r in rows if r.get('technical_validation')=='PASS'];errors=[e['abs_error'] for r in valid for e in r.get('node_errors',[])]
            summary.append(dict(cohort=group,scene=scene,completed=len(rows),valid=len(valid),success=sum(r['success'] for r in valid),
                wrong_stop=sum(r['wrong_stop'] for r in valid),collision=sum(r['collision'] for r in valid),
                node_error_mae=float(np.mean(errors)) if errors else None,node_error_p95=float(np.quantile(errors,.95)) if errors else None,
                stop_distance_median_m=median([r['stop_distance_m'] for r in valid if r.get('stop_distance_m') is not None])))
    pairs=[]
    for x in new:
        y=next(r for r in old if (r['scene'],r['index'])==(x['scene'],x['index']))
        valid=x.get('technical_validation')==y.get('technical_validation')=='PASS'
        pairs.append(dict(scene=x['scene'],seed=x['index'],valid=valid,phase43_success=y['success'],phase44_success=x.get('success'),
            success_delta=int(x['success'])-int(y['success']) if valid else None,
            wrong_stop_delta=int(x['wrong_stop'])-int(y['wrong_stop']) if valid else None,
            phase43_stop_distance_m=y.get('stop_distance_m'),phase44_stop_distance_m=x.get('stop_distance_m')))
    errors=[dict(e,cohort=r['cohort']) for r in all_rows for e in r.get('node_errors',[])]
    state=dict(status='COMPLETE' if len(new)==6 else 'PARTIAL',completed=len(new),planned=6,
               comparison='Same six scene/seed/jitter blocks; appearance and reference RGB only; no six-run decision threshold registered')
    output.mkdir(parents=True,exist_ok=True);save(output/'runs.json',new);save(output/'analysis.json',state)
    for name,rows in [('summary',summary),('paired',pairs),('node_errors',errors)]:csvout(output/(name+'.csv'),rows)
    blocks=[table([state]),table(summary),table(pairs)]
    if render_examples:
        examples(root,output/'figures')
        save(output/'topomaps_sealed.json',json.loads((root/'topomaps_sealed.json').read_text()))
        blocks.append('| 기존 외관 | 변경 외관 |\n|---|---|\n| ![기존](../research/results/phase44p/figures/render_original.png) | ![변경](../research/results/phase44p/figures/render_changed.png) |')
    doc=Path(document) if document else ROOT/'docs/PHASE44P_RESULTS.md';doc.write_text('\n\n'.join(blocks)+'\n');return doc


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    assert a.run_root.resolve()==RUN_ROOT.resolve();doc=generate(a.run_root)
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase44-P appearance pilot','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)


if __name__=='__main__':main()
