"""Synthetic-only tests. No Isaac, model, stored run replay or GPU imports."""
import ast
import json
from pathlib import Path
import unittest
import numpy as np
from nomad_phase0.graph_v4 import SignedDistanceField
from .depth_sdf import DepthSDF, backproject, camera_to_world, intrinsics
from .evaluate import available, choose, decision, distribution, sample_path, suffix
from .report import document


CAM=dict(focal_length_mm=18.,horizontal_aperture_mm=36.,vertical_aperture_mm=27.)


def synthetic_box():
    k=intrinsics(CAM); vv,uu=np.mgrid[:240,:320]
    # Off-grid front face x=1.003; don't hide cell quantization in the test.
    y=-(uu+.5-k[2])*1.003/k[0];z=.5-(vv+.5-k[3])*1.003/k[1]
    depth=np.where((abs(y)<=.4)&(z>=0)&(z<=.8),1.003,np.inf)
    return depth,k


class DepthTests(unittest.TestCase):
    def test_synthetic_box_within_one_cm(self):
        depth,k=synthetic_box(); field=DepthSDF([-.5,-1.5,2.,1.5])
        field.update(depth,k,camera_to_world([0,0,0]))
        config=dict(agent_radius_m=.09,corridor=dict(xmin=-.5,xmax=2.,half_width=1.5),
            obstacles=[dict(id='box',center_xy_m=[1.203,0],size_xyz_m=[.4,.8,.8])])
        truth=SignedDistanceField(config,.01,0.)
        xx,yy=np.meshgrid(np.linspace(.2,.95,37),np.linspace(-.3,.3,25));points=np.c_[xx.ravel(),yy.ravel()]
        # Observable free side only: unseen interiors cannot be reconstructed.
        error=np.max(abs(field.query(points)[0]-truth.query(points)[0]))
        self.assertLessEqual(error,.01)
        self.assertAlmostEqual(field.error_bound,.01/np.sqrt(2))

    def test_camera_axes_and_axial_not_radial(self):
        depth=np.array([[2.,2.]])
        p,r,_=backproject(depth,np.array([1.,1.,1.,.5]),camera_to_world([3,4,np.pi/2]))
        np.testing.assert_allclose(p,[[2,6,.5],[4,6,.5]],atol=1e-12)
        np.testing.assert_allclose(r,np.sqrt(5))

    def test_noise_filter_unknown_and_persistence(self):
        depth,k=synthetic_box(); f=DepthSDF([-.5,-1.5,4.,1.5])
        a=backproject(depth,k,camera_to_world([0,0,0]),True,np.random.default_rng(7))[0]
        b=backproject(depth,k,camera_to_world([0,0,0]),True,np.random.default_rng(7))[0]
        np.testing.assert_array_equal(a,b)
        stats=f.update(depth,k,camera_to_world([0,0,0]));occupied=f.occupied.copy()
        self.assertTrue(f.height_rejected.any());self.assertTrue((~f.observed).any())
        self.assertAlmostEqual(stats['update_ms'],stats['pointcloud_ms']+stats['accumulate_ms']+stats['sdf_ms'])
        f.update(np.full((240,320),4.),k,camera_to_world([0,0,0]))
        np.testing.assert_array_equal(f.occupied,occupied)
        self.assertTrue(f.range_rejected.any())

    def test_query_gradient_empty_and_bounds(self):
        f=DepthSDF([-1,-1,1,1]);v,g=f.query(np.array([[0.,0.]]))
        self.assertGreater(v[0],0);np.testing.assert_array_equal(g,[[0.,0.]])
        self.assertEqual(f.unknown_fraction([[0,0]]),1.)
        f.mark(f.occupied,np.array([[.5,0.]]))
        from scipy.ndimage import distance_transform_edt
        f.values=distance_transform_edt(~f.occupied,sampling=f.h)-f.radius
        v,g=f.query(np.array([[.123,0.]]));self.assertAlmostEqual(g[0,0],-1.)
        with self.assertRaises(ValueError): f.query(np.array([[2.,0.]]))

    def test_time_gating_projection_and_selection(self):
        self.assertTrue(available(dict(capture_end_monotonic_ns=10),dict(application_monotonic_ns=10)))
        self.assertFalse(available(dict(capture_end_monotonic_ns=11),dict(application_monotonic_ns=10)))
        path,length=suffix([[0,0],[1,0],[2,0]],[.5,.2,0])
        np.testing.assert_allclose(path[0],[.5,0]);self.assertAlmostEqual(length,1.5)
        q,step=sample_path(path);self.assertLessEqual(step,.005)
        self.assertEqual(choose([.025,.026,.001],[1,1,5]),0)
        self.assertIsNone(choose([.024],[1]))
        path,length=suffix([[0,0],[1,0]],[2,0,0]);self.assertEqual(length,0.)
        self.assertEqual(len(path),2)

    def test_decision_order_boundaries(self):
        self.assertEqual(decision(.02001,.9,51),'DEPTH_NOT_READY')
        self.assertEqual(decision(.02,.9,50.01),'TIMING_NOT_READY')
        self.assertEqual(decision(.02,.20001,50),'DEPTH_CONSERVATIVE')
        self.assertEqual(decision(.02,.20,50),'DEPTH_READY')

    def test_rgb_default_and_replay_gate_static(self):
        source=(Path(__file__).parents[1]/'nomad_isaac/simulator.py').read_text()
        ast.parse(source)
        self.assertIn('"distance_to_image_plane" if args.depth_camera else "rgb"',source)
        self.assertIn('if args.depth_camera != bool(args.depth_replay_manifest)',source)
        self.assertIn('else:\n        main()',source)
        protocol=json.loads(Path(__file__).with_name('protocol.json').read_text())
        self.assertEqual(protocol['expected_runs'],24);self.assertFalse(protocol['navigation'])

    def test_report_timing_and_both_conditions(self):
        d=distribution([1.,2.]);timing={k:d for k in ('pointcloud_ms','accumulate_ms','sdf_ms','update_ms','points','obstacle_points','unknown_fraction')}
        c=dict(samples=8,agreement_fraction=1.,dangerous_fraction=0.,conservative_fraction=0.,
            clearance_error_m=d,dangerous_oracle_clearance_m=d,timing=timing,confusion={},error_causes={},
            selection_agreement_fraction=1.,selected_count=1,selected_unsafe=0,selection_both_null=0,
            depth_selection_oracle_clearance_m=d)
        text=document(dict(label='TIMING_NOT_READY',render_git_sha='test',report_git_sha='test',
            runs=24,frames=1,conditions={'none':c,'gaussian':c},collision_counterfactuals=[]))
        for word in ('none','gaussian','pointcloud_ms','accumulate_ms','sdf_ms','Accuracy passed'):
            self.assertIn(word,text)
        self.assertEqual(text.strip().splitlines()[-1],'TIMING_NOT_READY')


if __name__=='__main__':unittest.main()
