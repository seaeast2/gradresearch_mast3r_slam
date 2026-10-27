# E1_MASt3R-SLAM 단독 지도 빠른 점검

**실행일:** 2026-10-27  
**상태:** 예비 점검 완료 / 단차 의심, 동일 물리 표면 대응 미검증. 정식 E1 게이트 판정은 보류.

## 질문과 실행

HKairport01 기존 `[60s,120s)` 구간의 240 RGB 입력을 MASt3R-SLAM 단독으로 처리한 지도에서 포장면의 불연속이 보이는지 확인했다. 사용자 요청에 따라 1초와 2초 정책의 기하 비교는 수행하지 않았다.

기존 E0a의 2초 최소 keyframe 간격, 512 입력(실제 모델 이미지 512×416), 32 KF 버퍼, single-thread 및 uncalibrated 설정을 사용했다. 입력 목록의 실제 RGB timestamp를 적용했다. 현재 GPU 호환·저메모리 패치 및 keyframe 정책이 포함되므로 공식 원본 설정과 동일하다고 주장하지 않는다. 결과는 6 keyframe, 1,192,768개의 유한 XYZ 점이다.

최종 PLY export에 keyframe 번호와 canonical pixel index만 추가로 저장하는 관측 패치로 같은 설정을 다시 실행했다. **재실행 PLY의 SHA-256은 이전 2초 실행과 완전히 동일**했다 (`99f85cf7651031c12c0e7919f374bac65f5449e62f6da5ad212731bbcfd95628`). 단일 실행 쌍의 export parity이며 여러 실행·중간 단계의 완전한 parity를 보증하지 않는다. Source ID는 최종 keyframe/canonical pixel 출처이지 fusion에 기여한 모든 원본 프레임 출처는 아니다. 설정과 파일 해시는 `configs/E1_baseline_reproduction/quicklook_manifest.json`에 보존했다.

## 관찰

- RGB에서 포장면으로 보이는 영역을 각 KF 이미지에 수작업 polygon으로 표시했다. KF0–4에서 유효 ROI 점이 각각 32,564 / 13,482 / 11,188 / 9,760 / 8,102개였다. KF5에서는 포장면 ROI를 지정하지 않았다.
- KF1 ROI의 평면을 기준으로 표시한 측면 분포에서 **KF4의 포장면 점들이 KF1–3보다 아래에 분리된 띠**가 눈에 띈다. 따라서 MASt3R-SLAM 단독 결과에 기하 불연속이 **의심되는 구간**이 있다.
- 보조 확인으로 KF1 기준 평면의 두 접선 좌표를 0.05 지도 단위로 나누어, 두 KF에 각각 5점 이상 있는 격자의 높이 중앙값을 비교했다. KF4−KF1은 공통 격자 170개, 중앙값 −0.051 지도 단위; KF4−KF2는 183개, −0.043; KF4−KF3은 183개, −0.042였다. 이 값은 **격자 기준 예비 묘사**이며 metric 높이·오차나 seam 지표가 아니다.
- 이 ROI는 각각 포장면으로 보이는 영역이지 동일한 실제 위치를 영상 대응과 가시성으로 검증한 mask가 아니다. 평면 방향도 중력 방향이 아니라 KF1의 탐색적 기준 평면이며 지도 scale은 검증되지 않았다. 따라서 이 그림만으로 실제 같은 표면의 단차로 **확정할 수 없고**, G0/G2 통과나 원인 규명으로 간주하지 않는다.

## 파일과 다음 확인

- 최종 RGB 지도: `results/E1_baseline_reproduction/2026-10-27/quicklook/output/mapping.ply`
- KF별 색 지도: `results/E1_baseline_reproduction/2026-10-27/quicklook/map_keyframe_colors.ply` (KF0 빨강, KF1 파랑, KF2 초록, KF3 보라, KF4 주황, KF5 갈색)
- 포장면 이미지 ROI: `results/E1_baseline_reproduction/2026-10-27/quicklook/pavement_roi_images.png`
- KF별 ROI 측면 분포: `results/E1_baseline_reproduction/2026-10-27/quicklook/pavement_by_keyframe.png`
- 전체 지도 직교 투영: `results/E1_baseline_reproduction/2026-10-27/quicklook/world_views.png`. 지도 축은 중력 정렬되지 않았고 그림은 1–99% 범위로 잘렸다. PLY 원본은 잘리지 않았다.
- 원본 로그와 출처: `results/E1_baseline_reproduction/2026-10-27/quicklook/run.log`, `provenance.npz`.

다음은 KF1–4에서 시각적 특징점 및 가시성을 이용해 같은 포장 위치의 대응을 검증하고, 그 공통 support에 대해 분리 현상이 유지되는지 보는 것이다. 관측 지원이 부족하면 `INSUFFICIENT_SUPPORT`로 남긴다. 추적 타임라인, 원본 프레임까지의 fusion ancestry 및 stage별 원인 분석은 아직 수행하지 않았다.
