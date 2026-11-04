"""Original V1/shadow/recency publisher plus persistent component metadata."""
import types
from nomad_phase20f.depth import DepthMapThread as Original
from nomad_phase20f.history import HistorySnapshot
from nomad_phase24.retention import archive_compact,full_frames
from .trigger import PersistentMap

class DepthMapThread(Original):
    _initialize=types.FunctionType(Original.__init__.__code__,dict(Original.__init__.__globals__,RecentMap=PersistentMap,RecentSnapshot=HistorySnapshot))
    def __init__(self,*a,**kw):self.full_frames=full_frames();self._initialize(*a,**kw)
    def archive(self):
        if self.full_frames:return super().archive()
        return archive_compact(self)
    def retain_latest(self):
        if not self.full_frames:self.archive_queue.put_nowait((self.snapshot(),None,None))
