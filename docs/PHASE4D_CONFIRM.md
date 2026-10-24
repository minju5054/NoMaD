# Phase 4d CURV vs GRAPH Confirmation

Execution commit: `1917ee6ebc3dbfc224bd9e47415a88d1eedd97d8`.
Oracle geometry; SE(2) kinematic Isaac Sim. D750, v_max=0.3m/s. N=8 per alpha/method: prior indices1–3 plus new indices4–8.

|α|Method|Success/N|Collision|Corridor|Timeout|Technical|Goal median s|Mean speed m/s|Min clearance m|ω error RMS/max rad/s|Graph accepted/calls (rate)|
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
|inf|CURV|4/8|0|3|1|0|29.8194|0.1350|0.0250|0.0000/0.0000|0/0 (N/A)|
|inf|GRAPH|7/8|1|0|0|0|29.9583|0.1564|-0.0005|0.0000/0.0000|183/255 (0.7176)|
|2.0|CURV|2/8|2|2|2|0|36.1458|0.1329|-0.0008|0.1797/0.7722|0/0 (N/A)|
|2.0|GRAPH|7/8|0|1|0|0|30.3056|0.1460|0.0056|0.1632/0.7722|190/243 (0.7819)|
|pooled|CURV|6/16|2|5|3|0|30.7500|0.1340|-0.0008|0.1321/0.7722|0/0 (N/A)|
|pooled|GRAPH|14/16|1|1|0|0|30.1319|0.1512|-0.0005|0.1144/0.7722|373/498 (0.7490)|

Goal medians above use each method’s successful runs. Paired speed claims below use only jointly successful pairs; failed goal times are not replaced by the timeout.

|α|Index|Source|CURV|GRAPH|CURV goal s|GRAPH goal s|GRAPH−CURV s|
|---|---:|---|---|---|---:|---:|---:|
|inf|1|Phase4c reuse|SUCCESS|SUCCESS|30.1944|28.0694|-2.1250|
|inf|2|Phase4c reuse|SUCCESS|SUCCESS|34.7083|29.9583|-4.7500|
|inf|3|Phase4c reuse|SUCCESS|SUCCESS|29.0972|28.5139|-0.5833|
|inf|4|Phase4d new|SAFETY_FAILURE|SAFETY_FAILURE|N/A|N/A|N/A|
|inf|5|Phase4d new|SAFETY_FAILURE|SUCCESS|N/A|29.4306|N/A|
|inf|6|Phase4d new|SAFETY_FAILURE|SUCCESS|N/A|33.0972|N/A|
|inf|7|Phase4d new|STUCK|SUCCESS|N/A|62.5417|N/A|
|inf|8|Phase4d new|SUCCESS|SUCCESS|29.4444|30.6528|1.2083|
|2.0|1|Phase4c reuse|SUCCESS|SUCCESS|31.3056|29.7361|-1.5694|
|2.0|2|Phase4c reuse|SAFETY_FAILURE|SUCCESS|N/A|30.3056|N/A|
|2.0|3|Phase4c reuse|STUCK|SUCCESS|N/A|31.0278|N/A|
|2.0|4|Phase4d new|SAFETY_FAILURE|SUCCESS|N/A|39.6667|N/A|
|2.0|5|Phase4d new|STUCK|SUCCESS|N/A|29.9583|N/A|
|2.0|6|Phase4d new|SAFETY_FAILURE|SUCCESS|N/A|38.7361|N/A|
|2.0|7|Phase4d new|SAFETY_FAILURE|SAFETY_FAILURE|N/A|N/A|N/A|
|2.0|8|Phase4d new|SUCCESS|SUCCESS|40.9861|29.7361|-11.2500|

|α|Reliability claim|Speed claim|Successful pairs / seed clusters|Median Δt s|Paired bootstrap 95% CI s|Fisher exact p|Verdict|
|---|---|---|---|---:|---|---:|---|
|inf|True|False|4/4|-1.3542|[-4.7500, 1.2083]|0.2821|PARTIAL|
|2.0|True|True|2/2|-6.4097|[-11.2500, -1.5694]|0.0406|CONFIRMED|
|pooled|True|True|6/4|-1.8472|[-4.7500, -0.5833]|0.0091|CONFIRMED|

Overall preregistered verdict: **CONFIRMED**.

Bootstrap: 20,000 replicates, seed20261024, percentile95% CI. Each alpha resamples paired indices. Pooled bootstrap resamples seed-index clusters and keeps the two alpha results together when both are eligible; pooled N=16 pairs is at most8 independent seed clusters.
Fisher exact is two-sided on success/non-success among technically valid runs, descriptive only; it does not model paired/cross-alpha seed dependence. The declared verdict uses success counts and the paired bootstrap, not Fisher p.
Technical failures are shown separately, are not collision/timeout outcomes, and have no imputed goal time. Reliability is the requested observed success-count comparison; incomplete technical evidence is flagged in summary.json.
Minimum clearance is the smallest swept lower bound; omega RMS is weighted over72Hz intervals. Reused infinity CURV has identity-plant error0. The original2cm margin statistic remains independent of goal/no-overlap/corridor success.
These data reuse the earlier3 runs that motivated this extension. Shared seed offsets do not guarantee identical RGB or predictions; a small-sample confirmatory criterion does not establish general navigation superiority.
