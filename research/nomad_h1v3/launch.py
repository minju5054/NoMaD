"""Same J0 launcher, redirected to the one registered new scene."""
from nomad_j0 import launch as frozen
from .config import bind,HERE,SCENES,INDICES,DELAYS,METHOD,verify

build=bind(frozen.build,HERE=HERE,SCENES=SCENES,INDICES=INDICES,DELAYS=DELAYS,METHOD=METHOD,verify=verify)
parser=bind(frozen.parser,SCENES=SCENES,INDICES=INDICES,DELAYS=DELAYS,METHOD=METHOD)

def write(path,value):
    if path.name=='provenance.json':value=dict(value,phase='H1-v3 J0 screen')
    frozen.atomic_json(path,value)

main=bind(frozen.main,build=build,parser=parser,verify=verify,atomic_json=write)
if __name__=='__main__':main()
