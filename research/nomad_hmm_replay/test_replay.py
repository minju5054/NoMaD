"""Synthetic filter/restart/report tests; never replay existing run inputs here."""
import csv,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from nomad_phase42l.filter import WindowHMM
from .filter import Replay,predict,VARIANTS
from . import data,replay,report

class Tests(unittest.TestCase):
    def test_HMM0_matches_frozen_forward_function(self):
        f=Replay(7,.4,'HMM0');old=WindowHMM(7,.4);total=0.
        for i,(ids,values,move) in enumerate([([0,1,2],[0,2,4],0),([0,1,2,3],[3,1,0,2],.1),([2,3,4],[2,1,0],.9),([5,6],[3,0],0)]):
            total+=move;n,d=f.step(ids,values,[i*.1,0],total);on,od=old.step(ids,values,move)
            self.assertEqual(n,on)
            for k,v in od.items():self.assertEqual(d[k],v)
            np.testing.assert_array_equal(f.filter.logp,old.logp)
    def test_NET_zero_width_and_self_transition(self):
        f=Replay(5,1.,'NET');f.step(range(5),[0,20,30,40,50],[0,0],0)
        f.filter.logp=np.array([0.,-np.inf,-np.inf,-np.inf,-np.inf])
        n,d=f.step(range(5),[10,0,0,0,0],[.1,0],5.)
        self.assertEqual(d['transition_half_width'],0);self.assertEqual(n,0)
        self.assertAlmostEqual(d['entry_displacement_m'],.1);self.assertEqual(d['odometry_travel_m'],5.)
        p=predict(np.array([-np.inf,0.,-np.inf]),3,0);self.assertEqual(p[1],0.);self.assertTrue(np.isneginf(p[[0,2]]).all())
    def test_entry_resets_on_change_memory_preserves_first_visit(self):
        f=Replay(3,1.,'NET+MEM');f.step(range(3),[0,100,100],[0,0],0)
        n,d=f.step(range(3),[100,0,100],[.8,0],.8);self.assertEqual(n,1);np.testing.assert_array_equal(f.entry_position,[.8,0])
        n,d=f.step(range(3),[0,100,100],[.2,0],1.4);self.assertEqual(n,0)
        np.testing.assert_allclose(f.entry_position,[.2,0]);np.testing.assert_array_equal(f.visits[0],[0.,0.]);self.assertFalse(d['first_visit'])
        n,d=f.step(range(3),[0,100,100],[.4,0],1.6)
        self.assertAlmostEqual(d['memory_log_factors'][0],-.08);self.assertEqual(d['memory_log_factors'][2],0.)
        self.assertEqual(d['transition_half_width'],0)
    def test_round_half_to_even_and_no_path_distance_width(self):
        f=Replay(10,1.,'NET');f.step(range(10),[0]+[100]*9,[0,0],0)
        _,d=f.step(range(10),[0]+[100]*9,[.5,0],2.);self.assertEqual(d['transition_half_width'],0)
        _,d=f.step(range(10),[0]+[100]*9,[1.5,0],4.);self.assertEqual(d['transition_half_width'],2)
    def test_fixed_window_reset_and_outside_counters(self):
        f=Replay(8,1.,'NET');f.step([0,1],[0,10],[0,0],0)
        n,d=f.step([6,7],[1,0],[0,0],0)
        self.assertTrue(d['window_reset']);self.assertTrue(d['previous_map_outside_window']);self.assertTrue(d['predicted_map_outside_window'])
        self.assertFalse(d['posterior_map_outside_window']);self.assertEqual(n,7)
    def test_memory_log_domain_normalization(self):
        f=Replay(3,.2,'NET+MEM');f.step([0,1,2],[0,10,20],[0,0],0)
        _,d=f.step([0,1,2],[0,1,2],[10,10],15)
        self.assertTrue(np.isfinite(np.exp(f.filter.logp)).all());self.assertAlmostEqual(np.exp(f.filter.logp).sum(),1.)
        self.assertEqual(d['ell_m'],.2);self.assertEqual(d['memory_log_factors'][1],0.)

    def fixture(self,tmp):
        root=Path(tmp);folder=root/'attempt1';(folder/'model').mkdir(parents=True)
        nodes=root/'nodes.json';nodes.write_text(json.dumps(dict(nodes=[dict(node_id=i,world_pose=[i,0,0]) for i in range(3)])))
        (folder/'scenario.json').write_text(json.dumps(dict(topomap_manifest=str(nodes),phase43p=True)))
        (folder/'summary.json').write_text(json.dumps(dict(delivery_delay=dict(configured_additional_s=.75))))
        poses=[[0.,0.,0.],[.1,0.,0.],[.8,0.,0.]];times=[0.,1/72,2/72];dist=[[0,4,8],[0,3,8],[4,0,2]];old=WindowHMM(3,1.);inferences=[];truth=[0,0,1]
        for i in range(3):
            total=poses[i][0];delta=0. if not i else total-poses[i-1][0];n,d=old.step([0,1,2],dist[i],delta)
            inferences.append(dict(id=i,observation_sim_s=times[i],observation_pose=poses[i],hmm_odometry_tick=i,hmm_odometry_total_m=total,
                topomap=dict(candidate_ids=[0,1,2],distances=dist[i],goal_node=2,closest_node=n,hmm=d)))
        (folder/'model/inference.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in inferences))
        (folder/'received.jsonl').write_text(''.join(json.dumps(dict(id=i,latched_sim_s=times[i],terminal_unapplied=i==2))+'\n' for i in range(3)))
        with (folder/'agent_trajectory.csv').open('w') as f:
            w=csv.writer(f);w.writerow(['simulation_time_s','x_m','y_m','yaw_rad']);w.writerows([[times[i],*poses[i]] for i in range(3)])
        (folder/'declared_arrival.json').write_text(json.dumps(dict(id=2,simulation_time_s=times[2],goal_node=2)))
        row=dict(output=str(folder),technical_validation='PASS',classification='WRONG_STOP',wrong_stop=True,success=False,stop_distance_m=1.2,
            node_errors=[dict(inference_id=i,true_node=truth[i]) for i in range(3)])
        metric=root/'metric.json';metric.write_text(json.dumps(row))
        files=[metric,*[p for p in folder.rglob('*') if p.is_file()],nodes]
        return dict(uid='Synthetic/SLW_221_CUT',key='SLW_221_CUT',phase='Synthetic',scene='SLW',seed=221,method='CUT',folder=str(folder),row=row,metric=str(metric),input_sha256={str(f):data.sha(f) for f in files})
    def test_saved_input_plumbing_and_declaration_ID(self):
        with tempfile.TemporaryDirectory() as tmp:
            item=self.fixture(tmp);result=replay.process(item)
            self.assertEqual(result['input_events'],3);self.assertEqual(len(result['rows']),9)
            self.assertEqual(len(result['declarations']),3)
            self.assertTrue(all(r['declaration_id']==2 and r['status']=='MATCHED' for r in result['declarations']))
            hmm=[r for r in result['rows'] if r['variant']=='HMM0'];self.assertTrue(all(r['map_node']==r['logged_map'] for r in hmm))
            self.assertTrue(all(r['valid_delivery'] for r in result['rows'] if r['inference_id']==2))
            self.assertFalse(any(r['terminal_drained'] for r in result['rows']));json.dumps(result,allow_nan=False)
    def test_cache_fingerprint_changes_with_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            item=self.fixture(tmp);a=replay.fingerprint(item,'protocol');item['input_sha256']['new']='changed'
            self.assertNotEqual(a,replay.fingerprint(item,'protocol'))
    def test_report_cached_synthetic_rows_and_false_goal_definition(self):
        with tempfile.TemporaryDirectory() as tmp:
            item=self.fixture(tmp);result=replay.process(item);h=replay.verify();result.update(fingerprint=replay.fingerprint(item,h),input_sha256=item['input_sha256'])
            root=Path(tmp)/'replay';(root/'cache').mkdir(parents=True)
            key=__import__('hashlib').sha256(item['uid'].encode()).hexdigest()[:20]+'.json'
            (root/'cache'/key).write_text(json.dumps(result))
            (root/'inventory.json').write_text(json.dumps(dict(items=[item],coverage=[dict(uid=item['uid'],phase='Synthetic',status='AVAILABLE')],protocol_sha256=h)))
            doc=report.generate(root,root/'out',root/'report.md')
            self.assertIn('NET+MEM',doc.read_text());self.assertIn('would_declare',doc.read_text())
            self.assertEqual(json.loads((root/'out/reproduction.json').read_text())['map_match_rate'],1.)
            self.assertEqual(json.loads((root/'out/status.json').read_text())['replayed_runs'],1)
    def test_discovery_skips_unfinished_attempt_and_nonHMM(self):
        with tempfile.TemporaryDirectory() as tmp:
            item=self.fixture(tmp);root=Path(tmp);(root/'metrics').mkdir()
            (root/'metrics/SLW_221_CUT.json').write_text(json.dumps(item['row']))
            protocol=root/'source_protocol.json';protocol.write_text(json.dumps(dict(main_order=[dict(scene='SLW',index=221,method='CUT'),dict(scene='SLW',index=222,method='CUT'),dict(scene='SLW',index=223,method='NOMAD_RAW')])))
            with patch.object(data,'SOURCES',(('Synthetic',str(protocol),str(root)),)):
                items,coverage=data.discover()
            self.assertEqual(len(items),1);self.assertEqual(len(coverage),2);self.assertEqual(coverage[1]['status'],'NOT_FINALIZED_OR_NOT_RUN')
if __name__=='__main__':unittest.main()
