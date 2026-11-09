import copy,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from scipy.stats import binomtest
from . import config,runtime,launch,campaign,report


class Tests(unittest.TestCase):
    def test_new_seed_common_jitter_frozen_methods_and_stop(self):
        from nomad_phase38.config import runtime_config as old
        from nomad_phase38.scenes import registered_jitter
        p=config.verify();blocks,order=config.registered_order()
        self.assertEqual(len(order),60);self.assertEqual(len(blocks),20)
        self.assertTrue(all(set(b['methods'])==set(config.METHODS) for b in blocks))
        for s in config.SCENES:
            for i in config.INDICES:
                placement=registered_jitter(s,i);self.assertEqual(p['placements'][f'{s}_{i}'],placement)
                for box in placement:self.assertTrue(box['geometry']['passed'])
                for m in config.METHODS:
                    c=config.runtime_config(m,i,90,s);source='OURS-DETOUR' if m=='OURS-DETOUR+HMM' else m
                    before=old(source,217,90,s)
                    skip={'seed_offset','run_id','phase35_index','phase38_index','phase29_index','phase32_index','phase38_jitter',
                          'phase41','nomad_goal_stop','phase47c','phase47c_method','phase43p','phase43p_method'}
                    self.assertEqual({k:v for k,v in c.items() if k not in skip},{k:v for k,v in before.items() if k not in skip})
                    self.assertEqual(c['seed_offset'],i*10000);self.assertEqual(c['phase38_jitter'],placement);self.assertTrue(c['nomad_goal_stop'])
                    self.assertEqual(c['depth_camera'],m!='NOMAD_RAW')
                    with patch.object(runtime,'original_localization') as original,patch.object(runtime,'hmm_localization') as hmm:
                        runtime.install(c)
                        self.assertEqual(hmm.call_count,int(m=='OURS-DETOUR+HMM'));self.assertEqual(original.call_count,int(m!='OURS-DETOUR+HMM'))

    def test_sixty_launch_checks_worker_routing_and_engine_no_simulation(self):
        from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
        class Boundary(Exception):pass
        jobs=campaign.jobs(config.RUN_ROOT);self.assertEqual(len(jobs),60)
        for j in jobs:
            for output in j['outputs']:self.assertLess(validate_socket_path(socket_path_for_run(Path(output))),100)
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No process')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            argv=['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]
            with patch.object(sys,'argv',argv),self.assertRaises(Boundary):fn()
        for use_hmm in (False,True):
            process=launch.Processes(hmm=use_hmm)
            with patch('subprocess.Popen',return_value=object()) as popen:
                process.Popen(['python','-m','nomad_isaac.worker'])
                self.assertEqual(popen.call_args.args[0][2],'nomad_phase43p.worker' if use_hmm else 'nomad_isaac.worker')
        code='''
from nomad_phase47c import campaign as c
from nomad_phase47c.config import RUN_ROOT
def halt():
 assert len(c.frozen.base.jobs(RUN_ROOT))==60
 assert c.frozen.base.run_job.__globals__['subprocess'].__class__ is c.Routes
 print('NO_EXECUTION')
c.frozen.base.main=halt
c.main()
assert not RUN_ROOT.exists()
'''
        r=subprocess.run(['/usr/bin/python3','-c',code],cwd=config.ROOT,env=dict(os.environ,PYTHONPATH='research'),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr[-1800:])

    def test_exact_mcnemar_holm_and_fake_tables(self):
        rows=[]
        for i,(s,k) in enumerate((s,k) for s in config.SCENES for k in config.INDICES):
            for m in config.METHODS:
                success=True if m=='OURS-DETOUR+HMM' else i<10
                collision=m=='NOMAD_RAW' and i>=10
                rows.append(dict(scene=s,index=k,method=m,technical_validation='PASS',success=success,collision=collision,
                                 wrong_stop=False,timeout_without_declaration=not success,stop_distance_m=.2,final_goal_distance_m=.2,node_errors=[]))
        tests,pairs=report.primary_tests(rows)
        expected=float(binomtest(10,10,.5).pvalue)
        self.assertEqual(tests[0]['p_exact_two_sided'],expected);self.assertEqual(tests[1]['p_exact_two_sided'],expected)
        self.assertEqual((tests[0]['left_only'],tests[0]['right_only']),(10,0))
        self.assertEqual((tests[1]['left_only'],tests[1]['right_only']),(0,10))
        self.assertEqual(tests[0]['p_holm_two_primary'],2*expected)
        failed=copy.deepcopy(rows);next(r for r in failed if r['method']=='OURS-DETOUR')['technical_validation']='FAIL'
        excluded,_=report.primary_tests(failed);self.assertEqual([r['n'] for r in excluded],[19,19])
        self.assertTrue(all(r['reject_equal_holm_0p05'] is None for r in excluded))
        empty,_=report.primary_tests([]);self.assertTrue(all(r['p_exact_two_sided'] is None for r in empty))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir()
            for i,r in enumerate(rows):(root/'metrics'/f'{i}.json').write_text(json.dumps(r))
            doc=report.generate(root,root/'results',root/'report.md')
            self.assertTrue(all(not line or line.startswith('|') for line in doc.read_text().splitlines()))
            self.assertEqual(json.loads((root/'results/analysis.json').read_text())['completed'],60)


if __name__=='__main__':unittest.main()
