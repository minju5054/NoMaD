"""Reuse Phase20 numerical replay; only the oracle placement diagnostic differs."""
import types
from pathlib import Path
import nomad_phase20.metrics as base
from .config import place

_audit=types.FunctionType(base.audit.__code__,{**base.__dict__,'place':place},name='audit')

def audit(run):
    result=_audit(run)
    # Dedicated pool log also preserves results completed after the last control tick.
    all_jobs=base.rows(Path(run)/'repair_pool_jobs.jsonl');assert not any(j.get('error') for j in all_jobs)
    jobs=[j for j in all_jobs if 'pool_wall_s' in j]
    lookup={j['job_id']:j for j in jobs};assert len(jobs)==len(lookup)
    samples=[v for j in jobs for v in j['sample_solve_s']]
    result.update(sample_solve_s=base.stats(samples),eight_solve_s=base.stats([j['pool_wall_s'] for j in jobs]),
        dispatch_to_complete_s=base.stats([j['dispatch_to_complete_s'] for j in jobs]),repair_timing_jobs=len(jobs),
        repair_job_timings=[dict(job_id=j['job_id'],sample_solve_s=j['sample_solve_s'],sample_total_s=j['sample_total_s'],
                               pool_wall_s=j['pool_wall_s'],dispatch_to_complete_s=j['dispatch_to_complete_s'],
                               pids=[r['pid'] for r in j['results']],sample_solver_started=j['sample_solver_started'],
                               sample_dispositions=j['sample_dispositions'],optimizer_wall_s=j['optimizer_wall_s']) for j in jobs])
    return result
