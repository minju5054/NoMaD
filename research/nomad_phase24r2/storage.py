"""Same atomic state/20GB reserve and thin retention; full L2 seed151 only."""
from nomad_phase24.storage import *


def retain_full_frames(index, smoke=False):
    return bool(smoke or int(index) == 151)


def capacity(root, plan, free_bytes=None):
    # Per-method size estimates include frozen completed L2 runs, preventing
    # a first short G run from underestimating remaining C0/C1 data.
    root = Path(root)
    pending = [j for j in plan if not (root/'metrics'/(j['key']+'.json')).exists()]
    details = []
    previous = ROOT.parent/'artifacts/isaac6/phase24r_pilot_01'
    for metric in sorted((previous/'metrics').glob('L2_*.json')) + sorted((root/'metrics').glob('*.json')):
        r = read(metric)
        if r.get('technical_validation') != 'PASS':
            continue
        run = Path(r['output'])
        full = read(run/'storage_policy.json')['full_frames']
        details.append(dict(method=r['method'], full_frames=full, **measure_run(run, full)))
    assert details, 'No completed-run size evidence'
    def estimate(method, full):
        rows = [r for r in details if r['method'] == method and (not full or r['full_frames'])]
        assert rows, method
        return sum(r['bytes'] if full else r['thin_projected_bytes'] for r in rows)/len(rows)
    expected = sum(estimate(j['method'], retain_full_frames(j['index'])) for j in pending)
    free = shutil.disk_usage(root.parent if root.parent.exists() else ROOT).free if free_bytes is None else free_bytes
    return dict(remaining_runs=len(pending), completed_valid_runs=len(details),
                expected_remaining_bytes=expected, old_remaining_bytes=sum(estimate(j['method'], True) for j in pending),
                required_free_bytes=expected+HEADROOM_BYTES, free_bytes=free, headroom_bytes=HEADROOM_BYTES,
                enough=free >= expected+HEADROOM_BYTES, details=details, checked_ns=time.time_ns(),
                estimate_source='completed frozen Phase24-R L2 runs plus completed R2 runs, per-method mean')
