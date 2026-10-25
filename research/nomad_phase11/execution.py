"""Only substitute the CPU Graph worker; scheduling and CURV are inherited."""
from nomad_phase8.execution import OvernightExecution
from .worker import Client


class AdaptiveExecution(OvernightExecution):
    def __init__(self,config,out,client=None):
        assert config.get('phase11_v61') and config['overnight_method']=='GRAPH-v6'
        super().__init__(config,out,Client(out) if client is None else client)
