# E2 — 원본 pair pointmap 국소 평면성 예비 결과

**실행일:** 2026-10-28  
**상태:** KF31–35 재추론 및 ROI 평면성 측정 완료. H-L 원인 판정과 E2 전체 검증은 보류.

## 질문과 범위

E1 최종 PLY에서 층이 보인 포장면의 원본 pair pointmap이 국소적으로 얼마나 평면에서 벗어나는가? 사용자는 CloudCompare에서 여러 층이 같은 실제 표면임을 확인했다. 그 관찰을 존중하되, E1에서 선택한 ROI 전체의 픽셀별 대응과 공통 support는 별도로 계측되지 않았다.

E1의 KF31–35와 사전 사용된 RGB polygon을 그대로 사용했다. 각각 두 실제 tracking 입력 쌍을 재추론했다. `birth_self`는 keyframe 생성 프레임을 첫 이미지로, 이전 keyframe을 두 번째로 넣은 self-branch다. `next_cross`는 다음 추적 프레임을 첫 이미지로, 해당 keyframe을 두 번째로 넣은 cross-branch다. 각각 KF 이미지에 해당하는 polygon을 적용했다. Cross-branch XYZ는 첫 번째인 다음 프레임 좌표계에 있다. 두 branch는 입력 쌍과 좌표계가 서로 다르며, 값은 원본 E1 실행 중 캡처한 것이 아니라 별도 replay다. 원본 중간 출력과의 parity는 확인하지 못했다.

E1과 같은 체크포인트, 입력 PNG, 512 장변 및 uncalibrated 설정으로 실행했다. 입력 PNG 해시와 E1 frame/KF timeline을 확인했다. RTX 5060 8 GB, PyTorch 2.7.1+cu128. 체크포인트·입력 목록·설정·스크립트 해시는 결과 폴더의 `manifest.json`에 있다. 재실행:

```bash
TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 thirdparty/mast3r-env/bin/python scripts/E2_raw_pointmap/replay_raw_pairs.py
MPLCONFIGDIR=/tmp/mpl-e2 thirdparty/mast3r-env/bin/python scripts/E2_raw_pointmap/analyze_saved_roi.py
```

## 측정과 결과

각 ROI에서 유한 XYZ와 tracking의 `C_conf > 0`을 통과한 점에 비가중 PCA 평면을 맞췄다. 아래는 평면까지의 절대 수직거리 90백분위수를 PCA 평면에 투영한 ROI bounding box의 대각 길이로 나눈 값이다. 하나의 평면이 타당한 영역이어야 평면 잔차를 왜곡으로 해석할 수 있지만, 이 ROI의 전체 평면성은 독립 검증되지 않았다. 점은 ROI별 7,466–10,309개이며 모두 해당 필터를 통과했다. 이 수치는 관측의 정확도나 대응의 정확도를 뜻하지 않는다.

| KF | 생성 시 self p90 / ROI 대각 | 다음 관측 cross p90 / ROI 대각 |
|---|---:|---:|
| 31 | 0.79% | 1.87% |
| 32 | 0.72% | 1.43% |
| 33 | 1.17% | 1.27% |
| 34 | 0.89% | 2.19% |
| 35 | 1.39% | 2.33% |

다섯 경우 모두 cross-branch의 정규화 잔차가 더 컸다. 각 ROI를 이미지상 4개로 나눈 부분의 PCA 법선과 전체 ROI 법선의 최대 각도는 self 2.34–5.95°, cross 5.75–10.53°였다. 부분 영역 경계와 전체 평면의 타당성에 민감하므로 탐색적 수치다. 원본 camera-Z 분포와 confidence p10/중앙값/p90, 평면 normal, RMSE 및 절대 잔차 중앙값은 CSV에 있다. `next_cross`의 Z는 첫 번째 프레임 기준이며 KF 카메라의 Z가 아니다. 원본 XYZ로 정규화 방향을 계산할 수 있지만, uncalibrated 입력에서 별도로 검증된 실제 카메라 ray는 확보하지 않았다.

원본 점 배열, 픽셀 ID, confidence, descriptor 및 descriptor confidence는 `kf*_*.npz`에 보존했다. signed residual 시각화의 법선 부호는 각 PCA가 임의로 정하므로 색의 부호를 서로 다른 패널 사이에서 비교하지 않는다. 각 패널의 색상 범위도 다르다. 10개 ROI에 대해 공분산 고유값으로 평면 RMSE를 독립 재계산하고, 픽셀 중복 및 XYZ 유한성을 확인했다.

## 해석과 한계

- 원본 pointmap 내부에서도 완전한 평면이 아닌 공간적 잔차가 존재한다. 그러나 실제 표면 기하, ROI의 단일 평면 타당성, 별도 기준 자료가 없으므로 이를 모델의 오류나 최종 층의 발생 원인으로 확정할 수 없다. 사전 판정 임계치도 없다. **H-L은 미결**이다.
- Self와 cross는 이미지 쌍, branch, 좌표계가 함께 바뀐다. 잔차 차이는 관찰이지 어느 하나의 인과 효과가 아니다. 절대 깊이 또는 평면 offset을 서로 직접 비교하지 않았다.
- E1의 fused pointmap, backend 전후 pose, 실제 pixel correspondence 및 replay와 원본 중간 출력 parity는 측정하지 않았다. 높은 confidence도 정답의 보증이 아니다. 정상 ROI 음성 대조와 합성 테스트는 수행하지 않았고, 비교를 위한 공통 물리 support도 계측하지 않았다. 따라서 E2 전체의 원인 판정 및 계획서 품질 gate의 통과를 주장하지 않는다.

## 산출물과 다음 결정

결과는 `results/E2_raw_pointmap/2026-10-28/raw_pairs/`에 있다. `R1_raw_plane.csv`, `R1_auxiliary.csv`, `R1_raw_plane.png`, `R1_signed_residual_maps.png`, raw ROI NPZ와 manifest를 포함한다. 초기 실행은 로그 JSON 직렬화 오류로 중단됐고 수정 후 `run_retry.log`에서 정상 종료했다.

다음에는 E4의 최소 subset에서 KF31–35의 동일 물리 support와 backend 전후 배치를 계측해 local 형상과 world placement의 기여를 분리한다. 이를 위해 실제 실행 중 중간 상태 계측과 parity 검증이 필요하다. E3에서 fusion 입력·전후를 추적하기 전까지 cross-branch 차이가 최종 층에 미친 영향도 미확정이다.
