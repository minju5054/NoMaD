"""Reuse run top-down plots; oracle U-Graph condition is explicitly labelled."""
import inspect
from nomad_phase57p import figures as previous
source=inspect.getsource(previous.generate).replace('Phase57-P','Phase62-P UG-GOAL ORACLE (analysis only)')
ns=dict(previous.generate.__globals__);exec(compile(source,__file__,'exec'),ns);generate=ns['generate']
