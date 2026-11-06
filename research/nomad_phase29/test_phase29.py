import copy,io,json,tempfile,time,unittest
from pathlib import Path
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase15.depth_sdf import DepthSDF
from nomad_phase15b.depth import Snapshot
from nomad_phase17.graph import ClearanceGraph
from nomad_phase28.runtime import NAExecution
from nomad_phase3_stage2.execution import decision
from .paths import smooth,certificate
from .worker import solve
from .runtime import PathExecution
from .report import dev_gate,confirm_decision
from .config import protocol,runtime_config

def field():return Snapshot(DepthSDF([-1,-2,3,2]),dict(frame_id=0,sim_s=0.,file='unit'))
def job():return dict(job_id=0,id=1,path=np.c_[np.linspace(.08,.8,8),np.zeros(8)].tolist(),boundary=[0.,0.,0.],previous_vw=[.2,0.],previous_xy=None)

class Tests(unittest.TestCase):
    def test_smoothing_frozen_strength_and_endpoints(self):
        p=np.array([[0.,0.],[.2,.1],[.4,-.1],[.6,0.]])
        s,r=smooth(p,[.1,0.,0.],field());self.assertTrue(r['applied']);np.testing.assert_array_equal(s[0],[.1,0]);np.testing.assert_array_equal(s[-1],p[-1]);self.assertEqual(s.shape,(11,2));self.assertEqual(r['attempts'][0]['strength'],.5);json.dumps(r)
    def test_certificate_fallback(self):
        f=field();f.occupied.flags.writeable=True;f.occupied[:]=True;f.occupied.flags.writeable=False
        p=np.c_[np.linspace(.08,.8,8),np.zeros(8)];s,r=smooth(p,[0,0,0],f)
        self.assertFalse(r['applied']);np.testing.assert_array_equal(s,p);self.assertEqual(len(r['attempts']),4)
    def test_g18_is_frozen_clearance_graph(self):
        r=solve(job(),field());json.dumps(r);self.assertIn('solver',r)
        g=ClearanceGraph(job()['path'],job()['boundary'],job()['previous_vw'],field(),None)
        q,s=g.solve();np.testing.assert_allclose(r['poses'],q,rtol=0,atol=1e-9);self.assertEqual(r['accepted'],s['feasible'])
    def test_initialization_rejection_and_old_decision(self):
        j=job();j['previous_vw']=[0.,0.];r=solve(j,field());self.assertTrue(r['initialization_rejected']);json.dumps(r)
        self.assertEqual(decision(r,1,True)[0],'INITIALIZATION_REJECTED');self.assertEqual(decision(r,2,True)[0],'SUPERSEDED')
        r['worker_end_ns']=r['worker_start_ns']+500000001;self.assertEqual(decision(r,1,True)[0],'STALE')
    def test_all_log_records_standard_json_and_raw_install(self):
        x=object.__new__(PathExecution);x.path_log=io.StringIO();x.path_method='SM';x.path_sequence=0;x.snapshot=field();x.last_command=[.2,0.];x.plant=SimpleNamespace(actual_w=0.)
        c=SimpleNamespace(pose=np.array([0.,0.,0.]));refresh=dict(simulation_time_s=np.float64(1.))
        with patch.object(NAExecution,'new_path') as install:x.new_path(np.array(job()['path']),c,refresh,1,'SAFE');self.assertEqual(install.call_count,1)
        x.path_record('ARRAY',a=np.array([1,2]),b=np.bool_(True),i=np.int64(2))
        for line in x.path_log.getvalue().splitlines():json.dumps(json.loads(line))
    def test_matrix_and_config(self):
        p=protocol();self.assertEqual([len(p[k]) for k in ('smoke','dev','confirm')],[2,20,60])
        for s in p['scenes']:
            for i in range(201,206):
                for m in p['methods']:
                    c=runtime_config(m,i,90,s);self.assertEqual(c['seed_offset'],10000*i);self.assertEqual(c['timeout_sim_s'],90);self.assertEqual(c['goal_tolerance_m'],.3)
    def test_gate_and_labels(self):
        p=protocol();old=[dict(method='C0-NA',success=True,collision=False) for _ in range(10)]
        rows=[dict(r,technical_validation='PASS',success=True,collision=False,path_jobs=10,path_applied=7) for r in p['dev']]
        self.assertTrue(dev_gate(rows,old)['passed']);rows[1]['path_applied']=6;self.assertFalse(dev_gate(rows,old)['passed'])
        rr=[dict(r,technical_validation='PASS',success=True,collision=r['method']=='C0-NA',goal_time_s=10. if r['method']=='G18' else 12.,minimum_clearance_m=.3 if r['method']=='G18' else .2) for r in p['confirm']]
        self.assertEqual(confirm_decision(rr)['label'],'G18_SUPPORTED')
        for r in rr:
            if r['method']=='C0':r['goal_time_s']=9.
        self.assertEqual(confirm_decision(rr)['label'],'G18_PARTIAL')
        for r in rr:r['collision']=False
        self.assertEqual(confirm_decision(rr)['label'],'G18_NOT_SUPPORTED');self.assertEqual(confirm_decision(rr[:-1])['label'],'PARTIAL')
    def test_normal_only_and_fallback_rule_shared(self):
        self.assertIs(PathExecution.start_detour,NAExecution.start_detour);self.assertIs(PathExecution.use_fallback,NAExecution.use_fallback)
        x=object.__new__(PathExecution)
        with patch.object(NAExecution,'new_path') as original:x.new_path([],None,None,0,'DETOUR');original.assert_called_once()

if __name__=='__main__':unittest.main()
