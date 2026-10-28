# MASt3R-SLAM 기반 드론 영상의 활주로 기하 단차 원인분석 실험계획서

**버전:** v1.0  
**작성일:** 2026-10-27  
**대상 저장소:** `https://github.com/seaeast2/gradresearch_mast3r_slam`  
**기준 연구:** MASt3R-SLAM (Murai et al., CVPR 2025)  
**상태:** *계획서 / 미실행*. 앞선 E0–E4f, A0–A2-O-M의 결과를 새로운 실험 성공으로 소급하지 않음.

**실행 환경:** 사용자에 따르면 NVIDIA 드라이버와 CUDA는 샌드박스 밖에서 정상적으로 사용할 수 있다. 샌드박스 안에서의 `nvidia-smi` 드라이버 통신 실패는 호스트 장애로 단정하지 않는다. 실험은 GPU 접근이 가능한 실제 실행 환경에서 수행하고, GPU 모델·VRAM·드라이버·CUDA 및 PyTorch 버전과 실제 연산을 준비 단계에서 확인해 기록한다. 세부 절차는 [실험 준비 단계 계획서](mast3r_slam_experiment_preparation_plan_v1.md)를 따른다.

> **핵심 목적:** 단안 드론 영상의 실제로 연속적인 활주로 표면이 3D 지도에서 계단형 높이 불연속으로 나타나는 현상이 **(1) 이미지 쌍의 원본 Pointmap**, **(2) Tracking과 Canonical Pointmap Fusion**, **(3) Keyframe별 Sim(3) 배치·Backend 최적화**, **(4) 지도 Export/표현** 중 어느 단계에서 처음 발생하고 증폭되는지 확인한다. 원인 판정 전에는 새로운 Depth/Plane 보정 알고리즘을 구현하지 않는다.

---

## 0. 연구 범위와 근거 수준

### 0.1. 연구 질문

- **RQ1 — 발생 단계:** 같은 물리적 활주로 영역의 높이 불연속이 Raw/Fused/Globally placed/exported geometry 중 최초로 나타나는 단계는 어디인가?
- **RQ2 — 원인 분리:** Keyframe 전환·추적 누락·상대 Sim(3) scale·회전(특히 pitch/roll)·이동과 단차 사이에 재현 가능한 관계가 있는가?
- **RQ3 — 관측 제약:** 낮은 텍스처·작은 시차·반복된 노면 패턴·시점 중복 부족이 Tracking/Fusion 실패를 설명하는가?
- **RQ4 — 개선 가능성:** 특정 원인을 분리하고 *이미 관측된 정보로* 수정할 수 있는 가장 작은 변경은 무엇인가? 독립 장면에서 기하 개선과 coverage 보존을 입증할 수 있는가?

### 0.2. 현재 확인된 사실 / 확인되지 않은 가설

**기존 실험에서 확인됨**

1. Splatt3R-SLAM의 검사된 raw self-branch에서 Gaussian 중심은 입력 raw pointmap과 동일했다. 따라서 **최초 중심 오차가 GS 생성 단계에서 새로 발생했다는 전제는 폐기**한다. 단, 별도 branch, Gaussian covariance/opacity, export는 미검증이다.
2. HKairport01 파일럿은 **240 RGB 입력 / 21 keyframe / Pose 228/240 성공 / 최장 연속 누락 2.4초**였다. 관찰된 활주로 단차와 이 누락의 위치가 일치하는지는 아직 측정하지 않았다.
3. 이전 A1-U는 local point × keyframe scale의 가역 재표현으로 world mean/covariance와 렌더링이 동일함을 검증했다. **Scale 파라미터 변동 자체는 물리적 오류 증거가 아니다.**
4. A1-G/M의 rigid-pose 오류 해석은 gauge 및 support 조건에 민감했고, HKairport01의 Terra pose, 이미지 왜곡 및 외부 보정 계약은 해결되지 않았다. 이를 확정 GT로 취급하지 않는다.
5. A2-O-M의 RGB-only scalar 보정 연구는 관측 지원 부족으로 중단됐다. 새 연구에서 그 보정 경로를 자동 재개하지 않는다.

**이번에 검증할 가설**

- H-L: 각 Keyframe의 활주로 Raw Pointmap 내부에 이미 국소 휨·깊이 편향이 있다.
- H-F: Tracking과 weighted-average Canonical Pointmap Fusion 과정에서 이상 정렬 또는 대응이 단차를 형성한다.
- H-P: Raw/Fused geometry는 국소적으로 평면이지만 Keyframe별 world Sim(3) placement가 불연속을 형성한다.
- H-B: Backend 또는 Loop Closure 전후에 pose/scale revision과 map 갱신의 불일치가 단차를 확대한다.
- H-E: Pointcloud/PLY export 및 후단 처리 때문에 단차가 새로 보이는 착시 또는 표현상의 왜곡이다.
- H-O: 실제 동일 표면의 중복 관측이 적어 상기 원인 사이를 판별하기 어렵다.

**주의:** 활주로는 완벽한 수평면이 아닐 수 있다(횡단 경사·종단 경사·배수구조). 연구의 주 표적은 *절대 $z=\mathrm{constant}$* 가 아니라 **같은 물리적 위치를 서로 다른 관측이 일관되게 표현하는가**이다.

