"""Process-local factory injection; existing C0/C1 method code is imported intact."""
from nomad_phase21.execution import make_execution as baseline,install as baseline_install,run_without_oracle

def make_execution(c,out):
    if c['phase24_method']=='G':
        from .live import DecisionGraphExecution
        return DecisionGraphExecution(c,out)
    return baseline(c,out)

def install():
    baseline_install()
    import nomad_phase15b.execution as factory
    factory.make_execution=make_execution
