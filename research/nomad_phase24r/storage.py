"""Reuse hardened persistence; Phase24-R keeps full maps for seed141."""
from nomad_phase24.storage import *  # operational persistence is unchanged
def retain_full_frames(index,smoke=False):return bool(smoke or int(index)==141)
def capacity(root,plan,free_bytes=None):
    import nomad_phase24.storage as base
    original=base.retain_full_frames;base.retain_full_frames=retain_full_frames
    try:
        try:return base.capacity(root,plan,free_bytes)
        except AssertionError as exc:
            if str(exc)!='No completed-run size evidence':raise
            # A clean Phase24-R main root has no completed run yet. The six
            # full-frame smoke roots are the registered storage evidence.
            smoke=ROOT.parent/'artifacts/isaac6/phase24r_smoke_01'
            samples=[base.measure_run(p,True) for p in sorted(smoke.iterdir()) if p.is_dir() and (p/'launch_complete.json').exists()]
            assert len(samples)==6,'Missing complete smoke storage evidence'
            def projection(item,full):
                run=Path(item['output']);gjob=run/'g_jobs'
                cache=sum(f.stat().st_size for f in gjob.glob('cache_*.npz'));snap=sum(f.stat().st_size for f in gjob.glob('snapshot_*.npz'))
                # Input/outputs remain; only derived cache disappears. Use a
                # conservative 0.50 compression factor for retained inputs.
                raw=item['bytes'] if full else item['thin_projected_bytes'];return raw-cache-.5*snap
            full_non=[x for x in samples if not x['output'].endswith('_G')];full_g=[x for x in samples if x['output'].endswith('_G')]
            full_mean=sum(x['bytes'] for x in samples)/len(samples);compact_mean=sum(x['thin_projected_bytes'] for x in samples)/len(samples)
            projected_full=dict(C0=sum(x['bytes'] for x in full_non if x['output'].endswith('_C0'))/2,C1=sum(x['bytes'] for x in full_non if x['output'].endswith('_C1'))/2,G=sum(projection(x,True) for x in full_g)/len(full_g))
            projected_compact=dict(C0=sum(x['thin_projected_bytes'] for x in full_non if x['output'].endswith('_C0'))/2,C1=sum(x['thin_projected_bytes'] for x in full_non if x['output'].endswith('_C1'))/2,G=sum(projection(x,False) for x in full_g)/len(full_g))
            pending=list(plan);expected=sum((projected_full if retain_full_frames(j['index']) else projected_compact)[j['method']] for j in pending);free=base.shutil.disk_usage(root.parent if root.parent.exists() else ROOT).free if free_bytes is None else free_bytes
            return dict(remaining_runs=len(pending),completed_valid_runs=0,completed_full_mean_bytes=full_mean,compact_mean_bytes=compact_mean,
                old_remaining_bytes=full_mean*len(pending),expected_remaining_bytes=expected,headroom_bytes=base.HEADROOM_BYTES,required_free_bytes=expected+base.HEADROOM_BYTES,
                free_bytes=free,enough=free>=expected+base.HEADROOM_BYTES,details=samples,projected_full_bytes_by_method=projected_full,projected_compact_bytes_by_method=projected_compact,
                checked_ns=base.time.time_ns(),estimate_source='six_complete_phase24r_smokes; derived G strict-cache removed and input snapshot losslessly compressed after all solver workers finish')
    finally:base.retain_full_frames=original
