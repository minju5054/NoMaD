"""Same saved-log top-down renderer as Phase59; title only changes."""
import inspect
from nomad_phase57p import figures as previous
source=inspect.getsource(previous.generate).replace('Phase57-P','Phase60-P')
ns=dict(previous.generate.__globals__);exec(compile(source,__file__,'exec'),ns);generate=ns['generate']
