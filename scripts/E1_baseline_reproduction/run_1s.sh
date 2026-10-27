#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
upstream="$root/thirdparty/MASt3R-SLAM"
env_dir="$root/thirdparty/mast3r-env"
result="$root/results/E1_baseline_reproduction/2026-10-27/one_second"
export CUDA_HOME="$env_dir" PATH="$env_dir/bin:$PATH" TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1
unset MAST3R_SLAM_IMAGE_SIZE
cd "$upstream"
for mode in baseline instrumented; do
 run="E1_1s_${mode}"
 if [ -e "$result/$mode/exit_code.txt" ] || [ -e "$upstream/logs/$run" ]; then echo "Existing run: $mode" >&2; exit 2; fi
 mkdir -p "$result/$mode"
 if [ "$mode" = instrumented ]; then export E1_PROVENANCE_PATH="$result/$mode/provenance.npz"; else unset E1_PROVENANCE_PATH; fi
 nvidia-smi --query-gpu=timestamp,memory.used,memory.total --format=csv,nounits -l 1 > "$result/$mode/gpu.csv" & monitor=$!
 trap 'kill "$monitor" 2>/dev/null || true' EXIT
 set +e
 /usr/bin/time -v timeout 900 "$env_dir/bin/python" main.py --dataset "$root/data/HKairport01/mapping" --config "$root/configs/E0_environment_preparation/low_vram_base.yaml" --no-viz --save-as "$run" --keyframe-buffer 32 --low-vram --frame-time-csv "$root/data/HKairport01/mapping_frames.csv" --min-keyframe-seconds 1 > "$result/$mode/run.log" 2>&1
 status=$?
 set -e
 kill "$monitor" 2>/dev/null || true
 wait "$monitor" 2>/dev/null || true
 trap - EXIT
 if [ -d "$upstream/logs/$run" ]; then mv "$upstream/logs/$run" "$result/$mode/output"; fi
 printf '%s\n' "$status" > "$result/$mode/exit_code.txt"
 echo "$mode exit=$status"
 if [ "$status" -ne 0 ]; then exit "$status"; fi
done
