# E1_주기적 1초 keyframe 기준선 실행 결과

**실행일:** 2026-10-27  
**상태:** 실행 및 예비 지도 점검 완료 / 동일 실제 표면의 대응 미검증으로 단차 확정 보류.

## 실행 조건

HKairport01 기존 `[60s,120s)` 구간의 mapping RGB 240프레임을 실제 촬영 시각으로 입력했다. 512 장변 입력(실제 512×416), uncalibrated, keyframe buffer 64, single-thread 및 low-vram 설정이다. 사용자의 요청에 따라 마지막 keyframe 이후 1초가 지난 첫 **추적 성공 프레임**을 keyframe으로 추가한다. 추적 실패·재위치와 입력 timestamp의 불규칙성에 따라 정확히 매초 생성되는 것은 아니다. 강제 keyframe 추가는 공식 기본 정책의 변경이며 별도의 [패치](../../../configs/E1_baseline_reproduction/periodic_keyframes.patch)로 보존했다.

초기 주기적 실행은 backend의 GPU 메모리 누적으로 약 34 KF 뒤 CUDA OOM으로 실패했다. 실패 로그 `results/E1_baseline_reproduction/2026-10-27/periodic_1s/run.log`를 보존했다. [backend 캐시 반환 패치](../../../configs/E1_baseline_reproduction/backend_cache.patch)를 추가하여 재시도했고, 이 변경도 공식 기본 환경과 구분한다. 체크포인트·소스·설정 해시는 [manifest](../../../configs/E1_baseline_reproduction/periodic_1s_manifest.json)를 따른다.

## 결과

- 240프레임 입력에서 초기화 1회, 나머지 239개 tracking 호출이 모두 성공으로 기록됐다. skip, Cholesky 실패 및 재위치 시도 로그는 없었다. tracking 성공 로그는 궤적의 절대 정확도를 보증하지 않는다.
- **53 keyframe**이 생성됐다. 인접 keyframe 시간 차이는 최소 1.000초, 중앙값 1.200초, 최대 1.400초였다. 원래 입력의 불규칙한 간격 및 held-out 프레임 제외 때문에 1초보다 긴 간격이 생긴다.
- 정상 종료 후 10,376,415개의 유한 XYZ 점을 포함한 PLY가 생성됐다. 1초마다 측정한 GPU 전체 사용량의 최대는 7,150 / 8,151 MiB였고 실행 시간은 161.45초였다. 표본 사이 순간 피크는 확인할 수 없다.
- 출처·tracking 기록 없는 기준 실행과 기록을 켠 실행을 동일 설정으로 각각 수행했다. PLY SHA-256은 둘 다 `7745b3f2bb7a281151b7c7c2c9acfb1f93b40b96827c5438a60b25cd294530be`; keyframe 궤적 SHA-256은 둘 다 `25a68a01327cfab8ea2733a37bb1a80677e56aebb1386c81a7ba6fa3e146d7f0`이었다. 단일 실행 쌍에 대한 최종 export parity이며 중간 pointmap과 전반적인 결정론을 보증하지 않는다.
- KF29–35의 RGB 포장면을 탐색적으로 표시해 KF29 평면 기준 측면 분포를 시각화했다. KF32의 점 띠가 위쪽, KF35의 점 띠가 아래쪽에 분리되어 보여 **단차 의심**이 있다. 선택한 ROI가 같은 실제 물리 위치임을 영상 대응으로 검증하지 않았고, 표시 축도 중력 정렬이나 metric scale이 아니다. 따라서 단차 확정, 원인 판정 또는 G0/G2 통과로 주장하지 않는다.
- 사용자 요청에 따라 **1초와 2초 실행의 기하 비교는 하지 않았다.**

## 산출물

- RGB 3D 지도: `results/E1_baseline_reproduction/2026-10-27/periodic_1s_retry/output/mapping.ply`
- KF 색상 지도: `results/E1_baseline_reproduction/2026-10-27/periodic_1s_retry/map_keyframe_colors.ply`
- KF 이미지: `results/E1_baseline_reproduction/2026-10-27/periodic_1s_retry/keyframe_contact.png`
- 포장면 이미지 ROI 및 KF별 측면 분포: 같은 폴더의 `pavement_roi_images.png`, `pavement_by_keyframe.png`. KF 색상은 그래프 범례를 따른다.
- 프레임별 기록: `tracking_timeline.csv`, 최종 keyframe별 canonical 픽셀 출처 `provenance.npz`. 이 출처는 fused map에 기여한 모든 프레임의 ancestry가 아니다.
- 재실행: `scripts/E1_baseline_reproduction/run_periodic_1s.sh data/HKairport01/mapping data/HKairport01/mapping_frames.csv <고유-run-id>`.

다음에는 KF29–35에서 영상 특징점과 가시성을 이용해 같은 실제 포장 위치를 확인하고, 공통 support에서 분리 현상이 유지되는지 평가한다. 지원이 부족하면 `INSUFFICIENT_SUPPORT`로 기록한다. 향후 다른 구간에서 64 KF 또는 8 GB를 초과할 수 있다.
