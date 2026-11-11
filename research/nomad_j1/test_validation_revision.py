import ast
import copy
import inspect
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from nomad_isaac.common import sha256_file
from . import metrics,config,report,statistics,campaign,interim_analysis,reassess
from .validation_revision import ALLOWED
from .postprocess_guard import is_live_command,assert_stopped

BASE='ff6fd30'

def frozen_file(path):return subprocess.check_output(['git','show',f'{BASE}:{path}'],cwd=config.ROOT,text=True)

class Tests(unittest.TestCase):
    def test_mask_prefix_d_only_and_d0_NA(self):
        target=dict(d=4,H_old=5,target_local_xy_m=np.arange(10,dtype=float).reshape(5,2).tolist())
        a=np.zeros((8,8,2));a[:,:4]=np.asarray(target['target_local_xy_m'])[:4]
        with self.assertRaises(ValueError):a[:,:4]-np.asarray(target['target_local_xy_m'])[None]
        np.testing.assert_array_equal(metrics.rtc_prefix_errors(a,target),np.zeros((8,4)))
        self.assertIsNone(metrics.rtc_prefix_errors(a,dict(target,d=0)))
        with self.assertRaises(AssertionError):metrics.rtc_prefix_errors(a,dict(target,d=6))

    def test_saved_LC231_RTC_run_full_audit_and_frozen_outcomes(self):
        run=config.ROOT.parent/'artifacts/isaac6/j1_01/main/LC_231_D750_RTC-hard/attempt1'
        inputs=[run/f for f in ('summary.json','controller.jsonl','requests.jsonl','agent_trajectory.csv')]
        before={str(f):sha256_file(f) for f in inputs}
        raw=metrics.base_audit(run);fixed=metrics.audit(run)
        self.assertEqual(fixed['technical_validation'],'PASS')
        for name in ('success','collision','wall_intrusion','timeout','classification','goal_time_s','checkpoint_time_s','checkpoint_tick',
                     'checkpoint_threshold_m','minimum_clearance_m','duration_s'):
            self.assertEqual(fixed[name],raw[name],name)
        self.assertEqual(fixed['rtc_prefix_validation'],'FIRST_D_ONLY');self.assertLessEqual(fixed['rtc_prefix_max_m'],1e-6)
        self.assertGreater(fixed['rtc_hard_prefix_point_count'],0)
        self.assertEqual(before,{str(f):sha256_file(f) for f in inputs})
        requests=[json.loads(x) for x in (run/'requests.jsonl').read_text().splitlines()]
        self.assertTrue(any(0<q['rtc_target']['d']<q['rtc_target']['H_old'] for q in requests))

    def test_protocol_runtime_statistics_and_schedule_unchanged(self):
        p=config.verify();self.assertEqual(sha256_file(config.HERE/'protocol.json'),'2dbe6817a6751d04971453222baeccb971a4a0f24db6fc40ed1e4a71ec701586')
        for file,h in p['source_sha256'].items():
            if file not in ALLOWED:self.assertEqual(sha256_file(config.ROOT/file),h,file)
        before=ast.parse(frozen_file('research/nomad_j1/config.py'));after=ast.parse((config.HERE/'config.py').read_text())
        functions=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
        a,b=functions(before),functions(after)
        for name in a:
            if name!='verify':self.assertEqual(a[name],b[name],name)
        marker="            state['stage']='REPORT';save()"
        self.assertEqual(frozen_file('research/nomad_j1/campaign.py').split(marker)[0],(config.HERE/'campaign.py').read_text().split(marker)[0])
        old_ns=dict(__name__='nomad_j1._old_metrics',__package__='nomad_j1',__file__=metrics.__file__)
        exec(compile(frozen_file('research/nomad_j1/metrics.py'),'<frozen metrics>','exec'),old_ns)
        self.assertEqual(metrics.base_audit.__code__.co_code,old_ns['base_audit'].__code__.co_code)
        self.assertEqual(metrics.base_audit.__code__.co_consts,old_ns['base_audit'].__code__.co_consts)
        self.assertIn('from .metrics import audit',inspect.getsource(campaign.execute))

    def test_one_shot_process_guard_no_real_process_poll(self):
        self.assertTrue(is_live_command(['python','-m','nomad_j1.campaign']))
        self.assertTrue(is_live_command(['python','-m','nomad_phase8.worker','--socket','/x/artifacts/isaac6/j1_01/main/a/ipc.sock']))
        self.assertFalse(is_live_command(['python','-m','nomad_j1.reassess']))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'987654321').mkdir()
            (root/'987654321/cmdline').write_bytes(b'python\0-m\0nomad_j1.campaign\0')
            with self.assertRaisesRegex(RuntimeError,'still running'):assert_stopped(root)

    def test_exploratory_checkpoint_and_full_horizons(self):
        t=np.arange(73)/72;v=np.r_[0.,np.full(36,.1),np.zeros(36)];xy=np.c_[np.r_[0.,np.cumsum(v[1:]/72)],np.zeros(73)]
        controls=[dict(simulation_time_s=0.,valid=True,pure_pursuit={'stop_reason':None},stage2={'v_target_m_s':.3}),
                  dict(simulation_time_s=.5,valid=True,pure_pursuit={'stop_reason':None},stage2={'v_target_m_s':.1})]
        cp=interim_analysis.horizon_metrics(t,xy,v,controls,36);full=interim_analysis.horizon_metrics(t,xy,v,controls,72)
        self.assertAlmostEqual(cp['mean_speed_m_s'],.1);self.assertEqual(cp['stop_s'],0.)
        self.assertAlmostEqual(full['distance_m'],.05);self.assertAlmostEqual(full['stop_s'],.5)
        self.assertAlmostEqual(full['curvature_slow_fraction_active'],.5)

    def test_primary_table_has_both_current_tests_and_interim_label(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'metrics').mkdir();rr=[]
            for j in config.order()[:15]:
                r=dict(j,key=f"{j['scene']}_{j['index']}_{j['method']}",technical_validation='PASS',success=True,collision=False,wall_intrusion=False,
                    timeout=False,goal_time_s=20.,checkpoint_time_s=10.,graph_applied=0,solve_times_s=[],ec_checks=0,ec_rejected=0)
                rr.append(r);(root/'metrics'/(r['key']+'.json')).write_text(json.dumps(r))
            expected=statistics.primary(rr)
            doc=report.generate(root,root/'out',root/'report.md',include_exploratory=False)
            self.assertIn('중간 결과, 판정 보류',doc.read_text());self.assertIn('OURS_only_failure',doc.read_text())
            got=json.loads((root/'out/decision.json').read_text())
            self.assertEqual(expected['primary'],got['primary'])

    def test_reassessment_archive_nonRTC_hashes_and_idempotence(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'metrics').mkdir();(root/'attempt_metrics').mkdir();out=root/'report'
            for j in config.order()[:15]:
                key=f"{j['scene']}_{j['index']}_{j['method']}";run=root/'raw'/key;run.mkdir(parents=True)
                (run/'summary.json').write_text('{}');(run/'launch_complete.json').write_text('{"exit_code":0}')
                r=dict(j,key=key,output=str(run),attempt=1,technical_validation='FAIL' if j['method']=='RTC-hard' else 'PASS',
                    classification='TECHNICAL_FAILURE' if j['method']=='RTC-hard' else 'SUCCESS',error='prefix broadcast' if j['method']=='RTC-hard' else None)
                (root/'metrics'/(key+'.json')).write_text(json.dumps(r));(root/'attempt_metrics'/(key+'.json')).write_text(json.dumps(r))
            (root/'state.json').write_text(json.dumps(dict(status='PARTIAL',stage='REPORT')))
            nonrtc=reassess.metric_hashes(root,True)
            with (patch.object(reassess,'OUT',out),patch.object(metrics,'audit',return_value=dict(technical_validation='PASS',classification='SUCCESS')) as audit,
                  patch.object(report,'generate',return_value=root/'report.md'),patch.object(report,'publish_report')):
                reassess.process(root,False);self.assertEqual(audit.call_count,3)
                reassess.process(root,False);self.assertEqual(audit.call_count,3)
            self.assertEqual(nonrtc,reassess.metric_hashes(root,True))
            self.assertEqual(len(list((root/'audit_revisions').glob('*/original_metrics/*.json'))),3)

if __name__=='__main__':unittest.main()
