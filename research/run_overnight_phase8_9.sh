#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.." || exit 1
unset LD_LIBRARY_PATH LD_PRELOAD PYTHONHOME VIRTUAL_ENV
export PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
exec /usr/bin/python3 -m nomad_phase8.overnight
