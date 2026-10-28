#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
run=e7a_amtown_probe
out="$root/results/E7a_overlap_support/2026-10-28/$run"
upstream="$root/thirdparty/MASt3R-SLAM"; env_dir="$root/thirdparty/mast3r-env"
if [ -e "$out" ] || [ -e "$upstream/logs/$run" ]; then echo 'Existing run; refusing overwrite' >&2; exit 2; fi
mkdir -p "$out/events"
export CUDA_HOME="$env_dir" PATH="$env_dir/bin:$PATH" TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 E1_PROVENANCE_PATH="$out/provenance.npz" E3_OUTPUT="$out/events" E3_RUN_ID="$run"
unset MAST3R_SLAM_IMAGE_SIZE
cd "$upstream"
set +e
/usr/bin/time -v "$env_dir/bin/python" "$root/scripts/E7a_overlap_support/run_instrumented.py" > "$out/run.log" 2>&1
status=$?
set -e
if [ -d "$upstream/logs/$run" ]; then mv "$upstream/logs/$run" "$out/output"; fi
printf '%s\n' "$status" > "$out/exit_code.txt"
exit "$status"
