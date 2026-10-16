#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"
# The official diffusion_policy setup.py uses find_packages but has namespace dirs.
# Explicit source paths avoid changing that external repository or global sys.path.
export PYTHONPATH="$repo_dir/research:$repo_dir/train:$repo_dir/external/diffusion_policy"
exec "$repo_dir/../.venv/bin/python" "$@"
