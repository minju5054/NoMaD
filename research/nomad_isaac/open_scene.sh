#!/usr/bin/env bash
# Open an existing USD with Isaac's native GUI; no inference or new navigation.
# Isolate inherited Python/CUDA/ROS library paths only for the child process.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
artifact_root="$(cd -- "$repo_root/../artifacts/isaac6" && pwd)"
isaac_root=/home/gpuadmin/isaacsim
scene="${1:-$artifact_root/static_obstacle_video_02/recorded_motion_gui.usda}"
opener="$isaac_root/extscache/omni.usd-1.16.0+f9bf0dda.lx64.r.cp312/scripts/open_stage.py"
portable_root="$artifact_root/gui_obstacle_check_02/portable"

if [[ $# -gt 1 ]]; then
    echo "Usage: bash $0 [existing_scene.usda]" >&2
    exit 2
fi
for required_file in "$isaac_root/isaac-sim.sh" "$opener" "$scene"; do
    if [[ ! -f "$required_file" ]]; then
        echo "Missing required file: $required_file" >&2
        exit 1
    fi
done
scene="$(realpath -e -- "$scene")"

exec env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV \
    "$isaac_root/isaac-sim.sh" \
    --no-ros-env \
    --/app/settings/persistent=false \
    --/isaac/startup/create_new_stage=false \
    --/isaac/startup/ros_bridge_extension="" \
    --/rtx/hydra/supportMultiTickRate=false \
    --portable-root "$portable_root" \
    --exec "$opener $scene"
