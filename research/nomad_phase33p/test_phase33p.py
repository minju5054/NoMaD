import json,tempfile,unittest
from pathlib import Path
from types import MappingProxyType,SimpleNamespace
import numpy as np
from .graph import NormalGraph,RepairGraph,DetourGraph,sagitta,segment_margin
from .storage import save_snapshot,snapshot_arrays,load_snapshot
from nomad_storage_sdf.loader import reconstruct,load_npz,bit_equal
from nomad_phase17.graph import ClearanceGraph
from nomad_phase20.repair import RepairGraphR2
from nomad_phase20c.detour_known import KnownDetourGraph
from nomad_phase0.graph_v4 import menger
from nomad_phase15b.depth import Snapshot

class Field:
    error_bound=.01/np.sqrt(2)
    def query(self,p):
        p=np.asarray(p);return .5+.02*p[:,1],np.tile([0.,.02],(len(p),1))
    def exact_clearance(self,p):return float(self.query(np.asarray(p))[0].min())
    def unknown_fraction(self,p):return 0.

def jacobian(fn,x):
    h=1e-6
    return np.column_stack([(fn(x+np.eye(len(x))[i]*h)[0]-fn(x-np.eye(len(x))[i]*h)[0])/(2*h) for i in range(len(x))])

class Tests(unittest.TestCase):
    def test_gate_uses_all_247_and_strict_ec_improvement(self):
        from .report import decide
        old=dict(scope='ALL',variant='G18',n=247,solve_success_rate=.9,compute_p95_s=.1,solve_and_ec_rate=100/247)
        new=dict(scope='ALL',variant='G18X',n=247,solve_success_rate=198/247,compute_p95_s=.15,solve_and_ec_rate=101/247)
        self.assertEqual(decide([old,new])['label'],'OFFLINE_OK')
        self.assertEqual(decide([old,dict(new,solve_and_ec_rate=100/247)])['label'],'OFFLINE_FAIL')
        self.assertEqual(decide([old,dict(new,solve_success_rate=197/247)])['label'],'OFFLINE_FAIL')
        self.assertEqual(decide([old,dict(new,compute_p95_s=.150000001)])['label'],'OFFLINE_FAIL')
    def test_start_relaxation_is_retained_plus_margin(self):
        class NearField(Field):
            def query(self,p):return np.full(len(p),.022),np.zeros_like(np.asarray(p))
        q=np.c_[np.linspace(0,1.2,8),[0,.012,.039,.073,.094,.081,.108,.157]];old=RepairGraphR2(q,[0,0,0],NearField());new=RepairGraph(q,[0,0,0],NearField())
        self.assertEqual(new.near_threshold,old.near_threshold);self.assertLess(new.near_threshold,.025)
        x=new.initial;k,jk=menger(new.points(x));e,_,_=segment_margin(k,jk[:,1:,:].reshape(6,14),8)
        np.testing.assert_allclose(old.constraints(x)[0][:63]-new.constraints(x)[0][:63],e[new.segment_ids],atol=1e-14)
    def test_sagitta_definition_and_derivative(self):
        k=np.array([-.7,0.,.3,1.2,2.,3.])
        e,j=sagitta(k);self.assertEqual(e[1],0.)
        q=np.array([-.7,.3,1.2,2.]);expected=1/np.abs(q)-np.sqrt(1/q**2-.25**2)
        np.testing.assert_allclose(e[[0,2,3,4]],expected,atol=1e-14)
        numeric=(sagitta(k+1e-6)[0]-sagitta(k-1e-6)[0])/2e-6
        np.testing.assert_allclose(j,numeric,atol=1e-5)
    def test_segment_endpoint_rule(self):
        k=np.array([1.,-2.,.4]);e,j,chosen=segment_margin(k,np.eye(3),5)
        np.testing.assert_array_equal(chosen,[0,1,1,2]);np.testing.assert_allclose(e,sagitta(k[chosen])[0])
    def test_normal_only_two_hard_changes(self):
        xy=np.c_[np.linspace(0,1.4,8),[0,.02,.08,.12,.1,.08,.1,.13]];B=[.1,.005,.1];vw=[.2,.1];f=Field()
        old=ClearanceGraph(xy,B,vw,f);new=NormalGraph(xy,B,vw,f)
        self.assertEqual([k for k in old.p if old.p[k]!=new.p[k]],['curvature_limit_m_inv'])
        x=old.initial.ravel();np.testing.assert_array_equal(old.residual_jacobian(x)[0],new.residual_jacobian(x)[0])
        np.testing.assert_array_equal(old.residual_jacobian(x)[1],new.residual_jacobian(x)[1])
        np.testing.assert_array_equal(old.initial,new.initial)
        np.testing.assert_allclose(new.constraints(x)[1],jacobian(new.constraints,x),atol=1e-5,rtol=1e-5)
        with self.assertRaises(ValueError):NormalGraph(xy,B,[.1,.3],f)
    def test_repair_gradient_and_frozen_cost(self):
        # Avoid equal-|k| branch boundaries for a central-difference check.
        B=[0,0,.1];q=np.c_[np.linspace(0,1.2,8),[0,.012,.039,.073,.094,.081,.108,.157]];f=Field()
        old=RepairGraphR2(q,B,f);new=RepairGraph(q,B,f);x=new.initial
        np.testing.assert_array_equal(old.residual_jacobian(x)[0],new.residual_jacobian(x)[0])
        np.testing.assert_array_equal(old.bounds.lb,new.bounds.lb)
        np.testing.assert_allclose(new.constraints(x)[1],jacobian(new.constraints,x),atol=1e-5,rtol=1e-5)
        self.assertEqual(old.near_threshold,new.near_threshold)
    def test_detour_gradient_and_frozen_cost(self):
        f=Field();old=KnownDetourGraph([0,0,0],[1,0],f,f,30);new=DetourGraph([0,0,0],[1,0],f,f,30)
        x=new.initial.copy();x[1::2]+=.01*np.sin(np.arange(10)*1.3)
        np.testing.assert_array_equal(old.residual_jacobian(x)[0],new.residual_jacobian(x)[0])
        np.testing.assert_allclose(new.constraints(x)[1],jacobian(new.constraints,x),atol=1e-5,rtol=1e-5)
        r=DetourGraph([0,0,0],[1,0],f,f,0).solve();self.assertTrue(r['accepted']);self.assertLessEqual(r['maximum_abs_curvature_m_inv'],2+1e-7);json.dumps(r,allow_nan=False)
    def test_storage_v2_nonempty_and_empty_bitwise(self):
        for empty in (False,True):
            occ=np.zeros((14,15),bool)
            if not empty:occ[6,7]=True
            d=dict(occupied=occ,observed=~occ,origin=np.array([-.13,-.23]),h=np.array(.01),radius=np.array(.09))
            values=reconstruct(d)
            if empty:values.fill(np.nextafter(values[0,0],np.inf))
            s=SimpleNamespace(**d,values=values,metadata=MappingProxyType({'frame_id':3,'sim_s':.75}),last_free_tick=np.zeros(occ.shape,np.int32),
                first_free_tick=np.full(occ.shape,-1,np.int32),first_occupied_tick=np.full(occ.shape,-1,np.int32),new_component_ids=np.zeros(occ.shape,np.int32),component_births=MappingProxyType({1:3}))
            original=snapshot_arrays(s)
            with tempfile.TemporaryDirectory() as td:
                file=Path(td)/'snapshot.npz';save_snapshot(s,file,compressed=False)
                with np.load(file) as z:self.assertNotIn('values',z.files)
                restored=load_npz(file);self.assertEqual(set(original),set(restored));self.assertTrue(all(bit_equal(v,restored[k]) for k,v in original.items()))
                loaded=load_snapshot(Snapshot,file);self.assertTrue(bit_equal(loaded.values,s.values));self.assertEqual(dict(loaded.metadata),dict(s.metadata));self.assertFalse(loaded.values.flags.writeable)
                self.assertTrue(all(bit_equal(v,snapshot_arrays(s)[k]) for k,v in original.items()))

if __name__=='__main__':unittest.main()
