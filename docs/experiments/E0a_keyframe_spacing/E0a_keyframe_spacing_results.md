# E0a_keyframe 간격 확대 테스트 결과

**실행일:** 2026-10-27  
**상태:** 실행 완료 / 탐색적 실행 가능성 테스트. E1 원인분석 및 E6-T-KF 통제실험이 아니다.

## 목적과 조건

HKairport01에서 keyframe이 짧은 간격으로 집중되는 구간을 완화할 수 있는지 확인한다. 추적 입력 240장은 바꾸지 않고 정상 tracking의 새 keyframe 후보를 마지막 keyframe의 실제 촬영 시각으로부터 2초가 지나기 전에는 보류한다. 2초는 사용자의 간격 확대 요청에 따른 첫 시험값이다. 최소 간격일 뿐 주기적으로 2초마다 keyframe을 생성하지는 않는다. 재위치 성공으로 생성되는 keyframe은 복구를 우선하므로 이 제한의 예외다.

대조군은 동일 코드·실제 timestamp 입력·모델·240 PNG·512 해상도·32 KF buffer·single-thread·low-vram 조건에서 최소 간격만 0으로 설정했다. 후보군은 2초로 설정했다. 입력 시각은 기존 30 fps 가상값이 아닌 `data/HKairport01/mapping_frames.csv`의 `rgb_timestamp`를 사용하며, 입력 순서·파일명을 검증했다. 모델 및 설정과 패치 hash는 [결과 manifest](../../../configs/E0a_keyframe_spacing/results_summary.json)에 기록했다.

실행은 `scripts/E0a_keyframe_spacing/run_comparison.sh`, 결과는 `results/E0a_keyframe_spacing/2026-10-27/{control,candidate_2s}/`에 보존했다. 해당 스크립트와 테스트는 E0의 PyTorch 호환 및 저메모리 패치 위에 [keyframe 간격 패치](../../../configs/E0a_keyframe_spacing/keyframe_spacing.patch)를 적용한 소스를 사용했다.

## 결과

| 항목 | 기존 정책 | 2초 최소 간격 |
|---|---:|---:|
| 정상 종료 | 예 | 예 |
| keyframe 수 | 19 | 6 |
| 연속 keyframe 간격 중앙값 | 0.200초 | 2.400초 |
| 연속 keyframe 최소 간격 | 0.200초 | 2.000초 |
| 2초 미만인 간격 수 | 15/18 | 0/5 |
| keyframe 후보 보류 로그 | 0 | 23 |
| 추적 skip / Cholesky 실패 로그 | 0 / 0 | 0 / 0 |
| 재위치 시도 로그 | 0 | 0 |
| 재방문 검색 로그 | 17 | 4 |
| PLY 유한 좌표 점 수 | 3,331,363 | 1,192,768 |
| GPU 전체 사용량 표본 최대 | 6,244 MiB | 5,678 MiB |
| 실행 시간 | 1분 47.59초 | 1분 36.64초 |

2초 정책의 실제 간격은 약 33.2, 2.4, 2.0, 2.4, 9.2초다. 앞의 33.2초는 기존 정책에서도 같았으며, 최소 간격 규칙은 최대 간격을 제한하지 않는다. GPU 값은 1초 간격 샘플의 시스템 전체 사용량이므로 순간 최대값을 놓칠 수 있다. 생성 점 수의 감소는 지도 저장량 차이이며 기하 정확도나 coverage 개선의 증거가 아니다. 로그상 실패가 없다는 사실도 pose 정확도 또는 모든 프레임의 기하 품질을 보증하지 않는다.

## 후속 적용과 제한

이후 HKairport01 탐색 실행의 기본은 `scripts/E0a_keyframe_spacing/run_2s.sh data/HKairport01/mapping data/HKairport01/mapping_frames.csv <고유-run-id>`다. 실행마다 매핑 CSV와 이미지 수·순서를 검사하며, 동일 run ID 덮어쓰기를 방지한다. 다른 영상도 실제 timestamp와 동일 형식의 CSV가 필요하다. 원래 E0 실행 스크립트와 원본 keyframe 정책은 대조군 재현용으로 남긴다.

- 재위치 성공은 2초 미만 keyframe을 만들 수 있으며, 이번 실행에는 재위치 시도가 없어 예외 경로를 검증하지 못했다.
- keyframe 감소로 coverage, 대응 support, backend 그래프 및 단차가 달라질 수 있다. 두 지도에서 동일 물리 표면을 확인하고 분석하기 전에는 개선이나 악화를 결론 내리지 않는다.
- 이 테스트는 원래 R0–R4 이후의 E6 인과 통제실험을 대체하지 않는다. E1에서 정책과 동일 표면 support를 명시하고, 기존 정책의 대조 결과를 보존한다.
