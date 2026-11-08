"""Freeze only the specified three map consumers; never solve measured inputs."""
import argparse,datetime,json,os,re,subprocess
import numpy as np
from nomad_isaac.common import sha256_file
from nomad_phase32o.evaluate import save
from .data import ROOT,HERE,OUT,O2,INPUTS,read,collect_metadata

SOFT_POLICY_MAP=False  # Hard constraints/certificate/geometry only; frozen CLR view.

def prepare(refresh=False):
    assert not list((OUT/'jobs').glob('*.json')) and not list((OUT/'baseline_metrics').glob('*.json')),'Do not refreeze after execution'
    if refresh or not (OUT/'preparation/metadata.json').exists():
        meta,hashes=collect_metadata();save(OUT/'preparation/metadata.json',meta);save(OUT/'preparation/reference_hashes.json',hashes)
    else:meta=read(OUT/'preparation/metadata.json')
    assert len(meta)==209;times=[read(m['ve_file'])['numeric']['pool_wall_s'] for m in meta if m['kind']=='R3'];p95=float(np.quantile(times,.95))
    estimate=(180+2*sum(max(t,p95) for t in times)*1.5*9/7)/60
    old=read(ROOT/'research/nomad_phase39o2/protocol.json')
    p=dict(status='FROZEN_OFFLINE',phase='39-O3',frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        variants=['VN','VU'],baseline_variants=['V0','VE'],jobs=209,new_R3_jobs=274,R2_reused_per_variant=72,
        baseline_policy='V0 and VE numerical results never re-solved; unchanged R2 uses cached VE including timing',
        input_reference=str(INPUTS),input_sha256=sha256_file(INPUTS),metadata_sha256=sha256_file(OUT/'preparation/metadata.json'),
        reference_hashes_sha256=sha256_file(OUT/'preparation/reference_hashes.json'),
        maps=dict(VU='base.occupied only',VN='base.occupied OR (~base.observed AND cell-center distance to original B <=.6m)',
            hard_certificate_geometry_scope='same policy map for ALL R3 segments including first.3m',
            legacy_VE_actual_map='base first.3m; occupied OR unknown OR last_free<0 OR age>144tick afterward; strict map for geometry',
            new_maps_recency_blocking=False,cB='always ORIGINAL base.query(B)-h/sqrt(2)',observed='original observed mask, never redefined'),
        soft_policy_map=SOFT_POLICY_MAP,soft_map_scope='frozen VE base/strict split; only explicitly specified hard/certificate/geometry maps replaced',
        frozen_formulation='Phase39-O2 VE B-row exclusion, low-cB escape, exact certificate thresholds, original objective weights/bounds/SLSQP/selection',
        geometry='same Phase39-O2 full-map8connectivity, first strip component,1.6m disk clipping,boundary exclusions, two geometric seeds; no A* or path search',
        metrics=dict(unknown='selected path uniform arclength samples <=.005m over original observed; all and conditional within Euclidean .6m of original B',
            base_exact='ALL accepted paths, exact segment-to-base-occupied-site clearance; selected flag; geometric test only, not EXEC-CERT',
            cached_metrics='additional measurements of saved paths only; no optimizer or baseline certificate replay'),
        gate=dict(all_jobs=True,success_increase_pp=30.,baseline='V0',p95_s=1.,certificate_failures=0,select_simplest=['VN','VU']),
        solver=old['solver'],timing='R3 full4-worker job including map/cache/geometry/IPC/selection; audits excluded; R2 timing reused from VE',
        estimated_minutes=estimate,runtime_budget_s=3300,variant_order='alternate VN,VU by case ordinal',
        simulations=0,measured_solves_during_preparation=0,V0_solves=0,VE_solves=0,astar_used=False,
        frozen_sources={**old['frozen_sources'],**old['source_sha256']},
        source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in sorted(HERE.glob('*.py'))})
    save(HERE/'protocol.json',p)
    save(OUT/'preparation/inventory.json',dict(inputs=209,R3=137,R2=72,new_solves=274,V0_reused=209,VE_reused=209,
        estimated_minutes=estimate,soft_map='FROZEN_VE',VO_generation_on_real_inputs_executed=False))
    from .report import preparation_text
    (ROOT/'docs/PHASE39O3_RESOLVE.md').write_text(preparation_text(p));return p

def verify(references=False):
    p=read(HERE/'protocol.json');assert p['status']=='FROZEN_OFFLINE'
    for f,h in {**p['frozen_sources'],**p['source_sha256']}.items():assert sha256_file(ROOT/f)==h,f
    assert sha256_file(INPUTS)==p['input_sha256'];assert sha256_file(OUT/'preparation/metadata.json')==p['metadata_sha256']
    assert sha256_file(OUT/'preparation/reference_hashes.json')==p['reference_hashes_sha256']
    if references:
        from nomad_phase39o2.prepare import verify as previous_verify
        previous_verify(references=True)
        for f,h in read(OUT/'preparation/reference_hashes.json').items():assert sha256_file(f)==h,f
    return p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--refresh',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args();p=prepare(a.refresh)
    if a.validate:
        env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        r=subprocess.run(['/usr/bin/python3','-m','unittest','discover','-s','research/nomad_phase39o3','-t','research','-p','test_*.py','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
        (OUT/'preparation/tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr)[-2500:]
        dry=subprocess.check_output(['/usr/bin/python3','-m','nomad_phase39o3.run','--dry-run'],cwd=ROOT,env=env,text=True);save(OUT/'preparation/dry_run.json',json.loads(dry))
        v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),new_R3_jobs=274,R2_reused=72,
            V0_solves=0,VE_solves=0,measured_solves=0,simulation_runs=0,protocol_sha256=sha256_file(HERE/'protocol.json'))
        assert not (OUT/'jobs').exists() and not (OUT/'baseline_metrics').exists();save(OUT/'preparation/validation.json',v)
        from .report import preparation_text
        (ROOT/'docs/PHASE39O3_RESOLVE.md').write_text(preparation_text(p)+f"\n검증: 합성 테스트{v['tests']}개·새 R3 274개 dry-run 통과. 실데이터 재풀이0회.\n")
    print(json.dumps(dict(new_R3_jobs=274,V0_solves=0,VE_solves=0,estimated_minutes=p['estimated_minutes'])))
if __name__=='__main__':main()
