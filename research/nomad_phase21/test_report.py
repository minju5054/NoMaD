import tempfile,unittest
from pathlib import Path
from .config import METHODS,protocol
from .report import eligibility,summary_rows,labels,pairs,render

class Tests(unittest.TestCase):
    def records(self):
        return [dict(scene=s,index=i,method=m,technical_validation='PASS',classification='SUCCESS',success=True,passed_box=True,passage_censored=False,passage_time_capped_s=20.,goal_time_s=50.,collision=False,corridor=False,path_curvature=[],output='/missing') for s in ('L2','L2A') for i in protocol()['indices'] for m in METHODS]
    def test_exclusion_and_reference(self):
        r=self.records();r[0]['technical_validation']='FAIL';inc,exc=eligibility(r);self.assertEqual(len(exc),0)
        r[1]['technical_validation']='FAIL';inc,exc=eligibility(r);self.assertEqual(len(exc),1);self.assertNotIn(('L2',protocol()['indices'][0]),inc)
    def test_scene_threshold_and_astar(self):
        r=self.records()
        for x in r:
            if x['method'] in ('B1_SAFE_TE','B2_SAFE_RTC','B3_M1') and x['index']<113:x['success']=False
            if x['method']=='M3_GRAPH':x['passage_time_capped_s']=19.
        inc,_=eligibility(r);v=labels(summary_rows(r,inc));self.assertEqual(v['final'],'GRAPH_BEST');self.assertEqual(v['scenes'][2]['label'],'GRAPH_BEST')
        for x in r:
            if x['method']=='M3_GRAPH':x['collision']=True
        v=labels(summary_rows(r,inc));self.assertEqual(v['final'],'GRAPH_BEATS_HEURISTICS')
    def test_report_and_empty_panels(self):
        r=self.records()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);v=render(r,p/'out',p/'report.md',True);self.assertEqual(v['final'],'NO_GRAPH_ADVANTAGE');self.assertTrue((p/'out/heldout_seed.png').exists());self.assertIn('Phase18 handoff 규칙',(p/'report.md').read_text())
if __name__=='__main__':unittest.main()
