# E7-V0 — AMtown01 독립 시퀀스 검증

**실행일:** 2026-10-28  
**판정:** local fusion replay 실행 완료. KF 간 동일 물리 표면 support 부족으로 **독립 seam 재현성은 INSUFFICIENT_SUPPORT / INCONCLUSIVE**. 실제 seam-free 음성 대조는 확보하지 못했다.

## 질문과 사전 가설

HKairport01에서 본 첫 fusion 입력의 높은 영향과 낮은 ROI tracking 유효 대응이 별도의 UAV 장면에서도 나타나는가? E6에서 선택한 첫 입력 하나 제외 frozen replay를 동일하게 적용한다. 사전에 성공 임계값을 추가하지 않았으며, 유효 공통 대응이 없으면 seam 수치를 계산하지 않는다. 실행 전 [실험 protocol](../../../configs/E7_validation/protocol.json)과 RGB 기반 [도로 ROI](../../../configs/E7_validation/roi.json)를 고정했다. [overlap protocol](../../../configs/E7_validation/overlap_protocol.json)은 계측 실행 중 결과를 열기 전에 고정했다.

## 데이터와 좌표

개발 시퀀스가 아닌 UAVScenes `AMtown01`의 기존 연구에서 등록한 첫 RGB 기준 `[60s,120s)` 구간을 사용했다. 5 Hz grid의 300개 중 매 다섯 번째를 제외한 mapping 240장이다. 기존 연구 기록상 AMtown01은 metadata preflight만 수행했고 모델 baseline을 실행하지 않았다. 본 실험에서는 구간을 모델 결과로 재선택하지 않았다. 공통된 장면 유형은 UAV 관측의 지면이지만 활주로가 아니라 마을 도로이므로 장면 특성이 다르다.

기존 분할 JSON의 일부 `rgb_member` 문자열은 실제 archive 항목과 timestamp 소수점 끝자리가 달랐다. 등록된 `rgb_timestamp`에 1μs 이내로 가장 가까운 archive 파일을 선택했고 240개가 모두 서로 다르다. 원본 archive SHA-256은 기존 manifest의 `5670cda374096f22804a8a907783a68d609a1247a52e04c97ad57f165a97006e`와 일치하며, 모든 변환 PNG의 SHA-256을 다시 검증했다. 정확한 파일명·timestamp·hash는 `data/AMtown01/mapping_frames.csv`에 있다.

RGB 영상에서 KF8–12의 도로 부분을 3D나 replay 결과를 보기 전에 수작업 선택했다. 각 다각형은 1,887픽셀이다. 이미지상 포장 도로 후보지만 도로 경계·그림자, 실제 곡률과 가시성은 완전히 검증되지 않았다. 다각형들이 같은 물리 위치를 정확히 가리킨다는 가정도 성립하지 않았다. ROI 지정 시 사용한 영상은 `preflight/roi_draft.png`에 보존한다.

비보정 입력, 512 long side 및 416×512 image, E1/E3와 같은 checkpoint·설정, 1초 forced periodic keyframe, 64개 buffer, single-thread/low-VRAM을 사용했다. 공개 AMtown calibration의 회전 행렬은 `max|RᵀR−I|=4.91×10⁻⁷`, determinant 1.0000006으로 수치 직교성이 있으나 JPG distortion과 camera/pose 연결을 검증하지 않았다. Calibration을 사용하지 않았고 reference/metric GT로 해석하지 않는다.

각 KF의 local XYZ에서 camera Z와 초기 local point의 원점→점 단위 ray를 사용했다. 평면 법선은 초기 ROI의 PCA 법선으로 고정하되 부호는 임의다. 두 KF local Z를 직접 빼지 않는다. World 배치를 위해 저장한 Sim(3)은 `s R X + t`, quaternion `xyzw`, map unit은 비미터 단위다. 실제 유효 대응 부재로 world normal/tangent 수치는 산출하지 않았다.

## 결과: tracking과 첫 fusion

