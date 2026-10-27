#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
upstream="$root/thirdparty/MASt3R-SLAM"
env_dir="$root/thirdparty/mast3r-env"
result="$root/results/E0a_keyframe_spacing/2026-10-27"
export CUDA_HOME="$env_dir" PATH="$env_dir/bin:$PATH" TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1
unset MAST3R_SLAM_IMAGE_SIZE
cd "$upstream"
for variant in control candidate_2s; do
  case "$variant" in control) gap=0 ;; candidate_2s) gap=2 ;; esac
  run="E0a_${variant}_512"
  if [ -e "$result/$variant" ] || [ -e "$upstream/logs/$run" ]; then echo "Run exists: $variant" >&2; exit 2; fi
  mkdir -p "$result/$variant"
  nvidia-smi --query-gpu=timestamp,memory.used,memory.total --format=csv,nounits -l 1 > "$result/$variant/gpu.csv" &
  monitor=$!
  trap 'kill "$monitor" 2>/dev/null || true' EXIT
  set +e
  /usr/bin/time -v timeout 900 "$env_dir/bin/python" main.py --dataset "$root/data/HKairport01/mapping" --config "$root/configs/E0_environment_preparation/low_vram_base.yaml" --no-viz --save-as "$run" --keyframe-buffer 32 --low-vram --frame-time-csv "$root/data/HKairport01/mapping_frames.csv" --min-keyframe-seconds "$gap" > "$result/$variant/run.log" 2>&1
  status=$?
  set -e
  kill "$monitor" 2>/dev/null || true
  wait "$monitor" 2>/dev/null || true
  trap - EXIT
  if [ -d "$upstream/logs/$run" ]; then mv "$upstream/logs/$run" "$result/$variant/output"; fi
  printf '%s\n' "$status" > "$result/$variant/exit_code.txt"
  echo "$variant exit=$status"
  if [ "$status" -ne 0 ]; then exit "$status"; fi
done
