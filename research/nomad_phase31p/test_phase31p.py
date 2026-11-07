import copy,io,json,random,tempfile,unittest
from contextlib import ExitStack,redirect_stdout
from pathlib import Path
from unittest.mock import patch
from . import config,runtime,launch,campaign,report

class Validated(Exception):pass

def fake_rows(root):
    rows=[]
    for job in config.registered_order()[1]:
        rows.append(dict(job,output=str(root/'main'/f"{job['scene']}_{job['index']}_{job['method']}"/'attempt1'),
            technical_validation='PASS',success=not(job['method']=='C0-NA' and job['scene']=='SLW' and job['index']==206),
            collision=False,goal_time_s=30.,mean_speed_m_s=.2,stopped_fraction=.1,minimum_clearance_m=.1,
            path_jobs=20,path_applied=15,path_reasons={'ACCEPTED':15,'NONCONVERGED':5}))
    for r in rows:
        if not r['success']:r['goal_time_s']=None
    return rows

class Tests(unittest.TestCase):
    def test_randomized_complete_blocks(self):
        p=config.verify();blocks,order=config.registered_order();self.assertEqual((blocks,order),(p['blocks'],p['main_order']))
        self.assertEqual(len(blocks),10);self.assertEqual(len(order),30)
        rng=random.Random(20261107)
        for i,b in enumerate(blocks):
            expected=list(config.METHODS);rng.shuffle(expected);self.assertEqual(b['methods'],expected)
            self.assertEqual([r['method'] for r in order[3*i:3*i+3]],expected)
        self.assertGreater(len({tuple(b['methods']) for b in blocks}),1)

    def test_configs_only_change_registered_seed_and_labels(self):
        for scene in config.SCENES:
            for index in config.INDICES:
                for method in config.METHODS:
                    before=config.r_config(method,201,90,scene) if method=='G18-R' else config.na_config(method,201,90,scene) if method=='C0-NA' else config.c0_config(method,201,90,scene)
                    after=config.runtime_config(method,index,90,scene)
                    self.assertEqual(after['seed_offset'],10000*index)
                    for k in ('phase31p','phase31p_method','phase31p_index'):after.pop(k)
                    for k in ('seed_offset','run_id','phase29_index'):
                        if k in before:after[k]=before[k]
                    self.assertEqual(after,before)

    def test_frozen_install_entrypoints(self):
        import nomad_phase26.execution as c0
        import nomad_phase28.online_r1 as na
        import nomad_phase30r.runtime as gr
        for method,module in [('C0',c0),('C0-NA',na),('G18-R',gr)]:
            with patch.object(c0,'install') as a,patch.object(na,'install') as b,patch.object(gr,'install') as c:
                value=config.runtime_config(method,206,90,'H1');runtime.install(value)
                expected={'C0':a,'C0-NA':b,'G18-R':c}[method];expected.assert_called_once_with(value)
                for item in (a,b,c):
                    if item is not expected:item.assert_not_called()

    def test_exact_four_predicates_and_auxiliary_independence(self):
        rows=fake_rows(config.RUN_ROOT);self.assertEqual(report.decide(rows)['label'],'EXPAND')
        changed=copy.deepcopy(rows)
        for r in changed:
            if r['method']=='G18-R':r.update(goal_time_s=999.,mean_speed_m_s=.01,stopped_fraction=.99,minimum_clearance_m=-10.)
        self.assertEqual(report.decide(rows),report.decide(changed))
        tied=copy.deepcopy(rows)
        for r in tied:
            if r['method']=='C0-NA':r['success']=True
        self.assertFalse(report.decide(tied)['checks']['goal_gt_na']);self.assertEqual(report.decide(tied)['label'],'HOLD')
        unsafe=copy.deepcopy(rows);next(r for r in unsafe if r['method']=='G18-R')['collision']=True
        self.assertEqual(report.decide(unsafe)['label'],'HOLD')
        lower=copy.deepcopy(rows);next(r for r in lower if r['method']=='G18-R')['success']=False
        self.assertFalse(report.decide(lower)['checks']['goal_ge_c0'])

    def test_missing_and_invalid_evidence_never_expands(self):
        rows=fake_rows(config.RUN_ROOT)
        self.assertEqual(report.decide(rows[:-1])['label'],'HOLD')
        rows[0]['technical_validation']='FAIL';self.assertFalse(report.decide(rows)['evidence_valid'])
        self.assertEqual(report.decide(rows)['label'],'HOLD')

    def test_thirty_real_base_argument_checks_no_process(self):
        from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
        for job in config.registered_order()[1]:
            method=job['method'];out=config.RUN_ROOT/'main'/f"{job['scene']}_{job['index']}_{method}"/'attempt1'
            with ExitStack() as stack:
                base=launch.base.base
                for key in ('subprocess','verify','METHODS','SCENES','write_json'):
                    stack.enter_context(patch.object(base,key,getattr(base,key)))
                for fn in launch.LAUNCHERS.values():
                    if 'plan' in fn.__globals__:
                        stack.enter_context(patch.dict(fn.__globals__,plan=lambda:dict(possible=True,worker_cpu=7,driver_cpus=[0]),pin=lambda cpus:dict(passed=True)))
                stack.enter_context(patch.object(launch.base.os,'sched_setaffinity'))
                proc=stack.enter_context(patch.object(launch.subprocess,'Popen'))
                edge=stack.enter_context(patch.object(base,'socket_path_for_run',side_effect=Validated))
                stack.enter_context(patch('sys.argv',['launch','--scene',job['scene'],'--method',method,'--index',str(job['index']),'--output',str(out)]))
                with self.assertRaises(Validated):launch.main()
                proc.assert_not_called();edge.assert_called_once_with(out.resolve());self.assertFalse(out.exists())
            self.assertLess(validate_socket_path(socket_path_for_run(out)),100)

    def test_kit_first_and_frozen_launcher_bodies(self):
        from nomad_phase27r.launch import main as c0
        from nomad_phase28.launch import main as na
        from nomad_phase29.launch import main as gr
        for name,fn in [('C0',c0),('C0-NA',na),('G18-R',gr)]:self.assertIs(launch.LAUNCHERS[name].__code__,fn.__code__)
        source=(config.ROOT/'research/nomad_phase26/simulator.py').read_text().replace('from nomad_phase26.config','from nomad_phase31p.config').replace('from nomad_phase26.execution','from nomad_phase31p.runtime')
        self.assertLess(source.index('# SimulationApp is now initialized.'),source.index('from nomad_phase31p.runtime'))
        compile(source,'<phase31p-kit-first>','exec')

    def test_report_history_cannot_change_primary_label(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);run=root/'run';(run/'metrics').mkdir(parents=True);(root/'docs').mkdir();rows=fake_rows(run)
            for i,r in enumerate(rows):(run/'metrics'/f'{i}.json').write_text(json.dumps(r))
            results=[]
            for success in (False,True):
                old=[dict(rows[0],study='Phase30-R',index=201,method='G18-R',success=success,collision=not success)]
                with patch.object(report,'ROOT',root),patch.object(report,'OUT',root/'result'),patch.object(report,'RUN_ROOT',run),patch.object(report,'historical',return_value=old):doc=report.generate(run)
                results.append(json.loads((root/'result/decision.json').read_text()))
                self.assertIn('과거 자료를 합친 표',doc.read_text());self.assertIn('판정 미사용',doc.read_text())
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0]['label'],'EXPAND')
            self.assertEqual(results[0]['auxiliary']['c0_both_success_pairs'],10)

    def test_historical_filter_and_readonly_baseline(self):
        rows=report.historical()
        self.assertEqual(len(rows),40)
        self.assertEqual(sum(r['method']=='G18-R' for r in rows),10)
        self.assertTrue(all(r['index'] not in config.INDICES for r in rows))
        self.assertTrue(all(r['method']!='G18' for r in rows))

    def test_campaign_retry_disk_and_routes(self):
        p=config.verify()
        with patch.object(campaign.base,'protocol',return_value=p):jobs=campaign.base.jobs(config.RUN_ROOT)
        self.assertEqual(len(jobs),30);self.assertEqual([j['method'] for j in jobs],[r['method'] for r in p['main_order']])
        self.assertTrue(all(len(j['outputs'])==2 for j in jobs))
        for free,expected in [(29_999_999_999,False),(30_000_000_000,True)]:
            with patch.object(campaign.shutil,'disk_usage',return_value=type('Disk',(),dict(free=free))()):self.assertEqual(campaign.capacity(config.RUN_ROOT,jobs)['enough'],expected)
        self.assertEqual(campaign.Routes.route(['nomad_phase26.launch','nomad_phase26.report']),['nomad_phase31p.launch','nomad_phase31p.report'])

if __name__=='__main__':unittest.main()
