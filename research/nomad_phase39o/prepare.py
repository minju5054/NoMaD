"""Input audit, source freeze, bounded scope and dry-run; no dataset solves."""
import argparse,hashlib,json,os,random,re,subprocess,datetime
from collections import defaultdict
import numpy as np
from nomad_isaac.common import sha256_file
from nomad_phase32o.evaluate import save
from .inputs import ROOT,HERE,OUT,collect

def read(p):return json.loads(p.read_text())
def estimate(cases):
    times=[c['recorded_numeric']['pool_wall_s'] for c in cases if c['recorded_numeric'] and c['recorded_numeric'].get('pool_wall_s') is not None]
    floor=float(np.median(times)) if times else 1.;total=0.
    for c in cases:
        baseline=max((c['recorded_numeric'] or {}).get('pool_wall_s',floor),floor)
        ratio=(7+len(c['job']['extra_initializations']))/7 if c['kind']=='R3' else 1.
        total+=baseline*(1+8+8+8*ratio)
    return 120+1.25*total

def subset(cases,n):
    rng=random.Random(20261112);groups=defaultdict(list)
    for c in cases:groups[(c['scene'],c['kind'])].append(c)
    chosen=[];remaining=[]
    for key,g in sorted(groups.items()):
        g=list(g);rng.shuffle(g);chosen.append(g[0]);remaining.extend(g[1:])
    rng.shuffle(remaining);chosen+=remaining[:max(0,n-len(chosen))]
    return sorted(chosen,key=lambda c:c['case_id'])

def prepare(refresh_inputs=False):
    assert not list((OUT/'jobs').glob('*.json')),'Do not refreeze after measured solves'
    if refresh_inputs or not (OUT/'preparation/all_inputs.json').exists():cases,inventory=collect()
    else:cases=read(OUT/'preparation/all_inputs.json');inventory=read(OUT/'preparation/inventory.json')
    selected=cases
    for n in range(len(cases),0,-1):
        selected=cases if n==len(cases) else subset(cases,n)
        if estimate(selected)<=3000:break
    assert selected and estimate(selected)<=3000,'Budget cannot cover even the minimum cohort'
    save(OUT/'preparation/inputs.json',selected)
    p=dict(status='FROZEN_OFFLINE',phase='39-O',variants=['V0','V1','V2','V3'],
        frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selected_jobs=len(selected),available_jobs=len(cases),
        selection='All jobs if conservative estimate<=50min; otherwise seeded stratified subset, at least1 per scene/kind, seed20261112',
        selected_ids=[c['case_id'] for c in selected],excluded_budget_ids=[c['case_id'] for c in cases if c not in selected],
        estimated_minutes=estimate(selected)/60,estimate_slack_multiplier=8,estimate_margin=1.25,estimate_setup_s=120,
        runtime_budget_s=3300,workers=4,blas_threads=1,solver='SLSQP',maxiter=100,ftol=1e-8,solve_retries=0,
        slack=dict(one_per_sdf_inspection=True,rho=1000.,penalty='L1',nonnegative=True,initial='max(0,-physical_sdf_constraint)',accept_max=1e-6,
            physical_violation_tolerance=1e-7,accept_requires_unslacked_physical_constraints=True),
        escape=dict(enabled_when='V2/V3 AND frozen cB<.025',cB='base.query(B)-h/sqrt(2)',
            threshold='min(.025,cB-.005+.5*s) for s<=.30, .025 after',negative_B_precheck_removed=True,
            certificate='exact segment distance; original adjacent waypoint segments split at .30; threshold at segment far endpoint; no new subdivision',
            otherwise='original frozen certificate',certificate_comparison='exact_clearance >= threshold, original strict comparison',
            online_limitation='온라인 시 EC도 같은 c(s) 기준 필요',ec_executed=False),
        additional_initializations=dict(R3_points=11,fan_kept=7,nomad_max=8,previous_installation_max=1,
            arclength_prefix_max_m=1.5,segment_bounds_m=[.10,.20],short_policy='exclude only that extra seed; no padding/extrapolation',
            missing_policy='saved paths only; do not reconstruct missing candidate set/map/job'),
        timing='Original pool_wall_s, warmed persistent4 processes, includes restore/cache/IPC/selection; independent audit excluded',
        variant_order='rotate V0,V1,V2,V3 by sorted case ordinal modulo4',
        gate=dict(scene='SLW',kinds=['R2','R3'],job_success='at least one accepted numerical solution',increase_pp=30.,p95_s=1.,accepted_certificate_failures=0,
            overall='any V1/V2/V3 passes',select_simplest=['V1','V2','V3'],incomplete='NOT_EVALUATED'),
        driving_preparation=False,simulations=0,dataset_solves_during_preparation=0,
        input_sha256=sha256_file(OUT/'preparation/inputs.json'),input_hashes_sha256=sha256_file(OUT/'preparation/input_hashes.json'))
    frozen=read(ROOT/'research/nomad_phase35/protocol.json')
    p['frozen_sources']={**frozen['frozen_sources'],**frozen['source_sha256']}
    for name in ('nomad_phase19r/repair.py','nomad_phase19r/evaluate.py','nomad_phase20/repair.py',
                 'nomad_phase20c/detour.py','nomad_phase20c/detour_known.py','nomad_phase20d/pool.py','nomad_phase20d/recent.py',
                 'nomad_phase15b/depth.py','nomad_phase33p/storage.py','nomad_storage_sdf/loader.py'):
        relative='research/'+name;p['frozen_sources'][relative]=sha256_file(ROOT/relative)
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in sorted(HERE.glob('*.py'))}
    save(HERE/'protocol.json',p)
    from .report import preparation_text
    (ROOT/'docs/PHASE39O_RESOLVE.md').write_text(preparation_text(p))
    return p