**E5 이후 관찰 — Z 방향 중복:** 사용자는 CloudCompare에서 포장면이 화면상 XY 방향으로 대체로 겹치지만 깊이 방향으로 여러 층을 형성한다고 보고했다. 이 관찰을 E6의 주요 평가 대상으로 추가한다. 해당 화면의 좌표축·view 방향은 스크린샷만으로 확인할 수 없으며, world Z·camera Z·표면 법선 방향은 서로 다른 개념이다. E1 지도에서 KF29 기준 ROI 평면 법선은 world Z에서 약 4.7° 떨어져 있어 이 영역에서는 world Z가 법선 방향과 가깝다. 다만 실제 중력 정렬이나 metric 단위는 확인되지 않았고, Z 방향 층 분리만으로 원본 네트워크의 깊이 추정이 주원인이라고 판정하지 않는다. 기존 대응 후보에서 축별 차이를 별도로 계산한 예비 관찰은 [E5 축별 관찰](experiments/E5_timeline/E5_axis_observation.md)에 기록한다.

---

## 1. 파이프라인과 계측 지점

```text
원본 RGB / timestamp / camera calibration
  │
  ├─ [S0] 입력 프레임 (원본/resize/crop/undistort의 대응)
  ▼
MASt3R pair inference
  ├─ [S1] raw pair pointmap, confidence, descriptor, pair IDs
  ▼
Tracking + pairwise correspondences
  ├─ [S2] match/inlier, relative pose, tracking fail/recovery
  ▼
Canonical pointmap fusion
  ├─ [S3] keyframe-local fused pointmap before/after update, weight/support
  ▼
Backend + loop closure / global optimization
  ├─ [S4] keyframe Sim(3) before/after revision, graph edges/residuals
  ▼
World point cloud
  ├─ [S5] transformed raw/fused point cloud, per-KF provenance
  ▼
Export / downstream GS (진단용 선택)
  └─ [S6] exported PLY / eventual Gaussian map, source IDs
```

**실험의 주 대상은 S0–S5의 MASt3R-SLAM 출력**이다. Splatt3R 및 3DGS 최적화를 본 실험에 연결하지 않는다. S6은 MASt3R-SLAM 결과와 기존 PLY 관찰이 일치하는지 확인하는 최소 대조다.

### 소스 계측 위치 조사 순서

사용자 실험 저장소의 파일 트리/commit은 **이 문서 작성 시 검증하지 못했으므로 특정 파일 경로를 사실로 단정하지 않는다.** 먼저 upstream `rmurai0610/MASt3R-SLAM`과 사용자의 저장소를 diff하고 실제 함수 호출 경로를 기록한다. upstream에는 `main.py`, `mast3r_slam/`, `config/`, `scripts/` 등이 있다. 아래는 찾을 *기능*이며 파일명 후보는 탐색 결과로 확정한다.

| 기능 | 찾을 호출 지점 | 추가 로그 |
|---|---|---|
| Pair forward | MASt3R inference/decoder 반환 직후 | pointmap raw, descriptor/confidence, source image pair, shape |
| Matching/tracking | matching output 및 relative pose solve 직후 | match 수, valid/inlier 비율, residual, 추적 성공 여부 |
| Canonical fusion | weighted average update 전후 | 이전/현재 pointmap, weight, validity, effective baseline |
| Keyframe 생성 | new keyframe append 및 keyframe 기준 변경 | frame IDs, 결정 사유, timestamp, predecessor |
| Backend 최적화 | global graph optimization 전후 | poses Sim(3), 각 edge residual, gauge anchor, loop state |
| Map export | pointcloud/PLY serialization 직전 | 원래 KF ID/pixel ID, world XYZ, export transform |

**코드 변경 원칙:** 모델의 inference·pose·fusion 값 변경 없이 **관측용 저장 기능만** 추가한다. 추론 출력의 dtype, 텐서 메모리 생명주기, 동기화가 달라지지 않도록 저장은 복사 후 비동기/배치 I/O 또는 replay 경로로 분리한다. 출력 parity를 baseline과 비교한다.

---

## 2. 데이터와 평가 계약

### 2.1. 데이터 등록

- **개발/원인 진단:** 기존 `UAVScenes/HKairport01`의 동일 영상·동일 `[60s,120s)` 구간, 240개 입력 조건을 우선 재현. 시퀀스·프레임 ID 및 timestamp hash를 기록한다.
- **Validation 후보:** `AMtown01`, `AMvalley01` 등 이미 확보했던 영상에서 먼저 카메라 모델·하나 이상의 공통 평면·유효 overlap 여부를 QA한다. 확보만 된 상태이므로 실행 완료라고 기재하지 않는다.
- **Reference QA:** HKairport의 공개 extrinsics 직교성, sensor→camera 변환, JPG distortion, Terra pose와 물리 카메라의 대응, LiDAR/RGB 동기화를 확인하기 전에는 절대 높이/metric error에 확정 GT 표기를 하지 않는다.
- **최종 독립 검증:** 개발 결과와 판정 기준을 고정한 뒤 **한 번도 tuning하지 않은 다른 UAV 시퀀스/구간**을 지정한다. 동일 구간에서 서로 이웃한 프레임은 독립 장면으로 세지 않는다.

