# Phase 4 Graph v5 pilot
Execution SHA: `6802a75a37fffd5d426349ca9f1b1f3b378e2314`. `STOP_AND_REPORT`.
Oracle static geometry; SE2 kinematic Isaac Sim; N4/N2 pilot; paired offsets not identical closed-loop RGB. RAW/CURV execution cap 0.3m/s; NoMaD metric scaling unchanged.
Technical validation: 14/14 PASS. Original RGB histories, Topomap, seeds, delay clocks, actual commands, 72Hz poses and swept clearance re-audited.
Success = goal entry without overlap/corridor breach. 2cm margin violations are independent. Missing successful goal times are never replaced by timeout.
|D ms|Method|Success/attempts|Collision|Corridor|Timeout|Technical|Goal median s|Mean speed m/s|Switch abs dw median|Graph calls/accepted|
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|750|RAW|0/4|2|2|0|0|N/A|0.2548|0.2558|0/0|
|750|CURV-SPEED|3/4|0|1|0|0|30.1944|0.1445|0.4481|0/0|
|750|GRAPH-v5|1/4|1|2|0|0|30.4167|0.1516|0.3438|201/91|
|0|GRAPH-v5|2/2|0|0|0|0|19.9653|0.2332|0.1752|152/14|

## Preregistered decision
{
  "verdict": "STOP_AND_REPORT",
  "checks": {
    "all_14_technical_PASS": true,
    "D750_graph_success_ge_curv": false,
    "D750_graph_goal_median_le_90pct_curv": false,
    "D0_graph_2_of_2_success": true
  },
  "D750_graph_goal_median_s": 30.416666666666668,
  "D750_curv_goal_median_s": 30.194444444444443,
  "scope": "Pilot only; undefined successful goal median fails. No automatic extension."
}

## Run outcomes
|Run|Result|Goal s|Mean speed m/s|Margin violation s|
|---|---|---:|---:|---:|
|S0_01_D750_RAW|SAFETY_FAILURE|N/A|0.2654|0.0000|
|S0_01_D750_CURV-SPEED|SUCCESS|30.1944|0.1555|0.0000|
|S0_01_D750_GRAPH-v5|SAFETY_FAILURE|N/A|0.1374|0.0000|
|S0_02_D750_RAW|SAFETY_FAILURE|N/A|0.2471|0.0000|
|S0_02_D750_CURV-SPEED|SUCCESS|34.7083|0.1424|0.0000|
|S0_02_D750_GRAPH-v5|SUCCESS|30.4167|0.1671|0.0000|
|S0_03_D750_RAW|SAFETY_FAILURE|N/A|0.2533|0.0694|
|S0_03_D750_CURV-SPEED|SUCCESS|29.0972|0.1692|0.0000|
|S0_03_D750_GRAPH-v5|SAFETY_FAILURE|N/A|0.1510|0.0000|
|S0_04_D750_RAW|SAFETY_FAILURE|N/A|0.2533|0.0833|
|S0_04_D750_CURV-SPEED|SAFETY_FAILURE|N/A|0.1111|0.0000|
|S0_04_D750_GRAPH-v5|SAFETY_FAILURE|N/A|0.1509|0.1111|
|S0_01_D000_GRAPH-v5|SUCCESS|21.1944|0.2194|0.3194|
|S0_02_D000_GRAPH-v5|SUCCESS|18.7361|0.2470|0.0000|

## Graph processing and limitations
D750: dispositions `{'NONCONVERGED': 67, 'ACCEPTED': 91, 'APP_MISMATCH': 36, 'STALE': 6, 'INITIALIZATION_REJECTED': 1}`; solve median/p95/max `{'n': 200, 'median': 0.11707496698363684, 'p95': 0.2612609288014936, 'min': 0.0029077139915898442, 'max': 0.38451149995671585}` s; processing `{'n': 201, 'median': 0.117821901, 'p95': 0.262201257, 'min': 0.00080871, 'max': 0.401073211}` s; corrected valid ticks fraction 0.3625; correction abs dw `{'n': 91, 'median': 0.060663895781891075, 'p95': 0.3642113064099519, 'min': 0.0, 'max': 0.8}`; movement while waiting `{'n': 201, 'median': 0.02407234057950463, 'p95': 0.0506798600432419, 'min': 0.005555548411068242, 'max': 0.07011110010305366}` m; temporal acceleration exceedance ticks 52.
D0: dispositions `{'SUPERSEDED': 75, 'ACCEPTED': 14, 'APP_MISMATCH': 43, 'NONCONVERGED': 18}`; solve median/p95/max `{'n': 150, 'median': 0.12069796997820958, 'p95': 0.26670941695629147, 'min': 0.07246644794940948, 'max': 0.33986250299494714}` s; processing `{'n': 150, 'median': 0.1219977115, 'p95': 0.27385059174999976, 'min': 0.073656063, 'max': 0.341341131}` s; corrected valid ticks fraction 0.0441; correction abs dw `{'n': 14, 'median': 0.06349319064556383, 'p95': 0.10821155500553638, 'min': 0.0, 'max': 0.1103807207029881}`; movement while waiting `{'n': 150, 'median': 0.042072533437101045, 'p95': 0.09722211917083709, 'min': 0.014814795762848226, 'max': 0.122662766001495}` m; temporal acceleration exceedance ticks 0.
The unchanged v4 full-path certificate does not certify a PP arc. Spatial node-speed acceleration constraints do not guarantee temporal acceleration at path replacement. Exact profile interpolation is logged separately from clipping. B_app predicts two control ticks, while application uses the first eligible tick: fast results can be APP_MISMATCH. STALE is worker processing >0.3s; queue time is separate.
N=4/N=2 exploratory pilot; paired offsets do not imply identical RGB or predictions. Goal-time comparisons condition on success. No automatic follow-up, tuning or retries.

![D750 actual trajectories](../research/results/phase4_pilot/d750_paths.png)

## Technical failures
None.
