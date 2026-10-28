# E7c — 표면 provenance, 영상 대응 및 카메라 보정 QA

**실행일:** 2026-10-28  
**상태:** 51개 KF 및 전체 export 점의 이미지 provenance 연결, 영상 대응 후보 감사, 카메라 자료와 수치 QA 완료. 사용자가 확인한 U자형 표면의 point-level mask, 독립 pixel 대응 및 JPG 보정 상태는 미확정이다. 검증된 원본·보정 pose 비교의 선행 조건이 충족되지 않아 해당 비교는 **NOT_PERFORMED**다.

## 질문과 사전 조건

사용자는 동일 평면의 U자형과 Z 방향 층을 육안으로 확인했으며, 실험에서는 그 관찰을 받아들인다. 이 표면을 이루는 개별 점은 지정하기 어렵다는 사용자 응답에 따라 기존 영상 후보와 source provenance를 사용해 탐색한다. Export된 전체 점을 자동으로 사용자가 확인한 표면의 mask라고 간주하지 않는다. 동일 장면과 E7b 결과를 이미 본 뒤의 E7c는 독립 확증 실험이 아니다. 실행 전 [protocol](../../../configs/E7c_surface_calibration_qa/protocol.json)에 후보 및 calibration QA의 해석 범위를 기록했다.

질문은 세 가지다. (1) 최종 점이 어떤 KF/입력 픽셀에서 왔는가? (2) 서로 다른 KF의 같은 물리적 위치를 충분히 독립 검증할 수 있는가? (3) 현재 JPG에 적용해야 할 camera model과 왜곡 보정이 확인되는가? 이 중 point-level provenance와 수치적 QA를 수행했고, (2)·(3)은 충분한 근거가 없어 미판정으로 남는다.

## KF·픽셀 연결

E7 AMtown01 최종 지도에 사용된 **10,663,929개 점과 51개 KF**를 확인했다. 모든 점에 대해 `kf_id`, input `frame_id`, 해당 KF 512×416 영상의 `pixel_index = y × 512 + x`를 확인하고, 원본 색이 아닌 KF별 색의 [검토용 PLY](../../../results/E7c_surface_calibration_qa/2026-10-28/provenance_review/mapping_kf_frame_pixel.ply)에 세 ID를 저장했다. 이는 PLY의 source provenance이지 물리 표면 분류나 정답 대응 라벨이 아니다.

각 KF 안에서 pixel ID가 중복되지 않고 범위 안에 있으며, point 수 합이 PLY 전체와 같다. 51개 source PNG hash는 입력 CSV와 일치하고 resize/crop 후 영상은 저장된 KF 이미지와 정확히 일치했다. 각 KF의 RGB 영상 [검토 자료](../../../results/E7c_surface_calibration_qa/2026-10-28/provenance_review/keyframes_page_1.jpg), `kf_provenance.csv`, KF별 `masks/kfNN_export_support.png`를 보존했다. PNG mask에서 255는 해당 픽셀이 export되었다는 뜻이며 U자형 표면의 지정이 아니다.

E7a에서 실제 local pointmap과 최종 Sim(3)이 저장된 KF8–12는 독립적으로 좌표 계산을 대조했다. 해당 capture와 export가 겹치는 **321,871점**에서 `s R X+t`와 PLY XYZ의 최대 거리는 3.71×10⁻⁷ map 단위였다. 나머지 46 KF의 local pointmap에 대한 별도 좌표 parity는 이번에 하지 않았다. 검토용 PLY의 XYZ bit, 색, 점 순서, KF ID, frame ID 및 pixel ID는 기존 PLY/provenance와 일치했다.

## 독립 영상 대응과 가시성

E7a의 도로·갓길 후보를 RGB상 다시 살피고, 두 영상에서 생성한 SIFT match의 **동일 source 좌표**를 중간 영상 전체에 LK로 추적해 SIFT target과 직접 비교했다. E7a에서 사용한 가까운 grid점과의 차이와는 분모·source가 다르므로 숫자를 직접 비교하지 않는다.

