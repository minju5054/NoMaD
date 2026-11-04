"""Process-local factory injection; existing C0/C1 method code is imported intact."""
from nomad_phase21.execution import make_execution as baseline,install as baseline_install
from .retention import retained_apply,run_without_oracle

def make_execution(c,out):
    if c['phase24_method']=='G':
        from .live import DecisionGraphExecution
        return retained_apply(DecisionGraphExecution(c,out))
    return retained_apply(baseline(c,out))

def install():
    baseline_install()
    import nomad_phase15b.execution as factory
    factory.make_execution=make_execution
    from .retention import install_depth_retention
    install_depth_retention()
