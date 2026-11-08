import unittest
from .evaluate import trigger_gate

def row(old,new,label='BOX_AHEAD',old_wrong=False,new_wrong=False):
    return dict(original_fire=old,TRIG_fire=new,original_label=label,TRIG_label=label,
                original_direction_wrong=old_wrong,TRIG_direction_wrong=new_wrong)

class GateTests(unittest.TestCase):
    def test_registered_boundaries(self):
        rows=[row(True,True,old_wrong=True) for _ in range(4)]+[row(True,True) for _ in range(15)]+[row(True,False)]
        rows += [row(True,i<5,'PASSED_BOX') for i in range(10)]
        result=trigger_gate(rows);self.assertEqual(result['box_recall'],.95);self.assertEqual(result['label'],'OFFLINE_OK')
        rows[4]['TRIG_fire']=False;self.assertEqual(trigger_gate(rows)['label'],'OFFLINE_FAIL')

    def test_static_events_not_in_gate_denominators(self):
        rows=[row(True,True,old_wrong=True)];base=trigger_gate(rows)
        rows += [row(False,True,'STATIC_AHEAD',new_wrong=True) for _ in range(200)]
        self.assertEqual(trigger_gate(rows),base)

    def test_no_box_evidence_cannot_claim_pass(self):
        r=trigger_gate([row(True,True,'NOTHING_AHEAD')])
        self.assertEqual(r['label'],'OFFLINE_FAIL');self.assertIsNone(r['box_recall'])

if __name__=='__main__':unittest.main()
