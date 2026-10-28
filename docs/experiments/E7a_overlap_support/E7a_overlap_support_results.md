# E7a — 공통 관측 support 보강 및 음성 대조

**실행일:** 2026-10-28  
**판정:** 도로·갓길 영상 대응 후보와 고정 support의 frozen replay를 확보했으나 **독립적으로 검증된 대응 및 유효한 seam-free 음성 대조는 INSUFFICIENT_SUPPORT**. E7의 KF 간 seam 재현성 판단은 여전히 보류한다.

## 질문과 가설

E7에서 다른 영상 위치를 가리킨 KF별 polygon 대신 영상 추적으로 같은 정적 도로의 관측 후보를 확보하고, E6과 같은 첫 fusion 입력 제외 replay의 KF 간 영향을 관찰할 수 있는가? 별도의 정적 평면 후보를 seam이 낮은 음성 대조로 검증할 수 있는가?

이는 **E7 결과와 해당 장면을 이미 본 후의 탐색 실험**이다. E7의 실패를 대체하지 않으며, 한 번도 조정하지 않은 새로운 독립 검증으로 보지 않는다. 사전 [protocol](../../../configs/E7a_overlap_support/protocol.json), RGB 기준 [영역과 수정 기록](../../../configs/E7a_overlap_support/regions.json)을 보존했다. 절대 성공 임계치를 결과에 맞춰 추가하지 않았다.

## 데이터, ROI 및 실행

E7 AMtown01 `[60s,120s)`의 240장, 동일 checkpoint·비보정 설정과 KF8–12를 사용했다. E7에 비해 KF-local의 계측 영역을 넓혀 KF마다 69,003픽셀을 저장했다. 원래 입력 및 저장 Sim(3), 나머지 관측을 고정하고 각 KF의 첫 tracking fusion 입력을 하나씩 제외한다. 후속 tracking이나 backend를 재실행한 개입이 아니다.

도로 source 영역은 E7의 RGB polygon, 음성 대조 후보는 별도의 밝은 지붕에서 RGB로 지정했다. 이후 **새 3D 결과를 보기 전** 후보 overlay를 검토하니 도로 polygon 위쪽이 나무를 포함했다. 도로 source의 이미지 y<165를 제외하는 탐색적 수정을 기록하고 최초 후보도 `preflight/initial_rgb_review/`에 보존했다. 남은 영역에도 도로 경계·갓길·그림자가 있어 동일 물리 평면이라는 보장은 없다. 지붕 후보는 여러 지붕 면과 능선을 가로질러 단일 평면 조건이 무너졌다. 따라서 정상 대조로 선언하지 않았다.

각 source grid에서 중간 RGB 프레임 전체를 사용한 forward/backward LK, 왕복 ≤1픽셀 및 9×9 NCC ≥0.8을 적용하고 중복 target 픽셀을 제거했다. E7의 좁은 도로 영역에 적용한 3픽셀 grid·2픽셀 침식을 유지하되, target은 사전 등록한 넓은 capture 영역에 있으면 된다. 별도 SIFT 양방향 ratio matching으로 영상 특징을 확인했고 후보 그림을 육안으로 살폈다. LK·SIFT가 자동 매칭을 공유하는 것과, 소수의 시각적 일치가 모든 픽셀의 독립 정답이나 가시성을 검증하는 것은 다르다. 특히 균일한 도로는 개별 픽셀의 오대응을 이미지로 구분하기 어렵다.

## 영상 후보와 지원

| 영역·KF 쌍 | source grid | LK 후보 | 독립 SIFT 후보 | 원본 및 양 개입 공통 export support |
|---|---:|---:|---:|---:|
| 도로·갓길 8–11 | 85 | 28 | 1 | 28 |
| 도로·갓길 9–12 | 87 | 35 | 0 | 35 |
| 도로·갓길 10–12 | 85 | 58 | 1 | 58 |
| 지붕 8–11 | 78 | 18 | 1 | 2 |
| 지붕 9–12 | 78 | 61 | 1 | 0 |
| 지붕 10–12 | 78 | 72 | 1 | 0 |

도로 후보의 왕복 오차 p90은 각각 0.348, 0.257, 0.142픽셀이다. 8–11의 SIFT 후보 1개는 가장 가까운 LK source가 5픽셀 이내이며 target 차이가 1.92픽셀이었다. 10–12의 대응하는 차이는 3.72픽셀이다. Source 자체가 다를 수 있어 이 차이는 SIFT 정답 오차가 아니다. 9–12에는 해당 영역 SIFT 후보가 없다. 도로의 **검증된 정확한 대응 수는 미확정**이며 LK 후보 수를 G2의 검증된 관측 수나 실제 관측 면적으로 환산하지 않는다.

도로 후보는 각 쌍의 모든 원본 export에서 존재했고, 각 KF의 첫 입력을 제외한 후 평균 confidence 기준 `>1.5`도 양쪽 모두 통과해 동일 support를 유지했다. 지붕 후보의 원본 양쪽 export support는 2·0·0개뿐이고 복수 지붕 면을 포함한다. 따라서 지붕의 기하 수치나 seam-free 판정을 하지 않았다. 음성 대조는 `INSUFFICIENT_SUPPORT`다. 빈 지원을 0 오차로 기입하지 않았다.

## 후보 기하의 탐색 결과

