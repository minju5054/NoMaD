"""Synthetic-only checks; V0 optimization is forbidden even in these tests."""
import ast,json,multiprocessing as mp,tempfile,time,unittest
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase20.repair import RepairGraphR2
from nomad_phase20c.detour_known import KnownDetourGraph
from .solver import ModifiedGraph,solve,escape_certificate
from .geometry import obstacle_initializations,via_path
from .data import clusters,cB_bin
from .report import decision,grouped_rates

class Plane:
    h=.01;radius=.09;error_bound=.01/np.sqrt(2)
    def __init__(self,value=1.,gradient=(.05,.02)):self.value=value;self.gradient=np.asarray(gradient)
    def query(self,p):p=np.asarray(p);return self.value+p@self.gradient,np.repeat(self.gradient[None],len(p),axis=0)
    def exact_clearance(self,p):return float(self.query(p)[0].min())
    def unknown_fraction(self,p):return 0.

def jacobian(fn,x):
    eye=np.eye(len(x));h=1e-6
    return np.column_stack([(fn(x+h*d)-fn(x-h*d))/(2*h) for d in eye])

def graph(kind,value=.014):
    B=np.array([0.,0.,.1]);base=Plane(value)
    if kind=='R2':return RepairGraphR2(np.c_[np.linspace(0,1.05,8),np.zeros(8)],B,base)
    g=KnownDetourGraph(B,[1,0],base,base,30);g.initial*=.93;return g

def grid(rectangles,h=.05):
    field=SimpleNamespace(h=h,origin=np.array([-2.,-2.]),radius=.09,occupied=np.zeros((81,81),bool))
    y,x=np.indices(field.occupied.shape);xx=field.origin[0]+x*h;yy=field.origin[1]+y*h
    for xmin,xmax,ymin,ymax in rectangles:field.occupied|=(xx>=xmin-1e-9)&(xx<=xmax+1e-9)&(yy>=ymin-1e-9)&(yy<=ymax+1e-9)
    return field

class GraphTests(unittest.TestCase):
    def test_exactly_one_B_row_removed_and_no_slack(self):
        for kind in ('R2','R3'):
            for v in ('VB','VO','VE'):
                old=graph(kind,1.);m=ModifiedGraph(old,v);g,j=old.constraints(old.initial);a,b=m.constraints(old.initial)
                np.testing.assert_array_equal(a,g[1:]);np.testing.assert_array_equal(b,j[1:])
                self.assertEqual(b.shape[1],14 if kind=='R2' else 20)
                self.assertIs(m.graph,old);self.assertEqual(len(old.initial),14 if kind=='R2' else 20)
                self.assertEqual(m.certificate(old.points(old.initial)),old.certificate(old.points(old.initial)))
    def test_escape_constraint_jacobian(self):
        for kind in ('R2','R3'):
            old=graph(kind);m=ModifiedGraph(old,'VE');x=old.initial+.001*np.sin(np.arange(len(old.initial)))
            _,j=m.constraints(x);np.testing.assert_allclose(j,jacobian(lambda x:m.constraints(x)[0],x),atol=1e-5,rtol=0)
            _,j=old.objective(x);np.testing.assert_allclose(j,jacobian(lambda x:np.array([old.objective(x)[0]]),x).ravel(),atol=1e-5,rtol=0)
    def test_negative_precheck_retained_and_V0_never_dispatchable(self):
        b=Plane(-.02);job=dict(variant='VB',B=[0,0,0],u_ref=[1,0])
        with patch('nomad_phase39o2.solver.minimize',side_effect=AssertionError('Should not solve')):
            self.assertEqual(solve('R3',0,job,b,b)['disposition'],'NEGATIVE_DEPTH_AT_B')
            with self.assertRaises(AssertionError):solve('R3',0,dict(job,variant='V0'),b,b)
        from .pool import evaluate_job
        with self.assertRaises(AssertionError):evaluate_job(None,dict(variant='V0'))
    def test_synthetic_VE_can_solve_negative_B_with_new_certificate(self):
        base=Plane(-.02,(1.,0.));job=dict(variant='VE',B=[0,0,0],u_ref=[1,0])
        with patch.object(KnownDetourGraph,'solve',side_effect=AssertionError('Frozen V0 solver forbidden')):
            r=solve('R3',0,job,base,base)
        self.assertTrue(r['solver_started']);self.assertTrue(r['accepted']);self.assertTrue(r['certificate_pass'])
        self.assertLess(r['removed_B_sdf_value_m'],0.);self.assertEqual(r['slack_variables'],0);json.dumps(r,allow_nan=False)
    def test_certificate_two_closed_thresholds_and_map_boundary(self):
        base=Plane(-.2,(3.,0.));strict=Plane(-.2,(3.,0.));g=KnownDetourGraph([0,0,0],[1,0],base,strict,0)
        p=np.array([[0,0],[.2,0],[.4,0],[.8,0]])
        r=escape_certificate(g,p);s=(.03-g.cB)/.5;parts=r['certificate_segments']
        self.assertEqual([x['strict_field'] for x in parts],[False,True,True])
        self.assertEqual([x['threshold_m'] for x in parts],[g.cB-.005,g.cB-.005,.025])
        self.assertAlmostEqual(parts[1]['s_b'],s);self.assertAlmostEqual(parts[2]['s_a'],s)
        self.assertTrue(r['certificate_pass'])
        # Even when the path ends exactly at sesc, the closed high-threshold
        # singleton is checked, not lost by an empty final interval.
        flat=Plane(-.02,(0.,0.));g=KnownDetourGraph([0,0,0],[1,0],flat,flat,0);s=(.03-g.cB)/.5
        r=escape_certificate(g,[[0,0],[s,0]]);self.assertFalse(r['certificate_pass'])
        self.assertEqual(r['certificate_segments'][-1]['threshold_m'],.025)
    def test_failed_certificate_keeps_SLSQP_message_and_cannot_accept(self):
        g=graph('R3',1.);m=ModifiedGraph(g,'VB')
        def failed(fun,x,**kw):return SimpleNamespace(x=x,success=False,status=8,message='Positive directional derivative for linesearch',nit=2,fun=fun(x))
        with patch('nomad_phase39o2.solver.minimize',side_effect=failed),patch.object(m,'certificate',side_effect=ValueError('degenerate certificate path')):
            r=m.solve()
        self.assertFalse(r['accepted']);self.assertEqual(r['solver_status'],8)
        self.assertEqual(r['disposition'],'NONCONVERGED');self.assertIn('linesearch',r['message'])