기준 실행과 계측 실행은 각각 240프레임을 처리했고 tracking 239회가 모두 성공했으며 51개 KF를 생성했다. 기준 실행은 2분 36.69초, 계측은 2분 36.71초였다. ROI tracking 유효성은 E3와 같이 `valid_match`, `Q>1.5`, 두 confidence 양수 조건의 교집합이다. 추적 유효는 정답 대응을 보장하지 않는다.

| KF / 최초 fusion 입력 프레임 | ROI 점 수 | tracking 유효 점 | 최초 update 법선 이동 중앙값의 크기 / 초기 ROI 크기 | 입력 가중치 비율 중앙값 |
|---|---:|---:|---:|---:|
| 8 / 40 | 1,887 | 1,887 | 1.81% | 44.8% |
| 9 / 45 | 1,887 | 1,887 | 1.98% | 39.6% |
| 10 / 50 | 1,887 | 1,887 | 1.58% | 43.6% |
| 11 / 55 | 1,887 | 1,886 | 0.19% | 45.1% |
| 12 / 59 | 1,887 | 1,887 | 0.70% | 43.7% |

E5의 HKairport01에서는 선정된 5개 KF 중 4개의 첫 update 법선 이동이 약 10.2%였고 KF32·33의 유효 점은 각각 0개였다. 이번 도로 ROI에서는 첫 이동이 0.19–1.98%, 유효 비율이 99.95–100%여서 **해당 관찰 패턴은 이 다섯 ROI에서 재현되지 않았다**. 다만 다른 시퀀스, 좁은 ROI, 텍스처와 장면 구성이 모두 다르며, 5개 KF는 인접한 한 구간이다. 이 비교는 일반적인 부재를 증명하거나 영상 조건 하나의 인과 효과를 분리하지 않는다.

## 첫 입력 제외 replay

초기 pointmap과 후속 입력·상대 pose를 고정하고 각 KF의 첫 tracking fusion 입력만 제외했다. 재실행이 아닌 조건부 replay이므로 이후 tracking 결과 변화는 포함하지 않는다. 아래 Z와 ray는 `(제외 − 원본)`의 동일 픽셀별 중앙값, 각 KF local 임의 단위다. 평면 잔차는 각 map의 PCA 절대 잔차 p90을 초기 ROI 크기로 나눈 값이다.

| KF | update 수 | camera Z 변화 | 초기 ray 방향 변화 | 원본 / 제외 평면 잔차 p90 ÷ 초기 ROI 크기 |
|---|---:|---:|---:|---:|
| 8 | 5 | -0.00159 | -0.00204 | 0.400% / 0.380% |
| 9 | 5 | -0.00368 | -0.00448 | 0.759% / 0.746% |
| 10 | 5 | -0.00201 | -0.00282 | 0.976% / 0.992% |
| 11 | 4 | -0.00004 | +0.00145 | 1.117% / 1.105% |
| 12 | 5 | -0.00345 | -0.00426 | 2.190% / 2.197% |

첫 입력을 제외했을 때 지도는 변하지만, ROI 평탄도 p90은 일부에서 늘고 일부에서 줄었다. 평면성 변화나 Z/ray 변화는 깊이 정확도와 동치가 아니다. 전체 업데이트와 confidence·validity, normal 이동은 `events_summary.csv`, 최종 두 replay map과 원본/제외 confidence는 KF별 NPZ에 있다.

## 공통 관측과 음성 대조

LK optical flow를 모든 중간 프레임에 적용하고 각 ROI를 2픽셀 침식, 3픽셀 grid, 왕복 오차 ≤1픽셀, 9×9 NCC ≥0.8 조건을 사용했다. 도로가 좁아 E2a의 5픽셀 grid·침식 대신 해당 값을 결과 전에 별도 고정했다. 이 자체도 정답 보증은 아니다.

| KF 쌍 | source grid | 전·역 추적 성공 | 목표 ROI 내부 | 최종 후보 |
|---|---:|---:|---:|---:|
| 8–11 | 129 | 129 | 0 | 0 |
| 9–12 | 131 | 131 | 0 | 0 |
| 10–12 | 129 | 129 | 0 | 0 |

