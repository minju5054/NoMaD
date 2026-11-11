"""Synthetic-only calibration/replay tests; no saved experiment is evaluated."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import nomad_hmm_replay.test_replay as fixture_module
from nomad_hmm_replay.filter import Replay
from . import data,calibration,filter,replay,report

class Tests(unittest.TestCase):
    def part(self):
        h=[{} for _ in range(10)];h[4]={'0':3,'1':1};h[9]={'4':2}
        return dict(uid='CAL',phase='Phase47-C',histogram=h,residuals=[-.2,.3,.8],inference_count=3,missing_events=[])
    def test_histogram_fixed_bins_laplace_outside_and_normalization(self):
        m=calibration.fit([self.part()]);self.assertEqual(m['distance_bin_count'],7)
        p=np.array(m['probabilities']);np.testing.assert_allclose(p.sum(axis=1),1.)
        self.assertAlmostEqual(p[4,1],4/11);self.assertEqual(m['laplace'],1.)
        self.assertEqual(calibration.offset_bin(-5),9);self.assertEqual(calibration.offset_bin(5),9)
        self.assertEqual(calibration.offset_bin(-4),0);self.assertEqual(calibration.offset_bin(4),8)
        self.assertAlmostEqual(m['sigma2'],np.var([-.2,.3,.8],ddof=0))
    def test_OBS_product_uses_all_window_values_and_no_eval_range_growth(self):
        m=calibration.fit([self.part()]);saved=json.dumps(m,sort_keys=True)
        ids=np.array([0,1]);d=np.array([.1,999.]);got=calibration.obs_log_emission(m,ids,d);p=np.array(m['probabilities'])
        self.assertAlmostEqual(got[0],np.log(p[4,1])+np.log(p[5,-1]))
        self.assertAlmostEqual(got[1],np.log(p[3,1])+np.log(p[4,-1]))
        self.assertEqual(json.dumps(m,sort_keys=True),saved)
    def test_SIGN_tangent_and_logged_MAP_calibration(self):
        xy=np.array([[0,0],[1,0],[1,1],[1,2]],float);t=data.tangents(xy)
        np.testing.assert_allclose(t[1],[2**-.5,2**-.5]);np.testing.assert_array_equal(t[2],[0,1])
        events=[dict(id=0,odometry_xy=[0,0],true_node=0,logged_map=2,ids=[0],distances=[0]),
                dict(id=1,odometry_xy=[1,0],true_node=1,logged_map=2,ids=[1],distances=[0])]
        item=dict(split='CAL',uid='CAL',phase='Phase47-C',input_sha256={})
        with patch.object(calibration,'load',return_value=(events,xy,1.,None,[])):r=calibration.contributions(item)
        # Wrong logged MAP2 points +y; using true MAP0 would yield residual0.
        self.assertEqual(r['residuals'],[1.])
        with self.assertRaises(AssertionError):calibration.contributions(dict(split='EVAL'))
        with self.assertRaises(AssertionError):replay.evaluate(dict(split='CAL'),{})
    def test_Gaussian_signed_progress_and_global_row_normalization(self):
        forward=filter.gaussian_transition(7,1.,.2);backward=filter.gaussian_transition(7,-1.,.2)
        np.testing.assert_allclose(np.exp(forward).sum(axis=1),1.)
        self.assertEqual(int(np.argmax(forward[3])),4);self.assertEqual(int(np.argmax(backward[3])),2)
        model=calibration.fit([self.part()]);f=filter.Filter(np.c_[np.arange(7),np.zeros(7)],1.,'SIGN',model)
        f.step(list(range(7)),[100,100,0,100,100,100,100],[2,0],0.)
        _,detail=f.step(list(range(7)),[100,100,0,100,100,100,100],[1.5,0],.5)
        self.assertEqual(detail['transition_mean_nodes'],-.5)
    def test_HMM0_and_NET_delegate_to_original(self):
        xy=np.c_[np.arange(7)*.4,np.zeros(7)];m=calibration.fit([self.part()])
        for variant in ('HMM0','NET'):
            f=filter.Filter(xy,.4,variant,m);base=Replay(7,.4,variant)
            for pos,total in [([0,0],0.),([.1,0],.1),([0,0],.2)]:
                a,ad=f.step([0,1,2,3],[0,2,4,5],pos,total);b,bd=base.step([0,1,2,3],[0,2,4,5],pos,total)
                self.assertEqual(a,b);self.assertEqual(ad,bd)
    def test_variance_no_tuned_floor(self):
        p=self.part();p['residuals']=[1.,1.]
        with self.assertRaisesRegex(ValueError,'Zero/nonfinite'):calibration.fit([p])
    def test_goal_delay_censor_and_negative_separate(self):
        rows=[]
        map_by={'HMM0':[0,0,0,0,0],'NET':[4,0,0,0,4],'OBS':[0,0,4,0,0],'SIGN':[4,0,0,0,0],'OBS+SIGN':[0,0,0,4,0]}
        for v in filter.VARIANTS:
            for i,identifier in enumerate(range(8,13)):
                rows.append(dict(variant=v,inference_id=identifier,true_node=4 if identifier>=10 else 3,goal_node=4,map_node=map_by[v][i],uid='R',phase='Phase57-P',scene='H2',seed=227,method='MIN'))
        out={x['variant']:x for x in replay.delays(rows)}
        self.assertTrue(out['HMM0']['right_censored_after_true']);self.assertEqual(out['NET']['delay_after_true_inferences'],2)
        self.assertEqual(out['NET']['signed_first_MAP_delay'],-2);self.assertTrue(out['SIGN']['right_censored_after_true']);self.assertTrue(out['SIGN']['early_negative_delay'])
        stats=report.delay_stats(list(out.values()));self.assertEqual(stats['right_censored_runs'],2);self.assertEqual(stats['negative_early_goal_runs'],2)
        self.assertEqual(list(stats).index('right_censored_runs'),list(stats).index('delay_median_inferences')+1)
    def test_synthetic_end_to_end_calibration_then_eval_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);caldir=root/'cal';caldir.mkdir();evaldir=root/'eval';evaldir.mkdir()
            a=fixture_module.Tests().fixture(caldir);a.update(split='CAL',phase='Phase47-C',uid='Phase47-C/CAL')
            b=fixture_module.Tests().fixture(evaldir);b.update(split='EVAL',phase='Phase57-P',uid='Phase57-P/EVAL',seed=227)
            part=calibration.contributions(a);model=calibration.fit([part]);before=copy.deepcopy(model)
            evaluated=replay.evaluate(b,model);self.assertEqual(len(evaluated['rows']),15);self.assertEqual(model,before)
            h=replay.verify();part['fingerprint']=replay.fingerprint(a,h)
            model.update(protocol_sha256=h,frozen_at_utc='SYNTHETIC_BEFORE_EVAL',frozen_before_evaluation=True,training_fingerprint='synthetic')
            run=root/'run';(run/'cal_cache').mkdir(parents=True);(run/'eval_cache').mkdir()
            (run/'calibration.json').write_text(json.dumps(model));model_hash=replay.sha256_file(run/'calibration.json')
            evaluated.update(fingerprint=replay.fingerprint(b,h,model_hash),input_sha256=b['input_sha256'])
            replay.cache_path(run/'cal_cache',a).write_text(json.dumps(part));replay.cache_path(run/'eval_cache',b).write_text(json.dumps(evaluated))
            coverage=[dict(split='CAL',phase='Phase47-C',status='AVAILABLE'),dict(split='EVAL',phase='Phase57-P',status='AVAILABLE')]
            (run/'inventory.json').write_text(json.dumps(dict(protocol_sha256=h,groups={'CAL':[a],'EVAL':[b]},coverage=coverage)))
            doc=report.generate(run,root/'out',root/'report.md');text=doc.read_text()
            self.assertIn('OBS+SIGN',text);self.assertIn('right_censored_runs',text)
            limits=text.split('## 한계\n\n')[1].strip().splitlines();self.assertEqual(len(limits),2)
            import csv
            with (root/'out/summary.csv').open() as stream:summary=list(csv.DictReader(stream))
            self.assertEqual(len(summary),5);self.assertTrue(all(int(x['inferences'])==3 for x in summary))
    def test_eval_input_change_does_not_change_calibration_fingerprint(self):
        a=dict(input_sha256={'cal':'A'});b=dict(input_sha256={'eval':'B'})
        cal=replay.fingerprint(a,'p');ev=replay.fingerprint(b,'p','m');b['input_sha256']['eval']='C'
        self.assertEqual(cal,replay.fingerprint(a,'p'));self.assertNotEqual(ev,replay.fingerprint(b,'p','m'))
if __name__=='__main__':unittest.main()