### 2.2. 공통 좌표와 시간

- 명시적으로 `pointmap source frame`, `anchor keyframe`, `camera-to-world/world-to-camera`, quaternion ordering, unit 및 Sim(3) composition convention을 기록한다.
- MASt3R의 raw local scale과 keyframe placement scale을 **별도 보고**하되 지도의 실체 비교는 항상 $s R X + t$로 만든 world geometry로 수행한다.
- **A1-U 재표현 계약:** $y_k=a_k x_k$, $\Sigma^y_k=a_k^2\Sigma^x_k$, rigid placement $(R_k,t_k)$ 는 원본 world map과 동일해야 한다. 그 자체를 보정 기법으로 부르지 않는다.
- 비중력 정렬 world z를 높이로 해석하지 않는다. *측정 높이 방향*은 검증된 gravity/reference가 있으면 그 방향, 없으면 공통 기준 평면 normal에 대한 signed coordinate로 정의한다. 서로 다른 정렬을 섞지 않는다.
- 입력 영상의 연속성은 이미지 및 추적 기록으로 측정한다. 단순한 프레임 순서만으로 동일 픽셀의 실제 3D 대응이 보장되지 않는다.

### 2.3. 활주로 영역 선택

1. 소수 개발 프레임에서 **활주로로 확인되는 정적 표면 ROI**를 RGB 이미지에 polygon으로 표시한다.
2. ROI는 Pointmap/단차 결과를 보면서 유리하게 조정하지 않는다. segmentation model은 선택 사항이며 결과 마스크를 육안 검수한다.
3. 사전 정의한 독립 확인 표본(수작업 대응 또는 검증된 image tracking)을 통해 서로 다른 KF가 *같은 물리적 활주로 영역*을 보는지 확인한다.
4. 마킹/이음매/조인트, 활주로 외 건물·차량·하늘 및 경계/가림 영역을 분리한다.
5. ROI별 image texture, 시차, 반복 관측 수를 보고한다. 실제 물리 평면이 아니라면 **서로 다른 경사 영역**으로 분할하거나 전역 평면 가설을 철회한다.

---

## 3. 실험 단계: 원인 위치 찾기 (필수, R0–R4)

**실험 코드 규칙:** E0는 환경 준비, E1–E5는 각각 기존 R0–R4, E6은 선택한 최소 통제실험, E7은 독립 검증, E8은 논문 Go/No-Go 판단이다. 기존 R/T/V 표기는 연구 단계와 대조 종류를 식별하는 보조 코드로 유지한다. E0의 세부 준비 작업은 E0-P0–E0-P6으로 구분한다. E6의 후보는 E6-T-CAL, E6-T-KF, E6-T-FUS, E6-T-POSE, E6-T-PAR, E6-T-EXP로 구분하며 기존 원칙대로 하나만 선택한다. 각 단계의 결과 Markdown은 `E<번호>_설명.md`로 명명하고 반복 실행은 run ID로 구분한다. 예전 연구의 E0–E4f는 별도 저장소의 과거 코드이며 이번 연구의 코드와 동일한 실험이 아니다.

### E1 (R0) — 원본 재현과 provenance 확인

**현재 실행 설정:** 사용자 요청에 따라 HKairport01을 실제 촬영 시각 기준 가능한 한 1초마다 keyframe을 생성하여 실행한다. 입력 timestamp의 불규칙성과 추적/재위치 실패에 따라 간격은 달라질 수 있다. 실행은 64 KF buffer, single-thread 및 backend CUDA 캐시 반환을 사용하며 공식 기본 설정과 구분한다. 사용자 요청에 따라 1초와 2초 정책의 기하 비교는 수행하지 않는다. [E1 실행 기록](experiments/E1_baseline_reproduction/E1_periodic_1s_results.md)을 따른다.

**목적:** MASt3R-SLAM 단독 baseline이 관찰된 단차를 재현하는지 확정. 기존 Splatt3R-SLAM PLY만의 단차라면 별도 후단 문제이다.

**실행:** upstream/사용자 저장소 commit, checkpoint SHA, dataset hash, resolution, calibration mode, keyframe policy, seed, inference config, GPU metadata를 봉인. 로그 있는 baseline과 로그 없는 baseline을 동일 구간 실행하고 pose/keyframe/pointmap 결과를 비교한다. 출력을 KF별 색으로 표시한 side-view point cloud와 world XYZ를 저장한다.

**기본 결과:** `R0_map_by_keyframe.ply`, `R0_tracking_timeline.csv`, `R0_run_manifest.json`, `R0_image_map_contactsheet.png`. *이 단계에서 단차가 재현되지 않으면 downstream-only 진단으로 전환하고 R1–R4의 주장을 중단한다.*

### E2 (R1) — Raw Pointmap의 국소 평면성과 장면 간 차이

**목적:** MASt3R pair output에서 이미 구조가 휘어 있는지 판별.

