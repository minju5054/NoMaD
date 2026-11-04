# Phase24 disk recovery (operational amendment)

The frozen method/weights/seeds/decision protocol remains byte-identical to836127a. Only campaign persistence, storage guards and archival I/O changed. No navigation was executed during recovery.

## Integrity and preserved attempts

state.json and plan.json were valid. state.tmp was zero bytes and has been preserved under recovery/disk_full_20261104/. Four completed runs were re-audited; stored classifications, seed, distance, goal/collision fields and command/pose checks match. Their metric, summary, launch-complete and provenance hashes are recorded in research/results/phase24_online/disk_recovery.json and were unchanged.

Preserved runs: L2_131_C0, L2_131_C1, L2_131_G, SLW_131_C0. No completed run was rerun or rewritten.

SLW_131_C1 failed with OSError28 in the depth archive writer (FAILED.json contains the original traceback). Its worker EOF was a consequence. The original run, metric and launcher log are at attempts/SLW_131_C1/disk_full_attempt_01/. It remains recorded as DISK_FULL TECHNICAL_FAILURE and is authorized for one same-seed retry.

SLW_131_G has no requests.jsonl or agent_trajectory.csv; its zero-byte launch_failure.json and partial startup files are preserved at attempts/SLW_131_G/disk_full_attempt_01/. It is pending again, with the original seed. No outcome-based retry or general retry policy was introduced.

state.json is now READY_TO_RESUME:4completed,20pending. The original plan order and run-root remain unchanged.

## Capacity (decimal GB)

| Measure | GB |
|---|---:|
| Mean completed run, original storage | 3.05 |
| Projected compact run (incl map allowance) | 2.11 |
|20remaining runs, original storage | 60.98 |
|20remaining runs, new policy (2full+18compact) | 44.02 |
| Required including20GBheadroom | 64.02 |
| Available at recovery | 171.25 |

Storage is sufficient. Estimates are from four completed runs and are updated before every new run; they are not a guarantee of later run size. If free space falls below remaining expected storage+20GB, the campaign stops BEFORE starting the next run and records LOW_DISK_STOP.

## Storage and persistence

Seed131is the fixed full-frame visualization seed in each scene, for all three methods. Other seeds keep all sensor capture, RGB model inputs and4Hz live depth map updates. Only disk archives change: raw RGB/depth frames are omitted;1Hz visualization maps, native FRESH snapshots, initial/final maps, all graph/A*job snapshots, trajectories, metrics and numerical inference records remain. All prior raw is preserved. Archives.jsonl identifies omitted/retained maps; per-run storage_policy.json identifies the policy. Archival load is reduced; measured timing is not compensated.

JSON state/metrics use a unique temporary file, fsync and atomic replacement. state.json.bak retains the last valid state. A preallocated1MiBmetadata reserve is released on ENOSPC to write DISK_FULL_STOP; a failed write never truncates the last complete state. Corrupt/missing state can be rebuilt from backup/plan and committed run result files. Incomplete attempts are never silently retried.

Seven offline tests passed: ENOSPC atomicity/reserve, corrupt-state recovery, remaining+headroom guard, RGB write suppression with identical consumer input, snapshot retention, protected write-site assertions, and unchanged depth publisher/submit functions. No Isaac, NoMaD inference or Graph solve was run for this amendment.
