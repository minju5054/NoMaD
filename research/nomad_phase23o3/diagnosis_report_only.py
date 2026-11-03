"""Rebuild diagnosis presentation from saved outcomes; never solve again."""
import ast,csv,json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase23o2.inputs import read,write
from .diagnose import OUT,SOURCE,HERE,selected_values
from .diagnosis_report import generate

def rows(file):
    def parse(v):
        if not v:return None
        try:return ast.literal_eval(v)
        except (ValueError,SyntaxError):return v
    with Path(file).open() as stream:return [{k:parse(v) for k,v in r.items()} for r in csv.DictReader(stream)]
def main():
    protocol=read(OUT/'protocol.json');p=read(HERE/'protocol.json');m=read(SOURCE/'manifest.json');saved=read(OUT/'paths.json');records={};angles={r['case_id']:r['angle_to_positive_x_deg'] for r in rows(OUT/'directions.csv')}
    for identity in protocol['cases']:
        c=next(c for c in m['training'] if c['case_id']==identity);original,base=selected_values(c,p);data=saved[identity];extra={}
        for method,entry in data['extra'].items():extra[method]=dict(converted=entry['converted'],outcome=read(OUT/'solves'/f'{identity}_{method}.json'))
        records[identity]=dict(case=c,original=original,base=base,direction_world=data['direction_world'],direction_angle_deg=angles[identity],extra=extra)
    # Restore the preserved registered text before annotating, avoiding duplicate warnings.
    (ROOT/'docs/PHASE23O3_UNIFIED.md').write_text((OUT/'original_registered_report.md').read_text())
    generate(protocol,records,rows(OUT/'factor_costs.csv'),rows(OUT/'pairs.csv'),rows(OUT/'side_initializations.csv'),rows(OUT/'memory_sets.csv'),read(OUT/'summary.json'),read(OUT/'rejudgement.json'))
    write(OUT/'presentation_revision.json',dict(report_source_sha256=sha256_file(HERE/'diagnosis_report.py'),new_solves=0,reason='Include complete box extents and distinguish feasible retained paths from converged solutions'))
if __name__=='__main__':main()
