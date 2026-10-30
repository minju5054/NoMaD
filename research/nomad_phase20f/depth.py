"""Reuse20D publish-before-archive thread; replace only map/history snapshot types."""
from types import FunctionType
from nomad_phase20d.depth import DepthMapThread as Previous
from .history import HistoryMap,HistorySnapshot

class DepthMapThread(Previous):
    __init__=FunctionType(Previous.__init__.__code__,{**Previous.__init__.__globals__,'RecentMap':HistoryMap,'RecentSnapshot':HistorySnapshot})
    run=FunctionType(Previous.run.__code__,{**Previous.run.__globals__,'RecentMap':HistoryMap,'RecentSnapshot':HistorySnapshot})
