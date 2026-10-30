import unittest
from types import SimpleNamespace
import numpy as np
from .history import CellHistory,active_components
from .direction import component_direction,inside_rectangle
from .trigger import choose_ahead,no_new_obstacle_ahead


def snap(history,occupied):
    return SimpleNamespace(occupied=occupied.copy(),first_free_tick=history.first_free_tick.copy(),first_occupied_tick=history.first_occupied_tick.copy(),
        new_component_ids=history.new_component_ids.copy(),component_births=history.births.copy(),origin=np.zeros(2),h=.01,metadata={})

class Tests(unittest.TestCase):
    def test_free_to_occupied_window_and_size(self):
        h=CellHistory((120,120));free=np.full((120,120),-1,np.int32);occ=np.zeros_like(free,dtype=bool)
        free[10,50:55]=0;h.update(free,occ,0);occ[10,50:54]=True;h.update(free,occ,72)
        self.assertFalse(np.any(h.new_component_ids));occ[10,54]=True;h.update(free,occ,80);s=snap(h,occ)
        self.assertEqual(len(active_components(s,792)),1);self.assertEqual(len(active_components(s,793)),0)
        identity=int(h.new_component_ids[10,50]);birth=h.births[identity];h.update(free,occ,100)
        self.assertEqual(int(h.new_component_ids[10,50]),identity);self.assertEqual(h.births[identity],birth)
    def test_existing_wall_never_new(self):
        h=CellHistory((120,120));free=np.full((120,120),-1,np.int32);occ=np.zeros_like(free,dtype=bool);occ[10,50:60]=True
        h.update(free,occ,0);free[10,50:60]=72;h.update(free,occ,144)
        self.assertFalse(active_components(snap(h,occ),144))
        poses=np.zeros((217,3));choice,_=choose_ahead(snap(h,occ),poses,216,{})
        self.assertIsNone(choice)
    def test_direction_and_termination(self):
        poses=np.zeros((401,3));poses[:,0]=np.arange(401)/72*.2
        u,info=component_direction(poses,216);np.testing.assert_allclose(u,[1,0]);self.assertAlmostEqual(info['displacement_m'],.6)
        poses[:,:2]=0;poses[:,2]=np.pi/2;u,info=component_direction(poses,216);np.testing.assert_allclose(u,[0,1],atol=1e-12)
        h=CellHistory((120,120));free=np.full((120,120),-1,np.int32);occ=np.zeros_like(free,dtype=bool);free[10,50:55]=0;h.update(free,occ,0);occ[10,50:55]=True;h.update(free,occ,72);s=snap(h,occ)
        self.assertFalse(no_new_obstacle_ahead(s,[0,0,0],72,[1,0]));self.assertTrue(no_new_obstacle_ahead(s,[.6,0,0],72,[1,0]))
        self.assertTrue(no_new_obstacle_ahead(s,[0,0,0],793,[1,0]))
    def test_snapshot_age_rechecks_five_cell_rule(self):
        h=CellHistory((120,120));free=np.full((120,120),-1,np.int32);occ=np.zeros_like(free,dtype=bool);free[10,50:55]=0;h.update(free,occ,0)
        occ[10,50:52]=True;h.update(free,occ,72);occ[10,52:55]=True;h.update(free,occ,100)
        self.assertEqual(len(active_components(snap(h,occ),792)),1);self.assertFalse(active_components(snap(h,occ),793))
if __name__=='__main__':unittest.main()
