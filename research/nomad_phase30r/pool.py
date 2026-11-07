"""Original four-process R2/R3 broker; child-local R3 target substitution."""
import nomad_phase20d.pool as base
ORIGINAL_INITIALIZE=base.initialize

def initialize(queue):
    from .factors import install_detour_factor
    install_detour_factor();ORIGINAL_INITIALIZE(queue)

def main():
    base.initialize=initialize
    base.main()
if __name__=='__main__':main()
