# E5 — Tracking·keyframe 경계·매칭 상태 타임라인

**실행일:** 2026-10-28  
**상태:** 240프레임 타임라인 및 KF31–35의 23개 ROI 업데이트 분석 완료. 첫 업데이트 5건의 MASt3R 매칭 필터 재현 완료. 시차와 인과관계는 미판정.

## 질문과 방법

E3에서 관찰된 포장면의 낮은 tracking 유효 대응과 큰 fusion 이동이 keyframe 경계, 영상 관측 조건, E4의 backend 분리 변화와 시간상 어떻게 연결되는가?

E1의 모든 입력 timestamp 및 tracking/KF 이벤트에 E3의 23개 ROI 업데이트를 결합했다. E4의 backend 이벤트는 해당 최적화를 요청한 **새 keyframe이 생성된 프레임**에 연결했다. Backend의 실제 실행 시각은 프레임의 촬영 시각과 다르며, 표시는 처리 순서와 입력 시간 기준이다. Backend 분리 변화는 E4에서 최종 fused map을 고정한 결과이며 실제 당시 local map과 일치하는 KF36 이후만 타임라인에 넣었다.

E3 ROI의 이미지 gradient와 corner response를 측정하고, 같은 ROI의 5픽셀 격자에 별도의 LK optical flow를 적용했다. 전·역방향 왕복 오차 ≤1픽셀과 9×9 패치 NCC ≥0.8을 통과한 점을 영상 대응 **후보**로 표시했다. E3 tracking 유효 mask와 LK 후보는 알고리즘과 표본이 다르다. LK 통과는 정답 보증이 아니며 비율을 직접 같은 분모의 정확도처럼 해석하지 않는다. 상세 조건은 [protocol](../../../configs/E5_timeline/protocol.json)에 있다.

타임라인 관찰 후 추가한 탐색 분석으로, 각 KF 생성 직후 첫 tracking 업데이트 5건에서 MASt3R pair inference 및 matching을 GPU로 재현했다. 새 keyframe 생성 시 tracker는 매칭 초기 인덱스를 reset한다. 실제 코드의 iterative projection 통과와 그 뒤 3D 거리 `< 0.1` 검사를 분리했으며, 최종 matching mask 및 대응 인덱스가 E3 캡처와 모두 정확히 같음을 확인했다. 거리 검사는 descriptor 기반 후속 refinement **이전**의 추정 3D 점들에 적용된다.

## 결과

### Tracking 및 keyframe 경계

- E1의 239개 tracking 호출은 모두 성공했고 재위치 시도는 기록되지 않았다. 입력 프레임 간격의 중앙값은 약 0.200초, 최대는 약 0.400초다. 따라서 이 실행에는 계획서의 과거 실험에서 언급한 2.4초 tracking 누락 사례가 없다. 입력에서 제외한 held-out 프레임은 이 통계의 대상이 아니다.
- KF31–35의 23개 업데이트 중 포장면 ROI tracking 유효 대응이 0개인 업데이트는 **5개**였다: KF32의 프레임 149–151과 KF33의 프레임 153–154. 전체 ROI 기준 유효 대응 비율의 업데이트별 중앙값은 **1.63%**다. 전체 tracking 성공과 특정 ROI의 제약 정도는 다르다.
- KF31–35의 **첫 업데이트 5개 중 4개**에서 법선 방향 픽셀 이동 중앙값의 크기가 초기 ROI 크기의 약 10.2%였다. 첫 업데이트 5개의 중앙값은 10.17%, 나머지 18개의 중앙값은 2.19%였다. KF31 첫 업데이트는 1.92%로 예외다. 선택한 5개 KF는 같은 구간의 연속 사례이며, 이 관찰은 통계적 일반화나 경계가 원인이라는 증거가 아니다. 첫 업데이트 이후 이동이 상쇄될 수도 있다.

### 포장면 매칭 필터의 동작

| KF / 첫 입력 | ROI 픽셀 | projection 통과 | 3D 거리 `< 0.1` 통과 | 두 조건 모두 통과 | 거리 중앙값 |
|---|---:|---:|---:|---:|---:|
| 31 / 145 | 10,309 | 10,309 | 950 | 950 | 0.1479 |
| 32 / 149 | 9,545 | 8,781 | 0 | 0 | 0.1895 |
| 33 / 153 | 8,791 | 8,156 | 0 | 0 | 0.2467 |
| 34 / 158 | 7,986 | 7,470 | 1 | 1 | 0.2046 |
| 35 / 163 | 7,466 | 6,819 | 122 | 122 | 0.2257 |

거리와 임계치 0.1은 이 pair inference의 **내부 3D 좌표 단위**이며 미터가 아니다. 모든 ROI 픽셀에 대한 거리 중앙값을 표시했다. KF32·33 첫 업데이트에서는 projection에 통과한 픽셀이 많지만 거리 검사를 통과한 픽셀이 없어 `valid_match`가 0이 됐다. 다섯 첫 업데이트에서는 ROI의 매칭 신뢰도 `Q > 1.5` 조건은 모두 통과했다. 이 경우 유효 대응 부족의 직접적인 코드 경로는 3D 거리 검사다. **이것이 잘못된 필터링이라는 뜻은 아니다**: raw pair geometry, projection, 가림 또는 추정의 스케일 등 어떤 원인으로 거리가 컸는지는 분리하지 못했다.

