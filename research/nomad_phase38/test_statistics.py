import json,unittest
from .statistics import holm,analyze,paired,bootstrap_pairs

class StatisticsTests(unittest.TestCase):
    def test_holm_known_family(self):
        self.assertEqual(holm([.01,.04,.03]),[.03,.06,.06])
    def test_paired_missing_excluded_and_json(self):
        methods=('OURS','NOMAD_RAW','TE','RTC','CARE','TE+EC','RTC+EC','OURS-DETOUR','ASTAR+EC')
        rows=[dict(method=m,scene=s,index=i,success=m=='OURS',collision=False,goal_time_s=30. if m=='OURS' else None,technical_validation='PASS')
            for m in methods for s in ('SLW','H1') for i in (217,218)]
        rows.append(dict(method='OURS',scene='L2',index=217,success=False,technical_validation='FAIL'))
        tests,details,ni=analyze(rows,methods);json.dumps([tests,details,ni],allow_nan=False)
        self.assertEqual(len(tests),16);self.assertEqual(tests[0]['n'],4);self.assertEqual(tests[0]['excluded_pairs'],1)
        self.assertTrue(all(x['label']=='NONINFERIOR' for x in ni))
    def test_bootstrap_same_pairs_deterministic(self):
        self.assertEqual(bootstrap_pairs([0,-1,1,1],['a','a','b','b']),bootstrap_pairs([0,-1,1,1],['a','a','b','b']))
        self.assertEqual(bootstrap_pairs([-.1]*4,['a']*4),(-.1,-.1))
    def test_no_pairs_not_evidence(self):
        tests,_,ni=analyze([],('OURS','TE'))
        self.assertTrue(all(not x['estimable'] for x in tests));self.assertEqual(ni[0]['label'],'INSUFFICIENT_DATA')

if __name__=='__main__':unittest.main()
