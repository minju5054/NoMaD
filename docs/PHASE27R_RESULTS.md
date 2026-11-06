# Phase27-R — Phase26 suffix-alignment bug-fix rerun

Unchanged Phase26 protocol SHA256 `36b4d61b0ff3162a2369559e11bc3141f8061f10b20c8da8b47eead515266157`. Small descriptive pilot; no p-value determines a label. H1 is explicitly a u_ref limitation test. Exact simulator odometry. B0 is reference-only.

## Decisions

| label | C0_BETTER_vs | C0_vs_ASTAR | STATIC_OK | satisfied | unsatisfied | excluded_scene_seed |
| --- | --- | --- | --- | --- | --- | --- |
| PILOT_AGAINST | {'B1_SAFE_TE': False, 'B2_SAFE_RTC': True, 'B3_SAFE_ROTATE': False} | WORSE | True | ['B2_SAFE_RTC', 'STATIC_OK'] | ['B1_SAFE_TE', 'B3_SAFE_ROTATE', 'ASTAR'] | [] |

## Scene and pooled results

| group | method | n | goal | collision | box_collision | wall_collision | corridor_stop | passage | passage_time_median_s | goal_time_median_s | min_clearance_median_m | omega_saturation_median | stop_fraction_median | recovery_count | detour_triggers | detour_latency_median_s | compute_p95_median_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SLW | B0_NOMAD_RAW | 2 | 0 | 1 | 0 | 1 | 1 | 0 | — | — | 0.060487 | 0.73547 | 0.56979 | 0 | 0 | — | — |
| SLW | B1_SAFE_TE | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0.032931 | 0.62222 | 0.62037 | 4 | 0 | — | — |
| SLW | B2_SAFE_RTC | 2 | 0 | 1 | 0 | 1 | 1 | 0 | — | — | 0.001503 | 0.4268 | 0.41196 | 1 | 0 | — | — |
| SLW | B3_SAFE_ROTATE | 2 | 1 | 1 | 0 | 1 | 1 | 0 | — | 54.653 | 0.052563 | 0.3222 | 0.3332 | 1 | 0 | — | — |
| SLW | B4_ASTAR | 2 | 0 | 1 | 0 | 1 | 1 | 0 | — | — | 0.0084516 | 0.47471 | 0.53985 | 3 | 25 | 0.33333 | 0.27857 |
| SLW | C0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0.08967 | 0.58827 | 0.6716 | 2 | 25 | 0.38889 | 0.48789 |
| LC | B0_NOMAD_RAW | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — | 38.042 | 0.18574 | 0.49055 | 0.19196 | 0 | 0 | — | — |
| LC | B1_SAFE_TE | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — | 32.34 | 0.23021 | 0.457 | 0.25392 | 0 | 0 | — | — |
| LC | B2_SAFE_RTC | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — | 40.076 | 0.14157 | 0.49429 | 0.28931 | 0 | 0 | — | — |
| LC | B3_SAFE_ROTATE | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — | 37.632 | 0.17978 | 0.5482 | 0.27779 | 0 | 0 | — | — |
| LC | B4_ASTAR | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — | 37.361 | 0.14619 | 0.35365 | 0.22605 | 0 | 4 | 0.55556 | 0.43875 |
| LC | C0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — | 37.799 | 0.15341 | 0.36241 | 0.28507 | 0 | 2 | 0.44444 | 0.34928 |
| L2 | B0_NOMAD_RAW | 2 | 0 | 2 | 2 | 0 | 0 | 0 | — | — | -0.00033777 | 0.60275 | 0.40543 | 0 | 0 | — | — |
| L2 | B1_SAFE_TE | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 14.694 | — | 0.40682 | 0.73951 | 0.60926 | 0 | 0 | — | — |
| L2 | B2_SAFE_RTC | 2 | 0 | 1 | 1 | 0 | 0 | 1 | 66.236 | — | 0.032192 | 0.67149 | 0.4086 | 0 | 0 | — | — |
| L2 | B3_SAFE_ROTATE | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0.11044 | 0.67716 | 0.59753 | 1 | 0 | — | — |
| L2 | B4_ASTAR | 2 | 1 | 0 | 0 | 0 | 0 | 2 | 43.056 | 49.264 | 0.056822 | 0.64301 | 0.52851 | 0 | 3 | 0.30556 | 0.2529 |
| L2 | C0 | 2 | 2 | 0 | 0 | 0 | 0 | 2 | 15.139 | 54.09 | 0.13676 | 0.47303 | 0.22706 | 0 | 5 | 0.33333 | 0.28582 |
| H1 | B0_NOMAD_RAW | 2 | 1 | 1 | 1 | 0 | 0 | 1 | 9 | 35.569 | 0.051583 | 0.51264 | 0.26622 | 0 | 0 | — | — |
| H1 | B1_SAFE_TE | 2 | 2 | 0 | 0 | 0 | 0 | 2 | 6.8333 | 30.438 | 0.11159 | 0.41705 | 0.19176 | 0 | 0 | — | — |
| H1 | B2_SAFE_RTC | 2 | 1 | 1 | 1 | 0 | 0 | 1 | 10.847 | 53.875 | 0.033784 | 0.57052 | 0.31224 | 0 | 0 | — | — |
| H1 | B3_SAFE_ROTATE | 2 | 2 | 0 | 0 | 0 | 0 | 2 | 9.0278 | 38.118 | 0.11592 | 0.47903 | 0.31893 | 0 | 0 | — | — |
| H1 | B4_ASTAR | 2 | 2 | 0 | 0 | 0 | 0 | 2 | 10.34 | 33.694 | 0.053946 | 0.31886 | 0.23716 | 0 | 5 | — | 0.30392 |
| H1 | C0 | 2 | 1 | 1 | 1 | 0 | 0 | 1 | 6.1528 | 29.986 | 0.071469 | 0.35093 | 0.29737 | 0 | 9 | 0.33333 | 0.32668 |
| H2 | B0_NOMAD_RAW | 2 | 0 | 2 | 2 | 0 | 0 | 0 | — | — | -0.00075773 | 0.616 | 0.35011 | 0 | 0 | — | — |
| H2 | B1_SAFE_TE | 2 | 1 | 0 | 0 | 0 | 0 | 1 | 31.056 | 56.278 | 0.029507 | 0.44223 | 0.31388 | 6 | 0 | — | — |
| H2 | B2_SAFE_RTC | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 54.847 | — | 0.094695 | 0.66358 | 0.6142 | 3 | 0 | — | — |
| H2 | B3_SAFE_ROTATE | 2 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0.087666 | 0.63704 | 0.45062 | 0 | 0 | — | — |
| H2 | B4_ASTAR | 2 | 1 | 0 | 0 | 0 | 0 | 2 | 46 | 73.875 | 0.046685 | 0.46959 | 0.3593 | 0 | 16 | 0.36111 | 0.43519 |
| H2 | C0 | 2 | 1 | 0 | 0 | 0 | 0 | 1 | 32.611 | 54.931 | 0.039616 | 0.4147 | 0.26406 | 0 | 10 | 0.41667 | 0.39659 |
| SUDDEN | B0_NOMAD_RAW | 6 | 1 | 5 | 5 | 0 | 0 | 1 | 9 | 35.569 | -0.00036861 | 0.58297 | 0.32261 | 0 | 0 | — | — |
| SUDDEN | B1_SAFE_TE | 6 | 3 | 0 | 0 | 0 | 0 | 4 | 11.375 | 33.694 | 0.045626 | 0.4464 | 0.2966 | 6 | 0 | — | — |
| SUDDEN | B2_SAFE_RTC | 6 | 1 | 2 | 2 | 0 | 0 | 3 | 54.847 | 53.875 | 0.045183 | 0.64328 | 0.41403 | 3 | 0 | — | — |
| SUDDEN | B3_SAFE_ROTATE | 6 | 2 | 0 | 0 | 0 | 0 | 2 | 9.0278 | 38.118 | 0.099391 | 0.54506 | 0.36496 | 1 | 0 | — | — |
| SUDDEN | B4_ASTAR | 6 | 4 | 0 | 0 | 0 | 0 | 6 | 26.451 | 41.903 | 0.051895 | 0.44363 | 0.30135 | 0 | 24 | 0.33333 | 0.30392 |
| SUDDEN | C0 | 6 | 4 | 1 | 1 | 0 | 0 | 4 | 15.139 | 50.438 | 0.087331 | 0.42798 | 0.24563 | 0 | 24 | 0.33333 | 0.32849 |
| STATIC | B0_NOMAD_RAW | 4 | 2 | 1 | 0 | 1 | 1 | 0 | — | 38.042 | 0.11585 | 0.59283 | 0.31787 | 0 | 0 | — | — |
| STATIC | B1_SAFE_TE | 4 | 2 | 0 | 0 | 0 | 0 | 0 | — | 32.34 | 0.092175 | 0.49025 | 0.38457 | 4 | 0 | — | — |
| STATIC | B2_SAFE_RTC | 4 | 2 | 1 | 0 | 1 | 1 | 0 | — | 40.076 | 0.059455 | 0.49429 | 0.32626 | 1 | 0 | — | — |
| STATIC | B3_SAFE_ROTATE | 4 | 3 | 1 | 0 | 1 | 1 | 0 | — | 37.931 | 0.13799 | 0.50959 | 0.306 | 1 | 0 | — | — |
| STATIC | B4_ASTAR | 4 | 2 | 1 | 0 | 1 | 1 | 0 | — | 37.361 | 0.077771 | 0.4358 | 0.36582 | 3 | 29 | 0.44444 | 0.33158 |
| STATIC | C0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | — | 37.799 | 0.15341 | 0.42287 | 0.48156 | 2 | 27 | 0.38889 | 0.46311 |

