# E7b — KF-local 형상, backend pose 및 조건부 렌즈 보정 진단

**실행일:** 2026-10-28  
**판정:** 분석된 후보점에서 backend pose revision에 따른 Z·법선 방향 배치 변화를 확인했다. 공개 렌즈 모델을 이용한 조건부 raw 비교도 수행했다. 다만 사용자 확인 U자형 전체의 동일 표면 mask, 독립 pixel 대응, 실제 JPG 왜곡 상태가 없어 **누적 pose 오류나 렌즈 왜곡을 원인으로 확정하지 못했다**.

## 질문과 사전 가설

사용자는 KF 색상 PLY의 XZ 측면에서 보이는 U자형과 Z 방향 다층이 같은 평면에서 발생한다고 육안으로 확인했다. 본 실험은 요청에 따라 실제 지형·건물 혼합을 그 U자형의 대안 원인으로 다루지 않는다. 다만 스크린샷에 표시된 전체 표면의 3D point ID/mask는 따로 제공되지 않았으므로 E7a에서 이미 기록한 도로·갓길의 영상 대응 **후보 subset**으로 측정한다. 이 subset이 사용자가 확인한 전체 U자형 표면을 대표한다는 뜻은 아니다.

두 가설을 구분한다. (1) 각 local patch는 상대적으로 평탄하나 KF world pose/scale 배치가 Z·법선 방향 불연속에 기여한다. (2) JPG의 렌즈 왜곡이 raw 형상 및 상대 pose를 바꿔 전체 형상에 기여한다. 실행 전 [protocol](../../../configs/E7b_geometry_diagnostic/protocol.json)에 fixed support·pose replay와 조건부 raw 보정 비교를 등록했다. 이미 E7/E7a 및 사용자 이미지를 관찰한 동일 장면의 **탐색 실험**이다.

## 데이터, 좌표 및 방법

AMtown01 E7의 동일 240 PNG, 512×416 입력, 원래 checkpoint 및 비보정 설정, 1초 강제 KF, 64 buffer를 사용해 backend를 재계측했다. 51개 solve의 전후 Sim(3), frame IDs, graph edge를 기록했다. 점은 E7a KF8–12에서 캡처한 초기 pointmap 및 마지막 fused pointmap을 사용한다. KF13 생성 이후 pose에 최종 map을 그대로 적용한다. E7b에서는 각 solve 시점의 pointmap을 따로 캡처하지 않았으므로 이것은 **고정 map pose replay**이며 당시 실제 중간 map이 최종 map과 같았다는 독립 검증은 아니다.

E7a의 세 도로·갓길 LK 후보 및 양쪽 원본·개입 export 공통 support를 그대로 사용했다: KF8–11 28점, KF9–12 35점, KF10–12 58점. 자동 후보는 독립 정답·가시성이 확인되지 않았고 표본이 동일 구간에 몰려 있다. 각 쌍의 source 최종 world 점으로 PCA 법선을 구해 +world Z 방향으로 부호를 맞춘 후 비교 전체에 고정했다. `world = s R local + t`, quaternion은 `xyzw`, 단위는 map 단위이며 world Z는 중력 정렬이 아니다. 서로 다른 KF local camera Z를 직접 빼지 않는다.

## KF-local 평탄도

동일 후보 픽셀에서 각 KF의 초기 및 마지막 fused map을 각각 PCA 평면에 맞추고, 절대 잔차 p90을 **초기 ROI 평면 투영 크기**로 나누었다. 값이 작아도 실제 깊이 정확도를 뜻하지 않는다. 픽셀 폭 15–18, 높이 93의 좁은 띠이며 3D source 점의 둘째/첫째 특이값 비는 약 0.06–0.08로 법선 추정이 민감하다.

| 후보 쌍 | KF | 초기 p90 / 초기 크기 | fused p90 / 초기 크기 | 공통 후보 |
|---|---:|---:|---:|---:|
| 8–11 | 8 | 0.128% | 0.463% | 28 |
| 8–11 | 11 | 0.351% | 0.610% | 28 |
| 9–12 | 9 | 0.589% | 0.605% | 35 |
| 9–12 | 12 | 0.629% | 0.690% | 35 |
| 10–12 | 10 | 0.787% | 0.653% | 58 |
| 10–12 | 12 | 0.709% | 0.882% | 58 |

