"""Select frozen install entry points, never redefine a controller or factor."""
from nomad_phase26.execution import run_without_oracle

def install(config):
    method=config['phase31p_method']
    if method=='G18-R':
        from nomad_phase30r.runtime import install as frozen
    elif method=='C0-NA':
        from nomad_phase28.online_r1 import install as frozen
    elif method=='C0':
        from nomad_phase26.execution import install as frozen
    else:raise ValueError(method)
    frozen(config)
