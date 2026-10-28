#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
run=e7b_amtown_backend
out="$root/results/E7b_geometry_diagnostic/2026-10-28/$run"
upstream="$root/thirdparty/MASt3R-SLAM"; env_dir="$root/thirdparty/mast3r-env"
if [ -e "$out" ] || [ -e "$upstream/logs/$run" ]; then echo 'Existing run; refusing overwrite' >&2; exit 2; fi
mkdir -p "$out/events"
export CUDA_HOME="$env_dir" PATH="$env_dir/bin:$PATH" TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 E1_PROVENANCE_PATH="$out/provenance.npz" E7B_EVENTS="$out/events" PYTHONPATH="$root/scripts/E7b_geometry_diagnostic:$upstream${PYTHONPATH:+:$PYTHONPATH}"
unset MAST3R_SLAM_IMAGE_SIZE
"$env_dir/bin/python" - "$upstream/main.py" "$out/main_e7b.py" <<'PY'
import pathlib,sys
s=pathlib.Path(sys.argv[1]).read_text();needle='if __name__ == "__main__":';assert s.count(needle)==1
pathlib.Path(sys.argv[2]).write_text(s.replace(needle,'from backend_probe import run_backend\n\n'+needle))
PY
cd "$upstream"
set +e
/usr/bin/time -v "$env_dir/bin/python" "$out/main_e7b.py" --dataset "$root/data/AMtown01/mapping" --config "$root/configs/E0_environment_preparation/low_vram_base.yaml" --no-viz --save-as "$run" --keyframe-buffer 64 --low-vram --frame-time-csv "$root/data/AMtown01/mapping_frames.csv" --min-keyframe-seconds 1 --force-periodic-keyframes > "$out/run.log" 2>&1
status=$?
set -e
if [ -d "$upstream/logs/$run" ]; then mv "$upstream/logs/$run" "$out/output"; fi
printf '%s\n' "$status" > "$out/exit_code.txt"
exit "$status"