선택된 작은 patch들은 초기·fused 양쪽에서 이 지표상 상대적으로 평탄하다. 일부는 fusion 후 잔차가 증가하고 하나는 감소한다. ROI의 실제 평면성이나 whole-map U자형 생성 단계를 단독으로 확정할 수는 없다.

## 고정 map에서 backend pose 효과

아래는 같은 최종 fused pointmap과 동일 후보에 대해 KF13 solve 직전·직후와 마지막 KF50 solve 후 pose를 대입한 값이다. 법선은 쌍별 고정이고 양의 방향은 +world Z 쪽이다. 숫자는 `(KF B − KF A)`의 signed normal 중앙값과 tangent 크기 중앙값이다.

| KF 쌍 | KF13 직전 normal / tangent | KF13 직후 normal / tangent | KF50 직후 normal / tangent |
|---|---:|---:|---:|
| 8–11 | +0.02615 / 0.00930 | +0.02600 / 0.00918 | +0.02546 / 0.00890 |
| 9–12 | +0.01803 / 0.01932 | +0.01282 / 0.00564 | +0.01336 / 0.00574 |
| 10–12 | −0.00192 / 0.00780 | −0.00775 / 0.01007 | −0.00727 / 0.00970 |

예를 들어 9–12에서 KF13 pose revision 전후 `|world Z|` 차이 중앙값은 0.01692→0.01245, XY 거리는 0.02039→0.00596이었다. 10–12에서는 각각 0.00276→0.00784와 0.00780→0.00993으로 바뀌었다. 따라서 **고정된 후보 geometry에 pose 변화가 영향을 준다**. 그러나 한 쌍은 감소하고 다른 쌍은 증가하며, unverified 후보와 고정 map 재배치만으로 실제 pose 오차가 누적됐거나 지도의 전체 U자형이 그 때문에 생겼다고 판정할 수 없다.

최종 pose에 초기 map을 가상 배치했을 때의 signed normal 중앙값은 순서대로 +0.07040, +0.03285, +0.01897이었다. 초기와 최종 map의 차이에는 fusion과 pose의 상호작용이 있고, pose는 실제 fused map으로 최적화되었으므로 차이를 독립적인 원인 기여량으로 해석하지 않는다. 모든 step의 signed p10–p90, |normal|·tangent·Z·XY의 중앙값과 p90은 `backend_world_pairs.csv`에 기록했다.

## 카메라 보정 QA 및 조건부 raw 대조

공개 AMtown 보정은 `fx=1453.72`, `fy=1453.28`, `cx=1172.18`, `cy=1041.78` 및 5계수 distortion을 명시한다. 외부 회전은 수치적으로 직교하지만 이것은 intrinsic/distortion이 JPG에 적용되는지의 검증이 아니다. 샘플 JPG EXIF에는 그 전처리 여부를 확인할 정보가 없었다.

공개 계수로 2448×2048의 8,585개 pixel grid를 역변환한 뒤 다시 투영했을 때, 292개에서 round-trip 오차가 0.1픽셀 이상이었고 그중 127개는 1픽셀 이상이었다. 일부 외곽에서 OpenCV 기본 역변환이 수치적으로 불안정했다. 이는 모델의 역변환 수치 검사이며 **실제 렌즈 왜곡의 존재나 calibration의 정확성을 증명하지 않는다**. JPG가 이미 보정됐는지도 미확인이다. 원본 및 가정에 따른 remap 영상과 전체 grid QA를 보존했다.

그 제한을 명시하고 `JPG가 공개 distortion을 포함한다`고 **가정한 조건부 민감도 실험**을 수행했다. KF8·9·10의 생성 프레임과 이전 KF를 원본 및 OpenCV full-resolution undistortion으로 MASt3R raw self-branch에 각각 입력했다. E7a source 후보를 가정된 remap으로 대응시키고 이미지 안에 있으며 역변환 오차 <0.1 원본 픽셀인 공통점만 사용했다. 보정 후 점은 bilinear interpolation했다. Local 좌표의 gauge/scale이 다를 수 있으므로 점별 XYZ 차이는 계산하지 않았고 각 map의 PCA 잔차 p90/자체 patch 크기를 비교했다.

| KF | 공통 후보 / 기존 후보 | 원본 raw p90 / 크기 | 가정된 보정 raw p90 / 크기 |
|---|---:|---:|---:|
| 8 | 28 / 28 | 0.128% | 0.532% |
| 9 | 35 / 35 | 0.589% | 1.353% |
| 10 | 58 / 58 | 0.787% | 1.586% |

