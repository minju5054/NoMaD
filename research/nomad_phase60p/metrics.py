"""Only localization audit expectations change; frozen outcomes and metrics remain."""
import json
from pathlib import Path
import numpy as np
from nomad_phase40p.launch import bind
from nomad_phase43p import metrics as m43
from nomad_phase47c import metrics as m47
from nomad_phase53p import metrics as m53
from nomad_phase58p import metrics as m58
from nomad_phase59p.metrics import localization_metrics
from nomad_phase24r.online_metrics import rows
from .localization import Localization
from .config import load_model,MODEL_SHA256

def sign_audit(root):
    root=Path(root);model=load_model();events=rows(root/'model/inference.jsonl');positions=iter([e['observation_pose'][:2] for e in events]);expected=[]
    class AuditSelector(Localization):
        def select(self,*a,**kw):
            result=super().select(*a,**kw);expected.append(result);return result
    def factory(nodes):return AuditSelector(nodes,position_provider=lambda:next(positions))
    result=bind(m43.audit,Localization=factory)(root)
    assert len(expected)==len(events)
    for event,want in zip(events,expected):
        actual=event['topomap']['hmm'];reference=want['hmm']
        assert actual['transition_model']=='SIGN' and actual['model_sha256']==MODEL_SHA256 and actual['sigma2']==model['sigma2']
        assert actual['transition_half_width'] is None
        np.testing.assert_array_equal(actual['odometry_xy_m'],event['observation_pose'][:2])
        np.testing.assert_allclose([actual[k] for k in ('signed_forward_m','transition_mean_nodes','posterior_max')],
            [reference[k] for k in ('signed_forward_m','transition_mean_nodes','posterior_max')],atol=1e-12,rtol=0)
    return result
_a47=bind(m47.audit,hmm_audit=sign_audit)
_a53=bind(m53.audit,frozen_audit=_a47)
_a58=bind(m58.audit,frozen_audit=_a53)

def audit(root):
    r=_a58(root);c=json.loads((Path(root)/'scenario.json').read_text());model=load_model()
    assert c['phase60p_transition']=='SIGN' and c['phase60p_model_sha256']==MODEL_SHA256 and c['phase60p_sigma2']==model['sigma2']
    r.update(localization_metrics(root,r));r.update(transition_zero_width_count=None,transition_model='SIGN',model_sha256=MODEL_SHA256,sigma2=model['sigma2'])
    return r