**방법:** 동일 KF 및 그 인접 image pair의 raw pointmap을 카메라/anchor 좌표에서 측정. ROI의 PCA/RANSAC plane residual(MAD/p90/RMSE)과 normal consistency를 기록한다. *하나의 평면으로 표현 가능한 local patch에만* 평면 지표를 적용한다. 각 픽셀의 원본 ray, camera-Z, confidence 분포도 출력한다.

**판정:** Raw pair 내부에서도 패치 왜곡과 경계가 보이면 **H-L 지지**. 개별 Raw 패치가 평탄해도 물리적 높이가 옳다는 뜻은 아니다. Raw geometry를 동일 world로 옮기기 전에 평면간 offset을 직접 비교하지 않는다.

### E3 (R2) — Tracking과 canonical fusion 전후 변화

**목적:** Fusion으로 새 단차가 생기는지 확인.

**방법:** 각 keyframe의 canonical pointmap을 초기화 직후, 새 프레임 merge 직전/직후, keyframe freeze 시 저장. 원본 논문의 confidence-weighted average 식을 구현 계측에 맞춰 대조한다. 매 update마다 (i) 입력 프레임↔canonical의 유효 correspondence, (ii) 상대 pose, (iii) 융합 이전/이후 동일 ROI의 plane residual/normal/validity, (iv) 높은 가중치를 가진 서로 충돌하는 관측을 기록한다.

**판정:** Raw는 평탄하지만 fused patch에서만 휨/분절이 커지면 **H-F 지지**. Fusion이 raw noise를 줄이더라도 global KF간 불연속이 남으면 R3을 진행한다. *Fusion 이전/이후로 비교할 때 동일 local frame, 동일 ROI support를 유지*한다.

### E4 (R3) — Keyframe world placement / Backend revision

**목적:** 인접 KF의 local plane이 world 배치에서 분리되는가?

**방법:** 각 KF의 raw/fused map을 동일한 저장된 **pre-backend** 및 **post-backend** Sim(3)로 독립 배치해 비교한다. KF pair의 overlap ROI에서 normal 각도, plane-to-plane signed distance, symmetric point-to-plane residual 및 offset의 분포를 측정한다. 연속 KF의 $\log(s_k/s_{k-1})$와 pitch/roll/t 변화, relative pose residual, loop edge 추가 전후 수치를 함께 기록한다. **Scale 값의 점프와 물리적 단차를 동치로 해석하지 않는다.** A1-U 불변 재표현과 gauge 민감도를 통과해야 한다.

**판정:** local/fused patch는 평탄한데 world에서만 인접 패치가 갈라지면 **H-P 지지**. Backend 업데이트 전후 단차가 출현·증폭된다면 **H-B 지지**. camera-reference calibration 불확실할 경우 이 결과는 내부 일관성 진단으로만 보고한다.

### E5 (R4) — Tracking gap·keyframe 경계·매칭 퇴화와의 연계

**목적:** `HKairport01`의 2.4초 pose 누락, KF 전환/재초기화가 단차와 연결되는가?

**방법:** 단차를 보인 world ROI의 source `frame_id/KF_id`를 역추적한 뒤 `frame timestamp`, tracking success, keyframe transition, valid matches, residual, overlap/parallax, image gradient 및 sky ratio를 타임라인으로 그린다. Pose 누락 전·중·후 구간을 빠짐없이 보존한다. 이미지 시차는 검증된 correspondence에서만 산정하고 foreground motion을 제외한다.

**판정:** 원인 징후와 단차 발생의 시간적 일치는 **상관 단서**이다. 인과 귀속은 후속 조건 통제(§4)를 통과해야 가능하다.

---

## 4. E6 — 원인 후보별 최소 통제실험 (R0–R4 후 하나만 선택)

| 코드 | 실험 개입 | 고정 항목 | 무엇을 분리하는가 | 제한 |
|---|---|---|---|---|
| E6-T-CAL | Native calibration vs 검증된 calibrated/undistorted input | 같은 프레임·weight·KF policy | 카메라 왜곡/ray 추정 영향 | 미검증 calibration을 GT로 부르지 않음 |
| E6-T-KF | 짧은 gap 근처 KF selection/edge 유지 정책 소규모 변화 | 입력/weight, 평가 mask | KF 수·경계와 단차의 상관·민감도 | KF가 바뀌면 동일 ID의 직접 비교는 불가; 공통 ROI에 평가 |
| E6-T-FUS | Fusion update replay: 원래 vs 후보 입력 하나 제외 vs confidence cap | tracking poses frozen, same source frames | fusion 오염·높은 신뢰도 오류 | 인과 효과는 replay 조건에만 해당 |
| E6-T-POSE | Fused pointmap frozen; pre/post pose replay 및 local pair-fixed world placement | pointmap 그대로, 공통 gauge | pose/scale 배치 영향 | GT pose 대체는 **oracle**로 분리 |
| E6-T-PAR | 같은 장면에서 사전 정한 충분/불충분 시차 subset 비교 | scene·ROI·평가 지원 | 저시차 퇴화 영향 | subset 변화로 관측량도 변하므로 둘 다 보고 |
| E6-T-EXP | raw/fused/world pointcloud vs exported PLY 수치 parity | 동일 저장 포인트 ID | export/후단 오류 | 색·좌표 압축/축 전환도 점검 |

