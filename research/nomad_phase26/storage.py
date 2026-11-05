"""Frozen compact archival policy and atomic persistence; first seed full only."""
from nomad_phase24.storage import *
def retain_full_frames(index,smoke=False):return bool(smoke or int(index)==201)

def measure_storage(run,full=True):
    run=Path(run)
    if (run/'depth/updates.jsonl').exists():return measure_run(run,full)
    # B0 intentionally has no depth directory; apply the same RGB-only archive
    # accounting without requiring a nonexistent map publication log.
    total=raw=0
    for f in iter_files(run):
        rel=f.relative_to(run);n=f.stat().st_size;total+=n
        if rel.parts[0]=='observations' or (len(rel.parts)==1 and f.suffix=='.png' and (f.name.startswith('observation_') or f.name=='goal.png')):raw+=n
    return dict(output=str(run),bytes=total,thin_projected_bytes=total-raw if full else total,raw_frame_bytes=raw,unneeded_map_bytes=0)

def capacity(root,plan,free_bytes=None):
    root=Path(root);pending=[j for j in plan if not (root/'metrics'/(j['key']+'.json')).exists()]
    smoke=ROOT.parent/'artifacts/isaac6/phase26_smoke_01'
    details=[]
    for f in sorted((smoke/'metrics').glob('*.json')):
        r=read(f)
        if r.get('technical_validation')=='PASS':
            details.append(dict(method=r['method'],scene=r['scene'],**measure_storage(r['output'],True)))
    assert details,'No complete Phase26 smoke storage evidence'
    def estimate(j,full):
        rr=[r for r in details if r['method']==j['method'] and r['scene']==j['scene']]
        if not rr:rr=[r for r in details if r['method']==j['method']]
        if not rr:rr=details
        key='bytes' if full else 'thin_projected_bytes'
        return max(r[key] for r in rr)
    expected=sum(estimate(j,retain_full_frames(j['index'])) for j in pending)
    free=shutil.disk_usage(root.parent if root.parent.exists() else ROOT).free if free_bytes is None else free_bytes
    return dict(remaining_runs=len(pending),expected_remaining_bytes=expected,required_free_bytes=expected+HEADROOM_BYTES,free_bytes=free,
        headroom_bytes=HEADROOM_BYTES,enough=free>=expected+HEADROOM_BYTES,details=details,
        estimate_source='smoke bytes, same scene/method where available, otherwise maximum same-method smoke; no retention of raw frames except seed201')
