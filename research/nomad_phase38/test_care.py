import json,os,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from .care import correct,nearest_bins,frame_obstacles,ROTATION_CLIP,SAFE_FOV

class CareTests(unittest.TestCase):
    def test_empty_unchanged(self):
        p=np.array([[.3,0],[.6,0],[1.,0]])
        q,d=correct(p,[0,0,0],[]);np.testing.assert_array_equal(q,p);self.assertFalse(d['safe_fov'])
    def test_repulsive_equation_and_opposite_side_rotation_both_sides(self):
        p=np.array([[.5,0],[1,0]])
        for sign in (-1,1):
            obstacle=np.array([[.5,.2*sign]]);q,d=correct(p,[0,0,0],obstacle)
            delta=p[:,None]-obstacle[None];expected=(delta/np.linalg.norm(delta,axis=2)[...,None]**4).sum(axis=1)
            np.testing.assert_allclose(d['forces'],expected)
            self.assertEqual(d['selected_waypoint'],0);self.assertAlmostEqual(d['rotation_rad'],-sign*ROTATION_CLIP)
        np.testing.assert_allclose(np.linalg.norm(q,axis=1),np.linalg.norm(p,axis=1));json.dumps(d,allow_nan=False)
    def test_front_obstacle_uses_plain_atan2_clip_without_special_case(self):
        for offset in (0.,1e-10,-1e-10):
            _,d=correct([[.5,0]],[0,0,0],[[.7,offset]])
            force=np.array(d['forces'][0]);expected=np.clip(np.arctan2(force[1],force[0]),-ROTATION_CLIP,ROTATION_CLIP)
            self.assertEqual(d['rotation_rad'],expected)
    def test_camera_left_right_transform_then_repulsive_turn(self):
        camera=dict(height_m=.5,focal_length_mm=1.,horizontal_aperture_mm=2.,vertical_aperture_mm=2.)
        for col,expected in ((0,-ROTATION_CLIP),(3,ROTATION_CLIP)):
            depth=np.zeros((4,4));depth[2,col]=.5
            points,_=frame_obstacles(depth,camera,[0,0,0],0,0,noise=False)
            _,d=correct([[.5,0]],[0,0,0],points)
            self.assertEqual(d['rotation_rad'],expected)
    def test_32_uniform_lateral_bins_keep_nearest_axial_point(self):
        xyz=np.array([[-1,0,.9],[-.99,0,.4],[0,0,.7],[1,0,.6]])
        world=np.c_[xyz[:,2],-xyz[:,0],np.full(4,.5)]
        pts,d=nearest_bins(xyz,world)
        self.assertEqual(d['point_indices'],[1,2,3]);self.assertEqual(d['bin_ids'],[0,16,31])
        np.testing.assert_array_equal(pts,world[[1,2,3],:2])
        pts,d=nearest_bins([[0,0,.8],[0,0,.2]],[[.8,0,.5],[.2,0,.5]])
        self.assertEqual(d['point_indices'],[1]);self.assertEqual(len(pts),1)
    def test_frame_axial_range_height_and_camera_to_robot_axes(self):
        camera=dict(height_m=.5,focal_length_mm=1.,horizontal_aperture_mm=2.,vertical_aperture_mm=2.)
        depth=np.zeros((4,4));depth[2,0]=.8;depth[0,1]=.8;depth[3,2]=.8;depth[2,3]=1.01
        # First point passes despite Euclidean camera distance >1m: axial Z is .8.
        points,d=frame_obstacles(depth,camera,[0,0,0],0,0,noise=False)
        np.testing.assert_allclose(points,[[.8,.6]]);self.assertEqual(d['filtered_points'],1)
    def test_current_frame_replaces_previous_and_never_builds_map(self):
        from .care_depth import CareFrames
        camera=dict(height_m=.5,focal_length_mm=1.,horizontal_aperture_mm=2.,vertical_aperture_mm=1.5)
        with tempfile.TemporaryDirectory() as d:
            frames=CareFrames(Path(d),camera,950000);frames.submit(np.full((4,8),.8),[0,0,0],0.,0,0)
            old=frames.snapshot();self.assertGreater(len(old.points_world),0);self.assertFalse(old.points_world.flags.writeable)
            frames.submit(np.zeros((4,8)),[1,0,0],.25,1,1);self.assertEqual(len(frames.snapshot().points_world),0)
            self.assertGreater(len(old.points_world),0);self.assertFalse(hasattr(frames.snapshot(),'occupied'));frames.close()
    def test_safe_fov_boundary_and_common_speed_limits(self):
        from .runtime import CareProfile
        for theta,rotates in ((SAFE_FOV,False),(-SAFE_FOV,False),(SAFE_FOV+1e-8,True),(-SAFE_FOV-1e-8,True)):
            ctl=CareProfile();point=np.array([np.cos(theta),np.sin(theta)])
            ctl.replace_path([[0,0],point],[0,0,0],.2);ctl.care_waypoint=point;ctl.mode='GO'
            (v,w),diag=ctl.control(np.zeros(3),.2)
            self.assertEqual(diag['care_safe_fov_active'],rotates);self.assertLessEqual(v,.3);self.assertLessEqual(abs(w),.4)
            if rotates:self.assertEqual(v,0.)
    def test_same_raw_sample_zero_and_apply_function_without_safe_selection(self):
        from .runtime import CareExecution
        from nomad_phase35.runtime import RawNA
        from .test_runtime import prepare,fresh,refresh
        self.assertIs(CareExecution.apply,RawNA.apply)
        with tempfile.TemporaryDirectory() as d:
            e=CareExecution(Path(d));core,_=prepare(e);sw=fresh()
            sw['overnight_metric_samples'][1]=[[0,0],[2,1],[3,1],[4,1],[5,1],[6,1],[7,1],[8,1]]
            with patch('nomad_phase20.runtime.evaluate_samples',side_effect=AssertionError('SAFE forbidden')):
                e.apply(core,refresh(),sw)
            np.testing.assert_allclose(e.follower.path.points,sw['overnight_metric_samples'][0]);self.assertEqual(e.recovery.count,0)
            self.assertIsNone(e.repair_worker);self.assertEqual(e.path_kind,'RAW');e.close()
    def test_current_frame_raw_care_pipeline_logs_standard_json(self):
        from .runtime import CareExecution
        from .care_depth import CareFrames
        from .test_runtime import fresh,refresh
        camera=dict(height_m=.5,focal_length_mm=1.,horizontal_aperture_mm=2.,vertical_aperture_mm=2.)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);frames=CareFrames(out,camera,950000);depth=np.zeros((4,4));depth[2,0]=.5
            frames.submit(depth,[0,0,0],0.,0,0);e=CareExecution(out);e.depth_maps=frames
            core=SimpleNamespace(pose=np.zeros(3),v=0.,w=0.);sw=fresh()
            e.apply(core,refresh(),sw);self.assertEqual(core.v,0.);self.assertLess(core.w,0.)
            json.dumps(sw,allow_nan=False);self.assertFalse(sw['phase38_care']['recovery'])
            e.close();frames.close()
            for f in out.rglob('*.jsonl'):
                for line in f.read_text().splitlines():json.dumps(json.loads(line),allow_nan=False)
            record=json.loads((out/'care.jsonl').read_text().splitlines()[0])
            self.assertEqual(record['sample'],0);self.assertEqual(record['depth_frame']['source'],'CURRENT_FRAME_CARE')
            self.assertFalse(list(out.rglob('snapshot_*.npz')))
    def test_live_factory_routes_raw_executor_and_frame_receiver_without_simulator(self):
        from .config import ROOT
        code='''
import sys,tempfile
from pathlib import Path
from nomad_phase38.config import runtime_config
from nomad_phase38.runtime import install,CareExecution,CareFrames
from nomad_phase35.runtime import RawNA
c=runtime_config('CARE',95);install(c)
import nomad_phase15b.depth as depth
import nomad_phase15b.execution as factory
assert depth.DepthMapThread is CareFrames
assert c['phase21_method']=='B0_NOMAD_RAW'
with tempfile.TemporaryDirectory() as d:
 e=factory.make_execution(c,Path(d))
 assert isinstance(e,CareExecution) and e.apply.__wrapped__.__func__ is RawNA.apply
 assert e.repair_worker is None and not hasattr(e,'ec_file')
 e.close()
assert 'isaacsim' not in sys.modules
'''
        r=subprocess.run(['/usr/bin/python3','-c',code],cwd=ROOT,env=dict(os.environ,PYTHONPATH='research'),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr[-2000:])
    def test_rigid_transform_and_coincidence_are_finite(self):
        p=np.array([[.3,0],[.65,.1]]);obs=np.array([[.4,.2]])
        a,d=correct(p,[0,0,0],obs);rot=np.array([[0,-1],[1,0]])
        b,e=correct(p@rot.T+[2,3],[2,3,np.pi/2],obs@rot.T+[2,3]);np.testing.assert_allclose(b,a@rot.T+[2,3])
        _,d=correct(p,[0,0,0],[p[0]]);json.dumps(d,allow_nan=False);self.assertEqual(d['coincident_pairs'],1)

if __name__=='__main__':unittest.main()
