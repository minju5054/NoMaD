"""RTC hard-masking ablation (DDPM adaptation), not original flow-policy RTC."""
import numpy as np
from nomad_phase7.rtc import diffuse as soft_diffuse

def diffuse(model,condition,noise,seed,y,w,d,beta=5.):
    if not np.any(w) or d==0:return soft_diffuse(model,condition,noise,seed,y,w,beta)
    import torch
    from nomad_preflight.native import scheduler,get_action,ROBOT
    device=noise.device;actions=noise.clone();schedule=scheduler()
    cond=condition.detach();cond=cond.repeat(noise.shape[0],1) if cond.ndim==2 else cond.repeat(noise.shape[0],1,1)
    target=torch.as_tensor(y,dtype=noise.dtype,device=device)[None]
    weight=torch.as_tensor(w,dtype=noise.dtype,device=device)[None,:,None]
    # Independent deterministic mask stream never advances the DDPM scheduler RNG.
    generator=torch.Generator(device=device).manual_seed(seed ^ 0x5A17)
    with torch.random.fork_rng(devices=[device.index or 0]):
        torch.manual_seed(seed)
        for k in schedule.timesteps[:]:
            alpha=schedule.alphas_cumprod[k].to(device)
            eps_mask=torch.randn(actions[:,:d].shape,device=device,dtype=actions.dtype,generator=generator)
            actions[:,:d]=alpha.sqrt()*target[:,:d]+(1-alpha).sqrt()*eps_mask
            with torch.enable_grad():
                x=actions.detach().requires_grad_(True)
                eps=model('noise_pred_net',sample=x,timestep=k,global_cond=cond)
                x0=(x-(1-alpha).sqrt()*eps)/alpha.sqrt()
                gradient=torch.autograd.grad(torch.sum((weight*(target-x0))**2),x)[0]
                eta=.5*torch.minimum(beta*(1-alpha),alpha)
                corrected=(x-eta*gradient).detach()
                # RePaint prefix is fixed at the current noise level, including after VJP.
                corrected[:,:d]=alpha.sqrt()*target[:,:d]+(1-alpha).sqrt()*eps_mask
            with torch.no_grad():
                eps=model('noise_pred_net',sample=corrected,timestep=k,global_cond=cond)
                actions=schedule.step(model_output=eps,timestep=k,sample=corrected).prev_sample
        actions[:,:d]=target[:,:d]
    cumulative=get_action(actions);metric=cumulative*(ROBOT['max_v']/ROBOT['frame_rate'])
    return dict(normalized_diffusion=actions,cumulative=cumulative,metric=metric,selected_waypoint=metric[0,2].clone())