| KF 쌍 | E7a LK 후보 | 해당 ROI SIFT 후보 | 같은 source의 SIFT–LK target 거리 | LK 왕복 |
|---|---:|---:|---:|---:|
| 8–11 | 28 | 1 | 0.729 px | 0.391 px |
| 9–12 | 35 | 0 | 측정 불가 | 측정 불가 |
| 10–12 | 58 | 1 | 0.389 px | 0.013 px |

이 두 위치에서 서로 다른 방식의 영상 매칭이 유사한 점을 반환했지만, 각각 1점이고 같은 영상에 의존한다. 육안 검토한 영상에서 도로에는 식별 가능한 세부 특징이 적어 해당 점의 물리적 위치·가시성과 나머지 LK 후보 전체의 정확성을 독립적으로 판정할 수 없었다. SIFT와 LK의 일치를 점별 GT로 간주하지 않는다. 후보 좌표, 왕복 수치 및 [KF8–11 비교 이미지](../../../results/E7c_surface_calibration_qa/2026-10-28/match_audit/road_8_11_sift_lk.png), [KF10–12 비교 이미지](../../../results/E7c_surface_calibration_qa/2026-10-28/match_audit/road_10_12_sift_lk.png)를 보존했다.

별도 지붕 대조 후보는 E7a에서 여러 면을 가로질렀고 양쪽 export support가 2·0·0점이었다. 정상 seam-free 평면으로 검증되지 않았으므로 음성 대조로 사용하지 않는다. G2의 **독립 검증된 공통 관측**과 G4의 **정상 영역 음성 대조**는 `INSUFFICIENT_SUPPORT`다. 이미지 후보 수를 독립 정답 수나 실제 overlap 면적으로 환산하지 않는다.

## 카메라 모델·JPG 전처리 QA

원본 AMtown01 archive의 `sampleinfos_interpolated.json`에서 240개 입력의 실제 원본 파일명과 메타데이터가 모두 대응하고 해상도가 2448×2048임을 확인했다. 모든 입력은 image-to-map metadata에서 같은 `P3x3` (`fx=fy=1469.4899`, `cx=1174.0027`, `cy=1049.9120`) 및 0인 5개 왜곡 계수를 담는다. 저장된 240개 회전 행렬은 수치적으로 직교한다. 이 정보는 3D map과 이미지의 calibration 맥락이다.

