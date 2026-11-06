# Phase28-T single smoke

Excluded H1/C0-H/seed201 run only; no campaign results.

Gate application ratio = actually applied OPTIMIZED/INIT_ONLY cases / (all H cases minus discarded DETOUR_STARTED cases). Only DETOUR_STARTED is excluded; SUPERSEDED, WORKER_BUSY and other reasons remain. The excluded count and per-case audit are in summary.json and gate_cases.csv.

| cases | detour_started_excluded | gate_eligible_cases | case_reasons | jobs | actually_applied | numerically_accepted | feedback_commands | feedback_clipped | feedback_clip_fraction | technical_validation | technical_error | original_evaluator | compute_p50_s | compute_p95_s | compute_max_s | gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 1 | {'OPTIMIZED': 1} | 1 | 1 | 1 | 1 | 0 | 0 | FAIL | — | — | 0.073871 | 0.073871 | 0.073871 | {'label': 'GATE_FAIL', 'denominator': 'ALL_H_CASES_EXCEPT_DETOUR_STARTED', 'total_h_cases': 1, 'detour_started_excluded': 0, 'denominator_n': 1, 'applied': 1, 'application_fraction': 1.0, 'compute_p95_s': 0.07387113900040276, 'compute_samples': 1, 'applied_among_all': 1.0, 'applied_among_numerically_accepted': 1.0, 'technical_failure': True} |

| scope | type | count |
|---|---|---|
| effective_case | OPTIMIZED | 1 |
| ready_future | OPTIMIZED | 1 |
| worker_before_transport_deadline | OPTIMIZED | 1 |

| stage | n | p50_s | p95_s | max_s | cpu_p50_s | cpu_p95_s |
|---|---|---|---|---|---|---|
| total | 1 | 0.073871 | 0.073871 | 0.073871 | — | — |
| worker_inclusive | 1 | 0.072729 | 0.072729 | 0.072729 | — | — |
| B_prediction | 1 | 0.00014472 | 0.00014472 | 0.00014472 | — | — |
| transport_thread_queue | 1 | 0.00019293 | 0.00019293 | 0.00019293 | — | — |
| SDF_copy | 1 | 0.0039317 | 0.0039317 | 0.0039317 | — | — |
| send_to_worker_receive | 1 | 0.00018146 | 0.00018146 | 0.00018146 | — | — |
| field_attach | 1 | 0.00039326 | 0.00039326 | 0.00039326 | — | — |
| submit_to_solver_enter | 1 | 0.0047105 | 0.0047105 | 0.0047105 | — | — |
| worker_result_to_parent_receive | 1 | 0.0002164 | 0.0002164 | 0.0002164 | — | — |
| parent_decode | 1 | 0.00015255 | 0.00015255 | 0.00015255 | — | — |
| graph_construct | 1 | 0.00076752 | 0.00076752 | 0.00076752 | 0.00076656 | 0.00076656 |
| na_initial_72hz | 1 | 0.0070583 | 0.0070583 | 0.0070583 | 0.0040591 | 0.0040591 |
| initialization_total | 1 | 0.00723 | 0.00723 | 0.00723 | 0.00423 | 0.00423 |
| slsqp | 1 | 0.056981 | 0.056981 | 0.056981 | 0.041668 | 0.041668 |
| optimized_certificate | 1 | 0.00098011 | 0.00098011 | 0.00098011 | 0.00098022 | 0.00098022 |
| application_certificate | 1 | 0.0011618 | 0.0011618 | 0.0011618 | — | — |

| job_id | case_id | case_type | reason | numerical_type | worker_type | applied | compute_s | major_iterations_completed | iterations_at_timeout | returned_nit | timeout_stage | iteration_interval_p50_s | iteration_interval_p95_s | mean_solver_s_per_completed_major | worker_cpu | total | worker_inclusive | B_prediction | transport_thread_queue | SDF_copy | send_to_worker_receive | field_attach | submit_to_solver_enter | worker_result_to_parent_receive | parent_decode | graph_construct | na_initial_72hz | initialization_total | slsqp | optimized_certificate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | OPTIMIZED | OPTIMIZED | OPTIMIZED | OPTIMIZED | True | 0.073871 | 54 | — | 54 | — | 0.00061185 | 0.0045325 | 0.0010552 | [7] | 0.073871 | 0.072729 | 0.00014472 | 0.00019293 | 0.0039317 | 0.00018146 | 0.00039326 | 0.0047105 | 0.0002164 | 0.00015255 | 0.00076752 | 0.0070583 | 0.00723 | 0.056981 | 0.00098011 |

Iteration timestamps are completed major callbacks; internal SLSQP line searches/minor iterations are not exposed. Initialization total includes NA integration; submit-to-solver includes transport/copy/attach, so nested stages must not be summed. Application certificate is reported separately from compute budget. All dispatched completed-job times, including DETOUR_STARTED, timeout and other discarded jobs, enter compute p95; WORKER_BUSY has no dispatched job.

Affinity: {"launch": {"plan": {"possible": true, "allowed": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], "driver_cpus": [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14], "worker_cpu": 7, "reserved_siblings": [7, 15], "physical_core": [0, 7]}, "launcher": {"passed": true, "requested": [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14], "before": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], "actual": [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14], "pid": 810114}}, "worker": {"pid": 812937, "python": "/home/gpuadmin/isaacsim/kit/python/bin/python3", "numpy": "2.3.1", "scipy": "1.17.0", "numpy_file": "/home/gpuadmin/isaacsim/extscache/omni.kit.pip_archive-0.0.0+f9bf0dda.lx64.cp312/pip_prebundle/numpy/__init__.py", "scipy_file": "/home/gpuadmin/isaacsim/exts/omni.pip.compute/pip_prebundle/scipy/__init__.py", "affinity": {"passed": true, "requested": [7], "before": [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14], "actual": [7], "pid": 812937}, "ready_ns": 49708087167612}}
