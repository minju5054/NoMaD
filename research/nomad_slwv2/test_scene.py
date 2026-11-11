import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from nomad_phase18.config import scene as old_scene
from nomad_j0 import metrics as jmetrics,campaign as jcampaign
from nomad_j1.depth import registration
from . import config,reference,launch,campaign,metrics,report

class Tests(unittest.TestCase):
    def test_only_requested_geometry_changes(self):
        before=old_scene('SLW');c=config.build_scene();self.assertEqual(before['start_pose'],[0.,0.,0.])
        self.assertEqual(c['start_pose'],[-1.,0.,0.]);self.assertEqual(c['corridor'],dict(before['corridor'],xmin=-2.))
        for old,new,color in zip(before['obstacles'],c['obstacles'],config.COLORS):
            self.assertEqual(new,dict(old,color_rgb=list(color)))
        exclude={'name','phase16_scene','scene_variant','start_pose','corridor','obstacles','grid_feasibility'}
        for k,v in before.items():
            if k not in exclude and not k.startswith('reference_'):self.assertEqual(c[k],v,k)
        self.assertEqual(c['checkpoint'],before['checkpoint'])
        self.assertEqual(registration(c)['registered_bounds_m'],[-4.,-3.5,8.,6.2])

    def test_reference_reuses_original_procedure_without_execution(self):
        source=inspect.getsource(reference.define)
        self.assertIn('from nomad_phase16.geometry import reference_path,reference_rollout',source)
        render=(config.HERE/'reference_simulator.py').read_text()
        self.assertIn("'nomad_phase17/simulator.py'",render)
        original=(config.ROOT/'research/nomad_phase17/simulator.py').read_text()
        self.assertIn('ticks=list(range(0,len(poses),144))',original)
        p=reference.plan();self.assertFalse(p['NoMaD_inference']);self.assertEqual(p['spacing_sim_s'],2.)
        self.assertEqual(p['render_argv'][p['render_argv'].index('--mode')+1],'reference')
        self.assertFalse(config.RUN_ROOT.exists())

    def test_actual_four_launch_plans_even_before_new_assets_exist(self):
        p=config.verify();plan=campaign.jobs(config.RUN_ROOT)
        self.assertEqual([(j['delay'],j['index']) for j in plan],[(0.,221),(0.,222),(.75,221),(.75,222)])
        for j in plan:
            a=launch.parser().parse_args(j['argv'][4:]+['--dry-run']);row=launch.build(a)
            self.assertIn(str(config.TOPOMAP),row['worker']);self.assertIn(str(config.HERE/'simulator.py'),row['simulator'])
            self.assertEqual(row['simulations_started'],0)
        with self.assertRaisesRegex(AssertionError,'must be prepared first'):config.verify_assets()
        self.assertIs(metrics.audit.__code__,jmetrics.audit.__code__)
        self.assertIs(campaign.execute.__code__,jcampaign.execute.__code__)
        self.assertEqual(campaign.execute.__globals__['__package__'],'nomad_slwv2')

    def test_generated_assets_hash_guard(self):
        from nomad_isaac.common import sha256_file
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest=root/'manifest.json';manifest.write_text('{}');image=root/'node.png';image.write_bytes(b'saved image')
            data=dict(protocol_sha256=sha256_file(config.HERE/'protocol.json'),topomap_manifest=str(manifest),spacing_sim_s=2.,
                      sha256={str(manifest):sha256_file(manifest),str(image):sha256_file(image)})
            (root/'resolved_assets.json').write_text(json.dumps(data))
            with patch.object(config,'RUN_ROOT',root),patch.object(config,'TOPOMAP',manifest):
                self.assertEqual(config.verify_assets(),data)
                image.write_bytes(b'modified')
                with self.assertRaises(AssertionError):config.verify_assets()

    def test_same_selection_criterion_and_empty_report(self):
        rows=[dict(j,technical_validation='PASS',success=True,checkpoint_time_s=10.+j['delay']) for j in config.order()]
        self.assertEqual(report.selection(rows)['selected_scenes'],['SLW-v2'])
        rows[-1]['checkpoint_time_s']=9.25;self.assertEqual(report.selection(rows)['selected_scenes'],[])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);doc,pics=report.generate(root,root/'out',root/'report.md')
            self.assertEqual(pics,[]);self.assertIn('0s 성공2/2',doc.read_text())
            self.assertEqual(json.loads((root/'out/decision.json').read_text())['status'],'PREPARED_NOT_RUN')

if __name__=='__main__':unittest.main()
