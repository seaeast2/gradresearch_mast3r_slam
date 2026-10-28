# E7d — AMtown01 0001·0072 흰색 공원 인도 비교

**실행일:** 2026-10-28  
**상태:** 두 입력의 영상 대응 후보와 직접 이미지 쌍에서 생성한 MASt3R raw pointmap을 비교한 탐색 결과. 실제 물리 변형량·미터 오차·렌즈 왜곡 원인의 검증 결과는 아니다.

## 질문과 방법

사용자가 지목한 `data/AMtown01/mapping/0001.png`와 `0072.png`의 흰색 공원 인도는 같은 정적 구조물로 육안 확인된다. 영상 크기는 둘 다 2448×2048, 촬영 시각 간격은 약 17.7992초다. 0001에서 인도와 주변을 RGB만 보고 polygon으로 선택했으며 0072의 서로 겹치는 대응 후보를 SIFT 양방향 ratio 0.75로 추출했다. 이미지 pair와 ROI, 분석 계획은 [protocol](../../../configs/E7d_park_warp/protocol.json)에 기록했다. 선행 E7 계열에서 이 장면을 이미 관찰한 사후 탐색이다.

최초 이미지 비교 후, 식물·인도 경계를 포함할 수 있는 넓은 ROI에서 흰 표면을 더 가깝게 다루기 위해 두 이미지의 후보 중심 픽셀을 `HSV V≥185, S≤50`으로 제한했다. 이 [추가 규칙](../../../configs/E7d_park_warp/white_surface_analysis.json)은 이미지 및 최초 분석을 본 후의 탐색적 선택이다. 흰색 기준은 그림자나 일부 포장면을 제외할 수 있고 다른 밝은 객체·경계를 포함할 수 있으므로 정확한 표면 분할이 아니다.

두 영상에서 67개 흰색 SIFT 후보를 얻었다. 그중 5 native pixel homography RANSAC에 통과한 55개를 3D 후보로 사용했다. 유사 패턴이나 주변 물체와의 오대응이 남을 수 있으며 독립적인 pixel 정답은 없다. 색상 위치·대응 후보는 [그림](../../../results/E7d_park_warp/2026-10-28/white_surface/white_candidates.png)에 보존했다. 4개 holdout fold는 source 영상의 120×120 픽셀 타일로 정했지만, **55개 선택에 전체 영상 후보로 추정한 homography를 먼저 사용했으므로 3D holdout은 후보 선택에 대해 완전히 독립적이지 않다.**

## 원본 이미지의 이동과 형상

흰색 homography 후보 55개의 `0072−0001` image 이동 중앙값은 가로 **+773.38픽셀**, 세로 **−24.43픽셀**이다. 가로 양수는 오른쪽 이동이다. 이 값은 원본 2448×2048 이미지 기준이며 512 장변 모델 입력의 가로 축으로는 약 162픽셀이다.

67개 흰색 후보에서 전체 이동·회전·균일 scale을 허용한 2D similarity를 추정하면, scale은 약 **0.951**, 이미지 평면 회전은 약 **+0.76°**다. 따라서 인도는 영상에서 약 4.9% 작게 보이는 방향으로 이동했다. 이는 서로 다른 카메라 시점의 영상상 scale이며 실제 인도 크기가 변했다는 뜻이 아니다.

| 영상 정렬 모델 | RANSAC inlier / 전체 | inlier 잔차 중앙값 / p90 | 공간 holdout 잔차 중앙값 / p90 |
|---|---:|---:|---:|
| 2D similarity | 52 / 67 | 1.97 / 3.24 px | 3.04 / 6.73 px |
| 2D affine | 60 / 67 | 1.52 / 2.68 px | 1.88 / 6.04 px |
| 2D homography | 55 / 67 | 1.23 / 2.46 px | 1.72 / 7.14 px |

잔차는 **원본 이미지 픽셀**이며 정적 대응·투영 모델에 대한 2D 차이다. Holdout에는 모든 흰색 후보가 포함되어 잘못된 대응도 포함될 수 있다. 한 이미지에서 다른 시점으로의 원근, 가림·그림자, 반복 무늬, 매칭 오차가 함께 포함되므로 이 수치만으로 렌즈 왜곡이나 3D 변형의 양을 판정하지 않는다. RANSAC inlier 수는 모델별로 다르므로 그 중앙값을 공통 support의 정밀도처럼 직접 비교하지 않는다.

처음 영상만 보고 0072에서 인도가 일부 잘린 것으로 말씀드렸으나, 이번에 선택한 **넓은 source polygon**의 homography 추정 투영은 계산상 영상 경계 안에 들어온다. 55개 흰색 후보의 가장 오른쪽 점도 원본 영상 오른쪽 경계에서 약 39픽셀 안쪽이었다. 이는 해당 polygon에 대한 투영 기반 점검이며 인도 전체의 가림이나 진짜 가시성 검증은 아니다. 최초의 잘림 판단을 확정 관찰로 사용하지 않는다.

