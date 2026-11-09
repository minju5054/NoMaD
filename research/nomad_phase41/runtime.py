"""Common stop option only; Phase38 method factories remain unchanged."""
from nomad_phase38.runtime import install as frozen_install,run_without_oracle
from .stop import install as install_stop


def install(config):
    frozen_install(config)
    install_stop()
