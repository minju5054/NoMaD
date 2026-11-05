# Phase26 preregistered pilot

Protocol SHA256 `36b4d61b0ff3162a2369559e11bc3141f8061f10b20c8da8b47eead515266157`. Small descriptive pilot; no p-value determines a label. H1 is explicitly a u_ref limitation test. Exact simulator odometry. B0 is reference-only.

## Decisions

| label | C0_BETTER_vs | C0_vs_ASTAR | STATIC_OK | satisfied | unsatisfied | excluded_scene_seed |
| --- | --- | --- | --- | --- | --- | --- |
| PILOT_SUPPORTS | {'B1_SAFE_TE': True, 'B2_SAFE_RTC': True, 'B3_SAFE_ROTATE': True} | BETTER | True | ['B1_SAFE_TE', 'B2_SAFE_RTC', 'B3_SAFE_ROTATE', 'ASTAR', 'STATIC_OK'] | [] | [] |

## Scene and pooled results

| group | method | n | goal | collision | box_collision | wall_collision | corridor_stop | passage | passage_time_median_s | goal_time_median_s | min_clearance_median_m | omega_saturation_median | stop_fraction_median | recovery_count | detour_triggers | detour_latency_median_s | compute_p95_median_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SLW | B0_NOMAD_RAW | 2 | 0 | 1 | 0 | 1 | 1 | 0 | — | — | 0.004037 | 0.46268 | 0.47311 | 0 | 0 | — | — |
| SLW | B1_SAFE_TE | 2 | 1 | 0 | 0 | 0 | 0 | 0 | — | 87.208 | 0.097659 | 0.54796 | 0.49433 | 2 | 0 | — | — |
| SLW | B2_SAFE_RTC | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0.075068 | 0.59259 | 0.57037 | 2 | 0 | — | — |
| SLW | B3_SAFE_ROTATE | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0.05109 | 0.4784 | 0.4963 | 5 | 0 | — | — |
| SLW | B4_ASTAR | 2 | 0 | 1 | 0 | 1 | 1 | 0 | — | — | 0.011851 | 0.41509 | 0.48881 | 1 | 14 | 0.33333 | 0.22527 |
| SLW | C0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0.04736 | 0.49444 | 0.53025 | 1 | 20 | 0.41667 | 0.52061 |
| LC | B0_NOMAD_RAW | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — | 55.056 | 0.11297 | 0.43322 | 0.38095 | 0 | 0 | — | — |
| LC | B1_SAFE_TE | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — | 51.347 | 0.2139 | 0.42399 | 0.36379 | 0 | 0 | — | — |
| LC | B2_SAFE_RTC | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — | 57.597 | 0.11206 | 0.44188 | 0.43132 | 0 | 0 | — | — |
| LC | B3_SAFE_ROTATE | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — | 48.042 | 0.11524 | 0.40093 | 0.33089 | 0 | 0 | — | — |
| LC | B4_ASTAR | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — | 51.201 | 0.094376 | 0.39079 | 0.36489 | 0 | 5 | 0.44444 | 0.53342 |
| LC | C0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | — | 44 | 0.069469 | 0.32901 | 0.37062 | 0 | 12 | 0.38889 | 0.54553 |
| L2 | B0_NOMAD_RAW | 2 | 1 | 1 | 1 | 0 | 0 | 1 | 30.319 | 84.708 | 0.046111 | 0.54132 | 0.46547 | 0 | 0 | — | — |
| L2 | B1_SAFE_TE | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 39.806 | — | 0.12573 | 0.37901 | 0.38457 | 2 | 0 | — | — |
| L2 | B2_SAFE_RTC | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 27.542 | — | 0.022774 | 0.49198 | 0.43519 | 2 | 0 | — | — |
| L2 | B3_SAFE_ROTATE | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0.15488 | 0.61975 | 0.55617 | 1 | 0 | — | — |
| L2 | B4_ASTAR | 2 | 1 | 0 | 0 | 0 | 0 | 2 | 25.292 | 69.042 | 0.061038 | 0.39317 | 0.40626 | 0 | 13 | 0.30556 | 0.3379 |
| L2 | C0 | 2 | 2 | 0 | 0 | 0 | 0 | 2 | 22.576 | 81.799 | 0.04495 | 0.42075 | 0.39891 | 0 | 5 | 0.44444 | 0.38875 |
| H1 | B0_NOMAD_RAW | 2 | 1 | 1 | 1 | 0 | 0 | 1 | 12.5 | 53.097 | 0.055836 | 0.48785 | 0.369 | 0 | 0 | — | — |
| H1 | B1_SAFE_TE | 2 | 1 | 0 | 0 | 0 | 0 | 1 | 12.611 | 52.069 | 0.093203 | 0.45879 | 0.35046 | 0 | 0 | — | — |
| H1 | B2_SAFE_RTC | 2 | 1 | 0 | 0 | 0 | 0 | 2 | 20.09 | 68.847 | 0.037589 | 0.5547 | 0.49873 | 0 | 0 | — | — |
| H1 | B3_SAFE_ROTATE | 2 | 1 | 0 | 0 | 0 | 0 | 2 | 14.799 | 54.611 | 0.081247 | 0.50104 | 0.44523 | 1 | 0 | — | — |
| H1 | B4_ASTAR | 2 | 2 | 0 | 0 | 0 | 0 | 2 | 13.424 | 49.556 | 0.084088 | 0.39447 | 0.3413 | 0 | 6 | 0.33333 | 0.27356 |
| H1 | C0 | 2 | 2 | 0 | 0 | 0 | 0 | 2 | 16.062 | 54.042 | 0.12201 | 0.40594 | 0.40954 | 0 | 8 | 0.41667 | 0.37961 |
| H2 | B0_NOMAD_RAW | 2 | 0 | 2 | 2 | 0 | 0 | 0 | — | — | -0.0012795 | 0.37037 | 0.31904 | 0 | 0 | — | — |
| H2 | B1_SAFE_TE | 2 | 1 | 0 | 0 | 0 | 0 | 1 | 42.431 | 73.472 | 0.04799 | 0.51496 | 0.47189 | 0 | 0 | — | — |
| H2 | B2_SAFE_RTC | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 61.472 | — | 0.10764 | 0.53148 | 0.47469 | 2 | 0 | — | — |
| H2 | B3_SAFE_ROTATE | 2 | 1 | 0 | 0 | 0 | 0 | 1 | 46.403 | 77.472 | 0.11101 | 0.44942 | 0.32033 | 0 | 0 | — | — |
| H2 | B4_ASTAR | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0.10644 | 0.43889 | 0.51543 | 0 | 26 | 0.38889 | 0.51442 |
| H2 | C0 | 2 | 1 | 0 | 0 | 0 | 0 | 2 | 54.917 | 78.819 | 0.10031 | 0.43844 | 0.44657 | 0 | 9 | 0.38889 | 0.45183 |
| SUDDEN | B0_NOMAD_RAW | 6 | 2 | 4 | 4 | 0 | 0 | 2 | 21.41 | 68.903 | -0.00068553 | 0.48658 | 0.369 | 0 | 0 | — | — |
| SUDDEN | B1_SAFE_TE | 6 | 2 | 0 | 0 | 0 | 0 | 4 | 34.896 | 62.771 | 0.085093 | 0.43101 | 0.35046 | 2 | 0 | — | — |
| SUDDEN | B2_SAFE_RTC | 6 | 1 | 0 | 0 | 0 | 0 | 4 | 24.278 | 68.847 | 0.038216 | 0.52754 | 0.46787 | 4 | 0 | — | — |
| SUDDEN | B3_SAFE_ROTATE | 6 | 2 | 0 | 0 | 0 | 0 | 3 | 15.597 | 66.042 | 0.081431 | 0.50247 | 0.42239 | 2 | 0 | — | — |
| SUDDEN | B4_ASTAR | 6 | 3 | 0 | 0 | 0 | 0 | 4 | 15.229 | 53.611 | 0.061038 | 0.40137 | 0.40789 | 0 | 45 | 0.33333 | 0.35192 |
| SUDDEN | C0 | 6 | 5 | 0 | 0 | 0 | 0 | 6 | 23.965 | 75.875 | 0.065405 | 0.42376 | 0.40954 | 0 | 22 | 0.44444 | 0.39739 |
| STATIC | B0_NOMAD_RAW | 4 | 2 | 1 | 0 | 1 | 1 | 0 | — | 55.056 | 0.059466 | 0.43322 | 0.40756 | 0 | 0 | — | — |
| STATIC | B1_SAFE_TE | 4 | 3 | 0 | 0 | 0 | 0 | 0 | — | 56 | 0.13769 | 0.49903 | 0.43943 | 2 | 0 | — | — |
| STATIC | B2_SAFE_RTC | 4 | 2 | 0 | 0 | 0 | 0 | 0 | — | 57.597 | 0.075068 | 0.4947 | 0.46887 | 2 | 0 | — | — |
| STATIC | B3_SAFE_ROTATE | 4 | 2 | 0 | 0 | 0 | 0 | 0 | — | 48.042 | 0.078874 | 0.43833 | 0.41188 | 5 | 0 | — | — |
| STATIC | B4_ASTAR | 4 | 2 | 1 | 0 | 1 | 1 | 0 | — | 51.201 | 0.015916 | 0.39079 | 0.38569 | 1 | 19 | 0.38889 | 0.36833 |
| STATIC | C0 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | — | 44 | 0.064913 | 0.38642 | 0.41235 | 1 | 32 | 0.41667 | 0.52061 |

