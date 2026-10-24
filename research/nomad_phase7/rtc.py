"""RTC-style (DDPM adaptation); geometric OLD suffix, no native action timestamps."""
import numpy as np
from nomad_phase0.pure_pursuit import XYPath


def target(old_world, observation_pose, v_now, t_est):
    path=XYPath(old_world);a=np.asarray(observation_pose,dtype=float)
    projected,_=path.project(a[:2])
    indices=np.flatnonzero(path.s>projected+1e-12)[:8]
    world=path.points[indices];h=len(indices)
    c,s=np.cos(a[2]),np.sin(a[2]);local=(world-a[:2])@np.array([[c,-s],[s,c]])
    delta=np.diff(np.vstack([np.zeros((1,2)),local]),axis=0)/.05
    y=np.zeros((8,2));y[:h]=2*(delta-np.array([-2.5,-4.]))/np.array([7.5,8.])-1
    d=int(np.sum(path.s[indices]-projected<=max(0.,v_now)*t_est))
    w=np.zeros(8);w[:d]=1.
    for i in range(d,h):
        ci=(h-i)/(h-d+1);w[i]=ci*np.expm1(ci)/np.expm1(1.)
    return dict(Y=y.tolist(),W=w.tolist(),d=d,H_old=h,target_local_xy_m=local.tolist(),
        projected_arclength_m=projected,old_waypoint_indices=indices.tolist(),v_now=v_now,T_est_s=t_est,
        frozen_distance_m=max(0.,v_now)*t_est)


def diffuse(model,condition,noise,seed,y,w,beta=5.):
    """VP/DDPM variance-preconditioned VJP; beta=5 from RTC Appendix A.4.

    E=sum((W*(Y-x0hat))**2). eta=.5*(1-alpha)*min(beta,alpha/(1-alpha)).
    Correct xt once, recompute epsilon, then use unchanged original DDPM step.
    The alpha cap prevents the explicit x0 Jacobian 1/sqrt(alpha) from blowing
    up at high noise. This discrete VP rule is an adaptation, not RTC's flow ODE.
    No clamp/copy of target waypoints, iterations beyond the10 DDPM steps or tuning.
    """
    import torch
    from nomad_preflight.native import scheduler,get_action,ROBOT
    from nomad_isaac.topomap_inference import diffuse_condition
    if not np.any(w):
        return diffuse_condition(model,condition,noise,seed)
    device=noise.device;actions=noise.clone();schedule=scheduler()
    cond=condition.detach();cond=cond.repeat(noise.shape[0],1) if cond.ndim==2 else cond.repeat(noise.shape[0],1,1)
    y=torch.as_tensor(y,dtype=noise.dtype,device=device)[None]
    w=torch.as_tensor(w,dtype=noise.dtype,device=device)[None,:,None]
    with torch.random.fork_rng(devices=[device.index or 0]):
        torch.manual_seed(seed)
        for k in schedule.timesteps[:]:
            with torch.enable_grad():
                x=actions.detach().requires_grad_(True)
                eps=model('noise_pred_net',sample=x,timestep=k,global_cond=cond)
                alpha=schedule.alphas_cumprod[k].to(device)
                x0=(x-(1-alpha).sqrt()*eps)/alpha.sqrt()
                loss=torch.sum((w*(y-x0))**2)
                gradient=torch.autograd.grad(loss,x)[0]
                eta=.5*torch.minimum(beta*(1-alpha),alpha)
                corrected=(x-eta*gradient).detach()
            with torch.no_grad():
                eps=model('noise_pred_net',sample=corrected,timestep=k,global_cond=cond)
                actions=schedule.step(model_output=eps,timestep=k,sample=corrected).prev_sample
    cumulative=get_action(actions);metric=cumulative*(ROBOT['max_v']/ROBOT['frame_rate'])
    return dict(normalized_diffusion=actions,cumulative=cumulative,metric=metric,selected_waypoint=metric[0,2].clone())
