#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
run=e3_fusion_20261028
out="$root/results/E3_fusion/2026-10-28/instrumented"
upstream="$root/thirdparty/MASt3R-SLAM"
env_dir="$root/thirdparty/mast3r-env"
if [ -e "$out/exit_code.txt" ] || [ -e "$upstream/logs/$run" ]; then
  echo 'Run already exists; preserve it and select a new run ID.' >&2; exit 2
fi
mkdir -p "$out/events"
export CUDA_HOME="$env_dir" PATH="$env_dir/bin:$PATH" TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1
export E3_OUTPUT="$out/events" E3_RUN_ID="$run" E1_PROVENANCE_PATH="$out/provenance.npz"
unset MAST3R_SLAM_IMAGE_SIZE
cd "$upstream"
set +e
/usr/bin/time -v "$env_dir/bin/python" "$root/scripts/E3_fusion/run_instrumented.py" > "$out/run.log" 2>&1
status=$?
set -e
if [ -d "$upstream/logs/$run" ]; then mv "$upstream/logs/$run" "$out/output"; fi
printf '%s\n' "$status" > "$out/exit_code.txt"
exit "$status"
