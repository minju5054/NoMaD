from nomad_j0 import metrics as frozen
from .config import bind,protocol
checkpoint=bind(frozen.checkpoint,protocol=protocol)
audit=bind(frozen.audit,protocol=protocol,checkpoint=checkpoint)