이 세 좁은 patch에서는 조건부 remap 후 선택한 평탄도 지표가 커졌다. 그러나 잘못된 보정 가정, 보간·시야 변화, pair inference의 차이, ROI 형태와 검증되지 않은 correspondence가 모두 영향을 줄 수 있다. **렌즈 보정이 나쁘다거나 실제 원본에 왜곡이 없다는 뜻은 아니다.** 원본 raw self-branch 재추론은 저장된 E7a 초기 점과 세 표본 모두 정확히 일치했다. 후보의 이미지 중심 거리도 약 172–204픽셀에 국한되어 중심·가장자리의 독립 비교가 되지 않는다.

이 조건부 대조는 raw pair inference만 실행했다. Undistorted 영상으로 tracking/backend를 재실행하거나 상대 pose를 비교하지 않았으므로 렌즈 왜곡이 pose 누적에 미치는 효과는 **미측정**이다. 특히 원본 JPG preprocessing과 calibration 호환성이 해결되지 않은 상태에서 보정된 pose/map을 실제 정답으로 제시하지 않는다.

## 검증과 한계

- Backend 계측은 240프레임, 239 tracking 호출 및 51개 KF를 정상 처리했다. E7 baseline과 tracking event 및 최종 PLY·trajectory·provenance 해시가 일치했고 마지막 pose는 E7a에 저장한 pose와 완전히 일치했다. 실행 시간은 2분 36.04초다.
- 최종 pose + frozen fused point의 세 쌍 결과가 E7a의 동일 후보 결과와 일치한다. Sim(3) round-trip과 world-preserving gauge 재표현도 수치 오차 내 통과했다. Raw 재추론의 원본 parity와 보정 전후 공통 후보 count를 검증했다.
- `all_point_kf_orthogonal.png`는 XY/XZ/YZ에서 같은 축 비율로 표시한 전체 export의 표본이다. 사용자 확인 표면만을 분리한 mask가 아니며, 이 그림만으로 U자형 표면의 곡률을 정량화하지 않았다. 시점과 축의 부호에 따라 U 모양의 화면상 방향은 달라질 수 있다.
- E7a 후보의 정확성과 가시성, 실제 seam-free 음성 대조 및 외부 depth/pose 참조는 미검증이다. 전체 U자형의 추정 원인, 연속 pose 누적 여부, 렌즈 왜곡의 인과 효과 및 절대 metric 정확도는 아직 미판정이다.

## 다음 단일 결정

사용자가 확인한 **전체 표면의 KF/pixel mask와 독립적으로 확인 가능한 대응을 확보**하고, JPG의 distortion/카메라 모델 호환성을 검증한다. 그 후에만 같은 표면·공통 coverage에서 원본 및 검증된 보정 입력의 상대 pose와 backend 배치를 비교한다. 호환성을 확인할 수 없다면 조건부 민감도와 원인 미판정으로 남긴다.

## 재현 및 산출물

```bash
# 결과 디렉터리/run ID 중복 시 덮어쓰지 않음; GPU 필요
scripts/E7b_geometry_diagnostic/run_backend.sh
MPLCONFIGDIR=/tmp/mpl-e7b thirdparty/mast3r-env/bin/python scripts/E7b_geometry_diagnostic/calibration_qa.py
thirdparty/mast3r-env/bin/python scripts/E7b_geometry_diagnostic/calibration_grid_detail.py
MPLCONFIGDIR=/tmp/mpl-e7b thirdparty/mast3r-env/bin/python scripts/E7b_geometry_diagnostic/analyze.py
TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 thirdparty/mast3r-env/bin/python scripts/E7b_geometry_diagnostic/raw_calibration_sensitivity.py
MPLCONFIGDIR=/tmp/mpl-e7b thirdparty/mast3r-env/bin/python scripts/E7b_geometry_diagnostic/visualize_map.py
thirdparty/mast3r-env/bin/python scripts/E7b_geometry_diagnostic/validate.py
```

`results/E7b_geometry_diagnostic/2026-10-28/`에 `e7b_amtown_backend/`의 pose events·CSV·그래프·hash manifest, `calibration_qa/`의 remap QA, `conditional_raw/`의 공통 pixel과 분석 결과를 보존했다. 데이터·결과는 Git 제외이며 실행 코드·protocol은 저장소에 보존한다. 원래 E7/E7a 산출물을 변경하지 않았다.
