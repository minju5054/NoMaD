# Phase20-B preparation

Frozen L2/L3 pilot:12 new runs, indices80–82, seed→level→shuffled method (20261101). Phase20 L1 results are reused, including box passage6/6 for both methods and goal success5/6 vs6/6.

Parallel repair: four persistent CPU processes in a clean /usr/bin/python3 broker; unchanged protected R2 and Phase20 executor;1.0s deadline. Pool warmup performs no solve and occurs before the navigation clock. Serial/parallel dispositions and available paths agree within1e−6m; a real pool result drives the inherited executor/plant in a CPU unit test. Six tests pass.

L2 and L3 each had one excluded M1 D0 technical run. Sizes0.4×1.2 and0.4×2.0m, gaps0.9/0.9 and0.8/0.2m, physical rendering, depth and V1 map observation were verified. Center y is corridor-fixed as documented before execution.

**Smoke limitation:** the single excluded L3 M2 D750 seed901 run completed40s with ALL_UNSAFE=0 and repair attempts=0. Therefore there are no in-navigation eight-sample solve timings. This evidence was not replaced with unit-test timings. No extra run, seed change, geometry change or threshold tuning was performed. This negative trigger observation does not block the requested12-run pilot; the campaign warns about the missing timing evidence before starting. It is not a positive validation of the repair branch under live rendering.

Command/pose replay errors are0 for all three excluded runs. Smoke figures, a4.1s GIF and six RGB captures were generated and inspected; the missing same-seed M1 panel is explicitly blank rather than populated with the different technical-check seed.

No main navigation has started. Resumable campaign, lock, socket precheck, automatic report/figures/commit/push are prepared. Expected wall time about40–55min including figures.
