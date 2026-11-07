"""Sequential paired offline jobs; each job uses the frozen four-process pool."""
import argparse, hashlib, json, multiprocessing as mp, os, signal, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase20d.pool import ping
from nomad_phase32o.evaluate import save, csvout, clean
from nomad_phase32o.exec_cert import certify
from nomad_phase15b.depth import Snapshot
from nomad_phase33p.storage import install
from .inputs import OUT
from .pool import initialize, evaluate_job

FROZEN = ('nomad_phase19r/repair.py', 'nomad_phase19r/evaluate.py',
          'nomad_phase20/repair.py', 'nomad_phase20d/pool.py',
          'nomad_phase20c/detour.py', 'nomad_phase15b/depth.py',
          'nomad_phase32o/exec_cert.py', 'nomad_phase28/alignment.py',
          'nomad_phase20/execution.py', 'nomad_phase33p/storage.py',
          'nomad_storage_sdf/loader.py')


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze():
    file = Path(__file__).with_name('protocol.json')
    assert not file.exists(), 'Protocol already frozen'
    p = dict(phase='34-O', status='FROZEN_SOLVER', frozen_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        source_commit=os.popen('git rev-parse HEAD').read().strip(),
        source_hashes={str(Path('research') / f): sha(ROOT/'research'/f) for f in FROZEN},
        new_solver_hashes={f:sha(Path(__file__).with_name(f)) for f in ('repair.py','pool.py')},
        input_sha256=sha(OUT/'inputs.json'), input_manifest_sha256=sha(OUT/'input_hashes.json'),
        cohort=read(OUT/'input_audit.json'), variants=['R2','R2_CLR'],
        only_method_change=dict(residual='max(0,0.15-depth_clearance)/0.05', weight=1.,
            samples='same 9 closed points/segment as frozen R3, 63 points for 7 R2 segments',
            objective='0.5 * sum(residual**2)', oracle_input=False),
        optimization=dict(samples=8, workers=4, solver='SLSQP', maxiter=100, ftol=1e-8,
            initialization='frozen Phase20 R2', hard_constraints='unchanged', certificate='unchanged',
            selector='accepted sample of minimum mean edit, index tie-break', retries=0),
        timing='frozen evaluate_job.pool_wall_s: eight samples in warmed persistent 4-process pool, including IPC/map restore/selection; excludes EC',
        pairing='same saved job B/samples/map; R2 first for even ordinal, CLR first for odd; no parameter tuning',
        success='original public accepted flag (solver success AND constraints AND certificate); not EC-filtered selection',
        missing_EC_policy='Pending user clarification; numeric solves independent; do not compute gate until fixed',
        gate=dict(solution_rate_max_decrease_pp=5., joint_EC_min_increase_pp=20., total_job_p95_ratio_max=1.3),
        driving_preparation=False, simulation=False)
    save(file,p)
    return p


def verify():
    p=read(Path(__file__).with_name('protocol.json'))
    for name,h in p['source_hashes'].items():
        assert sha(ROOT/name)==h,name
    for name,h in p['new_solver_hashes'].items():
        assert sha(Path(__file__).with_name(name))==h,name
    assert sha(OUT/'inputs.json')==p['input_sha256']
    assert sha(OUT/'input_hashes.json')==p['input_manifest_sha256']
    return p


def solve_all():
    verify(); install(); cases=read(OUT/'inputs.json'); start=time.monotonic()
    status=dict(status='RUNNING',jobs_total=len(cases),jobs_completed=0,stage='PAIRED_SOLVE')
    ctx=mp.get_context('spawn'); ready=ctx.Queue()
    # A fixed single-threaded BLAS setting is applied equally to both arms.
    assert os.environ.get('OPENBLAS_NUM_THREADS')=='1'
    signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(ready,)) as pool:
            warm=[pool.submit(ping) for _ in range(4)]; pids=[ready.get(timeout=90) for _ in range(4)]
            for f in warm:f.result()
            assert len(set(pids))==4
            save(OUT/'environment.json',dict(pids=pids,workers=4,cpu_count=os.cpu_count(),
                cpu_affinity=sorted(os.sched_getaffinity(0)),python=os.sys.version,numpy=np.__version__,
                OPENBLAS_NUM_THREADS=os.environ['OPENBLAS_NUM_THREADS'],source_commit=os.popen('git rev-parse HEAD').read().strip()))
            for ordinal,c in enumerate(cases):
                file=OUT/'numeric'/f"{c['case_id']}.json"
                if file.exists():
                    old=read(file); assert set(old['variants'])=={'R2','R2_CLR'}
                else:
                    variants={}
                    for variant in (('R2','R2_CLR') if ordinal%2==0 else ('R2_CLR','R2')):
                        job=dict(kind='R2',variant=variant,job_id=c['job_id'],B=c['B'],
                            samples_world=c['samples_world'],snapshot_file=c['planning_snapshot_file'],dispatch_ns=time.monotonic_ns())
                        numeric=evaluate_job(pool,job)
                        assert len(numeric['results'])==8
                        variants[variant]=numeric
                    save(file,dict(case_id=c['case_id'],variants=variants))
                status.update(jobs_completed=ordinal+1,last=c['case_id'],elapsed_s=time.monotonic()-start)
                save(OUT/'status.json',status)
                if ordinal%20==0:print(f"[solve] {ordinal+1}/{len(cases)} elapsed={status['elapsed_s']:.1f}s",flush=True)
        status.update(status='SOLVES_COMPLETE',elapsed_s=time.monotonic()-start)
        save(OUT/'status.json',status)
    except BaseException as exc:
        status.update(status='FAILED',error=repr(exc),elapsed_s=time.monotonic()-start)
        save(OUT/'status.json',status);raise


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--solve',action='store_true');a=ap.parse_args()
    if a.freeze:print(json.dumps(freeze()['cohort']))
    if a.solve:solve_all()


if __name__=='__main__':main()
