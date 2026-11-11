"""Same Phase57 saved-run top-down drawing; title only changes."""
import inspect
from nomad_phase57p import figures as previous
source=inspect.getsource(previous.generate).replace('Phase57-P','Phase58-P')
ns=dict(previous.generate.__globals__);exec(compile(source,__file__,'exec'),ns);generate=ns['generate']
