import numpy as np
from nomad_phase7.rtc import target

def rtc_target(snapshot):
    if snapshot.get('command_valid') and snapshot.get('old_world_xy') is not None:
        try:
            result=target(snapshot['old_world_xy'],snapshot['pose'],snapshot.get('actual_vw',[0,0])[0],.888536777)
            return {**result,'old_id':snapshot['applied_id'],'observation_tick':snapshot['tick']}
        except ValueError as exc:reason=str(exc)
    else:reason='No valid OLD path at observation snapshot'
    return dict(Y=np.zeros((8,2)).tolist(),W=np.zeros(8).tolist(),d=0,H_old=0,target_local_xy_m=[],old_id=snapshot.get('applied_id',-1),observation_tick=snapshot['tick'],disabled_reason=reason)
