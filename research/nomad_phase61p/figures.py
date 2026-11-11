"""Same saved-run drawing; label the oracle analysis condition visibly."""
import inspect
from nomad_phase57p import figures as previous
source=inspect.getsource(previous.generate).replace('Phase57-P','Phase61-P ORACLE (analysis only)')
ns=dict(previous.generate.__globals__);exec(compile(source,__file__,'exec'),ns);generate=ns['generate']
