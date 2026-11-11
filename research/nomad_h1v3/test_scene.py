import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from nomad_h1v2 import scene as v2
from nomad_j1 import execution as shared
from nomad_j0 import metrics as j0metrics,report as j0report,campaign as j0campaign
from . import scene,config,launch,campaign,metrics,report

class Tests(unittest.TestCase):
    def test_y070_geometry_and_single_allowed_adjustment(self):
        p=scene.load_spec();self.assertEqual(p['requested_target']['adjustments'],0)
        np.testing.assert_allclose(p['box']['center_xy_m'],[2.7420996020815553,.7],rtol=0,atol=1e-12)
        self.assertEqual(p['static_overlap_reasons'],[]);self.assertGreaterEqual(p['gap_check']['right_m'],.28)
        self.assertAlmostEqual(p['return_gap_check']['top_to_aftercorner_m'],.8)
        self.assertAlmostEqual(p['return_gap_check']['diagonal_minimum_m'],.8764089769224076)
        _,_,choice=scene.center_choice([[2.5,0.],[2.5,2.]])
        self.assertEqual(choice['adjustments'],1);self.assertEqual(choice['selected_y_m'],.65)

    def test_only_center_and_derived_spawn_change_not_frozen_geometry(self):
        old,manifest=config.common.scene_config('H1-v2');before=copy.deepcopy(old);new=scene.configure(old)
        self.assertEqual(old,before)
        for k,v in old.items():
            if k not in ('dynamic_obstacle','scene_variant','h1v2'):self.assertEqual(new[k],v,k)
        for k,v in old['dynamic_obstacle'].items():
            if k!='center_xy_m':self.assertEqual(new['dynamic_obstacle'][k],v,k)
        self.assertEqual(new['h1v2']['topomap_manifest'],old['h1v2']['topomap_manifest'])
        self.assertEqual(new['h1v2']['topomap_nodes_xy_m'],old['h1v2']['topomap_nodes_xy_m'])
        self.assertEqual(new['h1v2']['spawn']['rule'],old['h1v2']['spawn']['rule'])

    def test_frozen_spawn_once_and_exact_front_arc(self):
        c,_=config.scene_config('H1-v3');p=c['h1v2']
        self.assertIs(scene.triggered,v2.triggered);self.assertIs(scene.place,v2.place)
        self.assertAlmostEqual(p['box_front']['arc_m']-p['spawn']['arc_m'],1.)
        for ds,expected in [(-1e-5,False),(1e-5,True)]:
            q,_=v2.at(p['topomap_nodes_xy_m'],p['spawn']['arc_m']+ds)
            self.assertEqual(scene.triggered(c,[*q,0.],0),expected)
            self.assertFalse(scene.triggered(c,[*q,0.],1))
        r=scene.place(c,[*p['spawn']['position_xy_m'],0.],0)
        self.assertEqual(r['status'],'PLACED');self.assertEqual(r['obstacle']['center_xy_m'],p['box']['center_xy_m'])
        json.dumps(r,allow_nan=False)

    def test_j0_runtime_metrics_and_campaign_are_reused(self):
        p=config.verify();c=config.runtime_config(config.METHOD,221)
        self.assertEqual(c['goal_tolerance_m'],.3);self.assertFalse(c['nomad_goal_stop'])
        self.assertEqual(c['checkpoint']['axis'],1);self.assertAlmostEqual(c['checkpoint']['threshold_m'],1.2)
        self.assertEqual(c['sdf_registration']['registered_bounds_m'],[-4.,-3.5,8.,6.2])
        self.assertIs(metrics.audit.__code__,j0metrics.audit.__code__)
        self.assertIs(campaign.execute.__code__,j0campaign.execute.__code__)
        self.assertEqual(campaign.execute.__globals__['__package__'],'nomad_h1v3')
        from nomad_j0.config import protocol as j0_protocol
        self.assertEqual(p['execution'],j0_protocol()['execution'])
        self.assertEqual(p['screening'],j0_protocol()['screening'])

    def test_actual_four_launch_arguments_no_process(self):
        plan=campaign.jobs(config.RUN_ROOT);self.assertEqual(len(plan),4)
        self.assertEqual([(j['delay'],j['index']) for j in plan],[(0.,221),(0.,222),(.75,221),(.75,222)])
        for j in plan:
            a=launch.parser().parse_args(j['argv'][4:]+['--dry-run']);p=launch.build(a)
            self.assertIn(str(config.HERE/'simulator.py'),p['simulator']);self.assertIn('nomad_isaac.worker',p['worker'])
            self.assertIn('H1-v3',p['simulator']);self.assertEqual(p['simulations_started'],0)

    def test_same_j0_selection_and_report_table(self):
        records=[dict(j,technical_validation='PASS',classification='SUCCESS',success=True,collision=False,wall_intrusion=False,
            timeout=False,checkpoint_time_s=10.+j['delay'],goal_time_s=20.,checkpoint_threshold_m=1.2) for j in config.order()]
        self.assertEqual(report.selection(records)['selected_scenes'],['H1-v3'])
        records[-1]['checkpoint_time_s']=9.25
        self.assertEqual(report.selection(records)['selected_scenes'],[])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'metrics').mkdir()
            for n,r in enumerate(records):(root/'metrics'/f'{n}.json').write_text(json.dumps(r))
            doc=report.generate(root,root/'out',root/'report.md')
            self.assertIn('0s 성공2/2',doc.read_text());self.assertEqual(json.loads((root/'out/decision.json').read_text())['status'],'COMPLETE')

if __name__=='__main__':unittest.main()
