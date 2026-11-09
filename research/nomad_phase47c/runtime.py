"""Unchanged Phase41 raw localization or frozen Phase43 HMM, per method."""
from nomad_phase41.runtime import install as original_localization,run_without_oracle
from nomad_phase43p.runtime import install as hmm_localization


def install(config):
    if config['phase47c_method']=='OURS-DETOUR+HMM':hmm_localization(config)
    else:original_localization(config)
