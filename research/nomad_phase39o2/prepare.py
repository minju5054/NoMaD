"""Read-only baseline audit, freeze, tests and dry-run; no measured solves."""
import argparse,datetime,json,os,re,subprocess
from collections import Counter
import numpy as np
from nomad_isaac.common import sha256_file
from nomad_phase32o.evaluate import save
from .data import ROOT,HERE,OUT,OLD,INPUTS,read,collect_metadata

def prepare(refresh=False):
    assert not list((OUT/'jobs').glob('*.json')),'Cannot refreeze after measurement'
    if refresh or not (OUT/'preparation/metadata.json').exists():
        cases,meta,hashes=collect_metadata()
        save(OUT/'preparation/metadata.json',meta);save(OUT/'preparation/reference_hashes.json',hashes)
    else:meta=read(OUT/'preparation/metadata.json')
    assert len(meta)==209
    times=[read(m['baseline_file'])['numeric']['pool_wall_s'] for m in meta];p95=float(np.quantile(times,.95))
    # V0 is historical. Conservative planning factors only, not new timings.
    budget=sum(max(t,p95)*(1+9/7+3*9/7) for t in times)
    estimated=(120+1.25*(budget+.15*2*sum(m['kind']=='R3' for m in meta)))/60
    oldp=read(ROOT/'research/nomad_phase39o/protocol.json')
    p=dict(status='FROZEN_OFFLINE',phase='39-O2',frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        variants=['VB','VO','VE'],jobs=209,planned_new_jobs=627,V0_policy='Reuse saved Phase39-O V0 numeric results/timings only; solver route explicitly rejects V0',
        input_reference=str(INPUTS),input_sha256=sha256_file(INPUTS),metadata_sha256=sha256_file(OUT/'preparation/metadata.json'),
        reference_hashes_sha256=sha256_file(OUT/'preparation/reference_hashes.json'),
        B_row='Remove only first segment k0 SDF row; keep soft residual at B and every other constraint',
        slack_variables=0,solver=dict(method='SLSQP',maxiter=100,ftol=1e-8,violation_tolerance=1e-7,workers=4,blas_threads=1,retries=0),
        VO=dict(map='same R3 strict map: occupied OR unknown OR free older than2s',connectivity=8,strip_length_m=1.6,strip_width_m=.18,
            first_component='Full-map label whose cell center has smallest nonnegative forward coordinate inside strip; label tie-break',
            clipping='Measure full component after clipping cell centers to disk radius1.6m around B',
            side_boundary='Any tied extremum cell square touches disk, or same-component neighboring cell is clipped outside disk -> exclude side',
            side_choice='Extreme cell nearest B, row/column tie-break',offset_m=.14,
            path='B->via->forward along u_ref; via retained as vertex; closed-form10-segment allocation, preferred.15m, target forward1.2m, obey.10-.20m and1.6m disk',
            excluded='no component / boundary touch / via blocked or out of map / spacing or disk impossible',
            no_path_search=True,fan_initializations=7,extra_initializations_max=2),
        VE=dict(enabled_when='cB<.025 only',cB='base.query(B)-h/sqrt(2)',optimization='min(.025,cB-.005+.5*s)',
            maps='base for s<=.30, strict afterward, as frozen',negative_B_precheck_removed=True,B_row_removed_always=True,
            certificate='sesc=(.03-cB)/.5; closed[0,sesc] exact>=cB-.005, closed[sesc,end] exact>=.025; split at.30 and sesc',
            high_cB='original constraints except B row, and original certificate',ec_used=False),
        grouping=dict(order='within same run by simulation_time,dispatch_ns,job_id',adjacent_xy_threshold_m=.01,
            mixed_R2_R3=True,transitive_adjacent=True,group_success='any accepted job',run_success='any successful group; also report successful groups/total groups',gate_uses_original_jobs=True),
        bins=['cB<0','0<=cB<.03125','cB>=.03125'],
        gate=dict(all_jobs=True,success_increase_pp=30.,p95_s=1.,accepted_certificate_failures=0,select_simplest=['VB','VO','VE']),
        timing='warmed4-process full job including restore/strict cache/geometric initialization/IPC/selection; independent audit excluded; V0 timing historical',
        estimated_minutes=estimated,runtime_budget_s=3300,variant_order='rotate VB,VO,VE by case ordinal modulo3',
        simulations=0,measured_solves_during_preparation=0,astar_used=False,
        frozen_sources=oldp['frozen_sources'],source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in sorted(HERE.glob('*.py'))})
    save(HERE/'protocol.json',p)
    counts=Counter((m['cB_bin'],m['kind']) for m in meta)
    save(OUT/'preparation/inventory.json',dict(jobs=len(meta),baseline_results_reused=len(meta),baseline_solves=0,
        positional_groups=len({m['group'] for m in meta}),runs=len({m['run'] for m in meta}),
        groups=[dict(cB_bin=b,kind=k,jobs=n) for (b,k),n in sorted(counts.items())],estimated_minutes=estimated))
    from .report import preparation_text
    (ROOT/'docs/PHASE39O2_RESOLVE.md').write_text(preparation_text(p));return p

def verify(references=False):
    p=read(HERE/'protocol.json');assert p['status']=='FROZEN_OFFLINE'
    for f,h in {**p['frozen_sources'],**p['source_sha256']}.items():assert sha256_file(ROOT/f)==h,f
    assert sha256_file(INPUTS)==p['input_sha256'];assert sha256_file(OUT/'preparation/metadata.json')==p['metadata_sha256']
    assert sha256_file(OUT/'preparation/reference_hashes.json')==p['reference_hashes_sha256']
    if references:
        from nomad_phase39o.prepare import verify as old_verify
        old_verify(inputs=True)
        for f,h in read(OUT/'preparation/reference_hashes.json').items():assert sha256_file(f)==h,f
    return p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--refresh',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args();p=prepare(a.refresh)
    if a.validate:
        env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        result=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase39o2.test_phase39o2','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
        (OUT/'preparation/tests.txt').write_text(result.stdout+result.stderr);assert result.returncode==0,(result.stdout+result.stderr)[-3000:]
        dry=subprocess.check_output(['/usr/bin/python3','-m','nomad_phase39o2.run','--dry-run'],cwd=ROOT,env=env,text=True);save(OUT/'preparation/dry_run.json',json.loads(dry))
        validation=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',result.stderr).group(1)),new_job_variants=627,V0_reused=209,V0_solves=0,
            measured_solves=0,simulation_runs=0,protocol_sha256=sha256_file(HERE/'protocol.json'),output_jobs_created=(OUT/'jobs').exists())
        assert not validation['output_jobs_created'];save(OUT/'preparation/validation.json',validation)
        from .report import preparation_text
        (ROOT/'docs/PHASE39O2_RESOLVE.md').write_text(preparation_text(p)+f"\n검증: 합성 테스트{validation['tests']}개와627개 새 job×변형 dry-run 통과. 저장 입력 및 V0 재풀이는0회.\n")
    print(json.dumps(dict(jobs=209,new_job_variants=627,V0_solves=0,estimated_minutes=p['estimated_minutes'])))
if __name__=='__main__':main()
