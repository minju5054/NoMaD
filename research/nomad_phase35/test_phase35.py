import io,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace,MappingProxyType
from unittest.mock import patch
import numpy as np
from nomad_isaac.common import integrate_se2
from nomad_phase32o.test_exec_cert import field
from nomad_phase12.methods import TransitionState
from nomad_phase21.execution import TEProfile,TEExecution
from nomad_phase28.alignment import NoAlignment
from nomad_phase32.runtime import Execution as ECExecution
from nomad_phase33p.storage import save_snapshot
from nomad_storage_sdf.loader import load_npz
from .config import METHODS,SCENES,INDICES,runtime_config,registered_order,RUN_ROOT,ALIASES
from .runtime import RawNA,RTCNA,TENA,make_execution
from .report import decide,exact_mcnemar

def instance(method):
    cls=ECExecution if method in ('OURS','ASTAR+EC') else TENA if method=='SAFE_TE' else RTCNA if method=='SAFE_RTC' else RawNA
    x=object.__new__(cls);x.last_command=[.1,0.];x.repair_log=io.StringIO();x.command_log=io.StringIO()
    x.recovery=SimpleNamespace(state='NORMAL',count=0,streak=0);x.repair_pending=None;x.named_method=method;x.plant=SimpleNamespace(actual_w=0.)
    f=field();f.metadata=MappingProxyType(dict(frame_id=0,sim_s=0.,publication_monotonic_ns=0))
    x.depth_maps=SimpleNamespace(snapshot=lambda:f);x.detour=None;x.detour_active=False;x.dcmd=io.StringIO()
    if method=='SAFE_TE':
        x.transition=TransitionState('TEMPORAL-ENSEMBLE');x.fresh=dict(received_monotonic_ns=1_000_000_000);x.now_ns=1_000_000_000
    if method in ('OURS','ASTAR+EC'):
        x.ec_method='C0-NA+EC';x.depth_maps=SimpleNamespace(snapshot=lambda:f);x.ec_samples={};x.active_sample=0
        x.ec_switch=dict(id=1);x.ec_cap=None;x.ec_generation=0;x.ec_check_sequence=0;x.ec_file=io.StringIO();x.plant=SimpleNamespace(actual_w=0.)
    return x

class WiringTests(unittest.TestCase):
    def test_all_install_thresholds_and_json_ticks(self):
        for method in METHODS:
            for degrees in (20,45,90,91,130):
                x=instance(method);angle=np.deg2rad(degrees);path=np.c_[np.linspace(0,.8,8)*np.cos(angle),np.linspace(0,.8,8)*np.sin(angle)]
                core=SimpleNamespace(pose=np.zeros(3));refresh=dict(monotonic_ns=1_000_000_000,simulation_time_s=0.)
                x.new_path(path,core,refresh,1,'SAFE')
                self.assertEqual(x.sp.alignment_threshold_deg,90.)
                self.assertEqual(bool(x.sp.trigger_S),degrees>90,(method,degrees))
                v=.1;pose=np.zeros(3)
                for tick in range(160):
                    (v,w),diag=x.sp.control(pose,v)
                    core.pose=pose;core.v=v;core.w=w;x.plant.actual_w=w;refresh['simulation_time_s']=tick/72;switch={}
                    x.write_command(core,refresh,switch,[v,w],[v,w],'NORMAL',diag)
                    json.dumps(switch,allow_nan=False)
                    json.dumps(dict(command=[v,w],controller=diag,refresh=refresh),allow_nan=False)
                    self.assertLessEqual(v,.3+1e-12);self.assertLessEqual(abs(w),.4+1e-12)
                    pose=integrate_se2(pose,v,w,1/72)
                for line in x.repair_log.getvalue().splitlines():json.dumps(json.loads(line),allow_nan=False)
                for line in x.command_log.getvalue().splitlines():json.dumps(json.loads(line),allow_nan=False)
                for line in x.dcmd.getvalue().splitlines():json.dumps(json.loads(line),allow_nan=False)
                if method in ('OURS','ASTAR+EC'):
                    for line in x.ec_file.getvalue().splitlines():json.dumps(json.loads(line),allow_nan=False)

    def test_te_handoff_kept(self):
        self.assertIs(TENA.new_path,TEExecution.new_path)
        self.assertIs(TENA.use_fallback,TEExecution.use_fallback)
        x=instance('SAFE_TE');core=SimpleNamespace(pose=np.zeros(3));r=dict(monotonic_ns=1_000_000_000,simulation_time_s=0.)
        x.new_path([[0,0],[.8,.1]],core,r,1,'SAFE')
        self.assertIs(type(x.sp),TEProfile);self.assertEqual(len(x.transition.ensemble.chunks),1)
        self.assertEqual(x.transition.ensemble.chunks[-1]['id'],1)

    def test_configs_only_authorized_wiring(self):
        from nomad_phase26.config import runtime_config as base
        for m in METHODS:
            for s in SCENES:
                c=runtime_config(m,212,90,s);old=base(ALIASES[m],201,90,s)
                permitted={'seed_offset','run_id','phase35','phase35_method','phase35_index','storage_version',
                    'phase29','phase29_method','phase29_index','phase32','phase32_method','phase32_index'}
                self.assertEqual({k:v for k,v in c.items() if k not in permitted},{k:v for k,v in old.items() if k not in permitted})
                self.assertEqual(c['depth_camera'],m!='NOMAD_RAW');self.assertEqual(c['goal_tolerance_m'],.3);self.assertEqual(c['timeout_sim_s'],90.)

    def test_ours_factory_same_ec_class_and_astar_worker(self):
        from . import worker
        from nomad_phase21 import pool as astar
        from . import astar_pool,graph_pool
        from nomad_phase20d import pool as graph
        self.assertIs(astar_pool.frozen.evaluate_job,astar.evaluate_job)
        self.assertIs(graph_pool.frozen.evaluate_job,graph.evaluate_job)
        self.assertIs(worker.AStarWorker.submit,__import__('nomad_phase21.worker',fromlist=['Worker']).Worker.submit)
        self.assertIs(worker.GraphWorker.submit,__import__('nomad_phase20d.worker',fromlist=['Worker']).Worker.submit)

    def test_storage_v2_roundtrip(self):
        f=field([.5,.4]);f.observed=np.ones_like(f.occupied);f.metadata=MappingProxyType(dict(frame_id=3,sim_s=.5))
        before=f.values.copy()
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'snapshot.npz';save_snapshot(f,p,compressed=False)
            with np.load(p) as z:self.assertNotIn('values',z.files)
            restored=load_npz(p);np.testing.assert_array_equal(restored['values'],before);np.testing.assert_array_equal(f.values,before)

