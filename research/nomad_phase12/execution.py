"""Geometry-only baseline hook. Original methods are routed to OvernightExecution."""
import json
import numpy as np
from nomad_isaac.common import local_to_world
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase4c.execution import AccelExecution
from nomad_phase4c.plant import control_command
from .methods import PATH_BASELINES,TransitionState


class BaselineExecution(AccelExecution):
    def __init__(self,config,out):
        assert config['phase12_method'] in PATH_BASELINES and config['phase4c_method']=='CURV'
        super().__init__(config,out);self.named_method=config['phase12_method'];self.state=TransitionState(self.named_method)
        self.last_application_ns=None;self.applications=(out/'phase6_applications.jsonl').open('x')
        self.oracle=(out/'overnight_oracle.jsonl').open('x')
    def apply(self,core,refresh,switch):
        before=list(self.last_command);original=None;detail=None
        if switch is not None:
            original=switch['chunk'];samples=np.array([local_to_world(np.asarray(x),np.asarray(switch['observation_pose'])) for x in switch['overnight_metric_samples']])
            xy,detail=self.state.switch(samples,core.pose,switch['id'],switch['received_monotonic_ns'],refresh['monotonic_ns'])
            try:XYPath(xy);valid=True
            except ValueError:valid=False
            switch['chunk']={**original,'world_xy_m':xy.tolist(),'path_valid':valid}
            switch['phase12']=dict(method=self.named_method,detail=detail,applied_initial_world_xy=xy.tolist(),oracle_used=False)
        try:super().apply(core,refresh,switch)
        finally:
            if original is not None:switch['chunk']=original
        if self.named_method=='TEMPORAL-ENSEMBLE':
            diag,ensemble=self.state.ensemble.control(core.pose,refresh['monotonic_ns'])
            pp=refresh['pure_pursuit'];flags={'CURVATURE_SATURATED':False,'ACCEL_LIMITED':False,'OMEGA_CLIPPED':False};kappa=None
            reason=refresh['status'] if not refresh['valid'] else 'no_valid_chunk' if diag is None else 'endpoint' if diag['endpoint_stop'] else None
            command=(0.,0.)
            if diag is not None:pp.update(diag)
            pp.update(stop_reason=reason,path_valid=diag is not None)
            if reason is None:
                x,y=diag['target_local_x_m'],diag['target_local_y_m'];kappa=2*y/(x*x+y*y) if x*x+y*y>1e-24 else 0.
                command,flags=control_command('CURV',kappa,before[0],self.plant.actual_w,self.plant.alpha)
            core.v,core.w=command;self.last_command=list(command)
            refresh.update(commanded_v_m_s=core.v,commanded_w_rad_s=core.w,applied_v_m_s=core.v,applied_w_rad_s=self.plant.actual_w,
                applied_command_source=self.named_method if reason is None else reason,
                stage2={**flags,'method':'CURV','kappa_pp':kappa,'corrected_path_active':False,'graph_applied_job':None,
                        'fresh_switch_sim_s':self.fresh_switch_s},phase12_ensemble=ensemble)
            if switch is not None:
                switch.update({k:refresh[k] for k in ('commanded_v_m_s','commanded_w_rad_s','applied_v_m_s','applied_w_rad_s','applied_command_source','stage2','pure_pursuit','phase12_ensemble')})
                switch['chunk_transition'].update(command_after=self.last_command,command_delta=(np.asarray(self.last_command)-before).tolist())
        refresh['phase12_method']=self.named_method
        if switch is not None:
            path=self.follower.path if self.follower is not None else None;s,d=path.project(core.pose[:2]) if path else (None,None)
            row=dict(tick=round(refresh['simulation_time_s']*72),simulation_time_s=refresh['simulation_time_s'],monotonic_ns=refresh['monotonic_ns'],
                id=self.active_id,pose=core.pose.tolist(),kind=self.named_method,graph_job_id=None,selected_sample=detail.get('selected_sample',0),
                world_xy=path.points.tolist() if path else None,path_length_m=float(path.s[-1]) if path else None,projected_arclength_m=s,projection_distance_m=d,
                staleness=float(s/path.s[-1]) if path else None,before_vw=before,after_vw=list(self.last_command),abs_dw=abs(self.last_command[1]-before[1]))
            if self.named_method=='TEMPORAL-ENSEMBLE':
                row.update(ensemble_components=refresh['phase12_ensemble']['components'],world_xy_role='latest native only; ensemble has no single path')
            self.applications.write(json.dumps(row)+'\n');self.applications.flush();self.last_application_ns=refresh['monotonic_ns']
    def close(self):
        self.oracle.close();self.applications.close();super().close()