## Paired seed outcomes

| scene | index | method | classification | success | collision | box_passage | box_passage_from_spawn_s | goal_time_s | technical_validation | attempt_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1 | 201 | B0_NOMAD_RAW | COLLISION | False | True | False | — | — | PASS | 1 |
| H1 | 201 | B1_SAFE_TE | SUCCESS | True | False | True | 5.6111 | 27.181 | PASS | 1 |
| H1 | 201 | B2_SAFE_RTC | SUCCESS | True | False | True | 10.847 | 53.875 | PASS | 1 |
| H1 | 201 | B3_SAFE_ROTATE | SUCCESS | True | False | True | 8.4167 | 37.556 | PASS | 1 |
| H1 | 201 | B4_ASTAR | SUCCESS | True | False | True | 9.6111 | 34.542 | PASS | 1 |
| H1 | 201 | C0 | SUCCESS | True | False | True | 6.1528 | 29.986 | PASS | 1 |
| H1 | 202 | B0_NOMAD_RAW | SUCCESS | True | False | True | 9 | 35.569 | PASS | 1 |
| H1 | 202 | B1_SAFE_TE | SUCCESS | True | False | True | 8.0556 | 33.694 | PASS | 1 |
| H1 | 202 | B2_SAFE_RTC | COLLISION | False | True | False | — | — | PASS | 1 |
| H1 | 202 | B3_SAFE_ROTATE | SUCCESS | True | False | True | 9.6389 | 38.681 | PASS | 1 |
| H1 | 202 | B4_ASTAR | SUCCESS | True | False | True | 11.069 | 32.847 | PASS | 1 |
| H1 | 202 | C0 | COLLISION | False | True | False | — | — | PASS | 1 |
| H2 | 201 | B0_NOMAD_RAW | COLLISION | False | True | False | — | — | PASS | 1 |
| H2 | 201 | B1_SAFE_TE | SUCCESS | True | False | True | 31.056 | 56.278 | PASS | 1 |
| H2 | 201 | B2_SAFE_RTC | STUCK | False | False | True | 54.847 | — | PASS | 1 |
| H2 | 201 | B3_SAFE_ROTATE | STUCK | False | False | False | — | — | PASS | 1 |
| H2 | 201 | B4_ASTAR | STUCK | False | False | True | 40.861 | — | PASS | 1 |
| H2 | 201 | C0 | STUCK | False | False | False | — | — | PASS | 1 |
| H2 | 202 | B0_NOMAD_RAW | COLLISION | False | True | False | — | — | PASS | 1 |
| H2 | 202 | B1_SAFE_TE | STUCK | False | False | False | — | — | PASS | 1 |
| H2 | 202 | B2_SAFE_RTC | STUCK | False | False | False | — | — | PASS | 1 |
| H2 | 202 | B3_SAFE_ROTATE | STUCK | False | False | False | — | — | PASS | 1 |
| H2 | 202 | B4_ASTAR | SUCCESS | True | False | True | 51.139 | 73.875 | PASS | 1 |
| H2 | 202 | C0 | SUCCESS | True | False | True | 32.611 | 54.931 | PASS | 1 |
| L2 | 201 | B0_NOMAD_RAW | COLLISION | False | True | False | — | — | PASS | 1 |
| L2 | 201 | B1_SAFE_TE | STUCK | False | False | False | — | — | PASS | 1 |
| L2 | 201 | B2_SAFE_RTC | COLLISION | False | True | False | — | — | PASS | 1 |
| L2 | 201 | B3_SAFE_ROTATE | STUCK | False | False | False | — | — | PASS | 1 |
| L2 | 201 | B4_ASTAR | SUCCESS | True | False | True | 12.042 | 49.264 | PASS | 1 |
| L2 | 201 | C0 | SUCCESS | True | False | True | 18.597 | 62.236 | PASS | 1 |
| L2 | 202 | B0_NOMAD_RAW | COLLISION | False | True | False | — | — | PASS | 1 |
| L2 | 202 | B1_SAFE_TE | STUCK | False | False | True | 14.694 | — | PASS | 1 |
| L2 | 202 | B2_SAFE_RTC | STUCK | False | False | True | 66.236 | — | PASS | 1 |
| L2 | 202 | B3_SAFE_ROTATE | STUCK | False | False | False | — | — | PASS | 1 |
| L2 | 202 | B4_ASTAR | STUCK | False | False | True | 74.069 | — | PASS | 1 |
| L2 | 202 | C0 | SUCCESS | True | False | True | 11.681 | 45.944 | PASS | 1 |
| LC | 201 | B0_NOMAD_RAW | SUCCESS | True | False | False | — | 40.722 | PASS | 1 |
| LC | 201 | B1_SAFE_TE | SUCCESS | True | False | False | — | 29.944 | PASS | 1 |
| LC | 201 | B2_SAFE_RTC | SUCCESS | True | False | False | — | 45.444 | PASS | 1 |
| LC | 201 | B3_SAFE_ROTATE | SUCCESS | True | False | False | — | 37.333 | PASS | 1 |
| LC | 201 | B4_ASTAR | SUCCESS | True | False | False | — | 36.958 | PASS | 1 |
| LC | 201 | C0 | SUCCESS | True | False | False | — | 36.861 | PASS | 1 |
| LC | 202 | B0_NOMAD_RAW | SUCCESS | True | False | False | — | 35.361 | PASS | 1 |
| LC | 202 | B1_SAFE_TE | SUCCESS | True | False | False | — | 34.736 | PASS | 1 |
| LC | 202 | B2_SAFE_RTC | SUCCESS | True | False | False | — | 34.708 | PASS | 1 |
| LC | 202 | B3_SAFE_ROTATE | SUCCESS | True | False | False | — | 37.931 | PASS | 1 |
| LC | 202 | B4_ASTAR | SUCCESS | True | False | False | — | 37.764 | PASS | 1 |
| LC | 202 | C0 | SUCCESS | True | False | False | — | 38.736 | PASS | 1 |
| SLW | 201 | B0_NOMAD_RAW | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 201 | B1_SAFE_TE | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 201 | B2_SAFE_RTC | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 201 | B3_SAFE_ROTATE | CORRIDOR | False | True | False | — | — | PASS | 1 |
| SLW | 201 | B4_ASTAR | CORRIDOR | False | True | False | — | — | PASS | 1 |
| SLW | 201 | C0 | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 202 | B0_NOMAD_RAW | CORRIDOR | False | True | False | — | — | PASS | 1 |
| SLW | 202 | B1_SAFE_TE | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 202 | B2_SAFE_RTC | CORRIDOR | False | True | False | — | — | PASS | 1 |
| SLW | 202 | B3_SAFE_ROTATE | SUCCESS | True | False | False | — | 54.653 | PASS | 1 |
| SLW | 202 | B4_ASTAR | STUCK | False | False | False | — | — | PASS | 1 |
| SLW | 202 | C0 | STUCK | False | False | False | — | — | PASS | 1 |

