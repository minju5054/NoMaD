"""Only Phase2 placement, public gating, conditional execution and stale handling."""
import json
from types import SimpleNamespace
import numpy as np
from nomad_isaac.common import ROOT
from nomad_isaac.async_core import WaypointExecution
from nomad_phase1.s1 import VisibilityGate
from nomad_phase2.config import HERE,place,select,triggered
from nomad_phase2.execution import Phase2Execution,speed_command
from nomad_phase2.batch import plan
from nomad_phase0.graph_v3 import speed_command as original_speed
from nomad_phase0.graph_v4 import selection_score


def config(method='M0'):
    c=json.loads((HERE/'scenario.json').read_text());c.update(phase2_method=method,phase2_distance_m=.8)
    c['dynamic_obstacle']={'id':'DynamicObstacle','size_xyz_m':[.35,.35,.8],'placement':{}}
    return c

def test_placement_and_visibility():
    c=config()
    for y in (0.,1.1,-1.1):
        p=[2.01,y,.7];r=place(c,p)
        assert r['status']=='PLACED' and abs(r['measured_world_forward_surface_d_m']-.8)<1e-12
        assert r['left_wall_gap_m']>=.4-1e-12 and r['right_wall_gap_m']>=.4-1e-12
    assert not triggered(c,[1.999,0,0]) and triggered(c,[2.,0,0])
    gate=VisibilityGate()
    for i,visible in enumerate((False,True,False)):
        row={'observation_id':i,'observation_sim_s':i/4,'capture_end_monotonic_ns':i,'frame_sha256':'x','rgb_file':'x',
             'dynamic':{'active':True,'visible':visible}}
        result=gate.observe(row);assert result['geometry_available']==(i==2)

def test_speed_and_score_match_original():
    settings={'v_min':.05,'v_max':.2,'w_max':.4,'acceleration_max_m_s2':.5}
    for v in (0.,.05,.1,.2):
        for k in (-20.,-8.,0.,2.,20.):
            cmd,flags=speed_command(k,v);a,b=original_speed(k,v,settings)
            assert cmd==a and all(b[key]==value for key,value in flags.items())
    points=np.column_stack([np.linspace(.1,.7,8),np.zeros(8)])
    c=config();c['obstacles']=[]
    result=select(np.array([points]*8),[0,0,0],c)
    assert result['selected_sample']==0 and not result['sample0_unsafe']
    p=json.loads((ROOT/'research/nomad_phase0/graph_v4_protocol.json').read_text())
    assert result['selection_scores'][0]==selection_score(points,points,[0,0,0],p)['total']

def test_conditional_original_pp_and_timeout(tmp_path):
    c=config('M3');engine=Phase2Execution(c,tmp_path);core=WaypointExecution([0,0,0])
    metric=np.tile(np.column_stack([np.linspace(.1,.8,8),np.zeros(8)]),(8,1,1))
    row={'id':0,'received_monotonic_ns':1000000000,'observation_pose':[0,0,0],
         'selected_waypoint_m':metric[0,2].tolist()}
    core.receive(row,metric[0,2]);engine.accept(row,metric)
    refresh,event=engine.control(core,0,1000000000)
    assert not event['phase2']['variable_speed'] and (core.v,core.w)==(.2,0.)
    refresh,event=engine.control(core,8,2000000000)
    assert not refresh['valid'] and (core.v,core.w)==(0.,0.)
    engine.close()

def test_worker_stale_fallback_and_hold(monkeypatch,tmp_path):
    import nomad_phase2.execution as module
    class Fake:
        def __init__(self,out):self.result=None
        def submit(self,j):self.job=j
        def poll(self):r=self.result;self.result=None;return r
        def close(self):pass
    monkeypatch.setattr(module,'GraphClient',Fake)
    c=config('M5');e=Phase2Execution(c,tmp_path);core=WaypointExecution([0,0,0])
    xy=np.column_stack([np.linspace(.1,.8,8),np.zeros(8)]);metric=np.tile(xy,(8,1,1))
    r={'id':0,'received_monotonic_ns':1000000000,'observation_pose':[0,0,0],'selected_waypoint_m':xy[2].tolist()}
    core.receive(r,xy[2]);e.accept(r,metric);e.control(core,0,1000000000)
    # Unsafe corridor sample triggers graph even with empty public obstacle set; mock terminal rejection.
    metric[:,:,:]=np.column_stack([np.linspace(.1,.8,8),np.full(8,2.)])
    r={**r,'id':1,'received_monotonic_ns':1100000000}
    core.receive(r,metric[0,2]);e.accept(r,metric)
    f,event=e.control(core,8,1100000000)
    assert event is None and f['graph_wait'] and core.v==.2
    e.client.result={'job_id':0,'id':1,'kind':'result','accepted':False,'result_received_ns':1700000000}
    f,event=e.control(core,16,1700000000)
    assert event['phase2']['graph_applied'] is False and event['phase2']['variable_speed'] is False
    e.close()
    result=json.loads((tmp_path/'phase2_graph.jsonl').read_text().splitlines()[-1]);assert result['stale']

def test_counts_offsets_and_branch_plan(tmp_path):
    p=plan(tmp_path)
    assert [len(p[k]) for k in ('pilots','baseline','main','paired','hard')]==[3,4,16,32,8]
    for j in p['paired']:
        match=next(x for x in p['main'] if (x['index'],x['D_s'],x['d_m'])==(j['index'],j['D_s'],j['d_m']))
        assert match['seed_offset']==j['seed_offset']==j['index']*10000
    assert p['max_branch2b']==55 and p['max_branch2c']==47

def test_m0_matches_original_chunk_core_tickwise(tmp_path):
    from nomad_phase0.chunk_execution import ChunkExecution,describe_chunk
    from nomad_isaac.common import integrate_se2
    actual=Phase2Execution(config('M0'),tmp_path)
    old=ChunkExecution();a=WaypointExecution([0,0,0]);b=WaypointExecution([0,0,0])
    rng=np.random.default_rng(11);idx=0
    for tick in range(220):
        now=1000000000+round(tick/72*1e9)
        if tick in (0,54,108):
            xy=np.cumsum(rng.uniform([.01,-.03],[.08,.03],(8,2)),axis=0);metric=np.tile(xy,(8,1,1))
            row={'id':idx,'received_monotonic_ns':now,'observation_pose':a.pose.tolist(),'selected_waypoint_m':xy[2].tolist(),
                 'chunk':describe_chunk(xy,a.pose)}
            a.receive(row,xy[2]);b.receive(row,xy[2]);actual.accept(row,metric);idx+=1
        x,y=a.control(tick,now)
        if x:old.apply(a,x,y)
        actual.control(b,tick,now)
        assert (a.v,a.w)==(b.v,b.w)
        np.testing.assert_array_equal(a.integrate(),b.integrate())
    actual.close()
