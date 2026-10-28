# E3 — Tracking 및 canonical pointmap fusion 계측 결과

**실행일:** 2026-10-28  
**상태:** E1 동일 조건 재실행 및 KF31–35의 실제 fusion 업데이트 계측 완료. Fusion이 최종 층 분리의 주원인인지에 대한 인과 판정은 미완료.

## 질문과 방법

E2a에서 같은 포장 구역으로 확인된 영역이 실제 실행의 tracking과 canonical fusion 중 어떻게 달라지는가? E1에서 사용한 ROI와 KF31–35를 대상으로, 각 KF의 생성 직후 초기 pointmap과 마지막 tracking 업데이트까지의 **23개 실제 업데이트**를 기록했다. 기록은 기존 실행 함수를 감싸 ROI 배열을 복사하는 방식으로 수행했고 연산의 입력이나 반환값을 수정하지 않았다. 업데이트별 파일은 keyframe-local 좌표의 기존 XYZ/가중치, pose로 변환된 새 입력 XYZ/가중치, 업데이트 후 XYZ/가중치, 상대 Sim(3), 대응 인덱스와 유효성·confidence를 담는다. 실행 조건은 [protocol](../../../configs/E3_fusion/protocol.json)과 같다.

기존 ROI의 같은 canonical 픽셀을 전 단계에서 유지했다. 각 단계에서 PCA 평면을 맞추고 절대 수직 잔차 p90을 **초기 ROI의 평면 투영 bounding-box 대각**으로 정규화했다. 법선 변화량은 ± 부호를 일치시킨 초기·최종 법선의 각도다. 이것은 포장면의 완벽한 평면성이나 실제 오차를 보장하지 않는 탐색 지표다.

추적용 유효 대응은 해당 ROI에서 코드의 `valid_match`, 매칭 신뢰도 `Q > 1.5`, 기존·현재의 `C > 0` 조건을 동시에 만족하는 픽셀 수다. **Tracking 성공 여부는 전체 이미지 기준**이므로 ROI 내부 대응이 적어도 전체 tracking은 성공할 수 있다. Fusion 입력 비중은 픽셀별 `C_input / (C_before + C_input)`의 중앙값이다. Normal 이동은 업데이트 전후 해당 픽셀의 3D 차이를 로컬 평면 법선에 투영한 값이다. 초기 ROI 크기로 정규화하며 중력 방향 높이나 미터가 아니다.

## 결과

| KF | 업데이트 수 | 초기 평면 잔차 p90 / 초기 크기 | 마지막 업데이트 후 | 초기–최종 법선 각도 | 초기–최종 점 이동의 법선 성분 절대값 p90 / 초기 크기 |
|---|---:|---:|---:|---:|---:|
| 31 | 4 | 0.79% | 0.90% | 4.44° | 3.48% |
| 32 | 4 | 0.72% | 1.00% | 3.80° | 5.00% |
| 33 | 5 | 1.17% | 0.84% | 4.27° | 2.04% |
| 34 | 5 | 0.89% | 1.62% | 1.79° | 4.04% |
| 35 | 5 | 1.39% | 1.84% | 5.57° | 3.04% |

KF31·32·34·35는 선택된 평면성 지표가 최종적으로 증가했고 KF33은 감소했다. 이 수치는 raw 입력이 실제보다 부정확해졌다는 뜻이 아니다. ROI의 진짜 형상이 검증되지 않았고, local pointmap의 평탄도만으로 최종 KF 간 층 차이를 판단할 수도 없다.

특히 KF32의 첫 세 업데이트(입력 프레임 149–151)에서 ROI 내 tracking 유효 대응은 각각 **0 / 9,545**였다. 네 번째 업데이트는 38개였다. 첫 업데이트에서 입력 가중치 비중의 ROI 중앙값은 47.5%였고, 갱신 전후의 픽셀별 법선 이동 중앙값의 크기는 초기 ROI 크기의 10.17%였다. 후속 업데이트가 다시 형상을 이동시켜 초기–최종 법선 이동 중앙값의 크기는 2.92%였다. 따라서 첫 업데이트의 이동을 최종 변화량으로 해석하면 안 된다.

KF33·34의 첫 업데이트도 ROI 내 유효 대응이 각각 0개, 1개였고, 첫 업데이트의 법선 이동 중앙값 크기는 각각 초기 ROI 크기의 10.22%, 10.26%였다. 각 KF의 법선 방향은 임의이므로 이동 부호를 KF 간 위·아래 방향으로 비교하지 않는다. 이미지 대응 후보와 이 tracking mask는 서로 다른 기준이다. KF32의 유효 대응이 0이라는 사실은 사용자가 확인한 표면 중복이나 E2a optical-flow 후보의 부재를 의미하지 않는다.