## Paired seed outcomes

| scene | index | method | classification | success | collision | box_passage | box_passage_from_spawn_s | goal_time_s | technical_validation | attempt_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1 | 201 | B0_NOMAD_RAW | COLLISION | False | True | False | — | — | PASS | 1 |
| H1 | 201 | B1_SAFE_TE | SUCCESS | True | False | True | 12.611 | 52.069 | PASS | 1 |
| H1 | 201 | B2_SAFE_RTC | SUCCESS | True | False | True | 19.167 | 68.847 | PASS | 1 |
| H1 | 201 | B3_SAFE_ROTATE | STUCK | False | False | True | 14 | — | PASS | 1 |
| H1 | 201 | B4_ASTAR | SUCCESS | True | False | True | 12.514 | 45.5 | PASS | 1 |
| H1 | 201 | C0 | SUCCESS | True | False | True | 19.222 | 58.25 | PASS | 1 |
| H1 | 202 | B0_NOMAD_RAW | SUCCESS | True | False | True | 12.5 | 53.097 | PASS | 1 |
| H1 | 202 | B1_SAFE_TE | STUCK | False | False | False | — | — | PASS | 1 |
| H1 | 202 | B2_SAFE_RTC | STUCK | False | False | True | 21.014 | — | PASS | 1 |
| H1 | 202 | B3_SAFE_ROTATE | SUCCESS | True | False | True | 15.597 | 54.611 | PASS | 1 |
| H1 | 202 | B4_ASTAR | SUCCESS | True | False | True | 14.333 | 53.611 | PASS | 1 |
| H1 | 202 | C0 | SUCCESS | True | False | True | 12.903 | 49.833 | PASS | 1 |
| H2 | 201 | B0_NOMAD_RAW | COLLISION | False | True | False | — | — | PASS | 1 |
| H2 | 201 | B1_SAFE_TE | STUCK | False | False | False | — | — | PASS | 1 |
| H2 | 201 | B2_SAFE_RTC | STUCK | False | False | True | 61.472 | — | PASS | 1 |
| H2 | 201 | B3_SAFE_ROTATE | STUCK | False | False | False | — | — | PASS | 1 |
| H2 | 201 | B4_ASTAR | STUCK | False | False | False | — | — | PASS | 1 |
| H2 | 201 | C0 | STUCK | False | False | True | 69.889 | — | PASS | 1 |
| H2 | 202 | B0_NOMAD_RAW | COLLISION | False | True | False | — | — | PASS | 1 |
| H2 | 202 | B1_SAFE_TE | SUCCESS | True | False | True | 42.431 | 73.472 | PASS | 1 |
| H2 | 202 | B2_SAFE_RTC | STUCK | False | False | False | — | — | PASS | 1 |
| H2 | 202 | B3_SAFE_ROTATE | SUCCESS | True | False | True | 46.403 | 77.472 | PASS | 1 |
| H2 | 202 | B4_ASTAR | STUCK | False | False | False | — | — | PASS | 1 |
| H2 | 202 | C0 | SUCCESS | True | False | True | 39.944 | 78.819 | PASS | 1 |
| L2 | 201 | B0_NOMAD_RAW | SUCCESS | True | False | True | 30.319 | 84.708 | PASS | 1 |
| L2 | 201 | B1_SAFE_TE | STUCK | False | False | True | 52.25 | — | PASS | 1 |
| L2 | 201 | B2_SAFE_RTC | STUCK | False | False | False | — | — | PASS | 1 |
| L2 | 201 | B3_SAFE_ROTATE | STUCK | False | False | False | — | — | PASS | 1 |
| L2 | 201 | B4_ASTAR | STUCK | False | False | True | 34.458 | — | PASS | 1 |
| L2 | 201 | C0 | SUCCESS | True | False | True | 28.708 | 87.722 | PASS | 1 |
| L2 | 202 | B0_NOMAD_RAW | COLLISION | False | True | False | — | — | PASS | 1 |
| L2 | 202 | B1_SAFE_TE | STUCK | False | False | True | 27.361 | — | PASS | 1 |
| L2 | 202 | B2_SAFE_RTC | STUCK | False | False | True | 27.542 | — | PASS | 1 |
| L2 | 202 | B3_SAFE_ROTATE | STUCK | False | False | False | — | — | PASS | 1 |
| L2 | 202 | B4_ASTAR | SUCCESS | True | False | True | 16.125 | 69.042 | PASS | 1 |
| L2 | 202 | C0 | SUCCESS | True | False | True | 16.444 | 75.875 | PASS | 1 |
| LC | 201 | B0_NOMAD_RAW | SUCCESS | True | False | False | — | 61.861 | PASS | 1 |
| LC | 201 | B1_SAFE_TE | SUCCESS | True | False | False | — | 46.694 | PASS | 1 |
| LC | 201 | B2_SAFE_RTC | SUCCESS | True | False | False | — | 60.056 | PASS | 1 |
| LC | 201 | B3_SAFE_ROTATE | SUCCESS | True | False | False | — | 49.472 | PASS | 1 |
| LC | 201 | B4_ASTAR | SUCCESS | True | False | False | — | 50.361 | PASS | 1 |
| LC | 201 | C0 | SUCCESS | True | False | False | — | 44 | PASS | 1 |
| LC | 202 | B0_NOMAD_RAW | SUCCESS | True | False | False | — | 48.25 | PASS | 1 |
| LC | 202 | B1_SAFE_TE | SUCCESS | True | False | False | — | 56 | PASS | 1 |
| LC | 202 | B2_SAFE_RTC | SUCCESS | True | False | False | — | 55.139 | PASS | 1 |
| LC | 202 | B3_SAFE_ROTATE | SUCCESS | True | False | False | — | 46.611 | PASS | 1 |
| LC | 202 | B4_ASTAR | SUCCESS | True | False | False | — | 52.042 | PASS | 1 |
| LC | 202 | C0 | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 201 | B0_NOMAD_RAW | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 201 | B1_SAFE_TE | SUCCESS | True | False | False | — | 87.208 | PASS | 1 |
| SLW | 201 | B2_SAFE_RTC | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 201 | B3_SAFE_ROTATE | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 201 | B4_ASTAR | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 201 | C0 | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 202 | B0_NOMAD_RAW | CORRIDOR | False | True | False | — | — | PASS | 1 |
| SLW | 202 | B1_SAFE_TE | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 202 | B2_SAFE_RTC | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 202 | B3_SAFE_ROTATE | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 202 | B4_ASTAR | CORRIDOR | False | True | False | — | — | PASS | 1 |
| SLW | 202 | C0 | STUCK | False | False | False | — | — | PASS | 1 |

