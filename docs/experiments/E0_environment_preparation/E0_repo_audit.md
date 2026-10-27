# E0_MASt3R-SLAM 환경 준비 기록

작성일: 2026-10-27. 상태: 축소 smoke test 통과, 원본 512 baseline은 GPU 메모리 부족으로 미완료.

- 연구 저장소 HEAD `b9fea290e2092dd4826a3914dd8aea90c93501b5`; upstream `thirdparty/MASt3R-SLAM` HEAD `e6f4e3d474fad0e11f561482012be864ba8c3f17`.
- upstream submodule: Eigen `bddaa99e151244402c6e804e01b970288650da6b`, pyimgui `c79137d6c47040e6ce226f8109868a3018d5354b`, imgui-cpp `35b1148efb839381b84de9290d9caf0b66ad7d03`. 별도 lietorch `e7df86554156b36846008d8ddbcc4d8521a16554`, Eigen `824272cde8ca2541e8b67b0887f5ded92b128d1f`.
- Ubuntu 26.04.1, RTX 5060 8151 MiB, NVIDIA driver 595.99.02, 호스트 nvcc 13.4.92. 샌드박스 밖에서 GPU 확인. 프로젝트 내 micromamba 환경 `thirdparty/mast3r-env`에 Python 3.11, CUDA toolkit 12.8 및 PyTorch 2.7.1+cu128 설치. 실제 GPU tensor 연산 합계 1240 확인.
- 공식 예제의 PyTorch 2.5.1과 달리 Blackwell 지원을 위해 2.7.1+cu128 사용. 최신 PyTorch 빌드 호환과 sm_120을 위한 upstream 수정은 [패치](../../../configs/E0_environment_preparation/mast3r_slam_pytorch27_compat.patch)에 기록. 이 변경을 포함한 환경으로 원본 수치 parity는 아직 검증하지 않았다.
- 원본 MASt3R 모델 다운로드가 느려 제3자 미러 `https://huggingface.co/vslamlab/mast3rslam_weights/resolve/5eec445/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth` 사용. SHA-256 `e28f91b488554653e2b46ddae9c78c1143e0bcb2e27d3e26cdb0b717f1568eb2`로 미러 게시값과 일치하나 공식 원본 해시와 비교하지 못했다. 나머지 retrieval 두 파일은 이전 연구 저장소의 파일을 복사했다. 파일 출처 확인 및 라이선스 검토가 필요하다. MASt3R-SLAM 및 MASt3R/DUSt3R에는 CC BY-NC-SA 4.0 조건이 명시돼 있고, 의존 패키지와 체크포인트별 조건은 별도 확인한다.
- TUM room 공식 데이터를 내려받았다. HKairport01 기존 원본 ZIP SHA-256 `ee059b678a4686b7578e4fa390927e6eac82a8e3d0e8836855b09bd4bd312336`은 기존 연구 manifest와 일치한다. 기존 `configs/e4e_input_split.json`의 mapping 240장만 추출. 5 Hz 후보 중 `grid_index mod 5 = 4` 60장은 held-out. 첫/마지막 timestamp는 1671606500.1999009 / 1671606559.799969이며 이미지 크기 2448×2048. 매핑 및 JPG/PNG hash는 `data/HKairport01/mapping_frames.csv`에 기록.
- 공식 RGBFiles 로더는 PNG만 읽고 프레임 순서/30의 가상 timestamp를 생성한다. PNG는 JPEG를 Pillow로 디코딩해 무손실로 저장했으며 원본 timestamp는 CSV를 사용해야 한다. 해당 로더는 시간 간격을 보존하지 않으므로 타임라인 분석 전에 adapter 또는 매핑이 필요하다. 원본 calibration/distortion은 미검증이며 smoke test는 uncalibrated로 계획한다.
- 공식 TUM 자료: `thirdparty/MASt3R-SLAM/datasets/tum/rgbd_dataset_freiburg1_room/`; HK 입력: `data/HKairport01/mapping/`, 최초 10장 `data/HKairport01/smoke/`. 큰 파일 및 실행 로그는 Git에서 제외된다.

## 실행 검증 결과

- 기본 512 설정의 전체 TUM room 시작: `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 python main.py --dataset datasets/tum/rgbd_dataset_freiburg1_room/ --config config/calib.yaml --no-viz --save-as prep_tum_20261027`. 첫 추론에서 CUDA OOM, 종료 코드 1. 로그 `results/E0_environment_preparation/2026-10-27/logs/prep_tum.log`. R0의 원본 설정 실행 가능성은 확보되지 않았다.
- 별도 smoke test용 `MAST3R_SLAM_IMAGE_SIZE=224` 환경 변수를 추가했다. 미설정 시 원래 512가 유지된다. 224는 짧은 변 resize 및 중앙 정사각형 crop이며 원래 512의 긴 변 resize/crop과 다르다. 축소 실행을 원본 baseline으로 취급하지 않는다. 모든 변경은 연결된 패치에 포함된다.
- TUM room의 앞 10장, `config/calib.yaml`의 `subsample=2`로 실제 5장 처리: 224, `--no-viz`, 종료 0, 11.82초. PLY 42,993 finite points, trajectory 1 keyframe. `results/E0_environment_preparation/2026-10-27/logs/prep_tum_224_smoke10.log` 및 `results/E0_environment_preparation/2026-10-27/outputs/prep_tum_224_smoke10/`.
- HKairport01 mapping 앞 10장: 224, `config/base.yaml`, 보정 미사용, `--no-viz`, 종료 0, 14.14초. PLY 48,801 finite points, trajectory 1 keyframe. `results/E0_environment_preparation/2026-10-27/logs/prep_hk_224_smoke10.log` 및 `results/E0_environment_preparation/2026-10-27/outputs/prep_hk_224_smoke10/`.
- 두 실행 모두 keyframe이 하나뿐이라 다중 keyframe, loop closure 및 전체 backend 최적화를 검증하지 못했다. GPU 최대 사용량은 별도 측정하지 않았다. `pip check` 통과. 출력은 사용 가능성 smoke test이며 단차 재현이나 기하 정확도 평가가 아니다.
- PyTorch 2.7의 체크포인트 로딩 기본값 변경 때문에 두 실행에서 `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` 사용. pickle 로딩은 코드 실행 가능성이 있으므로 파일 출처를 신뢰해야 한다. 모델은 공식 원본 파일과 해시 대조되지 않은 제3자 미러 사본이다. 512 원본 baseline 실행 시 공식 체크포인트와 대조하고, VRAM 부족을 해결한 뒤 parity와 실행을 다시 검증한다.

실행 당시 upstream `logs/`에 생성된 결과는 실험 격리를 위해 위 `results/E0_environment_preparation/2026-10-27/outputs/`로 이동했다. 명령 및 로그에 표시된 실행 당시 경로는 이력으로 보존한다.