각 대응 후보에서 최종 E7a Sim(3) `s R X+t`로 world 좌표를 만들고, 원본 source 후보의 PCA 법선을 +world Z 방향으로 부호 고정했다. 법선은 해당 쌍의 원본·개입에 동일하게 사용한다. 원본 export 및 양쪽 개입에서 유효한 **동일 후보**만 비교했다. 단위는 임의의 world map 단위이며 물리적 높이나 미터가 아니다. 후보가 좁은 띠여서 source 점의 두 번째/첫 번째 특이값 비는 0.066–0.084이다. PCA 법선과 평면 가정이 민감하며 도로·갓길 경계도 포함할 수 있다.

아래 값은 `|normal|` 및 tangent 거리의 중앙값이다. `A 제외`는 쌍 A–B에서 A의 첫 fusion 입력만 제외하고 B는 원본으로 두며, `B 제외`는 그 반대다.

| KF 쌍 | 공통 후보 | 원본 normal / tangent | A 제외 normal / tangent | B 제외 normal / tangent |
|---|---:|---:|---:|---:|
| 8–11 | 28 | 0.02546 / 0.00890 | 0.02445 / 0.00975 | 0.02772 / 0.01202 |
| 9–12 | 35 | 0.01336 / 0.00574 | 0.01594 / 0.00728 | 0.01109 / 0.00568 |
| 10–12 | 58 | 0.00727 / 0.00970 | 0.00546 / 0.00773 | 0.01001 / 0.01205 |

8–11에서 `|normal|` p90은 원본 0.02753, A 제외 0.02969, B 제외 0.02950이다. 모든 쌍의 signed normal p10·median·p90, absolute normal, tangent, world Z 및 XY의 중앙값·p90과 support 좌표는 `candidate_geometry.csv`, `support.csv`, `*_common_support.npz`에 있다. 한쪽 관측 제외에 따라 normal과 tangent가 서로 다른 방향으로 변하지만 **후보 대응의 정확성·평면성·가시성이 미검증**이라 이 수치를 실제 seam이나 원인 기여도로 확정할 수 없다. 첫 입력 제외가 더 작은 값을 주는 경우도 정확도 개선의 증거가 아니다.

## 검증 및 음성 대조

- E7a 계측 실행은 240프레임, 239개 tracking 이벤트, 51개 KF로 정상 종료했다. 실행 시간은 2분 41.41초다. E7 baseline과 tracking/KF 이벤트 전체 및 PLY·trajectory·provenance SHA-256이 일치한다.
- 5개 KF의 24개 업데이트에서 전체 capture ROI의 원본 confidence-weighted replay가 전후 XYZ 및 누적 weight와 bitwise 일치했다. E7의 초기 5개 및 update 24개 파일에 대해 겹친 1,887픽셀의 저장 XYZ·weight·match가 모두 일치했다.
- 후보의 원본 world 배치를 E7a export의 같은 KF/pixel ID와 대조한 최대 거리는 2.18×10⁻⁷ map 단위 이하였다. 5개 저장 Sim(3)에서 round-trip 및 gauge 재표현도 수치 오차 내 확인했다. 이 검증들은 물리적 대응 정답이나 외부 정확도를 검증하지 않는다.
- 서로 다른 지붕 면을 하나의 평면으로 취급하지 않았다. 정상 seam이 낮은 실제 영역은 독립적으로 확인되지 않았으며 G4 음성 대조를 통과하지 못했다. 동일 물리 표면에 대한 독립 pixel 정확도 및 가시성 확인도 부족해 G2 통과를 주장할 수 없다.

## 해석과 다음 단일 결정

E7에서 없었던 **영상 기반 자동 후보**를 수치적으로 확보하고 같은 후보에서 replay와 export parity를 확인했다. 그러나 독립 대응의 수와 품질, 정적 표면 경계 및 정상 음성 대조가 부족하므로 E6의 seam 원인에 대한 독립 재현이나 원인 우세를 판정할 수 없다. 외부 reference도 없어 metric 깊이 정확도나 알고리즘 개선을 주장하지 않는다.

다음에는 **영상상 식별 가능한 정적 도로 마킹/이음매를 갖춘 별도 UAV 시퀀스 또는 구간을 RGB만으로 선정하고, 독립 수작업 대응 및 가시성 검증으로 G2 support와 동일 평면 음성 대조를 먼저 확보**한다. 실패 시 관측 제한으로 기록하고 원인분리 주장을 보류한다.

## 재현 및 산출물

```bash
MPLCONFIGDIR=/tmp/mpl-e7a thirdparty/mast3r-env/bin/python scripts/E7a_overlap_support/select_tracks.py
# GPU 접근 필요; 기존 run ID는 덮어쓰지 않음
scripts/E7a_overlap_support/run_probe.sh
MPLCONFIGDIR=/tmp/mpl-e7a thirdparty/mast3r-env/bin/python scripts/E7a_overlap_support/analyze.py
thirdparty/mast3r-env/bin/python scripts/E7a_overlap_support/validate.py
```

`results/E7a_overlap_support/2026-10-28/preflight/`에는 RGB QA, SIFT·LK 좌표와 초기/수정 후보 그림이 있다. `e7a_amtown_probe/`에는 24개 fusion event, 후보별 replay, 기하 CSV·그래프, provenance, 최종 pose, hash manifest 및 검증 결과가 있다. 모든 결과 파일은 Git 제외이며 재실행에는 고유 run ID·결과 경로가 필요하다. E7 원본 및 E7의 판정을 수정하지 않았다.