구현상 tracking pose 산출에 쓰는 `valid_match` / `Q` mask와 별도로 `keyframe.update_pointmap(Xkk, Ckf)`는 전체 canonical 픽셀에 대해 `C` 가중 평균을 수행한다. 즉, **해당 ROI에 tracking 유효 대응이 적어도 tracking이 전체 이미지에서 성공하면 그 ROI의 새 pointmap 관측이 fusion에 반영될 수 있다.** 이는 현재 구현의 실제 동작이며, 그 자체로 오류나 원인 확정은 아니다. 상세 유효 비율 및 각 업데이트 수치는 `fusion_events.csv`에 있다.

## 검증

- 240개 입력 PNG 해시를 확인했고 239개 tracking 호출의 성공·KF 생성·참조 KF·timestamp가 E1 기록과 일치했다. E3의 최종 PLY, 궤적, provenance 파일 SHA-256이 각각 E1과 완전히 일치했다. 단일 실행 쌍의 최종 parity이며 실행 전체의 bitwise 결정론을 보증하지 않는다.
- KF31–35의 E3 초기 ROI XYZ와 confidence는 E2 replay의 `birth_self`와 정확히 일치했다. 이는 해당 ROI·해당 branch에 한정된 중간 parity다.
- 23개 업데이트에서 직전 출력과 다음 입력의 ROI XYZ가 일치했고, 저장된 전후 가중치와 pointmap이 `weighted_pointmap` 식 및 업데이트 카운터를 만족했다. 재계산 최대 절대차는 6.0×10⁻⁷ 로컬 단위 이하이며 부동소수점 반올림 범위다.
- 마지막 ROI를 별도 Sim(3)으로 최종 PLY의 같은 KF/pixel에 맞췄을 때 5개 KF 모두 최대 거리 2.4×10⁻⁷ 지도 단위 미만이었다. 이는 최종 export가 마지막 ROI와 같은 형상을 보존함을 뒷받침한다. **변환을 새로 맞춘 검사이므로 실제 backend pose의 정확성이나 world placement parity 검증은 아니다.**

## 해석과 한계

Fusion 업데이트 동안 해당 ROI의 pointmap 위치와 형상이 실질적으로 달라졌고, 일부 ROI에는 tracking에 사용되는 유효 대응이 매우 적었다. 이는 **tracking/fusion 단계가 검사할 만한 원인 후보**라는 직접적인 근거다. 그러나 같은 관측의 pose 추정, 원본 pointmap 자체의 변화, 실제 경사·곡률과 fusion 가중치 효과가 얽혀 있다. 평면 잔차 증가나 첫 업데이트 이동만으로 잘못된 대응이 층을 만들었다거나 fusion이 최종 층 분리의 주원인이라고 확정할 수 없다. 정상 영역 대조, 독립 correspondence 검증, frozen-pose/frozen-map counterfactual은 수행하지 않았다.

다음에는 E4에서 keyframe-local pointmap과 backend 전후 Sim(3)을 같은 공통 표면에 배치하여 최종 KF 간 분리의 배치 영향을 확인한다. 이어 가설에 따라 pose를 고정한 fusion replay 또는 pointmap을 고정한 pose replay로 기여도를 통제한다.

## 산출물 및 재현

- `results/E3_fusion/2026-10-28/instrumented/`: `fusion_summary.csv`, `fusion_events.csv`, `fusion_summary.png`, `fusion_support_shift.png`, `events/*.npz`, `manifest.json`, `validation.json`, 실행 로그와 최종 PLY.
- 실행: `bash scripts/E3_fusion/run_e3.sh` (고유 run ID 필요; 기존 결과 덮어쓰기 방지).
- 분석: `MPLCONFIGDIR=/tmp/mpl-e3 thirdparty/mast3r-env/bin/python scripts/E3_fusion/analyze_fusion.py`
- 독립 점검: `MPLCONFIGDIR=/tmp/mpl-e3 thirdparty/mast3r-env/bin/python scripts/E3_fusion/validate_e3.py`
- GPU RTX 5060, 8 GB, 단일 thread 설정. 실행 종료 코드 0, 벽시계 164.63초. 실험 산출물은 Git 제외 경로이며 코드·protocol은 저장소에 보존한다.
