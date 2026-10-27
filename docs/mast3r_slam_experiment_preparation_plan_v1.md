# MASt3R-SLAM 실험 준비 단계 계획서

**버전:** v1.0  
**작성일:** 2026-10-27  
**실험 코드:** E0 — 실험 환경 준비  
**상태:** 8 GB 설정 준비 완료; 512 입력, KF buffer 32 및 단일 스레드 설정을 검증했다. 원본 설정과의 수치 parity는 미검증. 실행 결과는 [E0 결과 기록](experiments/E0_environment_preparation/E0_repo_audit.md)을 따른다.
**연결 문서:** [활주로 기하 단차 원인분석 실험계획서](mast3r_slam_runway_geometry_diagnostic_plan_v1.md)

## 1. 목표와 완료 조건

공식 MASt3R-SLAM 소스와 모델을 독립적으로 설치하고, 공개 예제와 HKairport01 입력의 짧은 구간을 실행해 이후 R0 baseline을 시작할 수 있는 재현 가능한 환경을 확보한다. 이 문서는 설치·입력 QA·실행 가능성 확인까지 다루며 단차 원인 판정이나 알고리즘 변경을 수행하지 않는다.

준비 완료는 다음 조건을 모두 만족할 때 선언한다.

- 소스와 재귀 submodule의 commit, 체크포인트 SHA-256, 환경 및 실행 명령을 기록했다.
- CUDA 확장 빌드와 GPU 사용 확인을 통과하고 공식 예제가 정상 종료되어 궤적·복원 결과를 확인했다.
- HKairport01의 원본, [60s, 120s) 구간, 240개 입력의 유래와 프레임·시간 매핑을 검증했다. 기존 조건을 정확히 재현할 수 없으면 차이와 원인을 남기고 R0 재현으로 간주하지 않는다.
- HKairport01의 짧은 smoke test가 종료되고 출력·로그가 보존되었다. 전체 구간의 단차 재현은 이후 R0에서 판정한다.
- 원본 설정과 수정 여부, 입력 좌표/보정 상태, 실행 모드 및 결과 위치를 제3자가 따라 할 수 있게 기록했다.

## 2. 현재 확인 사항과 사전 조건

2026-10-27 현재 작업 디렉터리에서 확인한 사항이다. 다른 터미널이나 실행 호스트의 상태는 다를 수 있으므로 설치 직전에 다시 확인한다.

- 연구 저장소 HEAD는 `b9fea290e2092dd4826a3914dd8aea90c93501b5`, 작업 트리에 MASt3R-SLAM 소스는 없다. 기존 `.gitignore`는 루트의 `thirdparty/`, `data/`, `checkpoints/`, `results/`, `logs/` 및 `*.pth`, `*.ply` 등을 제외한다.
- **사용자 확인:** NVIDIA 드라이버와 CUDA는 샌드박스 밖에서 정상적으로 사용할 수 있다. 앞서 샌드박스 안에서 실행한 `nvidia-smi`는 드라이버와 통신하지 못했으며, 이 결과만으로 호스트 드라이버 장애를 뜻하지 않는다. 샌드박스 밖의 GPU 모델·VRAM·버전은 이 세션에서 직접 확인하지 않았다. 기존 계획의 8 GB는 예산 가정이며 실제 사양이나 실행 가능성의 증거가 아니다.
- 현재 셸 PATH에서 `conda`, `python`은 발견되지 않았고 `nvcc`는 `/usr/local/cuda/bin/nvcc`에 있다. CUDA 버전과 다른 셸의 Conda 설치 여부는 미확인이다.
- 현재 파일시스템의 여유 공간은 약 276 GiB다. 데이터와 체크포인트 위치·크기, 다운로드 권한과 라이선스는 아직 확인하지 않았다.

