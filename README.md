# MASt3R-SLAM 활주로 기하 진단 연구

단안 드론 영상에서 활주로 표면의 기하 불연속이 MASt3R-SLAM의 어느 단계에서 발생하는지 분석하는 연구 저장소다. 실험 계획과 실행 결과를 구분하며, 과거 `gradresearch` 저장소와 이 저장소의 E 코드는 서로 다른 실험이다.

- [원인분석 실험계획서](docs/mast3r_slam_runway_geometry_diagnostic_plan_v1.md)
- [E0 실험 환경 준비 계획서](docs/mast3r_slam_experiment_preparation_plan_v1.md)
- [E0 실행 결과와 미해결 사항](docs/experiments/E0_environment_preparation/E0_repo_audit.md)
- [E0 환경 manifest](configs/E0_environment_preparation/environment_manifest.json)

현재 E0의 224 입력 smoke test는 통과했다. 512 입력은 GPU 메모리 부족으로 실패했으며, E1 baseline 및 이후 실험은 아직 수행하지 않았다.

## 실험 코드와 폴더

| 코드 | 단계 | 결과 폴더명 |
|---|---|---|
| E0 | 실험 환경 준비 | `E0_environment_preparation` |
| E1 | R0 원본 재현 | `E1_baseline_reproduction` |
| E2 | R1 raw pointmap | `E2_raw_pointmap` |
| E3 | R2 tracking·fusion | `E3_tracking_fusion` |
| E4 | R3 world placement·backend | `E4_placement_backend` |
| E5 | R4 tracking gap 연계 | `E5_tracking_gap` |
| E6 | 선택한 최소 통제실험 | `E6_control_experiment` |
| E7 | 독립 검증 | `E7_independent_validation` |
| E8 | 연구 Go/No-Go | `E8_route_decision` |

각 단계명은 `docs/experiments/<단계명>/`, `configs/<단계명>/`, `results/<단계명>/` 및 필요할 때 `scripts/<단계명>/`에 동일하게 쓴다. 결과 보고서는 `E코드_*.md`, 실행 산출물은 `results/<단계명>/<날짜>/<run_id>/`에 둔다. E6의 후보별 결과는 `E6-T-CAL` 등 하위 코드와 별도 run ID로 구별한다. 아직 실행하지 않은 단계는 필요할 때 폴더를 생성한다.

```text
docs/experiments/  실험별 계획과 결과 보고서 (Git 추적)
configs/           실험별 설정·manifest·패치 (Git 추적)
results/           실험별 실행 로그와 산출물 (Git 제외)
scripts/           실험별 실행 스크립트
src/diagnostics/   여러 단계가 공유하는 검증된 분석 코드
data/              공통 입력 데이터 및 프레임 목록 (Git 제외)
thirdparty/        upstream 코드·실행 환경·체크포인트 (Git 제외)
```

실험마다 입력 hash, upstream commit, 설정, 명령, run ID, 결과와 실패를 기록한다. 공통 데이터와 환경은 공유하지만 실행 산출물은 각 실험 폴더에 두며, 이전 단계 출력을 입력으로 사용할 때 출처와 hash를 기록하고 원본을 보존한다. upstream이 자체 경로에 작성한 결과는 실행 완료 후 해당 실험 폴더로 정리한다. 대용량 데이터와 모델, 결과는 `.gitignore`에 따라 Git에 포함하지 않는다.