class GeometryTests(unittest.TestCase):
    def test_empty_and_first_component_and_full_width(self):
        extra,a=obstacle_initializations(grid([]),[0,0,0],[1,0]);self.assertFalse(extra)
        self.assertTrue(all(s['reason']=='NO_COMPONENT_IN_STRIP' for s in a['sides']))
        field=grid([(.6,.8,-.4,.4),(1.2,1.3,-.1,.1)])
        extra,a=obstacle_initializations(field,[0,0,0],[1,0]);self.assertEqual(len(extra),2)
        self.assertAlmostEqual(a['first_forward_m'],.6);self.assertAlmostEqual(a['lateral_max_m'],.4)
        for e in extra:
            p=np.array(e['path']);self.assertEqual(p.shape,(11,2));self.assertTrue(any(np.allclose(x,e['via']) for x in p))
            length=np.linalg.norm(np.diff(p,axis=0),axis=1)
            self.assertTrue(length.min()>=.1-1e-10 and length.max()<=.2+1e-10);self.assertLessEqual(np.linalg.norm(p,axis=1).max(),1.6+1e-10)
    def test_component_is_eight_connected(self):
        field=grid([]);field.occupied[40,52]=True;field.occupied[41,53]=True
        _,a=obstacle_initializations(field,[0,0,0],[1,0]);self.assertEqual(a['full_cells'],2)
    def test_disk_clipped_wall_sides_are_excluded(self):
        field=grid([(.55,.65,-2,2)]);extra,a=obstacle_initializations(field,[0,0,0],[1,0])
        self.assertFalse(extra);self.assertLess(a['clipped_cells'],a['full_cells'])
        self.assertTrue(all(s['reason']=='SIDE_TOUCHES_DISK_BOUNDARY' for s in a['sides']))
        extra,a=obstacle_initializations(grid([(.55,.65,-.2,2)]),[0,0,0],[1,0])
        self.assertEqual(a['sides'][0]['reason'],'SIDE_TOUCHES_DISK_BOUNDARY');self.assertTrue(a['sides'][1]['generated'])
    def test_via_blocked_and_frame_rotation(self):
        field=grid([(.6,.8,-.2,.2)])
        _,original=obstacle_initializations(field,[0,0,0],[1,0]);via=np.array(original['sides'][0]['via_world']);cell=np.rint((via-field.origin)/field.h).astype(int)
        field.occupied[cell[1],cell[0]]=True
        _,a=obstacle_initializations(field,[0,0,0],[1,0]);self.assertEqual(a['sides'][0]['reason'],'VIA_BLOCKED')
        extra,a=obstacle_initializations(grid([(-.2,.2,.6,.8)]),[0,0,np.pi/2],[0,1])
        self.assertEqual(len(extra),2);self.assertLess(a['sides'][0]['via_world'][0],0);self.assertGreater(a['sides'][1]['via_world'][0],0)
    def test_geometry_has_no_path_search_import(self):
        from . import geometry
        tree=ast.parse(Path(geometry.__file__).read_text());imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(x.name for x in node.names)
            if isinstance(node,ast.ImportFrom):imports.append(node.module)
        self.assertEqual(set(imports),{'numpy','scipy.ndimage'})