**선행 게이트:** GPU 접근이 가능한 샌드박스 밖의 실제 실행 환경에서 `nvidia-smi`, `nvcc --version`, 사용 가능한 Conda 및 디스크 공간을 확인한 뒤 설치한다. 샌드박스 안의 접근 실패와 실제 실행 환경의 실패를 구분해 기록한다. 실제 실행 환경에서도 GPU를 확인할 수 없으면 접근 설정을 점검하고 CUDA 빌드·실행을 성공으로 표시하지 않는다. 공식 저장소는 Ubuntu를 주로 테스트했으며 WSL에는 별도 `windows` 브랜치를 안내한다. OS와 브랜치를 기록하고 WSL이면 해당 브랜치 지침을 재확인한다. [공식 README](https://github.com/rmurai0610/MASt3R-SLAM#installation)

## 3. 단계별 실행 계획

아래 공식 설치·실행 명령은 최초 계획의 기준이다. 실제 8 GB 환경은 512 이미지 입력과 KF buffer 32, `single_thread: true`, 저메모리 패치를 사용한다. 실행은 `scripts/E0_environment_preparation/run_8gb.sh`와 E0 결과 기록을 따르며, 공식 기본 buffer 512는 OOM으로 실패했다.

### E0-P0. 호스트 및 저장소 감사

1. `git status --short`, `git rev-parse HEAD`, `git remote -v`로 연구 저장소 상태를 기록한다. 기존 작업은 보존한다.
2. 샌드박스 밖의 실제 실행 환경에서 `uname -a`, `nvidia-smi`, `nvcc --version`, `command -v conda`, `df -h .`를 기록하고 GPU 모델·VRAM·드라이버·CUDA toolkit·OS를 확인한다. Conda가 PATH에 없으면 기존 설치를 찾거나 별도 설치 경로를 결정한다.
3. 데이터 접근 경로, 영상 메타데이터, 기존 240프레임 추출 방식과 시간 정보의 출처를 확인한다. 불명확한 항목은 미확인으로 유지한다.
4. `docs/experiments/E0_environment_preparation/E0_repo_audit.md`와 `configs/E0_environment_preparation/environment_manifest.json`에 확인 결과와 미해결 사항을 남긴다.

### E0-P1. 공식 소스 확보와 버전 고정

연구 코드와 upstream을 분리하기 위해 다음 경로를 사용한다. 이미 경로가 존재하면 덮어쓰지 말고 상태를 먼저 조사한다. 아래는 **실행 예정 명령**이다.

```bash
mkdir -p thirdparty
git clone --recursive https://github.com/rmurai0610/MASt3R-SLAM.git thirdparty/MASt3R-SLAM
cd thirdparty/MASt3R-SLAM
git rev-parse HEAD
git submodule status --recursive
git status --short
```

실행 시점의 upstream commit을 기준으로 고정해 기록하고, 필요하면 해당 commit을 checkout한 후 `git submodule update --init --recursive`로 정확한 submodule을 맞춘다. 실행 시점에는 고정 commit의 README와 라이선스를 다시 읽는다. 연구 저장소에는 소스 복사본을 추적하지 않고 commit·submodule 목록과 이후 패치의 diff/hash를 기록한다. 원본 및 의존 코드·체크포인트의 라이선스와 데이터 이용 조건을 확인한다. [공식 의존성 안내](https://github.com/rmurai0610/MASt3R-SLAM/blob/main/Dependencies.md)

### E0-P2. 독립 Python/CUDA 환경 구성

공식 README는 Python 3.11과 PyTorch 2.5.1 / torchvision 0.20.1 / torchaudio 2.5.1의 CUDA 11.8, 12.1, 12.4 선택지를 제시한다. 실제 toolkit, 드라이버와 확장 빌드의 호환성을 먼저 확인하고 **하나만** 선택한다. 아래는 CUDA 12.1이 호환되는 경우의 예시이며 `nvcc`가 12.1이라는 뜻은 아니다. [공식 설치 절차](https://github.com/rmurai0610/MASt3R-SLAM#installation)

```bash
conda create -n mast3r-slam python=3.11
conda activate mast3r-slam
conda install pytorch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 pytorch-cuda=12.1 -c pytorch -c nvidia
cd thirdparty/MASt3R-SLAM
pip install -e thirdparty/mast3r
pip install -e thirdparty/in3d
pip install --no-build-isolation -e .
python -c 'import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CUDA unavailable")'
python -c 'import lietorch; import mast3r_slam; print("imports OK")'
```

명령은 연구 저장소 루트에서 시작한다고 가정한다. 설치에 필요한 시스템 빌드 도구와 CUDA extension 오류를 로그로 남긴다. `torch.cuda.is_available()`가 참이어도 실제 연산 및 아래 예제 실행으로 빌드를 검증한다. 공식 README는 선택 사항인 MP4 가속용 `torchcodec==0.1`을 안내한다. 먼저 이미지 폴더/기본 로더를 검증하고 필요할 때만 설치한다. `conda list --explicit`, `python -m pip freeze`, Python/PyTorch/CUDA 버전과 빌드 로그를 보관한다. 환경 export에 로컬 경로나 민감 정보가 포함되는지 확인한다.

### E0-P3. 체크포인트 확보 및 무결성 기록

공식 README의 세 파일을 **upstream 작업 디렉터리 안**의 `checkpoints/`에 둔다. 이 경로는 루트 `thirdparty/` 아래라 연구 저장소에서 제외된다. 기존 파일을 덮어쓰지 않도록 확인하고 다운로드 실패 또는 부분 파일을 검사한다.

```bash
mkdir -p checkpoints
wget -nc https://download.europe.naverlabs.com/ComputerVision/MASt3R/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth -P checkpoints/
wget -nc https://download.europe.naverlabs.com/ComputerVision/MASt3R/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric_retrieval_trainingfree.pth -P checkpoints/
wget -nc https://download.europe.naverlabs.com/ComputerVision/MASt3R/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric_retrieval_codebook.pkl -P checkpoints/
sha256sum checkpoints/*
```

다운로드 URL, 일시, 파일 크기, SHA-256 및 라이선스를 manifest에 기록한다. 로컬 SHA는 이후 동일 파일 확인에 사용하며, 공식 체크섬과 대조하지 않았다면 출처 무결성이 검증된 것으로 주장하지 않는다. [공식 체크포인트 안내](https://github.com/rmurai0610/MASt3R-SLAM#installation)

### E0-P4. 공식 예제 smoke test

공식 TUM 예제는 데이터 다운로드 스크립트와 `config/calib.yaml`을 사용한다. 스크립트 내용을 먼저 읽어 다운로드 경로와 용량을 확인한 후 upstream 루트에서 실행한다. 시각화 가능한 환경이면 공식 명령으로 먼저 실행하고, GUI가 없으면 확인된 `--no-viz` 옵션을 사용한다.

```bash
bash ./scripts/download_tum.sh
python main.py --dataset datasets/tum/rgbd_dataset_freiburg1_room/ --config config/calib.yaml --no-viz --save-as prep_tum
```

실행 종료 코드, stdout/stderr, GPU 메모리 최대 사용량, 소요 시간, 궤적·PLY·keyframe 출력의 실제 위치와 크기를 기록한다. 저장 경로와 기존 결과 삭제 여부를 먼저 소스에서 확인하고 매 실행마다 고유한 `--save-as`를 사용한다. 현재 upstream `main.py`는 결과를 저장하는 데이터셋에서 동일 경로의 기존 궤적과 PLY를 삭제할 수 있다. 정상 종료와 유효한 비어 있지 않은 결과를 확인하며, 단순히 프로세스가 종료됐다는 사실만으로 정확도나 활주로 재현을 주장하지 않는다. [공식 예제](https://github.com/rmurai0610/MASt3R-SLAM#examples), [실행 코드](https://github.com/rmurai0610/MASt3R-SLAM/blob/main/main.py)

### E0-P5. HKairport01 입력 등록과 QA

1. 확보한 원본 경로, 라이선스, 파일 크기와 SHA-256, 영상 길이·프레임레이트·해상도를 기록한다. 원본은 수정하지 않는다.
2. 기존 실험의 추출 스크립트/목록을 찾아 `[60s,120s)`의 시작 포함·끝 제외 규칙, 실제 timestamp, 샘플링 간격 및 240개라는 조건을 확인한다. 고정 4 fps 추출을 기존 조건으로 가정하지 않는다. 기존 목록이 없으면 명시적으로 신규 추출 조건을 정하고 기존 결과와 동등하다고 주장하지 않는다.
3. 각 입력 이미지의 순서, 원본 frame ID, 원본 timestamp, 추출 이미지 파일명·hash를 CSV로 보존하고 첫/마지막 timestamp 및 중복·누락을 검사한다. 실제 로더의 정렬·timestamp 처리와 resize/crop을 소스에서 확인하여 원본과 모델 입력의 대응을 기록한다. 이미지 폴더에서 원본 timestamp가 자동 보존된다고 가정하지 않는다.
4. 카메라 intrinsics, distortion 및 이미지 전처리의 출처·해상도 대응을 확인한다. 검증되지 않은 calibration은 사용하거나 GT로 취급하지 않는다. 우선 공식 `config/base.yaml`의 uncalibrated 경로를 확인하고, 보정 모드는 별도 QA 후 명시한다.
5. 재현 입력의 처음 몇 프레임으로 테스트용 subset을 만든 뒤 원본 설정으로 headless 실행한다. 예시의 경로는 실제 등록 경로로 바꾼다.

```bash
python main.py --dataset /absolute/path/to/hkairport01_smoke_frames --config config/base.yaml --no-viz --save-as prep_hk_smoke
```

실제 데이터셋 종류에 따라 결과 저장 여부와 위치가 달라질 수 있으므로 고정된 소스의 dataloader 및 저장 로직을 먼저 확인한다. 파일이 저장되지 않으면 해당 기능을 조사하고 필요한 최소 export를 별도 작업으로 기록한다. Smoke test는 입력 로딩, tracking 진행, 정상 종료 및 검토 가능한 출력 확인용이며 단차의 유무를 판정하지 않는다.

### E0-P6. R0 인계 및 환경 봉인

- `docs/experiments/E0_environment_preparation/E0_repo_audit.md`: 연구 repo/upstream/submodule commit, 로컬 수정 diff, 설치 경로와 라이선스 확인 상태.
- `configs/E0_environment_preparation/environment_manifest.json`: OS, GPU/VRAM, driver, toolkit, Python·PyTorch, 패키지 목록 경로, 체크포인트 파일별 SHA-256, 실행 모드·설정·seed 및 미확인 항목. 설정 파일 내용 또는 hash도 보존한다.
- 데이터 manifest 및 프레임 CSV: 원본 hash, 추출 명령/버전, 시간 규칙, 이미지 해시, calibration 및 전처리 상태.
- 공식 예제와 HK smoke test: 정확한 명령, 종료 코드, 로그, 출력 위치/크기, 소요 시간 및 GPU 메모리. 큰 데이터·모델·실행 결과는 Git 제외 경로에 두고 작은 문서와 manifest는 추적 가능하게 한다.
- 이후 R0는 기존 진단 계획서에 따라 전체 240개 입력의 baseline과 계측 parity, KF별 map 및 타임라인을 수행한다. 원본 코드에 관측 계측을 추가하기 전 원본 baseline을 보존한다.

## 4. 실패 시 결정

| 조건 | 조치 |
|---|---|
| 드라이버/GPU 접근 실패 | 샌드박스 안에서만 실패하면 GPU 접근이 가능한 실제 실행 환경에서 확인한다. 실제 실행 환경에서도 실패하면 호스트 또는 WSL 접근 설정을 점검하고 E0-P0를 재검증한다. CPU 실행 가능성을 가정하지 않는다. |
| CUDA 확장 빌드 실패 | toolkit·드라이버·PyTorch 및 컴파일러 버전과 전체 오류를 기록하고 고정된 upstream 지침에 맞춰 해결한다. |
| GPU 메모리 부족 | 공식 예제와 smoke test의 피크 메모리를 기록한다. 설정 변경이나 하드웨어 변경은 별도 실행으로 표시하고 baseline과 혼동하지 않는다. 임의의 해상도 축소를 재현 성공으로 취급하지 않는다. |
| 공개 예제 실패 | 데이터, checkpoint, 빌드, GUI/headless 및 로그를 차례로 확인하고 HK 결과 해석을 보류한다. |
| HK 입력 또는 240프레임의 출처 불명 | 확보 가능한 데이터로 smoke test만 수행하고 기존 구간 재현은 보류한다. |
| 추적 실패 또는 출력 없음 | 실패 프레임과 로그를 보존하고 입력/설정/저장 조건을 점검한다. 실패를 단차 원인이나 성공으로 해석하지 않는다. |

## 5. 실행 체크리스트

- [x] E0-P0 호스트/GPU 및 저장소 감사 완료
- [ ] E0-P1 upstream과 submodule 확보 및 commit 기록 완료; 의존 패키지·체크포인트별 라이선스 검토 보완 필요
- [x] E0-P2 독립 환경 설치, CUDA 빌드 및 GPU 연산 검증
- [x] E0-P3 세 체크포인트 확보 및 hash 기록
- [x] E0-P4 공식 TUM 예제 정상 실행 및 출력 확인
- [x] E0-P5 HKairport01 입력·시간 매핑 QA 및 짧은 smoke test
- [x] E0-P6 manifest, 로그, 설정과 미해결 사항 정리 후 R0 인계

본 문서의 명령과 경로는 실행 계획이며, 설치·다운로드·실험의 완료를 의미하지 않는다.
