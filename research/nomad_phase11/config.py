import json
from nomad_isaac.common import ROOT


def protocol():
    return json.loads((ROOT/'research/nomad_phase11/protocol.json').read_text())


def validate_flag(a):
    assert a.overnight_phase==9 and a.overnight_method=='GRAPH-v6'
    assert a.phase4c_method=='GRAPH' and a.asynchronous and a.pure_pursuit
    i=int(a.run_id[-2:]);assert a.run_id==f'S1_{i:02d}' and a.seed_offset==10000*i
    assert a.uniform_delivery_delay_s in (0.,.75)
    assert 1<=i<=(8 if a.uniform_delivery_delay_s==.75 and not getattr(a,'phase10b_no_obstacle',False) else 4)
