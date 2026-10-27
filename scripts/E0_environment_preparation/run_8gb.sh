#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <dataset-path> <base|tum> <unique-run-id>" >&2
  exit 2
fi
root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
dataset_path=$(realpath -e "$1")
case "$2" in
  base) config_path="$root_dir/configs/E0_environment_preparation/low_vram_base.yaml" ;;
  tum) config_path="$root_dir/configs/E0_environment_preparation/low_vram_tum.yaml" ;;
  *) echo "Configuration must be base or tum" >&2; exit 2 ;;
esac
run_id=$3
if [[ ! "$run_id" =~ ^[a-zA-Z0-9_-]+$ ]]; then echo "Invalid run ID" >&2; exit 2; fi
upstream_dir="$root_dir/thirdparty/MASt3R-SLAM"
env_dir="$root_dir/thirdparty/mast3r-env"
output_dir="$root_dir/results/E0_environment_preparation/$(date +%F)/$run_id"
if [ -e "$output_dir" ] || [ -e "$upstream_dir/logs/$run_id" ]; then echo "Run ID already exists" >&2; exit 2; fi
mkdir -p "$output_dir"
export CUDA_HOME="$env_dir" PATH="$env_dir/bin:$PATH" TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1
unset MAST3R_SLAM_IMAGE_SIZE
cd "$upstream_dir"
set +e
/usr/bin/time -v "$env_dir/bin/python" main.py --dataset "$dataset_path" --config "$config_path" --no-viz --save-as "$run_id" --keyframe-buffer 32 --low-vram > "$output_dir/run.log" 2>&1
status=$?
set -e
if [ -d "$upstream_dir/logs/$run_id" ]; then mv "$upstream_dir/logs/$run_id" "$output_dir/output"; fi
printf '%s\n' "$status" > "$output_dir/exit_code.txt"
echo "Run status: $status; results: $output_dir"
exit "$status"
