"""Read-only post-conversion coverage audit; does not repeat EDT computation."""
import json,os,time
from collections import Counter
from pathlib import Path
from . import bulk as b

def audit():
    state=b.read(b.OUT/'state.json');assert state['status']=='COMPLETE','Conversion is not complete'
    plan=b.read(b.OUT/'plan.json');counts=Counter();mismatch=Counter();seen=set();checked=equal=0;errors=[];temporaries=[];saved=0
    for entry in plan['roots']:
        if not entry['target_files']:continue
        folder=b.ROOT_OUT/entry['name']
        summary=b.read(folder/'summary.json') if (folder/'summary.json').exists() else next(r for r in state['completed_roots'] if r['root']==entry['name'])
        if summary['status'].startswith('EXCLUDED'):continue
        manifest=folder/'manifest.jsonl'
        if b.sha(manifest)!=summary['manifest_sha256']:errors.append('Manifest SHA: '+entry['name'])
        rows=b.read_jsonl(manifest);expected={p for run in entry['runs'] for p in run['files']};actual={r['path'] for r in rows}
        if expected!=actual or len(actual)!=len(rows):errors.append('Manifest coverage: '+entry['name'])
        for r in rows:
            path=Path(r['path'])
            if r['path'] in seen:errors.append('Duplicate ownership: '+r['path'])
            seen.add(r['path']);counts[r['status']]+=1;saved+=r['before_bytes']-r['after_bytes']
            if path.stat().st_size!=r['after_bytes']:errors.append('Final size: '+r['path'])
            if r.get('values_bit_equal') is not None:checked+=1;equal+=int(r['values_bit_equal'])
            if r['status'] in ('CONVERTED','ALREADY_COMPACT'):
                if not (r['values_bit_equal'] and r['restored_arrays_bit_equal'] and len(r['arrays_sha256'])==64):errors.append('Missing byte proof: '+r['path'])
            elif r['original_sha256']!=r['new_sha256'] or r['before_bytes']!=r['after_bytes']:errors.append('Skipped file changed: '+r['path'])
            if r['status']=='SKIPPED_SDF_MISMATCH':mismatch[str(r.get('max_abs_difference'))]+=1
        # Originals are never changed here; this only inventories our temp names.
        for directory,_,names in os.walk(entry['path']):
            temporaries.extend(str(Path(directory)/name) for name in names if name.endswith('.sdf-strip.tmp'))
    source_changes=[f for f,h in plan['protected_sources'].items() if b.sha(b.ROOT/f)!=h]
    document_changes=[f for f,h in plan.get('protected_documents',{}).items() if b.sha(b.ROOT/f)!=h]
    inventory=b.read(b.OUT/'backup_inventory_at_disable.json');backup_diffs=[]
    expected_backup={r['path']:r['bytes'] for r in inventory['files']}
    current_backup={str(p):p.stat().st_size for p in Path(inventory['directory']).iterdir() if p.is_file()}
    if current_backup!=expected_backup:backup_diffs=sorted(set(current_backup)^set(expected_backup))+[p for p in set(current_backup)&set(expected_backup) if current_backup[p]!=expected_backup[p]]
    samples=[json.loads(line) for line in (b.OUT/'memory_samples.jsonl').read_text().splitlines() if line]
    transitions=[];last=None
    for sample in samples:
        if last is None or sample['workers']!=last:transitions.append(sample);last=sample['workers']
    memory=dict(transitions=transitions,peak_worker_rss_bytes=max(s['worker_rss_bytes'] for s in samples),
                peak_system_used_bytes=max(s['system_used_bytes'] for s in samples),minimum_available_bytes=min(s['available_bytes'] for s in samples),
                sampling_seconds=.25)
    b.save(b.OUT/'memory_history.json',memory)
    original_names={r['name'] for r in plan['roots']}
    extra_roots=[dict(path=str(p),reason='SYMLINK_NOT_FOLLOWED' if p.is_symlink() else 'CREATED_AFTER_INITIAL_INVENTORY')
                 for p in b.ISAAC.iterdir() if p.is_dir() and (p.is_symlink() or p.name not in original_names)]
    result=dict(epoch=time.time(),status='PASS' if not any((errors,temporaries,source_changes,document_changes,backup_diffs)) else 'FAIL',
                files=len(seen),counts=dict(counts),bit_checked=checked,bit_equal=equal,bit_match_fraction=equal/checked if checked else None,
                saved_bytes=saved,manifest_or_size_errors=errors,temporary_files=temporaries,changed_frozen_sources=source_changes,
                changed_frozen_documents=document_changes,backup_files_changed_or_added=backup_diffs,backup_total_bytes=inventory['total_bytes'],
                sdf_mismatch_max_abs_difference_counts=dict(mismatch),extra_or_symlink_roots=extra_roots,
                validation='Per-file original/temp all-array byte equality and post-replace SHA verified at conversion; final audit checks durable proofs, manifest SHA/coverage, final size, and no leftover temps. No second full EDT pass.',
                phase31e_regression=b.read(b.OUT/'phase31e_regression_final.json'),memory_history=memory)
    b.save(b.OUT/'final_audit.json',result)
    print(json.dumps({k:result[k] for k in ('status','files','counts','saved_bytes','bit_match_fraction')}))
    if result['status']!='PASS':raise RuntimeError('Post-conversion audit failed; see final_audit.json')

if __name__=='__main__':audit()