KF32/프레임149에서 별도 LK 추적은 ROI 격자 380개 중 338개를 후보로 반환했다. KF33/프레임153에서도 348개 중 280개가 후보였다. 두 경우 모두 MASt3R tracking 유효 대응은 전체 ROI에서 0개였다. 이는 영상상 후보가 존재하는 상황에서도 MASt3R의 **3D 기하 유효성 검사**가 추적 대응을 제외한 사례다. LK 후보의 실제 대응 정확도는 독립 수작업/GT로 검증하지 않았으며, 서로 다른 검사이므로 충돌을 알고리즘 오류로 단정하지 않는다.

### 영상 조건 및 backend

다섯 KF ROI의 gradient 중앙값은 0.0178–0.0196이다. 이는 입력 512×416 영상의 [0,1] grayscale에 적용한 Sobel 값이며, 별도의 정상 영역 기준이 없어 낮은 텍스처가 원인이라고 판정할 수 없다. ROI 내 gradient 사분위별 tracking 유효 비율을 계산했지만, 인접 픽셀과 반복 프레임이 독립이 아니고 차선·그림자 경계가 gradient에 포함된다. `R4_texture_quartiles.csv`는 탐색 자료이며 인과 통계가 아니다.

LK 후보의 중앙 2D 이동은 첫 업데이트 5건에서 0.90–5.26픽셀, 이후 업데이트 전체에서는 2.05–32.11픽셀 범위였다. 이는 회전·이동과 장면 기하를 함께 포함한 **영상 이동**이다. 기준 카메라/자세와 검증된 대응을 사용한 순수 기하 시차는 측정하지 못했으므로, 작은 시차가 원인인지 판단할 수 없다. LK 후보 비율은 가시 overlap의 정확한 면적도 아니다.

KF35의 마지막 fusion 업데이트와 KF36 생성은 프레임 167에서 발생했다. 그 뒤 backend KF36 solve는 E4에서 같은 frozen map에 대해 KF32–35 분리의 절대 중앙값을 0.05100에서 0.06789 지도 단위로 바꾸었다. 이 시간적 연관은 관측 사실이지만, 앞선 ROI 매칭이나 fusion 업데이트가 그 backend 변화의 원인이라는 증거는 아니다. 임의 normal, 같은 영상 구간의 3쌍, E2a 후보 정확도 및 외부 기준의 한계는 E4와 동일하다.

## 검증과 제한

- 240개 timeline 행을 E1과 대조하고, 23개 이벤트의 ROI mask·LK 후보 수·임계치 및 E4 backend 단계→생성 프레임 연결을 검증했다. LK 분석에 읽은 원본 PNG는 CSV의 SHA-256과 대조했다.
- 첫 업데이트 5건의 matching 재추론은 E3에서 기록한 `valid_match`와 대응 인덱스에 대해 **모두 정확히 일치**했다. 이는 해당 첫 업데이트와 해당 mask/인덱스의 parity이며 전체 추적 재현이 아니다.
- 모든 tracking이 성공했으므로 이 실행은 tracking gap 가설의 인과 검증이나 tracking 실패 음성 대조를 제공하지 않는다. 정상 seam-free ROI, 독립 장면, pixel GT, 검증된 시차 및 backend edge별 잔차는 없다.
- 빈 ROI 지원을 0 오차로 채우지 않았다. LK와 MASt3R가 모두 유효한 격자점이 없으면 두 방법의 대응 위치 차이는 빈 값으로 둔다.

## 다음 결정

E4 직후에는 `E6-T-POSE`를 우선 후보로 제안했지만, E5에서 **keyframe 첫 업데이트의 반복적인 큰 이동과 3D 거리 검사 탈락 경로**가 드러났으므로 E6의 단일 우선 대조로 **E6-T-FUS**를 권고한다. 저장된 tracking pose와 후속 fusion 입력을 고정하고, 원래 replay와 첫 관측 제외 replay를 같은 ROI에서 비교해 그 관측이 최종 canonical map에 미치는 영향을 확인한다. 이 replay는 이후 tracking 입력까지 다시 생성한 전체 시스템 개입이 아니며, 정상 ROI 대조와 coverage 변화도 함께 다뤄야 한다. E4의 pose 효과도 이미 관찰됐으므로 다른 원인이 배제되는 것은 아니다.

## 산출물 및 재현

- `results/E5_timeline/2026-10-28/timeline/`: `R4_timeline.csv`, `R4_roi_events.csv`, `R4_texture_quartiles.csv`, `R4_first_match_gates.csv`, `R4_timeline.png`, LK 후보 및 매칭 필터 NPZ, 두 사례 이미지, manifest·검증·로그.
- CPU 타임라인: `MPLCONFIGDIR=/tmp/mpl-e5 thirdparty/mast3r-env/bin/python scripts/E5_timeline/analyze_timeline.py`
- 첫 매칭 필터 GPU 재추론: `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 thirdparty/mast3r-env/bin/python scripts/E5_timeline/replay_first_match_gates.py`
- 결과 검증: `thirdparty/mast3r-env/bin/python scripts/E5_timeline/validate_timeline.py`
