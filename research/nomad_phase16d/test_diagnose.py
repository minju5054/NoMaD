import json,unittest
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT
from .diagnose import classify_A,choose_escape,select_rule,solely_certificate_rejected,B_label,Inputs,load_run,measure_event,stop_chains

class Tests(unittest.TestCase):
    def test_A_priority_and_boundaries(self):
        self.assertEqual(classify_A(7,0,9,10),'MARGINAL_DEADLOCK')
        self.assertEqual(classify_A(0,7,9,10),'TRUE_BLOCK')
        self.assertEqual(classify_A(1,2,7,10),'NEAR_START_POSE')
        self.assertEqual(classify_A(1,2,6,10),'OTHER')
    def test_depth_only_candidates_and_ties(self):
        d=[.009,.012,.012,-.004];length=[1.,.3,.5,2.]
        r=choose_escape(d,length,.020)
        self.assertIsNone(r['E0']);self.assertIsNone(r['E1']);self.assertEqual(r['E2'],2);self.assertEqual(r['E3'],1)
        self.assertEqual(choose_escape([-.01,-.02],[1.,2.],-.01)['E1'],0) # negative threshold is not clamped
    def test_selection_and_insufficient(self):
        rows=[dict(candidate=x,penetrating_selections=0,escape_fraction=.4) for x in ('E0','E1','E2','E3')];rows[0]['escape_fraction']=0
        s=select_rule(rows);self.assertEqual(s['candidate'],'E1');self.assertEqual(s['label'],'INSUFFICIENT')
        rows[1]['penetrating_selections']=1;rows[2]['escape_fraction']=.6
        s=select_rule(rows);self.assertEqual(s['candidate'],'E2');self.assertEqual(s['label'],'OFFLINE_SELECTED')
    def test_B_certificate_not_nonconvergence_or_stale(self):
        r=dict(disposition='CONSTRAINT_FAILED',solver=dict(success=True,constraints_satisfied=True,exact_certificate_pass=False))
        self.assertTrue(solely_certificate_rejected(r));r['solver']['success']=False;self.assertFalse(solely_certificate_rejected(r))
        safe=dict(entered_radius=True,closest_oracle_clearance_m=.1)
        self.assertEqual(B_label(True,safe,.05,True,[safe,safe]),'GRAPH_APPROACH_CLOSER')
        self.assertEqual(B_label(False,safe,.05,True,[safe,safe]),'CERTIFICATE_REVERT')
        self.assertEqual(B_label(False,safe,.05,False,[safe,dict(entered_radius=False)]),'DIFFERENT_ROUTE')
    def test_saved_STOP_WAIT_reproduces_native_depth_clearances(self):
        records=json.loads((ROOT/'research/results/phase16/runs.json').read_text())
        r=next(x for x in records if x['scene']=='CL' and x['index']==55 and x['method']=='FRESHEST-SAFE+GRAPH-depth');r['split']='main'
        inputs=Inputs();d=load_run(r,inputs);e=next(x for x in d['events'] if x['phase16']['fallback_mode']=='STOP_WAIT')
        measured,_=measure_event(d,e,inputs)
        np.testing.assert_allclose(measured['depth_clearances_m'],[x['clearance_m'] for x in e['phase16']['selection']['candidates']],atol=1e-12,rtol=0)
        self.assertEqual(len(measured['oracle_clearances_m']),8);self.assertTrue(all(x<.025 for x in measured['depth_clearances_m']))
        self.assertTrue(stop_chains(d['events']))

if __name__=='__main__':unittest.main()
