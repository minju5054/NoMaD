import unittest
from types import SimpleNamespace
import numpy as np
from nomad_phase20f.history import CellHistory
from nomad_phase24r.trigger import choose_ahead
from .trig import ObservedTrigger
from .geometry import polygon,classify


class TriggerTests(unittest.TestCase):
    def data(self):
        field=SimpleNamespace(occupied=np.zeros((31,31),bool),observed=np.ones((31,31),bool),
            first_occupied_tick=np.full((31,31),-1,np.int32),origin=np.array([-1.,-1.]),h=.1,radius=.09,metadata={})
        field.occupied[8:13,16]=True;field.first_occupied_tick[field.occupied]=720
        poses=np.zeros((1001,3));poses[:721,0]=np.linspace(-1,0,721);poses[721:,0]=.05
        return field,poses

    def test_sudden_forward_appearance_has_original_tnew(self):
        field,poses=self.data();history=CellHistory(field.occupied.shape)
        history.update(np.zeros(field.occupied.shape,np.int32),field.occupied,720)
        field.new_component_ids=history.new_component_ids;field.component_births=history.births
        original,_=choose_ahead(field,poses,720,{})
        tracker=ObservedTrigger();new=tracker.choose(field,poses,720)
        self.assertEqual(original['t_new_tick'],new['t_ref_tick']);self.assertEqual(new['t_ref_tick'],720)
        np.testing.assert_array_equal(new['u_ref'],original['u_ref'])
        # Later robot heading/direction does not overwrite the established time.
        poses[900,2]=np.pi/2
        self.assertEqual(tracker.choose(field,poses,900)['t_ref_tick'],720)

    def test_new_free_to_occupied_evidence_not_required(self):
        field,poses=self.data();tracker=ObservedTrigger();self.assertIsNotNone(tracker.choose(field,poses,720))
        field.observed[:]=False;self.assertIsNone(tracker.choose(field,poses,728))

    def test_five_disconnected_cells_are_not_silently_excluded(self):
        field,poses=self.data();field.occupied[:]=False;field.occupied[10,12:21:2]=True
        field.first_occupied_tick[:]=-1;field.first_occupied_tick[field.occupied]=720
        c=ObservedTrigger().choose(field,poses,720);self.assertIsNotNone(c);self.assertEqual(c['cells_ahead'],5)

    def test_guard_ends_at_tref_not_current(self):
        field,poses=self.data();poses[0,:2]=[-1,0];poses[504,:2]=[.5,0];poses[720,:2]=[0,0]
        tracker=ObservedTrigger();u,detail=tracker.direction(poses,720)
        np.testing.assert_array_equal(u,[1,0]);self.assertTrue(detail['guard']['overridden'])
        poses[784,:2]=[0,-1];poses[1000,:2]=[0,0]
        np.testing.assert_array_equal(tracker.direction(poses,720)[0],[1,0])


class GeometryTests(unittest.TestCase):
    def box(self,center,passed=None):
        return dict(id='box',spawn_s=0.,passage_s=passed,polygon=polygon(dict(center_xy_m=center,size_xyz_m=[.2,.2,.8])))

    def test_labels_and_static_priority(self):
        B=[0,0,0];u=[1,0];near=self.box([.5,0]);wall=('wall',self.box([.8,0])['polygon'])
        self.assertEqual(classify(B,u,1.,[wall],[near])[0],'BOX_AHEAD')
        self.assertEqual(classify(B,u,1.,[wall],[self.box([-.5,0])])[0],'STATIC_AHEAD')
        self.assertEqual(classify(B,u,1.,[],[self.box([-.5,0])])[0],'PASSED_BOX')
        self.assertEqual(classify(B,u,1.,[],[self.box([2,0])])[0],'NOTHING_AHEAD')
        self.assertEqual(classify(B,u,1.,[],[])[0],'NOTHING_AHEAD')

if __name__=='__main__':unittest.main()