**조기 중단 원칙:** R0–R4 중 실패 단계가 특정되면 **그 단계의 가장 단순한 대조실험 1개**만 실행한다. 네트워크 재학습, full joint-optimizer, dense mesh 생성, 3DGS refinement는 하지 않는다.

### E5 이후 E6-T-FUS에 추가할 깊이 방향 진단

E5에서 첫 fusion 입력의 큰 이동과 tracking 거리 검사 탈락이 관찰되어 E6의 우선 후보를 T-FUS로 지정한다. 아래 항목은 **추가 평가·계측 계획**이며 아직 실행 결과가 아니다. 기존 값에 맞춰 사후 성공 임계치를 만들지 않는다.

1. **좌표와 관측 방향:** canonical keyframe-local camera Z, 원점으로부터의 ray 방향 거리, world Z와 검증된 포장면 기준 평면의 법선 및 접선 방향을 구분한다. 관측 이전·이후를 같은 KF local 좌표와 고정된 픽셀 support에서 비교한다. 서로 다른 카메라의 Z 값을 직접 빼지 않고, 각 점을 명시된 Sim(3)으로 공통 좌표계에 변환한다. 원본 pair의 cross 점은 저장된 상대 Sim(3)의 역변환으로 복원할 수 있되 round-trip과 저장된 원본이 있을 때의 parity를 먼저 확인한다. Camera Z 또는 ray 방향은 측정 가능한 깊이 성분이지 기준 깊이의 정확도 자체가 아니다.
2. **동일 support와 분해:** E2a 영상 대응 후보와 E3 전체 ROI를 별도로 보고하고, 공통 후보·export 가능한 점·변경 후 유효 점의 수와 공간 분포를 보존한다. 후보의 correctness/visibility는 독립 검증 전까지 후보로 표시한다. 후보 대응별 world 차이 벡터를 고정된 기준 법선 $n$에 대해 $d_n=n^\top\Delta X$, $d_t=\lVert(I-nn^\top)\Delta X\rVert$로 나누고 world의 $|\Delta Z|$와 $\lVert(\Delta X,\Delta Y)\rVert$도 같은 점에서 산출한다. 중앙값·p90 및 부호 있는 normal 차이 분포를 보고한다. 평면 법선은 동일 비교에서 고정하고 ground truth가 없으면 normal의 물리적 높이 의미는 주장하지 않는다.
3. **원본·fusion·배치 대조:** 동일 입력의 초기, 각 실제 fusion 전/입력/후, 마지막 fused pointmap을 KF-local camera Z 및 ray 성분으로 분석한다. 앞뒤의 적용 pose 및 confidence/매칭 유효성은 함께 기록한다. E4에서 기록된 동일 pre/post Sim(3)과 동일 pointmap으로 world normal/Z 성분 변화도 측정한다. Frozen pose와 frozen input으로 최초 fusion 입력 하나만 제외한 replay와 원본 replay를 비교하며, 원본 가중 평균식 및 E3 output parity를 먼저 검증한다. 이 변경은 나머지 입력·pose를 원래 실행에서 고정하므로 후속 tracking까지 다시 실행한 결과가 아니다.
4. **판정과 대조:** normal/Z 차이와 접선/XY 차이가 모두 보존·변화하는 양상을 함께 제시해 특정 축만 좋아지는 대신 옆으로 흐르거나 coverage가 줄어드는 경우를 표시한다. 사용자 확인 포장면과 별도로 seam이 낮은 후보 영역의 음성 대조를 찾고 독립 correspondences·가시성을 확인한다. 유효 support가 없으면 `INSUFFICIENT_SUPPORT`로 기록하고 임의의 0으로 채우지 않는다. 고정 pose replay에서 결과가 바뀌어도 그것은 관측값이 canonical map에 미친 조건부 영향이며 실제 depth 오류 또는 개선의 증거가 아니다. 외부 깊이/표면 reference QA 및 독립 시퀀스 검증 없이는 absolute depth 정확도, metric 오차, 일반화 또는 알고리즘 개선을 주장하지 않는다.

---

## 5. 정량 지표와 반증 가능성

### 5.1. 반드시 함께 보고할 지표

**(A) 내부 기하 정합성 — 검증된 GT 없이 가능**

