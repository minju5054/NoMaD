"""Phase4d N=8 tables and preregistered paired confirmation; no execution."""
import argparse
import copy
import json
import traceback
from pathlib import Path
import numpy as np
from scipy.stats import fisher_exact
from nomad_isaac.common import ROOT, sha256_file, write_json
from nomad_isaac.async_report import rows
from nomad_phase4.report import write_csv
from nomad_phase4c.report import summarize
from .config import ALPHAS, METHODS, protocol, reference_records
from .batch import matrix, audit, completion


def load(root):
    status, done = completion(root)
    assert done, f'All 20 attempts must finish before report generation: {status}'
    plan = json.loads((root / 'plan.json').read_text())
    jobs, refs = matrix(root)
    assert plan['jobs'] == jobs and plan['references'] == refs and plan['protocol'] == protocol()
    for name, digest in plan['fixed_input_sha256'].items():
        assert sha256_file(Path(name)) == digest, 'Frozen input changed: ' + name
    journal = rows(root / 'execution.jsonl')
    assert all(r['git_sha'] == plan['git_sha'] for r in journal)
    starts = [r for r in journal if r['event'] == 'START']
    ends = [r for r in journal if r['event'] == 'END']
    assert all(ends[i-1]['monotonic_ns'] < starts[i]['monotonic_ns'] for i in range(1, len(starts)))
    prior = {r['key']: r for r in reference_records()}
    records = []
    for j in refs + jobs:
        try:
            if j['reused']:
                r = copy.deepcopy(prior[j['key']])
                r['source_reused_in_phase4c'] = r['reused']
                if r['alpha'] == 'inf' and r.get('plant_intervals') == 0:
                    # Legacy identity plant: count its zero-error intervals in pooled RMS.
                    r['plant_intervals'] = round(r['duration_s'] * 72)
                # Original source hash verification above includes each stored log digest.
            else:
                old = json.loads((root / 'metrics' / f"{j['key']}.json").read_text())
                if old.get('launcher_exit_code') != 0:
                    raise RuntimeError(old.get('error', 'Launcher failed'))
                r = audit(Path(j['output']), j['run_id'], j['seed_offset'], .75)
                assert r['execution_git_sha'] == plan['git_sha']
                for name, digest in old.get('input_log_sha256', {}).items():
                    assert sha256_file(Path(j['output']) / name) == digest
        except Exception as e:
            r = dict(technical_validation='FAIL', classification='TECHNICAL_FAILURE', success=False,
                     error=repr(e), traceback=traceback.format_exc())
        r.update({k: v for k, v in j.items() if k not in ('argv', 'shell_command')})
        records.append(r)
    return records, plan


def paired_table(records):
    lookup = {(r['alpha'], r['index'], r['method']): r for r in records}
    assert len(lookup) == len(records) == 32, 'Expected exactly 32 distinct records'
    paired = []
    for alpha in ALPHAS:
        for i in range(1, 9):
            a, b = (lookup[alpha, i, m] for m in METHODS)
            jointly_successful = all(r.get('technical_validation') == 'PASS' and r.get('success') for r in (a, b))
            times = [r.get('goal_time_s') if r.get('technical_validation') == 'PASS' and r.get('success') else None for r in (a, b)]
            paired.append(dict(alpha=alpha, index=i, seed_offset=10000*i, reused=i <= 3,
                CURV=a['classification'], GRAPH=b['classification'], CURV_goal_s=times[0], GRAPH_goal_s=times[1],
                jointly_successful=jointly_successful,
                delta_graph_minus_curv_s=float(times[1]-times[0]) if jointly_successful else None))
    return paired


