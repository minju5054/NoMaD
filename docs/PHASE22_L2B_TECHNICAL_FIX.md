# Phase22 L2B — execution defect repair (before rerun)

## L2B execution defect and authorized rerun

Original L2B: **TECHNICAL_INVALID** (12 logical runs, 24 attempts). All attempts failed during rotated-box monitor construction before the spawn was published; no L2B navigation outcome was observed. The original report and raw data are retained unchanged. This was an execution-defect repair before observing L2B outcomes, authorized before rerunning the same preregistered seeds.

The parent ObstacleMonitor created `obstacle_geometry.json` with exclusive creation; OrientedMonitor tried to exclusively create the same file a second time. FileExistsError stopped the kinematic thread; the worker EOF was secondary. The only production-path change stores supplemental OBB metadata under a distinct filename. Placement, rigid-transformed swept collision, planners, weights, triggers, controller, seeds and decisions are unchanged.

```diff
diff --git a/research/nomad_phase22/drive_geometry.py b/research/nomad_phase22/drive_geometry.py
index 2e4742d..da843a8 100644
--- a/research/nomad_phase22/drive_geometry.py
+++ b/research/nomad_phase22/drive_geometry.py
@@ -39,7 +39,7 @@ def ray_distance(pose,box,radius):
 class OrientedMonitor(ObstacleMonitor):
     def __init__(self,config,out):
         super().__init__(config,out);self.box=config['obstacle'];self.lower,self.upper=bounds(self.box)
-        write_json(out/'obstacle_geometry.json',dict(**self.box,world_corners=corners(self.box).tolist(),world_aabb=[self.lower.tolist(),self.upper.tolist()],collision='Exact OBB via rigid transform and existing swept AABB evaluator',agent_radius_m=self.radius))
+        write_json(out/'oriented_obstacle_geometry.json',dict(**self.box,world_corners=corners(self.box).tolist(),world_aabb=[self.lower.tolist(),self.upper.tolist()],collision='Exact OBB via rigid transform and existing swept AABB evaluator',agent_radius_m=self.radius))
     def observe_interval(self,start,end,v,w,time_start,duration):
         gap=swept_gap(start,v,w,duration,self.box,self.radius,self.config['required_clearance_m']);wall=corridor_clearance(start,end,v,w,duration,self.config['corridor'],self.radius)
         self.minimum=min(self.minimum,gap['lower_m']);self.minimum_upper=min(self.minimum_upper,gap['upper_m']);self.corridor_minimum=min(self.corridor_minimum,wall)
```

Patch `research/nomad_phase22/drive_geometry.py`: `f2561ff94ea8c5b009350d1caadc2e851af437b5d81077906647ea4f5e0c6d41` → `da26c487edbdc4d42d14c6309e1bc23cb97439f917b7757f0e37081ad151ba9c`. Amendment protocol SHA256 `d877657bc4b25312cf30a7f85b3e83bfd54dad57ece51546b882a6e036f7b7ef`.

Original report: [PHASE22_REFINE_DRIVE.md](PHASE22_REFINE_DRIVE.md). Original L2 metrics are reused bit-for-bit from recorded hashes; only L2B is newly executed in a separate root. Same-seed one technical retry and full scene×seed group exclusion remain unchanged.

Spawn-only launch checks use unused indices901/902/903 at the trigger plane: method/backend startup, production SuddenObstacleMonitor, rotated collision model and actual depth capture. No inference, navigation, planner solve or performance outcome is recorded by these diagnostic fixtures.

## Spawn-only checks

| method | index | passed | depth_box_pixels | rigid_swept_error_m | worker_class | output |
| --- | --- | --- | --- | --- | --- | --- |
| P0_ASTAR | 901 | True | 9766 | 0 | nomad_phase21.worker.Worker | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase22_l2b_launch_checks_01/P0_ASTAR_901 |
| P1_GRAPH | 902 | True | 9761 | 0 | nomad_phase20d.worker.Worker | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase22_l2b_launch_checks_01/P1_GRAPH_902 |
| P2F_ASTAR_GRAPH | 903 | True | 9766 | 0 | nomad_phase22.drive_backend.Worker | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase22_l2b_launch_checks_01/P2F_ASTAR_GRAPH_903 |

Regression tests: 3/3 PASS. Frozen method/controller/trigger/decision source hashes match a955e0a. New execution: L2B only, indices121–124, 12 jobs; existing L2 12 jobs reused without recalculation. Main campaign not started.

The merged report will be written to `docs/PHASE22_REFINE_DRIVE_L2B_RERUN.md` and `research/results/phase22_l2b_rerun/`; it uses the original decision function and asserts that the L2 judgement is unchanged. The original report/results are not overwritten.
