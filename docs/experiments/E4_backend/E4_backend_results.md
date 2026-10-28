# E4 — Keyframe 배치와 backend 최적화 예비 결과

**실행일:** 2026-10-28  
**상태:** E1 조건 재실행, KF31–35의 backend 전후 pose 및 pointmap 계측, 세 겹침 후보의 고정 map 배치 비교 완료. 절대 정확도와 단일 원인 판정은 미완료.

## 질문과 방법

E3에서 확인된 canonical pointmap을 고정했을 때 backend 최적화 전후 keyframe pose/scale 변경만으로 포장면 분리가 달라지는가? 사용자가 CloudCompare에서 같은 표면이라고 확인한 구역의 E2a optical-flow 대응 후보를 이용했다. 개별 후보는 독립적인 픽셀 정답으로 검증되지 않았다.

E1과 같은 240프레임, uncalibrated, 512 장변, 1초 강제 keyframe, 64 KF buffer, single-thread 및 low-VRAM 설정으로 재실행했다. 별도 backend 프로세스의 `solve_GN_rays` 호출 직전·직후 Sim(3), graph edge와 KF31–35의 ROI pointmap을 저장했다. KF30–52 최적화 23회를 기록했다. E3의 초기 raw 및 마지막 fused pointmap은 각각 E4 실행의 해당 초기·최종 ROI와 배열이 정확히 일치한다.

KF31–35의 fusion이 모두 완료된 **KF36 backend solve 직전**부터는 E3 마지막 fused map이 실제 E4 실행의 해당 시점 map과 동일하다. 각 backend solve의 pre/post pose를 동일한 고정 map에 적용하여 차이를 계산했다. KF가 더 생기기 전의 pose를 이용한 비교도 수행했지만, 그때는 나중에 완성된 fused map을 과거 pose에 대입한 **가상 재배치**이므로 당시 실제 지도의 상태가 아니다. 동일 절차를 초기 raw map에 대해서도 수행했다. Raw map에도 원래 fused map으로 최적화한 pose를 적용했기 때문에 raw-only SLAM을 재실행한 결과가 아니다.

측정값은 후보 대응점 `world_B − world_A`를 각 쌍의 **E1 최종 지도에서 얻은 KF A 기준 평면 법선**에 투영한 중앙값이다. 법선을 각 쌍에서 모든 시점과 raw/fused에 고정했고 부호는 임의로 정했다. 중력 정렬과 metric scale이 없어 수치는 지도 단위이며 실제 높이 오차가 아니다. 두 keyframe의 평면 법선 각도와 양방향 point-to-plane 거리의 중앙값도 CSV에 저장했다.

## 고정 fused pointmap의 실제 backend 전후 변화

아래 세 쌍은 모두 KF36 solve 직전부터 최종까지 **동일한 실제 frozen local geometry와 동일한 대응 후보**를 사용했다. 부호는 기준 법선의 임의 방향에 따르므로 쌍 간 상하 방향으로 비교하지 않는다.

| KF 쌍 | 대응 후보 | KF36 solve 전 | KF36 solve 후 | 최종 KF52 solve 후 |
|---|---:|---:|---:|---:|
| 32–35 | 123 | −0.05100 | −0.06789 | −0.06586 |
| 31–34 | 116 | −0.02378 | −0.02148 | −0.02162 |
| 33–35 | 119 | −0.02524 | −0.04144 | −0.03894 |

예를 들어 KF32–35는 KF36 solve 한 번으로 signed 분리 중앙값이 **−0.01689 지도 단위** 변했다. 그 뒤 최종값은 solve 직전보다 −0.01486만큼 달라졌다. KF33–35도 KF36 solve에서 −0.01620 변했으며, KF31–34는 +0.00231 변했다. 이 사례에서는 backend pose 갱신이 KF35를 포함한 두 쌍의 분리 크기를 늘렸지만, 모든 쌍에서 같은 방향으로 작용하지는 않았다.

KF32–35 최종 signed 차이의 p10–p90은 −0.09508~−0.04320 지도 단위, 두 plane normal 각도는 3.63°, 양방향 point-to-plane 중앙 거리 평균은 0.06744였다. 각각의 수치는 영상 대응 후보 및 부분 평면 가정에 의존한다.

## 이전 pose에 대한 고정 map 재배치

참고로 최종 fused map을 KF35 solve 직전 pose에 **가상으로** 배치하면 KF32–35 signed 중앙값은 −0.00530이고, 그 solve 직후 pose에서는 −0.05100이다. KF35가 생성된 시점의 실제 map은 아직 최종 fused map이 아니었으므로 이는 당시 실제 지도가 −0.00530이었다는 의미가 아니다. 같은 고정 map에 대한 pose 변화의 민감도를 보여준다. KF35 solve 시 graph에 새 edge 3개가 추가됐고 이 중 2개는 비연속 KF edge였다. Edge의 잔차나 특정 loop closure의 인과적 기여는 계측하지 않았다.