- `local planar residual`: 동일 local ROI patch의 RANSAC/PCA plane absolute residual 중앙값·p90·RMSE. 로컬 scale 단위를 명시하거나 무차원화(패치 크기 정규화)를 병기.
- `overlap plane offset`: 두 KF에서 **동일한 물리적 ROI**에 대한 world plane의 signed separation. 두 평면이 기울었다면 하나의 숫자 offset 대신 *공통 support에서의 point-to-plane residual 분포*를 보고.
- `normal disagreement`: 같은 ROI의 두 plane normal 사잇각. normals의 ± 부호를 일관화.
- `map seam index`: 서로 다른 source KF의 overlap에서 불연속 residual이 사전 임계치를 초과한 비율. **새로 정의한 연구용 지표**이므로 정의/단위/임계치를 사전 등록.
- `temporal association`: seam과 KF 경계·tracking loss·scale/revision event의 시간적 인접 여부. 부정 사례도 포함.
- `support`: 유효 대응 점 개수, 겹침 KF 쌍, 면적, 관측 angle/parallax 및 score 불능 구간 비율.
- `axis/ray decomposition`: 동일 대응의 world $|\Delta Z|$, XY 크기, 고정 기준 평면 normal 및 접선 성분의 중앙값·p90; 같은 KF-local frame에서의 camera-Z와 ray 방향 fusion 전후 변화. 축 방향과 좌표계를 명시하고 두 관측의 대응 품질 및 coverage를 병기한다. 이 수치 자체는 metric depth error가 아니다.

**(B) 물리적 정확도 — 신뢰할 수 있는 기준자료가 있을 때만**

- GT 표면/Depth 대비 height/point-to-plane error 및 correct coverage, 독립 LiDAR가 있는 경우의 거리별 residual.
- Camera ATE/RPE, scale drift는 reference QA 통과 및 단일 gauge 이후 보고. 복원한 지도 전체의 absolute height는 calibration 불확실하면 주장하지 않음.
- 절대 MAE가 좋아져도 overlap에서 seam과 coverage가 악화된다면 **부분적 실패**로 기록.

### 5.2. 수식

Local-to-world:

$$
\mathbf X_w=s_k\mathbf R_k\mathbf X_k+\mathbf t_k,
\qquad \Sigma_w=s_k^2\mathbf R_k\Sigma_k\mathbf R_k^\top.
$$

동일 ROI에서 기준 plane $\pi_j: n_j^\top x + d_j=0$, $\lVert n_j\rVert=1$일 때:

$$
e_{i\to j}=\operatorname{median}_{\mathbf p\in\Omega_{ij}}
 (\mathbf n_j^\top \mathbf p+d_j),\quad
r_{i\to j}=\operatorname{median}_{\mathbf p\in\Omega_{ij}}
 |\mathbf n_j^\top \mathbf p+d_j|.
$$

- $\Omega_{ij}$는 geometric nearest-neighbor만이 아니라 **영상 대응·가시성으로 검증된 동일 물리 표면 영역**이다.
- $e$는 signed step, $r$은 magnitude. 정상 경사/곡률 및 다른 물리 영역 간 높이차를 seam으로 세지 않는다.
- 상대 KF scale $\Delta\log s=\log(s_k/s_{k-1})$ 는 로그 지표일 뿐 물리적 scale drift의 증거가 아니다. world-map preserving reparameterization에 대해 변하지 않는 geometry 지표를 주 결론에 사용.

### 5.3. 사전 등록 품질 게이트 (초기값; 파일럿 전에 조정 가능)

| Gate | 사전 조건 | 미달 시 |
|---|---|---|
| G0 재현 | 동일 입력과 설정에서 관찰된 활주로 단차가 MASt3R-SLAM 단독 world map에서도 나타남 | MASt3R 원인 주장 중단; export/GS쪽 검사 |
| G1 provenance | 평가된 3D point의 ≥95%가 KF/frame/source pixel까지 역추적 가능 | 결론 보류; ID 연결 오류 해결 |
| G2 공통 관측 | 분석할 KF pair별 유효 overlap ≥1,000 points 또는 ≥0.5% 공통 정적 ROI 픽셀, 분석 가능한 pair ≥3 (잠정) | 결과 기술만; 정량 seam 원인 우세 불가 |
| G3 좌표·scale | Sim(3) 변환 round-trip 및 원본 world point/covariance 재표현 parity 통과 | 원인 해석 금지 |
| G4 재현·대조 | 동일 징후가 단차 ROI의 복수 KF 경계에서 일관되며 정상 ROI 음성 대조도 존재 | 단일 에피소드 사례연구로 제한 |
| G5 외부 reference | calibration/distortion/time sync/pose frame mapping QA 통과 | absolute metric 및 LiDAR GT 인과 주장 불가 |

`G2`의 수치는 사전 실행 테스트로 지원 규모를 확인한 뒤 잠그고, 결과가 잘 나오도록 바꾸지 않는다. 충분한 overlap이 없으면 `INSUFFICIENT_SUPPORT` 판정 자체를 결과로 남기며 추정값을 0으로 채우지 않는다.

---

## 6. 단계별 Go / Revise / Stop 결정표

