import json,hashlib,random
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase33p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase33p_01'
METHODS=('C0-NA+EC','G18X+EC');SCENES=('SLW','LC','L2','H1','H2');INDICES=(208,209);SEED=20261108

def order():
    rng=random.Random(SEED);rows=[]
    for i in INDICES:
        for scene in SCENES:
            methods=list(METHODS);rng.shuffle(methods);rows.extend(dict(scene=scene,index=i,method=m) for m in methods)
    return rows

def freeze_offline():
    from .dataset import select
    from nomad_phase32.config import verify
    baseline=verify();cases=select();p=HERE/'protocol.json'
    if p.exists():raise FileExistsError('Protocol already frozen; do not overwrite after evaluation')
    frozen={str(x.relative_to(ROOT)):sha256_file(x) for folder in ('nomad_phase32','nomad_phase32o','nomad_phase29','nomad_phase17','nomad_phase20','nomad_phase20c','nomad_phase20d','nomad_phase20f','nomad_phase12','nomad_phase5','nomad_phase0','nomad_phase28','nomad_phase26','nomad_phase24r') for x in (ROOT/'research'/folder).glob('*.py')}
    frozen={**baseline['frozen_sources'],**baseline['source_sha256'],**baseline['historical_sources'],**frozen}
    spec=dict(phase='33-P',status='FROZEN_OFFLINE',navigation_allowed=False,seed=SEED,
        cohort_sha256=sha256_file(OUT/'cohort.json'),input_manifest_sha256=sha256_file(OUT/'input_manifest.json'),cohort_counts=dict(NORMAL=200,R2=7,R3=40,total=247),gate_population='all 247 unique PATH_APPLIED events',
        curvature=dict(limit_m_inv=2.,L_m=.25,formula='e=R-sqrt(R^2-L^2), R=1/abs(k), e(0)=0',
            assignment='max absolute endpoint Menger curvature per segment; endpoint nodes copy nearest internal curvature; left endpoint wins exact ties',
            near_start='R2/R3 original 0.30m relaxed threshold retained, plus e',
            infeasible_iterates='C1 tangent continuation beyond |k|=2 to avoid undefined sqrt; accepted domain uses exact formula',
            zero_derivative='zero subgradient at k=0'),
        frozen_changes=['hard curvature limit only','add e to existing hard SDF threshold only'],
        certificates='Existing continuous/exact certificate algorithms and tolerances retained; modified hard SDF rows include existing h/sqrt(2)+Lsegment/16 margins',
        comparison=dict(baseline='Frozen G18 numerical solver replay, not EC-selected installed path',variant='G18X numerical solver replay',
            NORMAL='single original job; recover previous_xy from earlier applied Graph RESULT logs',
            R2='all 8 original samples, persistent 4-process pool, original select_repair',R3='all 7 original angles, persistent 4-process pool, original select_detour before EC',
            EC_context='same recorded installation CHECK pose, actual velocity, latest depth snapshot and retained speed cap for both numerical solutions',
            failures='No selected feasible/certified solution => EC failure',
            metrics={'a':'existing accepted/feasible Graph output fraction (solver+hard constraints+certificate)',
                     'b':'EC PASS / selected feasible solutions','c':'selected feasible solution AND EC PASS / all events'},
            timing='NORMAL constructor+solve+certificate on CPU7; R2/R3 full frozen pool job, including load/cache/I/O/all starts; no EC time in Graph time',
            timing_order='alternate baseline-first and variant-first by case ordinal; one solve per variant/event, no retry',
            installed_path='reference-only EC replay column',
            limitation='fixed saved input/install state; no closed-loop pose/depth/NoMaD regeneration or future supersession replay'),
        gate=dict(label_pass='OFFLINE_OK',label_fail='OFFLINE_FAIL',solve_success_min=.8,compute_p95_max_s=.15,ec_rule='G18X metric (c) strictly greater than G18 metric (c)',denominator=247),
        storage=dict(version=2,writer='savez_compressed; no values; preserve all occupancy/observation/history arrays, component identity metadata, origin/h/radius',
            loader='nomad_storage_sdf.loader; original empty-map constant in metadata to preserve bits; no live EDT/map update change',
            legacy_phase32='bit-equal only; no backups; per-file atomic replacement',derived_cache='Frozen transient R3 derived cache transport retained; offline caches deleted after each case'),
        conditional_main=dict(run_root=str(RUN_ROOT),methods=list(METHODS),scenes=list(SCENES),indices=list(INDICES),jobs=20,main_order=order(),
            enabled_only_after='OFFLINE_OK',retry_technical=1,free_disk_min_bytes=30_000_000_000,cleanup_cache=True,decision='PROMISING iff G18X arrivals >= C0-NA+EC and collisions <= C0-NA+EC'),
        frozen_sources=frozen,source_sha256={str(x.relative_to(ROOT)):sha256_file(x) for x in HERE.glob('*.py')},
        storage_loader_sha256=sha256_file(ROOT/'research/nomad_storage_sdf/loader.py'))
    p.write_text(json.dumps(spec,indent=2)+'\n');print('FROZEN_OFFLINE',sha256_file(p));return spec

def verify():
    p=json.loads((HERE/'protocol.json').read_text())
    assert p['status'] in ('FROZEN_OFFLINE','FROZEN')
    for file,h in {**p['frozen_sources'],**p['source_sha256']}.items():assert sha256_file(ROOT/file)==h,file
    assert sha256_file(OUT/'cohort.json')==p['cohort_sha256'];assert sha256_file(OUT/'input_manifest.json')==p['input_manifest_sha256'];assert sha256_file(ROOT/'research/nomad_storage_sdf/loader.py')==p['storage_loader_sha256']
    return p

if __name__=='__main__':freeze_offline()
