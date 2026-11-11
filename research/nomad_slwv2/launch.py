import sys
from nomad_j0 import launch as frozen
from .config import bind,HERE,SCENES,INDICES,DELAYS,METHOD,verify
build=bind(frozen.build,HERE=HERE,SCENES=SCENES,INDICES=INDICES,DELAYS=DELAYS,METHOD=METHOD,verify=verify)
parser=bind(frozen.parser,SCENES=SCENES,INDICES=INDICES,DELAYS=DELAYS,METHOD=METHOD)

def write(path,value):
    if path.name=='provenance.json':value=dict(value,phase='SLW-v2 J0 screen')
    frozen.atomic_json(path,value)

def main():
    if '--dry-run' not in sys.argv:verify(require_assets=True)
    bind(frozen.main,build=build,parser=parser,verify=verify,atomic_json=write)()

if __name__=='__main__':main()