| 확인 결과 | 일차 원인 가설 | 후속 결정 |
|---|---|---|
| Raw에서 이미 계단/기하 왜곡, Fusion/placement에서 유사한 왜곡 유지 | MASt3R pair depth/shape bias (H-L) | Raw pair의 parallax·matching·calibration 진단으로 한정. Pose/plane-loss 개발 STOP |
| Raw는 평탄, fused에서 새 왜곡 발생 | Fusion/matching (H-F) | T-FUS 하나 실행. fusion confidence·잘못된 대응 분석 |
| Raw/fused는 평탄, world 배치 후 경계 분리 | Pose/Sim(3) (H-P) | T-POSE 및 Scale/Pitch sensitivity. 참조 pose가 없으면 내부 일관성 개선까지만 |
| Backend revision 후 단차 악화 | Backend/map correction (H-B) | before/after pose와 pointmap update parity 확인 후 제한적 보정 가능성 검토 |
| MASt3R world map은 평탄하나 export/GS PLY만 계단 | Export/downstream (H-E) | 3DGS가 아니라 export/좌표 연결 오류 진단 |
| 동일 ROI의 이중 관측 자체가 충분하지 않음 | Observability limitation (H-O) | 새 알고리즘 GO 금지, 실험 설계/영상 조건 변경. 성공으로 간주 금지 |
| 여러 원인이 혼합되어 명확히 분리되지 않음 | Coupling | 한 번에 하나씩 frozen replay, geometry/gauge/support 민감도와 상호작용 보고 |

**알고리즘 개선 단계는 이 표 이후 별도 계획서로 작성**한다. 이번 문서는 *원인분석 연구*이며 특정 loss·mesh prior·plane regularizer의 효과를 미리 약속하지 않는다.

---

## 7. 실행 순서, 규모 및 최소 산출물

| 실험 코드 | 단계 | 작업 범위 | 필수 출력 |
|---|---|---|---|
| E0 | 실험 환경 준비 | 저장소 감사, 설치, 데이터 QA 및 smoke test | `docs/experiments/E0_environment_preparation/E0_repo_audit.md`, `configs/E0_environment_preparation/environment_manifest.json` |
| E1 | R0 | HKairport01 한 구간 baseline, KF 색 분류 PLY, tracking/KF 타임라인 | `R0_*` 및 단차 ROI 지정 |
| E2 | R1 | 단차 발생 전후 **3–5 KF**의 raw pointmap 비교 | `R1_raw_plane.csv`, figure |
| E3 | R2 | 같은 KF의 fusion input/before/after/after-freeze | `R2_fusion_events.parquet`, figure |
| E4 | R3 | pre/post backend Sim(3), overlap seam, scale/pitch | `R3_pairwise_seams.csv`, graph |
| E5 | R4 | tracking gap 및 texture/parallax 연관성 | `R4_timeline.csv`, paired plots |
| E6 | T-* | R0–R4 결과에서 우선순위가 높은 한 원인만 최소 개입 | frozen replay + negative controls |
| E7 | V0 | 새 UAV 영상/미사용 구간에서 원인 패턴 재현성 | `E7_V0_results.md`, 실패 포함 |
| E8 | 논문 Go/No-Go | 원인과 설명력을 충분히 입증했는지 검토 | `E8_route_decision.md` |

**구현 우선순위:** 첫 주기의 완료 조건은 `R0 + R1 + R3의 최소 subset`이다. 이 정도 자료로 Local-vs-Placement를 일차 판별할 수 없다면 Fusion이나 backend 전체를 대규모 계측하기 전에 support/gauge를 먼저 수정한다. GPU 8GB는 잠정 예산 가정이므로 실제 VRAM과 사용량을 확인한다. 처음에는 원본 체크포인트·저해상도 로그/ROI subset을 사용하고 전체 지도 export를 반복 저장하지 않는다.

### 보고서 필수 구조

각 실험 보고서에는 `질문 → 사전 등록 가설 → 실행 hash/command → 데이터·좌표계·지원률 → 숫자·시각화 → negative controls → 해석 가능 범위 → 한계 → 다음 단일 결정` 순서를 유지한다. 계획·실행·사후 해석 파일을 분리한다.

### 저장소 구조와 실험 격리

이전 연구의 역할별 `configs/`, `docs/experiments/`, `results/` 구성을 따르되, 각 실험 코드를 별도 디렉터리로 분리한다. 현재 E0 외의 단계별 폴더와 구현 코드는 해당 단계가 시작될 때 만든다.

```text
gradresearch_mast3r_slam/
  docs/experiments/<E코드>_<단계명>/  # 실험 계획·결과 보고서
  configs/<E코드>_<단계명>/           # 설정·manifest·패치
  results/<E코드>_<단계명>/<날짜>/<run_id>/  # 로그와 생성 결과 (Git 제외)
  scripts/<E코드>_<단계명>/           # 해당 단계 전용 스크립트
  src/diagnostics/                    # 검증 후 공유하는 분석 코드
  data/                               # 공통 입력 및 데이터 manifest (Git 제외)
  thirdparty/                         # 공통 upstream·환경·체크포인트 (Git 제외)
```

E0의 기존 결과는 `results/E0_environment_preparation/2026-10-27/`에, 보고서와 manifest·패치는 같은 단계명의 문서/설정 폴더에 있다. 원본 데이터와 공통 환경은 공유하되 각 실행에서 입력 경로·hash와 설정을 기록한다. 단계 간 결과를 재사용할 때는 원본을 변경하지 않고 출처를 manifest에 명시한다. upstream이 자체 `logs/`에 쓰는 결과는 실행 후 해당 실험의 결과 폴더로 옮기고 당시 경로도 기록한다. 원본 MASt3R-SLAM 패키지를 가능한 변경하지 않고 logging wrapper/adapters를 권장한다. 내부 코드 수정이 불가피하면 patch만 분리하고 upstream parity test를 통과시킨다.