별도의 [공식 camera–LiDAR calibration](https://github.com/sijieaaa/UAVScenes/blob/main/calibration_results.py)은 AMtown에 `fx=1453.72`, `fy=1453.28`, `cx=1172.18`, `cy=1041.78`, distortion `[-0.121, 0.1113, 0.0016, 0.00013, -0.062353]`을 제공한다. 즉 두 행렬은 같지 않고 calibration 대상도 다르다. 선택된 JPG 240개에서 EXIF 정보는 없었다. 어느 행렬·왜곡 모델이 현재 JPG의 물리적 픽셀에 맞는지 또는 JPG가 이미 rectified되었는지는 이 정보만으로 확정하지 못한다.

[UAVScenes 공개 이슈 #6](https://github.com/sijieaaa/UAVScenes/issues/6)은 두 calibration 표기와 이미지 distortion 처리에 대한 질문을 담고 있으며, 확인 시 답변 없이 열려 있다. 이 질문은 **interval5 이미지**를 지칭하므로 E7c의 interval1 JPG에 대한 직접적인 답변은 아니다. 실제 입력의 전처리 이력을 검증할 근거도 아니다.

### 왜곡 모델 역변환의 수치 민감도

E7b의 카메라–LiDAR 모델 가정으로 2448×2048 grid 8,585점을 역변환하고 같은 모델로 다시 투영했다. 기준 0.1픽셀은 E7b에서 사용한 수치 검사 기준이다.

| OpenCV inverse 반복 수 | 왕복 오차 ≥0.1 px | 그중 ≥1 px | 왕복 p99 |
|---|---:|---:|---:|
| 5 | 292 | 127 | 2.420 px |
| 100 | 54 | 54 | 약 1.0×10⁻¹² px |

반복 횟수를 늘리면 대부분의 수치 오차가 줄지만 54개 grid점은 1픽셀 이상 남았다. 두 역변환이 동일한 분기를 얻는다는 보장은 없으며, 전체 input grid에서 일부 역변환 결과가 출력 영상 밖에 있다. 별도로 이상적인 native 영상 grid의 forward model Jacobian을 수치로 평가했을 때 8,585개 모두 양수이고 최솟값은 약 0.467이었다. 이것은 해당 **표본과 수치 모델의 국소 검사**이며 실제 카메라의 유효 시야 전체, 전역 일대일성 또는 물리 보정의 정확성을 보증하지 않는다. 위치별 round-trip 결과는 [그림](../../../results/E7c_surface_calibration_qa/2026-10-28/calibration_qa/inverse_roundtrip.png)과 `numeric_grid.npz`에 있다.

E7b의 조건부 보정 비교에서 사용한 후보에 대한 역변환과 원본 raw parity는 E7b에 기록되어 있다. E7c의 수치 실험은 전체 영상의 검증된 calibration QA 통과를 뜻하지 않으며, 원본 JPG에 E7b처럼 보정을 적용하는 것이 맞는지도 확정하지 못했다.

## 판정, 검증 및 다음 결정

- **Provenance:** 51 KF와 전체 export 점의 입력 frame/pixel 연결을 생성·검사했으며, 실제 저장된 E7a local 점에 대한 world coordinate parity는 KF8–12의 321,871점에서 확인했다. Surface membership와 physical correspondence를 별도로 입증한 것은 아니다.
- **공통 관측·음성 대조:** 독립 검증된 표면 대응과 정상 영역이 충분하지 않아 G2/G4 `INSUFFICIENT_SUPPORT`다. 사용자께 추가 점 선택을 요구하지 않고 확인 가능한 기존 후보를 분석했다.
- **Calibration:** 제공 metadata 간 카메라 모델 맥락이 다르고 JPG preprocessing 확인이 없어 `NOT_VERIFIED`다. 100회 반복의 수치 결과를 사후적으로 채택해 보정 검증 통과라고 부르지 않는다.
- **원본·보정 pose 대조:** 앞서 정한 표면·calibration 선행 조건을 충족하지 않아 `NOT_PERFORMED`. E7b의 고정 map pose 영향과 조건부 raw 비교를 넘는 렌즈 왜곡의 인과 결론을 낼 수 없다.

다음 결정은 **데이터 제공자의 JPG distortion 처리와 카메라–LiDAR / 카메라–map 좌표 계약을 확인할 수 있는 독립 자료를 확보하는 것**이다. 동시에 자동 영상 추적만으로 점별 동일성이 구분되지 않는 영역은 support 제한으로 유지한다. 그전의 보정 pose 실행을 검증된 calibration 대조라고 부르지 않는다.

## 실행 및 산출물

```bash
MPLCONFIGDIR=/tmp/mpl-e7c thirdparty/mast3r-env/bin/python scripts/E7c_surface_calibration_qa/provenance_review.py
thirdparty/mast3r-env/bin/python scripts/E7c_surface_calibration_qa/export_traceable_ply.py
thirdparty/mast3r-env/bin/python scripts/E7c_surface_calibration_qa/verify_world_provenance.py
thirdparty/mast3r-env/bin/python scripts/E7c_surface_calibration_qa/calibration_metadata.py
thirdparty/mast3r-env/bin/python scripts/E7c_surface_calibration_qa/calibration_numerics.py
MPLCONFIGDIR=/tmp/mpl-e7c thirdparty/mast3r-env/bin/python scripts/E7c_surface_calibration_qa/plot_calibration_numerics.py
MPLCONFIGDIR=/tmp/mpl-e7c thirdparty/mast3r-env/bin/python scripts/E7c_surface_calibration_qa/independent_match_audit.py
thirdparty/mast3r-env/bin/python scripts/E7c_surface_calibration_qa/validate.py
```

결과는 `results/E7c_surface_calibration_qa/2026-10-28/`에 저장한다. `provenance_review/`의 PLY·KF RGB·export mask·CSV, `match_audit/`의 SIFT/LK 좌표와 시각화, `calibration_qa/`의 metadata·수치 grid·그림, `validation.json`의 검증과 SHA-256을 포함한다. 스크립트는 기존 결과 디렉터리를 덮어쓰지 않으므로 반복에는 별도 경로가 필요하다. 원본 E7/E7a/E7b는 수정하지 않았다.