def verify(inputs=False):
    p=read(HERE/'protocol.json');assert p['status']=='FROZEN_OFFLINE'
    for file,h in {**p['frozen_sources'],**p['source_sha256']}.items():assert sha256_file(ROOT/file)==h,file
    assert sha256_file(OUT/'preparation/inputs.json')==p['input_sha256']
    assert sha256_file(OUT/'preparation/input_hashes.json')==p['input_hashes_sha256']
    if inputs:
        for file,h in read(OUT/'preparation/input_hashes.json').items():assert sha256_file(file)==h,file
    return p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--refresh-inputs',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    p=prepare(a.refresh_inputs)
    if a.validate:
        env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        result=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase39o.test_phase39o','-v'],cwd=ROOT,env=env,capture_output=True,text=True)
        (OUT/'preparation/tests.txt').write_text(result.stdout+result.stderr)
        assert result.returncode==0,(result.stdout+result.stderr)[-2000:]
        dry=subprocess.check_output(['/usr/bin/python3','-m','nomad_phase39o.run','--dry-run'],cwd=ROOT,env=env,text=True)
        save(OUT/'preparation/dry_run.json',json.loads(dry))
        record=dict(passed=True,unit_tests=int(re.search(r'Ran (\d+) tests',result.stderr).group(1)),
            protocol_sha256=sha256_file(HERE/'protocol.json'),dataset_solves=0,simulation_runs=0,
            stored_jobs_directory_created=(OUT/'jobs').exists())
        assert not record['stored_jobs_directory_created'];save(OUT/'preparation/validation.json',record)
        from .report import preparation_text
        (ROOT/'docs/PHASE39O_RESOLVE.md').write_text(preparation_text(p)+f"\n검증: 합성 단위테스트 {record['unit_tests']}개(해석 Jacobian/슬랙/탈출 certificate/4프로세스/v2 복원/가짜 report), {p['selected_jobs']*4} job×변형 dry-run 통과. 저장 입력의 수치 재풀이는 실행하지 않았다.\n")
    print(json.dumps(dict(selected_jobs=p['selected_jobs'],available_jobs=p['available_jobs'],estimated_minutes=p['estimated_minutes'],dataset_solves=0)))
if __name__=='__main__':main()