## Descriptive sign counts

| group | comparison | wins | losses | ties | exact_sign_p |
| --- | --- | --- | --- | --- | --- |
| SUDDEN | C0 vs B1_SAFE_TE | 3 | 2 | 1 | 1 |
| SUDDEN | C0 vs B2_SAFE_RTC | 3 | 0 | 3 | 0.25 |
| SUDDEN | C0 vs B3_SAFE_ROTATE | 3 | 1 | 2 | 0.625 |
| SUDDEN | C0 vs B4_ASTAR | 1 | 1 | 4 | 1 |
| STATIC | C0 vs B1_SAFE_TE | 0 | 0 | 4 | 1 |
| STATIC | C0 vs B2_SAFE_RTC | 0 | 0 | 4 | 1 |
| STATIC | C0 vs B3_SAFE_ROTATE | 0 | 1 | 3 | 1 |
| STATIC | C0 vs B4_ASTAR | 0 | 0 | 4 | 1 |
| SLW | C0 vs B1_SAFE_TE | 0 | 0 | 2 | 1 |
| SLW | C0 vs B2_SAFE_RTC | 0 | 0 | 2 | 1 |
| SLW | C0 vs B3_SAFE_ROTATE | 0 | 1 | 1 | 1 |
| SLW | C0 vs B4_ASTAR | 0 | 0 | 2 | 1 |
| LC | C0 vs B1_SAFE_TE | 0 | 0 | 2 | 1 |
| LC | C0 vs B2_SAFE_RTC | 0 | 0 | 2 | 1 |
| LC | C0 vs B3_SAFE_ROTATE | 0 | 0 | 2 | 1 |
| LC | C0 vs B4_ASTAR | 0 | 0 | 2 | 1 |
| L2 | C0 vs B1_SAFE_TE | 2 | 0 | 0 | 0.5 |
| L2 | C0 vs B2_SAFE_RTC | 2 | 0 | 0 | 0.5 |
| L2 | C0 vs B3_SAFE_ROTATE | 2 | 0 | 0 | 0.5 |
| L2 | C0 vs B4_ASTAR | 1 | 0 | 1 | 1 |
| H1 | C0 vs B1_SAFE_TE | 0 | 1 | 1 | 1 |
| H1 | C0 vs B2_SAFE_RTC | 0 | 0 | 2 | 1 |
| H1 | C0 vs B3_SAFE_ROTATE | 0 | 1 | 1 | 1 |
| H1 | C0 vs B4_ASTAR | 0 | 1 | 1 | 1 |
| H2 | C0 vs B1_SAFE_TE | 1 | 1 | 0 | 1 |
| H2 | C0 vs B2_SAFE_RTC | 1 | 0 | 1 | 1 |
| H2 | C0 vs B3_SAFE_ROTATE | 1 | 0 | 1 | 1 |
| H2 | C0 vs B4_ASTAR | 0 | 0 | 2 | 1 |

H2 scene passage requires both boxes; per-box spawn-to-passage times and collision/clearance are in runs.json. Missing passage time is not imputed. Raw attempts and original phase results are preserved. Primary technical failures after one identical-seed retry exclude the complete scene×seed primary group; B0 failure is independent.

Technical exclusions: []


Phase27-R registration SHA256 `6d615e7a4c440d9c957025f672514def627ec99d63cdbcaa9dc37832535647f8`. The sole controller change is SPAlignment.replace_path: project B, then use the first stored suffix waypoint at arclength >=s_B+0.05m; no alignment if unavailable. All Phase26 decisions, seeds, scenes, method ordering and technical-retry rules are reused. Original Phase26 results are preserved.