## Descriptive sign counts

| group | comparison | wins | losses | ties | exact_sign_p |
| --- | --- | --- | --- | --- | --- |
| SUDDEN | C0 vs B1_SAFE_TE | 3 | 0 | 3 | 0.25 |
| SUDDEN | C0 vs B2_SAFE_RTC | 4 | 0 | 2 | 0.125 |
| SUDDEN | C0 vs B3_SAFE_ROTATE | 3 | 0 | 3 | 0.25 |
| SUDDEN | C0 vs B4_ASTAR | 2 | 0 | 4 | 0.5 |
| STATIC | C0 vs B1_SAFE_TE | 0 | 2 | 2 | 0.5 |
| STATIC | C0 vs B2_SAFE_RTC | 0 | 1 | 3 | 1 |
| STATIC | C0 vs B3_SAFE_ROTATE | 0 | 1 | 3 | 1 |
| STATIC | C0 vs B4_ASTAR | 0 | 1 | 3 | 1 |
| SLW | C0 vs B1_SAFE_TE | 0 | 1 | 1 | 1 |
| SLW | C0 vs B2_SAFE_RTC | 0 | 0 | 2 | 1 |
| SLW | C0 vs B3_SAFE_ROTATE | 0 | 0 | 2 | 1 |
| SLW | C0 vs B4_ASTAR | 0 | 0 | 2 | 1 |
| LC | C0 vs B1_SAFE_TE | 0 | 1 | 1 | 1 |
| LC | C0 vs B2_SAFE_RTC | 0 | 1 | 1 | 1 |
| LC | C0 vs B3_SAFE_ROTATE | 0 | 1 | 1 | 1 |
| LC | C0 vs B4_ASTAR | 0 | 1 | 1 | 1 |
| L2 | C0 vs B1_SAFE_TE | 2 | 0 | 0 | 0.5 |
| L2 | C0 vs B2_SAFE_RTC | 2 | 0 | 0 | 0.5 |
| L2 | C0 vs B3_SAFE_ROTATE | 2 | 0 | 0 | 0.5 |
| L2 | C0 vs B4_ASTAR | 1 | 0 | 1 | 1 |
| H1 | C0 vs B1_SAFE_TE | 1 | 0 | 1 | 1 |
| H1 | C0 vs B2_SAFE_RTC | 1 | 0 | 1 | 1 |
| H1 | C0 vs B3_SAFE_ROTATE | 1 | 0 | 1 | 1 |
| H1 | C0 vs B4_ASTAR | 0 | 0 | 2 | 1 |
| H2 | C0 vs B1_SAFE_TE | 0 | 0 | 2 | 1 |
| H2 | C0 vs B2_SAFE_RTC | 1 | 0 | 1 | 1 |
| H2 | C0 vs B3_SAFE_ROTATE | 0 | 0 | 2 | 1 |
| H2 | C0 vs B4_ASTAR | 1 | 0 | 1 | 1 |

H2 scene passage requires both boxes; per-box spawn-to-passage times and collision/clearance are in runs.json. Missing passage time is not imputed. Raw attempts and original phase results are preserved. Primary technical failures after one identical-seed retry exclude the complete scene×seed primary group; B0 failure is independent.

Technical exclusions: []

## Draft expansion only — not authorized for execution

Freeze the same six methods and five scenes, add paired seeds203–208 (180new runs), preserve these pilot results separately and preregister confirmatory comparisons before launch. Define uncertainty/validity criteria and held-out interpretation before examining new outcomes; H1 remains a separate direction-limit analysis. No expansion command is generated or executed here.
