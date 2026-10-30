# Phase20 SO pilot preparation

READY after the two explicitly requested post-hoc fixes. Offline:141/241 repairs, NEAR_START12/27, selected oracle penetration0, 1.5s overlap6/141, sample solve p9541.35ms. Original NOT_READY data remain in phase20_preflight; recheck data in phase20_preflight_02.

Tests11/11. One SO M2 smoke (D0, index901,30s), excluded from main. Spawn9.319s, depth9.486s, V1 map10.236s; one ALL_UNSAFE repair attempt timed out at0.5s and used fallback. Command/pose replay error0; clearance error1.12e−16m. No accepted repair occurred in this smoke; its requirement was a real repair attempt, not outcome success.

The SO renderer uses unchanged protected Phase9 build_scene/capture functions. Oracle publication is removed from the opt-in driver; controller inputs are RGB policy output, depth snapshots and actual SE(2) pose. Only map allocation xmax is extended8→12m for the longer SO corridor/sensor extent; V1, noise, resolution and SDF rules are unchanged.

The campaign is12 runs, SO only, M1/M2 at seeds74–79; it reuses the saved technical smoke and Topomap, then runs serial navigation and a CPU report with commit/push. Resuming never retries a started navigation. No main run has been launched.
