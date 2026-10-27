#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 3 ]; then echo "Usage: $0 <png-directory> <frame-time-csv> <unique-run-id>" >&2; exit 2; fi
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
dataset=$(realpath -e "$1")
time_csv=$(realpath -e "$2")
run=$3
if [[ ! "$run" =~ ^[a-zA-Z0-9_-]+$ ]]; then echo 'Invalid run ID' >&2; exit 2; fi
upstream="$root/thirdparty/MASt3R-SLAM"; env_dir="$root/thirdparty/mast3r-env"
result="$root/results/E1_baseline_reproduction/$(date +%F)/$run"
if [ -e "$result" ] || [ -e "$upstream/logs/$run" ]; then echo 'Run ID already exists' >&2; exit 2; fi
mkdir -p "$result"
export CUDA_HOME="$env_dir" PATH="$env_dir/bin:$PATH" TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 E1_PROVENANCE_PATH="$result/provenance.npz"
unset MAST3R_SLAM_IMAGE_SIZE
cd "$upstream"
set +e
/usr/bin/time -v "$env_dir/bin/python" main.py --dataset "$dataset" --config "$root/configs/E0_environment_preparation/low_vram_base.yaml" --no-viz --save-as "$run" --keyframe-buffer 64 --low-vram --frame-time-csv "$time_csv" --min-keyframe-seconds 1 --force-periodic-keyframes > "$result/run.log" 2>&1
status=$?
set -e
if [ -d "$upstream/logs/$run" ]; then mv "$upstream/logs/$run" "$result/output"; fi
printf '%s\n' "$status" > "$result/exit_code.txt"
echo "Run status: $status; results: $result"
exit "$status"
