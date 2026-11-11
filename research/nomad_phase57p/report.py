"""End-of-campaign frozen outcomes, adoption tables and one top-down/run."""
import argparse,json,subprocess
from pathlib import Path
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,verify
FIELDS=('classification','success','collision','wrong_stop','timeout_without_declaration','box_passage','box_passage_from_spawn_s','goal_time_s','stopped_s','graph_adoption_rate','graph_solve_p50_s','graph_solve_p95_s')
def generate(root=RUN_ROOT,output=OUT,document=None):
    p=verify();root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    runs=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    expected={(r['scene'],r['index'],r['method']) for r in p['main_order']};keys=[(r['scene'],r['index'],r['method']) for r in runs]
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    summary=[]
    for m in METHODS:
        for s in (*SCENES,'ALL'):
            rr=[r for r in runs if r['method']==m and (s=='ALL' or r['scene']==s)];good=[r for r in rr if r['technical_validation']=='PASS']
            attempts=sum(r.get('graph_attempts',0) for r in good);applied=sum(r.get('graph_applied',0) for r in good)
            summary.append(dict(method=m,scene=s,n=len(rr),valid=len(good),**{k:sum(bool(r.get(k)) for r in good) for k in FIELDS[1:6]},
                goal_time_s=median([r['goal_time_s'] for r in good if r.get('goal_time_s') is not None]),stopped_s=median([r['stopped_s'] for r in good if r.get('stopped_s') is not None]),
                graph_attempts=attempts,graph_applied=applied,graph_adoption_rate=applied/attempts if attempts else None))
    by={(r['scene'],r['index'],r['method']):r for r in runs};details=[]
    for j in p['main_order']:
        r=by.get((j['scene'],j['index'],j['method']));row=dict(j,status=r['technical_validation'] if r else 'NOT_RUN')
        row.update({k:r.get(k) if r else None for k in FIELDS});details.append(row)
    status=dict(status='COMPLETE' if len(runs)==18 else 'PARTIAL' if runs else 'PREPARED_NOT_RUN',planned=18,completed=len(runs),protocol_sha256=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest())
    save(output/'runs.json',runs);save(output/'status.json',status);csvout(output/'summary.csv',summary);csvout(output/'runs.csv',details)
    from .figures import generate as figures
    files=figures(runs,output/'figures')
    doc=Path(document) if document else ROOT/'docs/PHASE57P_RESULTS.md'
    lines=['# Phase57-P',table([status]),'NOMAD_RAW는 Phase47-C 원래 argmin 위치추정/sample0/실행기를 유지한다. MIN 두 방법만 HMM·EC-tail·ENDPOINT latch를 사용하고 depth 사전 필터·회복·정렬·저속 후보 단계는 끈다. 1s 만료와 공식 도착 판정은 유지한다. 성과로 파라미터를 바꾸지 않는다.',table(summary),table([{k:('—' if v is None else v) for k,v in r.items()} for r in details])]
    for file in files:
        f=Path(file);lines.append(f'![{f.stem}](../{f.relative_to(ROOT)})' if f.is_relative_to(ROOT) else f'![{f.stem}]({f})')
    doc.write_text('\n\n'.join(lines)+'\n');return doc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');a=ap.parse_args();doc=generate()
    if a.publish:
        paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))];subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
        if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
            subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','--quiet','-m','Report Phase57-P RAW MIN and MIN+G18 pilot with run plots','--',*paths],cwd=ROOT,check=True)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