def bootstrap(pairs):
    """Resample seed-index clusters, preserving pair and cross-alpha dependence."""
    settings = protocol()['statistics']
    eligible = [r for r in pairs if r['jointly_successful']]
    ids = sorted({r['index'] for r in eligible})
    result = dict(paired_success_n=len(eligible), seed_clusters_n=len(ids), median_delta_s=None,
                  bootstrap_ci95_s=None, bootstrap_seed=settings['bootstrap_seed'],
                  bootstrap_replicates=settings['bootstrap_replicates'])
    if not ids:
        return result
    clusters = [np.array([r['delta_graph_minus_curv_s'] for r in eligible if r['index'] == i]) for i in ids]
    rng = np.random.default_rng(settings['bootstrap_seed'])
    samples = rng.integers(0, len(ids), size=(settings['bootstrap_replicates'], len(ids)))
    medians = np.array([np.median(np.concatenate([clusters[i] for i in draw])) for draw in samples])
    result.update(median_delta_s=float(np.median(np.concatenate(clusters))),
                  bootstrap_ci95_s=np.quantile(medians, [.025, .975], method='linear').tolist())
    return result


def assess(records, pairs, alpha):
    selected = [r for r in records if alpha == 'pooled' or r['alpha'] == alpha]
    valid = [r for r in selected if r.get('technical_validation') == 'PASS']
    success = {m: sum(bool(r.get('success')) for r in valid if r['method'] == m) for m in METHODS}
    denominators = {m: sum(r['method'] == m for r in valid) for m in METHODS}
    timing = bootstrap([r for r in pairs if alpha == 'pooled' or r['alpha'] == alpha])
    reliability = success['GRAPH'] >= success['CURV']
    speed = (timing['median_delta_s'] is not None and timing['median_delta_s'] < 0
             and timing['bootstrap_ci95_s'][1] < 0)
    table = [[success[m], denominators[m]-success[m]] for m in METHODS]
    p = float(fisher_exact(table, alternative='two-sided').pvalue) if all(denominators.values()) else None
    return dict(alpha=alpha, success_counts=success, valid_counts=denominators,
        technical_failure_count=len(selected)-len(valid), complete_technical_evidence=len(valid)==len(selected),
        reliability_claim=reliability, speed_claim=speed,
        verdict='CONFIRMED' if reliability and speed else 'PARTIAL' if reliability or speed else 'NOT_CONFIRMED',
        fisher_exact_two_sided_p=p, fisher_table_curv_graph=table, **timing)


