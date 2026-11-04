"""Reuse every Phase24-R interface, replace only G with the new subclass."""
from nomad_phase24r.online_execution import install as frozen_install, run_without_oracle


def install():
    frozen_install()
    import nomad_phase15b.execution as factory
    previous = factory.make_execution

    def make(c, out):
        if c['phase24r_method'] == 'G':
            from .live import DecisionGraphExecution
            return DecisionGraphExecution(c, out)
        return previous(c, out)

    factory.make_execution = make