class RegistrationTests(unittest.TestCase):
    def test_order_and_sockets(self):
        from .campaign import plan
        blocks,order=registered_order();self.assertEqual(len(blocks),15);self.assertEqual(len(order),75)
        self.assertEqual(set(r['index'] for r in order),{212,213,214});self.assertEqual(order,registered_order()[1])
        self.assertEqual(len(plan()),75);self.assertEqual(len(plan(True)),4)

    def test_launcher_argument_validation_without_process(self):
        from .launch import launcher_main
        from .campaign import plan
        class Halt(Exception):pass
        process=SimpleNamespace(Popen=lambda *a,**k:self.fail('Must not start process'))
        for smoke in (False,True):
            for job in plan(smoke):
                fn=launcher_main(process)
                fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Halt())
                argv=['launch','--scene',job['scene'],'--method',job['method'],'--index',str(job['index']),'--output',job['outputs'][0]]+(['--smoke'] if smoke else [])
                with patch.object(sys,'argv',argv),self.assertRaises(Halt):fn()

    def test_registration_decisions_and_exact_p(self):
        rows=[dict(r,technical_validation='PASS',success=True,collision=False,goal_time_s=10. if r['method']=='OURS' else 11.) for r in registered_order()[1]]
        d=decide(rows);self.assertEqual(d['GRAPH'],'GRAPH_BETTER');self.assertFalse(any(d['BEATS'].values()))
        for r in rows:
            if r['method']=='OURS':r['goal_time_s']=11.
        self.assertEqual(decide(rows)['GRAPH'],'GRAPH_EQUAL')
        for r in rows:
            if r['method']=='OURS' and r['index']==212:r['success']=False;r['goal_time_s']=None
        self.assertEqual(decide(rows)['GRAPH'],'GRAPH_WORSE')
        self.assertFalse(decide(rows[:-1])['evidence_valid'])
        self.assertEqual(exact_mcnemar(0,0),1.);self.assertEqual(exact_mcnemar(3,0),.25)

    def test_disk_and_deadline_guard(self):
        from . import campaign
        with patch.object(campaign,'write'),patch.object(campaign.time,'time',return_value=1794071828+23401):
            state={};self.assertFalse(campaign.guard(state));self.assertEqual(state['status'],'PARTIAL')
        with patch.object(campaign,'write'),patch.object(campaign.time,'time',return_value=1794071828),patch.object(campaign.shutil,'disk_usage',return_value=SimpleNamespace(free=29_000_000_000)):
            state={};self.assertFalse(campaign.guard(state));self.assertEqual(state['status'],'STOP_BLOCKED')

if __name__=='__main__':unittest.main()
