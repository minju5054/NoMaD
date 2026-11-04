"""Install Phase24-R shared depth/trigger semantics for G, C0 and C1."""
from nomad_phase21.execution import make_execution as baseline,install as baseline_install,run_without_oracle
from .trigger import PersistentNoProgress,choose_ahead,no_new_obstacle_ahead
from .depth import DepthMapThread
from .safety import certificate

def _shared_certificate(self,field,pose,tick,xy,B):
    strict=self._phase24r_cache(field,tick)
    return certificate(xy,B,field,strict)['passed']

def install():
    # Phase21's C0/C1 factories preserve their solver/weights. These globals are
    # the registered decision/depth interfaces used when each frozen executor
    # instantiates or checks its R3 path.
    baseline_install()
    import nomad_phase20f.runtime as f
    import nomad_phase20d.runtime as d
    import nomad_phase15b.execution as factory
    import nomad_phase15b.depth as depth
    f.NewObstacleNoProgress=PersistentNoProgress;f.choose_ahead=choose_ahead;f.no_new_obstacle_ahead=no_new_obstacle_ahead
    original_init=d.Execution.__init__
    if not getattr(d.Execution,'_phase24r_patched',False):
        def init(self,*args,**kwargs):
            original_init(self,*args,**kwargs);self._phase24r_cache_key=None;self._phase24r_strict=None
        def cache(self,field,tick):
            from nomad_phase20d.recent import build_cache
            key=(field.metadata['frame_id'],int(tick))
            if self._phase24r_cache_key!=key:self._phase24r_cache_key=key;self._phase24r_strict=build_cache(field,tick)[0]
            return self._phase24r_strict
        d.Execution.__init__=init;d.Execution._phase24r_cache=cache;d.Execution.certificate=_shared_certificate;d.Execution._phase24r_patched=True
    depth.DepthMapThread=DepthMapThread
    def make(c,out):
        if c['phase24r_method']=='G':
            from .live import DecisionGraphExecution
            return DecisionGraphExecution(c,out)
        return baseline(c,out)
    factory.make_execution=make