class ReportingTests(unittest.TestCase):
    def test_adjacent_groups_include_mixed_kinds_and_no_anchor_rule(self):
        cases=[dict(case_id=str(i),run='a/attempt1',job_id=i,job=dict(B=[x,0,0],simulation_time_s=i)) for i,x in enumerate((0,.009,.018,.04))]
        grouped=clusters(cases);self.assertEqual(grouped['0']['group'],grouped['2']['group']);self.assertNotEqual(grouped['2']['group'],grouped['3']['group'])
        self.assertEqual(cB_bin(0),'0<=cB<0.03125');self.assertEqual(cB_bin(.03125),'>=0.03125')
        rows=[dict(run='r',group='g',variant=v,success=i==0,kind=k,cB_bin='<0') for v in ('V0','VB') for i,k in enumerate(('R2','R3'))]
        groups,runs=grouped_rates(rows);self.assertEqual(len(groups),2);self.assertTrue(all(r['run_any_success'] for r in runs));self.assertTrue(all(r['groups']==1 for r in runs))
    def test_gate_raw_denominator_and_simplest(self):
        expected=[dict(case_id=str(i)) for i in range(10)]
        rows=[dict(case_id=str(i),variant=v,success=i<n,job_wall_s=.9,certificate_failures=0) for v,n in (('V0',2),('VB',5),('VO',7),('VE',9)) for i in range(10)]
        self.assertEqual(decision(rows,expected)['selected_variant'],'VB')
        rows[10]['certificate_failures']=1;self.assertEqual(decision(rows,expected)['selected_variant'],'VO')
        self.assertEqual(decision(rows[:-1],expected)['label'],'NOT_EVALUATED')
    def test_four_process_synthetic_job_without_V0(self):
        from nomad_phase20d.recent import RecentMap,RecentSnapshot
        from nomad_phase33p.storage import save_snapshot,install
        from .pool import initialize,ping,evaluate_job
        install();field=RecentMap([-2,-2,2,2],resolution=.05);field.observed[:]=True;field.last_free_tick[:]=0
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'input.npz';save_snapshot(RecentSnapshot(field,dict(frame_id=0,sim_s=0)),f)
            ctx=mp.get_context('spawn');queue=ctx.Queue()
            with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
                fs=[pool.submit(ping) for _ in range(4)];pids=[queue.get(timeout=30) for _ in range(4)]
                for x in fs:x.result()
                self.assertEqual(len(set(pids)),4)
                job=dict(variant='VO',kind='R3',B=[0,0,0],u_ref=[1,0],job_id=0,evaluation_tick=0,snapshot_file=str(f),cache_file=str(Path(d)/'cache.npz'))
                result=evaluate_job(pool,job);self.assertEqual(len(result['results']),7)
                self.assertIsNotNone(result['selected_sample']);json.dumps(result,allow_nan=False)
    def test_fake_report_reads_V0_files_and_emits_new_tables(self):
        from . import report
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'preparation').mkdir();(root/'jobs').mkdir();(root/'baseline').mkdir();metadata=[]
            for i in range(10):
                file=root/'baseline'/f'{i}.json'
                metadata.append(dict(case_id=str(i),run='r/attempt1',group='g'+str(i//2),scene='SLW',kind='R3',cB=.1,cB_bin='>=0.03125',baseline_file=str(file)))
                for v,count in (('V0',2),('VB',5),('VO',6),('VE',7)):
                    yes=i<count
                    numeric=dict(results=[dict(accepted=yes,disposition='ACCEPTED' if yes else 'NONCONVERGED')],selected_sample=0 if yes else None,pool_wall_s=.2)
                    if v in ('VO','VE'):numeric.update(geometry=dict(sides=[dict(source='OBSTACLE_LEFT',generated=True,reason='GENERATED'),dict(source='OBSTACLE_RIGHT',generated=False,reason='VIA_BLOCKED')]),selected_initialization_source='OBSTACLE_LEFT' if yes else None)
                    row=dict(case_id=str(i),variant=v,numeric=numeric,certificate_audit=[dict(certificate_pass=True)] if yes else [])
                    (file if v=='V0' else root/'jobs'/f'{i}_{v}.json').write_text(json.dumps(row))
            before={p.name:p.read_bytes() for p in (root/'baseline').glob('*.json')}
            (root/'preparation/metadata.json').write_text(json.dumps(metadata));(root/'protocol.json').write_text(json.dumps({'estimated_minutes':1.}))
            with patch.object(report,'OUT',root),patch.object(report,'HERE',root):result=report.generate(root,root/'report.md')
            self.assertEqual(result['label'],'GO');self.assertEqual(result['selected_variant'],'VB')
            for name in ('summary.csv','runs.csv','groups.csv','geometry.csv','messages.csv','decision.json'):self.assertTrue((root/name).exists())
            self.assertEqual(before,{p.name:p.read_bytes() for p in (root/'baseline').glob('*.json')})

if __name__=='__main__':unittest.main()
