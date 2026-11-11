"""Exactly the Phase18 paired seed-cluster bootstrap; RAW minus historical method."""
from nomad_phase18.statistics import paired as frozen_paired
from nomad_phase40p.launch import bind
from .config import METHOD,protocol
_paired=bind(frozen_paired,PROPOSED=METHOD)
def paired(records,comparator,scene=None):
    result=_paired(records,comparator,'checkpoint_time_s',alpha=protocol()['raw_comparison_alpha'],scene=scene)
    return dict(result,scope='EXPLORATORY different-day same-seed comparison;no confirmatory label')
