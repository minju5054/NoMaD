import json,unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase24r import trigger as original
from nomad_phase20f.history import CellHistory
from nomad_phase32o.evaluate import clean
from .rules import component_sets,choose_ahead,evaluate,outcome_envelope,view
from .evidence import published_free_witness


class ProvenanceTests(unittest.TestCase):
    def data(self):
        shape=(21,31);occupied=np.zeros(shape,bool);occupied[8:13,16]=True
        history=CellHistory(shape);history.update(np.zeros(shape,np.int32),occupied,72)
        f=SimpleNamespace(occupied=occupied,observed=np.ones(shape,bool),origin=np.array([-1.,-1.]),h=.1,radius=.09,
            new_component_ids=history.new_component_ids,component_births=history.births,metadata={})
        poses=np.zeros((433,3));return f,poses

    def test_all_proven_cells_reproduce_original_exactly(self):
        f,p=self.data();a=original.component_sets(f);b=component_sets(view(f,np.ones(f.occupied.shape,bool)))
        self.assertEqual(a.keys(),b.keys())
        for k in a:np.testing.assert_array_equal(a[k],b[k])
        old,_=original.choose_ahead(f,p,432,{})
        new=evaluate(f,np.ones(f.occupied.shape,bool),p,432)
        self.assertEqual(old,new['component']);self.assertTrue(new['fire'])

    def test_five_cells_required_after_filter(self):
        f,p=self.data();mask=np.ones(f.occupied.shape,bool);mask[8,16]=False
        self.assertIsNone(evaluate(f,mask,p,432)['component'])
        mask[8,16]=True;self.assertIsNotNone(evaluate(f,mask,p,432)['component'])

    def test_provenance_does_not_modify_birth_or_direction(self):
        f,p=self.data();p[72,2]=.1;mask=f.occupied.copy()
        r=evaluate(f,mask,p,432);self.assertEqual(r['component']['t_new_tick'],72)
        np.testing.assert_allclose(r['u_ref'],[np.cos(.1),np.sin(.1)])
        self.assertIs(choose_ahead.__code__,original.choose_ahead.__code__)

    def test_current_unknown_cells_still_excluded(self):
        f,p=self.data();f.observed[8,16]=False
        self.assertIsNone(evaluate(f,np.ones(f.occupied.shape,bool),p,432)['component'])

    def test_envelope_contains_every_small_unknown_assignment(self):
        f,p=self.data();f.occupied[8:13,18]=True;f.new_component_ids[8:13,18]=2;f.component_births[2]=90
        unknown=[(8,16),(9,16),(10,16),(11,16)];confirmed=f.occupied.copy()
        for cell in unknown:confirmed[cell]=False
        allowed={(x['fire'],x['component_id']) for x in outcome_envelope(f,confirmed,f.occupied,p,432)}
        for bits in range(1<<len(unknown)):
            mask=confirmed.copy()
            for i,cell in enumerate(unknown):mask[cell]=bool(bits&(1<<i))
            r=evaluate(f,mask,p,432);self.assertIn((r['fire'],r['component']['component_id'] if r['component'] else None),allowed)

    def test_json_and_input_arrays_unchanged(self):
        f,p=self.data();before=f.new_component_ids.copy();r=evaluate(f,f.occupied,p,432)
        json.dumps(clean(r),allow_nan=False);np.testing.assert_array_equal(before,f.new_component_ids)

    def test_witness_requires_final_observed_free_same_ray_frame(self):
        x=published_free_witness(np.array([1,0,1,1],bool),np.array([0,0,1,0],bool),np.array([10,10,10,9]),10,np.full(4,20))
        np.testing.assert_array_equal(x,[True,False,False,False])

    def test_free_after_first_occupied_is_not_prior_evidence(self):
        self.assertFalse(published_free_witness(np.array([True]),np.array([False]),np.array([20]),20,np.array([20]))[0])

    def test_old_timestamp_can_survive_observed_false(self):
        from nomad_phase20d.recent import RecentMap
        from nomad_phase20c.shadow import ShadowSDF
        f=object.__new__(RecentMap);f._free=np.zeros((2,3),np.uint8);f._hits=f._free.copy();f.observed=np.zeros((2,3),bool)
        f.last_free_tick=np.full((2,3),-1,np.int32);f.frame_tick=10
        def shadow_stub(self,*a,**kw):self._free[0,0]=1;return {}
        with patch.object(ShadowSDF,'accumulate',shadow_stub):f.accumulate(None)
        self.assertEqual(f.last_free_tick[0,0],10);self.assertFalse(f.observed[0,0])


class GateTests(unittest.TestCase):
    def rows(self):
        result=[]
        for label,n in [('BOX_AHEAD',20),('STATIC_AHEAD',10)]:
            for i in range(n):
                passed=label=='BOX_AHEAD' or i<5
                result.append(dict(original_fire=True,original_label=label,PROV_confirmed_fire=passed,PROV_confirmed_label=label,
                    PROV_fire_lower=passed,PROV_fire_upper=passed,PROV_nonbox_lower=passed and label!='BOX_AHEAD',PROV_nonbox_upper=passed and label!='BOX_AHEAD'))
        return result

    def test_gate_boundaries_include_static_in_nonbox(self):
        from .evaluate import gate
        rows=self.rows();rows[0].update(PROV_confirmed_fire=False,PROV_fire_lower=False,PROV_fire_upper=False)
        self.assertEqual(gate(rows)['label'],'PROV_OK')
        rows[-1].update(PROV_confirmed_fire=True,PROV_fire_lower=True,PROV_fire_upper=True,PROV_nonbox_lower=True,PROV_nonbox_upper=True)
        self.assertEqual(gate(rows)['label'],'PROV_FAIL')

    def test_missing_history_not_falsely_called_pass_or_fail(self):
        from .evaluate import gate
        rows=self.rows();rows[0].update(PROV_confirmed_fire=False,PROV_fire_lower=False);rows[1].update(PROV_confirmed_fire=False,PROV_fire_lower=False)
        self.assertEqual(gate(rows)['label'],'PROV_NOT_ESTABLISHED_MISSING_HISTORY')

if __name__=='__main__':unittest.main()