같은 최종 pose에 초기 raw map을 대입하면 KF32–35의 signed 중앙값은 −0.03813이었다. 이는 raw와 fused가 고정된 pose에서 다른 배치를 만든다는 기술적 비교이며, raw와 fusion의 독립적인 인과 기여량은 아니다. Pointmap·pose 간 상호작용과 pose가 fused geometry로 최적화됐다는 점 때문에 두 값의 차이만으로 원인을 분해할 수 없다.

## 검증

- E4 최종 PLY, keyframe 궤적, provenance SHA-256이 E1과 각각 동일했고, 239개 tracking 기록도 일치했다. 단일 실행 쌍의 최종 parity이며 모든 중간 값과 전체 결정론을 보장하지 않는다.
- KF31–35 초기 map과 E3 초기 ROI가 정확히 같고, KF36–52의 매 solve 전후 ROI가 E3 마지막 fused ROI와 정확히 같았다. 따라서 위 표에서 측정된 각 solve의 변화는 **동일 pointmap에 적용한 pose 변화에 따른 것**이다.
- 마지막 pose로 고정 fused 대응점을 변환한 좌표는 저장 PLY와 최대 1.95×10⁻⁷ 지도 단위 이내로 일치했다. Sim(3) round-trip, 임의 local scale 재표현의 world 좌표 불변성, synthetic 평면의 0 분리 및 알려진 법선 이동 검사를 통과했다.
- KF36 이후 pose는 KF31–35에 대해 backend solve별로 기록했고, graph 전체 edge 목록도 함께 보존했다. `backend_pose_revisions.csv`의 회전·이동·scale 로그는 gauge에 의존하는 진단값이며 scale 값의 변화만으로 물리적 오류를 주장하지 않는다.

## 해석, 한계와 다음 단계

**H-B 관련 증거:** 고정된 최종 pointmap과 같은 대응 후보에 대해 backend solve가 KF32–35 및 KF33–35의 분리 크기를 바꾼 것은 확인됐다. 이것은 계산상 해당 pose revision의 효과다. 다만 backend가 실제 표면으로부터 멀어졌는지, fusion/초기 placement 오류를 얼마나 교정하거나 악화했는지, 어떤 graph edge가 원인인지는 기준 자료와 통제실험이 없어 확정할 수 없다.

**H-P 관련 증거:** 최종 world 배치에서 대응 후보 간 분리가 존재하고, pose를 고정하면 초기 raw와 최종 fused map의 분리도 서로 다르다. 하지만 ROI의 실제 평면성, 개별 correspondence, pose의 외부 정확도는 검증되지 않았다. Raw/fused의 평탄성만으로 정확한 표면을 보장할 수 없으며 H-P를 단일 원인으로 확정하지 않는다. 양의 사례 3쌍은 같은 영상 구간에 속해 독립 장면이 아니고, 별도 정상 ROI 음성 대조 및 backend edge별 최적화 잔차 분석은 남아 있다.

E3의 ROI tracking 지원 부족과 E4의 pose revision이 함께 관찰되므로, 계획서의 다음 통제실험은 **E6-T-POSE**가 적절하다. 동일한 fused map과 동일 gauge에서 pre/post pose replay를 기준으로 특정 pose revision을 제한적으로 바꾸고, 정상 ROI와 coverage를 함께 보는 실험을 별도 설계한다. 실제 카메라 pose 기준 없이 해당 변경을 GT 교정으로 해석하지 않는다. Fusion의 기여에 대한 독립적 결론은 E6-T-FUS 별도 대조가 필요하다.

## 산출물 및 재현

- `results/E4_backend/2026-10-28/instrumented/`: `pair_seams.csv`, `backend_pose_revisions.csv`, `backend_frozen_overlap.png`, backend event NPZ, `manifest.json`, `validation.json`, 실행 로그와 출력 PLY.
- 계측 실행: `bash scripts/E4_backend/run_e4.sh` (기존 결과와 run ID 덮어쓰기 방지).
- 분석: `MPLCONFIGDIR=/tmp/mpl-e4 thirdparty/mast3r-env/bin/python scripts/E4_backend/analyze_backend.py`
- 검증: `MPLCONFIGDIR=/tmp/mpl-e4 thirdparty/mast3r-env/bin/python scripts/E4_backend/validate_backend.py`
- RTX 5060 8 GB, 정상 종료, 벽시계 162.30초. 결과 파일은 Git 제외 경로이며 protocol·계측 코드·보고서는 저장소에 보존한다.
