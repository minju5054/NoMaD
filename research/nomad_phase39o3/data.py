"""Read existing inputs and numeric results; do not copy input payloads."""
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase39o2.data import INPUTS,read

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase39o3'
O2=ROOT/'research/results/phase39o2'
BASELINES=('V0','VE')

def collect_metadata():
    from nomad_phase39o2.prepare import verify as old_verify
    old_verify(references=True);previous=read(O2/'preparation/metadata.json');manifest=read(O2/'result_hashes.json')
    hashes={str(INPUTS):sha256_file(INPUTS)};meta=[]
    for row in previous:
        file=O2/'jobs'/f"{row['case_id']}_VE.json";h=sha256_file(file);assert h==manifest[f'jobs/{file.name}']
        ve=read(file);assert ve['case_id']==row['case_id'] and ve['variant']=='VE'
        hashes[str(file)]=h;hashes[row['baseline_file']]=sha256_file(row['baseline_file'])
        meta.append(dict(row,ve_file=str(file),ve_sha256=h))
    return meta,hashes

def runtime_cases():
    meta={r['case_id']:r for r in read(OUT/'preparation/metadata.json')}
    return [dict(c,o3=meta[c['case_id']]) for c in read(INPUTS)]