def generate(root, out, doc):
    assert not out.exists() and not doc.exists(), 'Existing report preserved; choose another output/document explicitly'
    records, plan = load(root)
    pairs = paired_table(records)
    groups = [summarize(records, a, m) for a in ALPHAS for m in METHODS]
    pooled = [{**r, 'alpha': 'pooled'} for r in records]
    groups += [summarize(pooled, 'pooled', m) for m in METHODS]
    decisions = [assess(records, pairs, a) for a in (*ALPHAS, 'pooled')]
    compact = [{k: v for k, v in r.items() if k not in ('handoffs', 'request_seeds', 'input_log_sha256')}
               for r in records]
    result = dict(execution_git_sha=plan['git_sha'], protocol=protocol(), conditions=groups,
                  decisions=decisions, overall_verdict=decisions[-1]['verdict'])
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / 'summary.json', result); write_json(out / 'runs.json', compact)
    write_csv(out / 'conditions.csv', groups); write_csv(out / 'paired_goal_times.csv', pairs)
    write_csv(out / 'decisions.csv', decisions)
    f = lambda x: 'N/A' if x is None else f'{x:.4f}'
    text = ['# Phase 4d CURV vs GRAPH Confirmation', '', f"Execution commit: `{plan['git_sha']}`.",
        'Oracle geometry; SE(2) kinematic Isaac Sim. D750, v_max=0.3m/s. N=8 per alpha/method: prior indices1–3 plus new indices4–8.', '',
        '|α|Method|Success/N|Collision|Corridor|Timeout|Technical|Goal median s|Mean speed m/s|Min clearance m|ω error RMS/max rad/s|Graph accepted/calls (rate)|',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for g in groups:
        text.append(f"|{g['alpha']}|{g['method']}|{g['success']}/{g['attempts']}|{g['collision']}|{g['corridor']}|{g['timeout']}|{g['technical_failure']}|{f(g['goal_time_median_s'])}|{f(g['mean_speed_m_s'])}|{f(g['minimum_clearance_m'])}|{f(g['tracking_rms_rad_s'])}/{f(g['tracking_max_rad_s'])}|{g['graph_accepted']}/{g['graph_calls']} ({f(g['graph_acceptance_fraction'])})|")
    text += ['', 'Goal medians above use each method’s successful runs. Paired speed claims below use only jointly successful pairs; failed goal times are not replaced by the timeout.', '',
        '|α|Index|Source|CURV|GRAPH|CURV goal s|GRAPH goal s|GRAPH−CURV s|',
        '|---|---:|---|---|---|---:|---:|---:|']
    for r in pairs:
        text.append(f"|{r['alpha']}|{r['index']}|{'Phase4c reuse' if r['reused'] else 'Phase4d new'}|{r['CURV']}|{r['GRAPH']}|{f(r['CURV_goal_s'])}|{f(r['GRAPH_goal_s'])}|{f(r['delta_graph_minus_curv_s'])}|")
    text += ['', '|α|Reliability claim|Speed claim|Successful pairs / seed clusters|Median Δt s|Paired bootstrap 95% CI s|Fisher exact p|Verdict|',
        '|---|---|---|---|---:|---|---:|---|']
    for d in decisions:
        ci = 'N/A' if d['bootstrap_ci95_s'] is None else '['+', '.join(f(x) for x in d['bootstrap_ci95_s'])+']'
        text.append(f"|{d['alpha']}|{d['reliability_claim']}|{d['speed_claim']}|{d['paired_success_n']}/{d['seed_clusters_n']}|{f(d['median_delta_s'])}|{ci}|{f(d['fisher_exact_two_sided_p'])}|{d['verdict']}|")
    text += ['', f"Overall preregistered verdict: **{result['overall_verdict']}**.", '',
        'Bootstrap: 20,000 replicates, seed20261024, percentile95% CI. Each alpha resamples paired indices. Pooled bootstrap resamples seed-index clusters and keeps the two alpha results together when both are eligible; pooled N=16 pairs is at most8 independent seed clusters.',
        'Fisher exact is two-sided on success/non-success among technically valid runs, descriptive only; it does not model paired/cross-alpha seed dependence. The declared verdict uses success counts and the paired bootstrap, not Fisher p.',
        'Technical failures are shown separately, are not collision/timeout outcomes, and have no imputed goal time. Reliability is the requested observed success-count comparison; incomplete technical evidence is flagged in summary.json.',
        'Minimum clearance is the smallest swept lower bound; omega RMS is weighted over72Hz intervals. Reused infinity CURV has identity-plant error0. The original2cm margin statistic remains independent of goal/no-overlap/corridor success.',
        'These data reuse the earlier3 runs that motivated this extension. Shared seed offsets do not guarantee identical RGB or predictions; a small-sample confirmatory criterion does not establish general navigation superiority.']
    failures = [r for r in records if r.get('technical_validation') != 'PASS']
    if failures:
        text += ['', '|Technical failure|Recorded error|', '|---|---|']
        for r in failures:
            text.append(f"|{r['key']}|{r.get('error', 'Unknown')}|")
    doc.parent.mkdir(parents=True, exist_ok=True); doc.write_text('\n'.join(text)+'\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-root', type=Path, required=True)
    p.add_argument('--output', type=Path, default=ROOT / 'research/results/phase4d')
    p.add_argument('--document', type=Path, default=ROOT / 'docs/PHASE4D_CONFIRM.md')
    a = p.parse_args()
    print(generate(a.run_root.resolve(), a.output, a.document)['overall_verdict'])


if __name__ == '__main__':
    main()
