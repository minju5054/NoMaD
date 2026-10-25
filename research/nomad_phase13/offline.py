"""Deterministic saved-chunk/checkpoint checks; no simulation, GPU or Graph solves."""
import json
import subprocess
import tempfile
import sys
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT, sha256_file, write_json, local_to_world
from nomad_isaac.async_report import rows
from .config import HERE, protocol
from .methods import freshest, smooth
from .metrics import extra_metrics


def curvature(xy):
    xy=np.asarray(xy);a=xy[1:-1]-xy[:-2];b=xy[2:]-xy[1:-1];c=xy[2:]-xy[:-2]
    den=np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)*np.linalg.norm(c,axis=1)
    return float(np.max(np.abs(np.divide(2*(a[:,0]*b[:,1]-a[:,1]*b[:,0]),den,out=np.zeros_like(den),where=den>1e-15)))) if len(den) else 0.


def main():
    target=HERE/'offline_validation.json'
    assert not target.exists(),'Existing validation preserved'
    rs=json.loads((ROOT/'research/results/phase12/runs.json').read_text())
    selected=sorted([r for r in rs if r['method']=='FRESHEST+GRAPH-GF' and r.get('technical_validation')=='PASS'],key=lambda r:r['index'])[:3]
    assert len(selected)==3
    inputs=[ROOT/'research/results/phase12/runs.json'];samples=[];checks=[]
    for r in selected:
        run=Path(r['output']);cp=extra_metrics(run,r)
        # Includes a real pre-checkpoint failure: null is the required result.
        from nomad_phase0.chunk_report import trace
        records, poses = trace(run)
        expected = np.flatnonzero(poses[:, 0] >= cp['checkpoint_x_m'])
        expected_tick = int(expected[0]) if len(expected) else None
        if expected_tick is not None and (r.get('geometric_overlap') or r.get('corridor_violation')):
            if float(records[expected_tick]['simulation_time_s']) >= r['duration_s']:
                expected_tick = None
        assert cp['checkpoint_tick'] == expected_tick
        checks.append(dict(key=r['key'],classification=r['classification'],**cp))
        inputs += [run/n for n in ('scenario.json','agent_trajectory.csv','controller.jsonl','events.jsonl')]
        # First two switched chunks of each first three valid GF runs; never filter on smoothness/results.
        for e in rows(run/'events.jsonl')[:2]:
            b=np.array(e['agent_pose_at_switch']);a=np.array(e['observation_pose'])
            worlds=np.array([local_to_world(x,a) for x in e['overnight_metric_samples']])
            xy,detail=freshest(worlds,b);out,meta=smooth(xy,b);before=np.asarray(meta['unsmoothed_suffix_xy'])
            np.testing.assert_array_equal(out[[0,-1]],before[[0,-1]])
            assert np.isfinite(out).all()
            k0,k1=curvature(before),curvature(out)
            samples.append(dict(key=r['key'],id=e['id'],sample=detail['selected_sample'],before_max_abs_kappa=k0,
                after_max_abs_kappa=k1,reduced=bool(k1<k0),endpoints_fixed=True))
    # Execute the actual CLI with fake runs.json, not only a formatting helper.
    from .test_phase13 import fake_runs
    with tempfile.TemporaryDirectory(prefix='phase13-report-') as td:
        td=Path(td);(td/'runs.json').write_text(json.dumps(fake_runs()))
        completed=subprocess.run([sys.executable,'-m','nomad_phase13.report','--runs-json',str(td/'runs.json'),
            '--out',str(td/'results'),'--doc',str(td/'report.md')],capture_output=True,text=True)
        assert completed.returncode==0,completed.stderr[-2000:]
        fake_label=json.loads(completed.stdout)['label'];assert fake_label=='SPEED_FROM_GRAPH'
    files=list(HERE.glob('*.py'))+[HERE/'protocol.json']
    files += [ROOT/'research'/name for name in ('nomad_isaac/launch.py','nomad_isaac/simulator.py','nomad_isaac/async_runtime.py','nomad_phase8/config.py','nomad_phase12/metrics.py')]
    write_json(target,dict(passed=True,navigation_count=0,inference_count=0,graph_solves=0,
        source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in files},
        input_sha256={str(f):sha256_file(f) for f in inputs},smoothing_cases=samples,
        smoothing_reduced=sum(s['reduced'] for s in samples),smoothing_count=len(samples),
        curvature_note='Diagnostic discrete Menger curvature on B+suffix vs fixed two-pass output; reductions are observations, not a tuned gate.',
        checkpoints=checks,checkpoint_validation_count=3,synthetic_report='PASS',synthetic_verdict=fake_label))
    present=sum(c['checkpoint_time_s'] is not None for c in checks)
    print(f"Offline: endpoints PASS; saved curvature reduced {sum(s['reduced'] for s in samples)}/{len(samples)}; checkpoints 3/3 verified ({present} present, {3-present} missing); report CLI PASS; navigation/inference/Graph solves 0")


if __name__=='__main__':main()