---

## 8. 필수 단위 및 음성 대조 실험

1. `SE(3)/Sim(3) roundtrip`: 다른 scale과 회전/이동에서 point/covariance 동일성.
2. `Gauge invariance`: 임의 $q_k>0$로 local geometry·KF scale을 재배분해도 world geometry 및 seam 결과 같음.
3. `Source provenance`: Pointmap 픽셀·pair·anchor→KF/fused/world/export ID 연결이 유효함.
4. `Synthetic flat runway`: 알려진 planar points와 zero-error pose에서 $\mathrm{seam}\approx 0$.
5. `Synthetic local warp`: local pointmap만 휘게 하면 R1에서, world placement 단계 이전에 오류가 검출됨.
6. `Synthetic KF pose jump`: 정상 local patch에 rotation/translation/scale 점프를 넣으면 R3에서 검출됨.
7. `Synthetic fusion outlier`: single-frame biased pointmap으로 weighted fusion 왜곡이 R2에서 검출됨.
8. `Smooth slope negative control`: 실제 경사가 있는 평면/완만한 곡면을 '계단'으로 오판하지 않음.
9. `Different physical patch negative control`: 서로 다른 활주로 위치를 동일 표면처럼 비교하지 않음.
10. `Tracking gap negative control`: pose 누락만 있었고 seam이 없는 시퀀스에서는 가짜 인과 관계를 만들지 않음.
11. `Camera/distortion negative control`: 왜곡 매핑이 어긋나면 ray check가 실패하고 metric 평가 진행 금지.
12. `Support zero`: unscorable KF pair를 zero residual로 평균하지 않음.

---

## 9. 졸업논문으로 전환하는 판단 기준

**강한 분석 기여 후보:** 'MASt3R-SLAM을 사용한 단안 UAV의 반복 평면 관측에서, 어느 중간 표현/연산에서 기하 불연속이 생성되는지'를 동일 물리 표면 대응과 재현 가능한 로그로 보여주고, **원인별 최소 통제 실험이 그 설명을 지지하며 독립 구간에서도 재현**되는 경우.

**제한적 기여:** 특정 영상의 artifact를 한 번 찾아내는 것, Scale 그래프와 단차 그래프의 시간적 일치만 보여주는 것, 개별 plane의 평탄함만 보여주는 것. 이것만으로 알고리즘 개선이나 일반적인 SLAM 연구 기여를 주장하지 않는다.

**개선 연구로 확장할 조건:** 단차의 최초 생성 단계가 확인되고, 그 단계의 frozen/controlled baseline을 기준으로 **GT 없는 작은 변경**이 새로운 UAV 구간의 overlap seam 또는 검증된 surface error를 유의미하게 낮추며 coverage와 tracking 안정성을 해치지 않는 경우. 해당 조건 충족 시 별도의 v2 개선 계획 작성.

**연구 중단 조건:** R0에서 MASt3R-SLAM 단독에는 단차가 없거나, 실질적으로 같은 물리 표면의 반복 관측을 확보할 수 없거나, 유효 reference/calibration 없이 평가의 주요 결론이 원하는 gauge에 따라 뒤집히는 경우. 이때 후속 보정 알고리즘 개발을 강행하지 않는다.

### 잠정 논문 제목

- **원인 분석:** 「단안 드론 영상 기반 MASt3R-SLAM에서 활주로 표면의 Keyframe 간 기하 불연속 원인 분석」
- **개선 확인 이후에만:** 「단안 드론 영상 기반 MASt3R-SLAM의 Keyframe 간 표면 정합성 개선 연구」

---

## 10. 참고 문헌·출처 및 제한

- Murai, Dexheimer, Davison, **MASt3R-SLAM: Real-Time Dense SLAM with 3D Reconstruction Priors**, CVPR 2025. Sec. 3의 pairwise matching, tracking, canonical fusion, backend Sim(3) optimization 및 한계 참조.
- 사용자 이전 실험 보고서: `surface_guided_gaussian_mapping_experiment_summary.md` (E0–E4f), `pointmap_pose_error_decomposition_research_plan_v1(1).md` (A0–A2-O-M 결과와 종료 결정). 여기의 과거 수치는 *기존 실험 기록*이며 이번 계획 결과가 아니다.
- 공식 upstream 소스: `https://github.com/rmurai0610/MASt3R-SLAM`. 실제 사용자 저장소 `https://github.com/seaeast2/gradresearch_mast3r_slam` 의 현재 tree/branch, 수정 사항 및 commit은 실행 시작 시 확인해야 한다.

**최종 연구 원칙:** 3DGS 후처리를 평가하기 전에 **MASt3R-SLAM 자체가 어떤 단계에서 잘못된 3D 형상을 만드는지**를 먼저 규명한다. 추정 Scale 또는 Keyframe ID와의 상관 관계를 물리적 인과로 과장하지 않고, 실제로 *같은 표면을 관찰한* 독립 관측의 정합성과 충분한 support를 모든 결론의 선행 조건으로 둔다.
