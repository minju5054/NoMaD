"""Phase26 launcher unchanged except the explicit hash exception and provenance."""
from nomad_phase26 import launch as base
from .config import verify,registration

def main():
    base.verify=verify
    write=base.write_json
    def provenance(path,value):
        if path.name=='provenance.json':
            value=dict(value,phase='27-R',base_phase='26',phase27r_registration=registration())
        return write(path,value)
    base.write_json=provenance
    base.main()

if __name__=='__main__':main()
