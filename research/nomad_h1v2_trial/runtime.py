"""Only the environment changes. All control/Graph/EC functions are reused."""
from nomad_phase53p.runtime import install as frozen_install,run_without_oracle
from nomad_h1v2.scene import install_environment

def install(c):
    frozen_install(c)
    install_environment(c)
