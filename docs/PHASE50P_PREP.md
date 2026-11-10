| phase | runs | method | scenes | speeds | seeds | status |
|---|---|---|---|---|---|---|
| 50-P | 12 | OURS-DETOUR+HMM | H1,L2 | .5,1.0 | 221,222,223 | PREPARED_NOT_RUN |

| item | value |
|---|---|
| shape | vertical cylinder |
| diameter_m | 0.4 |
| height_m | 1.7 |
| speeds_m_s | [0.5, 1.0] |
| crossing | {'L2': 'x=3.5,perpendicular to straight reference', 'H1': 'y=2.7,across corner-exit corridor'} |
| spawn | First 72Hz tick at reference-projected remaining arclength <= Uniform(1.5,2.5)m; distance fixed per scene/seed |
| lateral | Start center inset0.35m + Uniform(-0.1,0.1)m from chosen wall; odd seed low->high,even high->low; same draw both speeds |
| endpoint | Opposite wall center inset0.25m => cylinder surface gap0.05m; remove at exact crossing duration,one crossing,no reappearance |
| removal_log | Exact simulation time and person pose;robot pose interpolated by frozen integrate_se2 within containing72Hz tick;center and footprint distances |
| no_static_changes | True |
| no_topomap_regeneration | True |
| no_method_changes | True |
| no_dynamic_velocity_to_controller | True |
| person_color | [0.65, 0.04, 0.65] |
| renderer | Frozen Phase26 static renderer + UsdGeom.Cylinder,linear time-sampled position |
| collision | Continuous relative moving circle vs frozen robot unicycle arc;chord/sagitta certified bounds and contact-stop convention |
| post_removal | Frozen depth update only;no deletion/mask/oracle clearing;passive snapshot observation at72Hz deduplicated by published frame_id |

| scene | index | passed | wall_clearance_m | static_clearance_m | start_xy | end_xy | diameter_m | height_m | depth_render_performed |
|---|---|---|---|---|---|---|---|---|---|
| H1 | 221 | True | 0.05 | {'InnerCorner': 0.1535878190101047, 'AfterCorner': 0.4000000000000001} | [2.7535878190101046, 2.7] | [3.95, 2.7] | 0.4 | 1.7 | False |
| L2 | 221 | True | 0.05 | {} | [3.5, -1.1680098742138458] | [3.5, 1.25] | 0.4 | 1.7 | False |
| H1 | 222 | True | 0.0999 | {'InnerCorner': 0.04999999999999999, 'AfterCorner': 0.4000000000000001} | [3.900099865249683, 2.7] | [2.65, 2.7] | 0.4 | 1.7 | False |
| L2 | 222 | True | 0.05 | {} | [3.5, 1.1939675748586775] | [3.5, -1.25] | 0.4 | 1.7 | False |
| H1 | 223 | True | 0.05 | {'InnerCorner': 0.17590163996573133, 'AfterCorner': 0.4000000000000001} | [2.7759016399657312, 2.7] | [3.95, 2.7] | 0.4 | 1.7 | False |
| L2 | 223 | True | 0.05 | {} | [3.5, -1.187690336305021] | [3.5, 1.25] | 0.4 | 1.7 | False |

| passed | tests | dry_run | simulations_started | renders | protocol_sha256 | disk_free_bytes |
|---|---|---|---|---|---|---|
| True | 7 | 12 | 0 | 0 | e2dc1f876327ebe8079bbe736ced947e5ac0a3acfd95cad6513a181be1117109 | 1137887023104 |

| campaign | status |
|---|---|
| cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase50p.campaign > ../artifacts/isaac6/phase50p_01.log 2>&1 < /dev/null & | cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase50p.campaign --status |