후속 진단에서 8→11의 grid 추적점 중앙 이동은 약 +41.5픽셀이었으나 목표 polygon은 source polygon보다 20픽셀 이동해 있었다. 즉, RGB에서 도로로 선택한 두 polygon이 **영상 추적상 같은 부분을 충분히 포함하지 못했다**. 이 값은 움직임의 진단일 뿐 추적의 정확성이나 실제 가시성을 입증하지 않는다. 선정 ROI가 실제로 겹치지 않는다는 뜻이지 장면 전체에 overlap이 없다는 뜻은 아니다. 결과를 본 뒤 polygon을 다시 맞추지 않았다.

세 쌍 모두 `INSUFFICIENT_SUPPORT`; world Z/XY·normal/tangent, export 공통 support의 분리와 replay 차이는 측정 불능이다. 0으로 기입해 평균하지 않았다. 이 때문에 E7은 G2의 검증된 공통 관측, G4의 실제 seam-free 음성 대조를 통과하지 못했다. 선택한 도로에서 첫 update 이동이 작다는 사실만으로 seam-free임을 선언하지 않는다.

## 검증과 한계

- 기준·계측 실행의 tracking/KF 이벤트 239개가 정확히 같고 PLY, trajectory, provenance SHA-256이 각각 일치했다. 단일 실행 쌍의 parity다.
- 24개 ROI 업데이트에서 confidence 가중 평균 원본 replay의 모든 XYZ와 weight가 저장된 값과 bitwise 일치한다. 각 KF의 pixel ID를 유지했다. 저장된 최종 pose 51개는 finite이고 positive scale이다.
- E6의 합성 가중 outlier 및 비편향 입력 대조, E4의 Sim(3) round-trip/gauge 테스트를 재사용한다. 이것들은 E7의 실제 음성 대조나 대응 검증을 대신하지 않는다.
- 실제 공통 표면/대응, seam-free 영역, 외부 깊이 기준 및 calibration QA가 부족하다. frozen 입력 replay는 전체 시스템 개입이 아니며 단일 시퀀스의 제한된 local 관찰이다. 높은 tracking 유효 비율을 실제 correspondence 정확도라고 부르지 않는다.

## 다음 단일 결정

현재 결과로 E6의 KF 간 seam 원인을 독립 검증하거나 일반화할 수 없다. 다음에는 **RGB 추적을 사용해 실제로 겹치는 정적 도로 ROI를 먼저 선정하고 독립 대응·가시성 및 seam-free 음성 대조를 검증하는 별도 support 보강 실험**을 설계한다. 이 결과를 본 후 바꾼 ROI는 새로운 탐색으로 구분하고 본 E7의 실패 기록을 유지한다. support가 확보되기 전에는 E8에서 원인 우세나 알고리즘 개선을 주장하지 않는다.

## 실행 및 산출물

```bash
thirdparty/mast3r-env/bin/python scripts/E7_validation/prepare.py
# GPU 접근 필요; 기존 run ID가 있으면 덮어쓰기를 거부함
scripts/E7_validation/run_baseline.sh
scripts/E7_validation/run_probe.sh
MPLCONFIGDIR=/tmp/mpl-e7 thirdparty/mast3r-env/bin/python scripts/E7_validation/analyze.py
MPLCONFIGDIR=/tmp/mpl-e7 thirdparty/mast3r-env/bin/python scripts/E7_validation/overlap.py
thirdparty/mast3r-env/bin/python scripts/E7_validation/validate.py
```

입력 준비는 기존 연구 archive 경로가 필요하다. 각 run 결과와 hash, `analysis.json`, `validation.json`, `overlap_summary.json`, candidate 좌표와 그림은 `results/E7_validation/2026-10-28/`에 있으며 Git 제외다. 반복 실행은 기존 산출물을 보존할 새 run ID와 경로가 필요하다. 원본 archive와 이전 실험 산출물은 수정하지 않았다.
