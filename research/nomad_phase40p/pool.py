"""Live VN: R2 is frozen VE, R3 is frozen 39-O3 VN (no A*)."""
import time
from types import FunctionType
from nomad_phase20d import pool as transport
from nomad_phase39o2 import pool as r2
from nomad_phase39o3 import pool as r3
from nomad_phase33p.storage import install


def initialize(queue):
    install()
    transport.initialize(queue)


def evaluate_job(pool, job):
    start = time.monotonic_ns()
    if job['kind'] == 'R2':
        result = r2.evaluate_job(pool, dict(job, variant='VE'))
    elif job['kind'] == 'R3':
        result = r3.evaluate_job(pool, dict(job, variant='VN', soft_policy_map=False))
    else:
        raise ValueError(job['kind'])
    return dict(result, online_variant='VN', selected_initialization=result['selected_sample'] if job['kind']=='R3' else None,
                dispatch_to_complete_s=(time.monotonic_ns()-job['dispatch_ns'])/1e9,
                online_envelope_s=(time.monotonic_ns()-start)/1e9)


def main():
    install()
    fn = transport.main
    FunctionType(fn.__code__, dict(fn.__globals__, initialize=initialize, evaluate_job=evaluate_job),
                 fn.__name__, fn.__defaults__, fn.__closure__)()


if __name__ == '__main__':
    main()
