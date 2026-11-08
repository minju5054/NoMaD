import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from .report import decision

class ReportingTests(unittest.TestCase):
    def test_gate_conservative_first(self):
        meta=[dict(case_id=str(i)) for i in range(10)]
        rows=[dict(case_id=str(i),variant=v,success=i<n,job_wall_s=.9,certificate_failures=0) for v,n in (('V0',2),('VE',3),('VN',5),('VU',7)) for i in range(10)]
        self.assertEqual(decision(rows,meta)['selected_variant'],'VN')
        rows[20]['certificate_failures']=1;self.assertEqual(decision(rows,meta)['selected_variant'],'VU')
        self.assertEqual(decision(rows[:-1],meta)['label'],'NOT_EVALUATED')
    def test_report_reuses_R2_and_writes_all_safety_tables(self):
        from . import report
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'jobs').mkdir();(root/'baseline').mkdir();(root/'baseline_metrics').mkdir();(root/'preparation').mkdir();meta=[]
            measurement=dict(accepted_base_clearances=[dict(index=0,selected=True,base_exact_clearance_m=.05,base_exact_ge_0p025=True)],
                selected_path_unknown=dict(unknown_fraction_all=.3,unknown_fraction_within_0p6=.1),optimizer_called=False)
            for i,kind in enumerate(('R2','R3')):
                m=dict(case_id=str(i),kind=kind,cB_bin='>=0.03125',scene='SLW',run='r',group='g'+str(i),baseline_file=str(root/'baseline'/f'{i}_V0.json'),ve_file=str(root/'baseline'/f'{i}_VE.json'));meta.append(m)
                for v in ('V0','VE','VN','VU'):
                    numeric=dict(results=[dict(accepted=True,disposition='ACCEPTED')],selected_sample=0,pool_wall_s=.2,geometry=None)
                    r=dict(case_id=str(i),variant=v,numeric=numeric,certificate_audit=[dict(index=0,certificate_pass=True)],measurements=measurement)
                    if v in ('V0','VE'):
                        (root/'baseline'/f'{i}_{v}.json').write_text(json.dumps(r))
                        (root/'baseline_metrics'/f'{i}_{v}.json').write_text(json.dumps({'measurements':measurement}))
                    elif kind=='R3':(root/'jobs'/f'{i}_{v}.json').write_text(json.dumps(r))
            (root/'preparation/metadata.json').write_text(json.dumps(meta));(root/'protocol.json').write_text(json.dumps(dict(soft_policy_map=False,estimated_minutes=1.)))
            before={f.name:f.read_bytes() for f in (root/'baseline').glob('*.json')}
            with patch.object(report,'HERE',root),patch.object(report,'OUT',root):result=report.generate(root,root/'report.md')
            self.assertEqual(result['label'],'NO_GO')
            for v in result['variants']:self.assertEqual(v['n'],2)
            for f in ('base_clearances.csv','base_clearance_summary.csv','summary.csv','jobs.csv','groups.csv'):self.assertTrue((root/f).exists())
            self.assertEqual(before,{f.name:f.read_bytes() for f in (root/'baseline').glob('*.json')})

if __name__=='__main__':unittest.main()