## MASt3R 직접 이미지 쌍의 3D 형상

동일 checkpoint로 0001과 0072를 **직접 한 이미지 쌍으로** 넣어 symmetric inference의 self pointmaps `X11`, `X22`를 구했다. 두 pointmap은 각각 자기 이미지 카메라 좌표계에 있으므로 앞선 55개 후보를 동일한 resize/crop 좌표로 옮겨 bilinear sampling하고 3D Sim(3)을 맞췄다. 이것은 이미지 쌍에 조건부인 raw model output이다. 두 입력은 E7의 저장된 keyframe 자체가 아니며, 이 직접 쌍 추론은 E7의 연속 tracking/fusion/backend에서 생성한 pointmap이나 pose가 아니다.

| 지표 | 값 |
|---|---:|
| 공통 후보 / homography inlier | 55 / 55 |
| 0001 local PCA 평면 잔차 p90 / 해당 patch 크기 | 0.560% |
| 0072 local PCA 평면 잔차 p90 / 해당 patch 크기 | 0.642% |
| 3D spatial holdout 거리 중앙값 / 0072 3D bbox 대각 | **0.482%** |
| 3D spatial holdout 거리 p90 / 0072 3D bbox 대각 | **0.924%** |
| holdout 차이의 기준 법선 절대값 중앙값 / p90 | 0.241% / 0.559% |
| holdout 차이의 접선 크기 중앙값 / p90 | 0.330% / 0.741% |

각 fold의 Sim(3)은 나머지 공간 타일에서만 맞췄다. 0072의 대상 bbox 대각과 PCA 기준 법선은 모든 후보를 사용했고, 앞서 영상 homography inlier를 전체 후보에서 고른 선택 편향이 남는다. 법선 성분은 0072 pointmap에서 맞춘 PCA 평면 기준이며 중력이나 실제 depth 오차가 아니다. 3D 이동·회전·균일 scale을 맞춘 뒤 남는 국소 형상 차이만 비교하므로, 두 map 사이의 전체 pose/scale 차이와 world 배치 오차를 해당 수치에 포함하지 않는다. 후보는 공간 상관이 강하고 55개가 독립 표본이 아니다. 결과는 [pointmap 비교 그림](../../../results/E7d_park_warp/2026-10-28/white_pointmaps/pointmap_comparison.png)과 각 좌표가 담긴 NPZ에 있다.

## 검증과 해석

- 두 source PNG SHA-256은 AMtown01 입력 CSV와 일치한다. native→512×416 resize/crop과 좌표계를 기록했고, 3D 후보 55개 모두 두 모델 이미지 범위 및 finite confidence 조건을 통과했다.
- 알려진 scale·rotation·translation을 적용한 합성 3D 점에서 Sim(3) 복원을 확인했다. 공간 fold 크기는 16·17·15·7개다. 저장된 holdout 거리와 정규화 결과를 독립적으로 재계산했다.
- 이 비교는 실제 인도가 변형됐다고 주장하는 것이 아니다. 후보 correspondence, 색상 proxy, 평면성, 3D 추정의 scale 및 두 카메라 관측에 따라 결과가 달라진다. 영상에서 scale과 원근 차이는 예상할 수 있으며, 잔차만으로 렌즈 왜곡을 식별할 수 없다.
- 가장 직접적인 결과는 해당 인도 **후보 patch의 두 직접-pair raw 예측이 Sim(3) 정렬 후 3D 크기 대비 중앙값 약 0.48%, p90 약 0.92% 차이를 보였다**는 것이다. 그 정렬이 전체 pose·균일 scale 차이를 흡수하므로, E7 지도에서 본 층 분리·U자형이 없거나 작다는 뜻은 아니다.

## 재현과 파일

```bash
MPLCONFIGDIR=/tmp/mpl-e7d thirdparty/mast3r-env/bin/python scripts/E7d_park_warp/compare_images.py
MPLCONFIGDIR=/tmp/mpl-e7d thirdparty/mast3r-env/bin/python scripts/E7d_park_warp/white_compare.py
TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 thirdparty/mast3r-env/bin/python scripts/E7d_park_warp/compare_pointmaps.py
MPLCONFIGDIR=/tmp/mpl-e7d thirdparty/mast3r-env/bin/python scripts/E7d_park_warp/visualize_pointmaps.py
thirdparty/mast3r-env/bin/python scripts/E7d_park_warp/pointmap_components.py
```

GPU가 pair inference에 필요하다. 기존 출력 경로는 덮어쓰지 않는다. `results/E7d_park_warp/2026-10-28/`의 `image_pair`, `white_surface`, `white_pointmaps`에 후보·시각화·summary·checkpoint 및 input 해시가 저장된다. 이전 산출물은 변경하지 않았다.
