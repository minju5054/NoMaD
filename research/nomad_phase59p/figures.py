"""Same saved-run top-down rendering as Phase58; title changes only."""
import inspect
from nomad_phase57p import figures as previous
source=inspect.getsource(previous.generate).replace('Phase57-P','Phase59-P')
ns=dict(previous.generate.__globals__);exec(compile(source,__file__,'exec'),ns);generate=ns['generate']
