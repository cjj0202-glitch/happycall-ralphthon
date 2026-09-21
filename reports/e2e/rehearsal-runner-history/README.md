# 실행기 관측 이력

2026-09-21 후속 보완. 과거 실행 결과를 수정하지 않고 실행기 변경 전후의 관측 byte 사본을 보존합니다.

| 사본 | 의미 | SHA-256 |
|---|---|---|
| pre-v2-observed.mjs | 이번 후속 보완 직전 디스크에서 읽은 실행기. 과거 19:03 실행 후 추가된 frontendSourceEnd 코드가 포함되므로 과거 실행 byte 사본이 아닙니다. | `0ab8bdfbfcdef1500bfd519df4803a3eb1c689fef280cf8ec28c6a2555cee8f9` |
| v2-aggregation-verified.mjs | six-flow-rehearsal-v2. 시작 버전/해시/소스 사본 보존과 offline safety 종료 게이트. 집계 자식 프로세스 8대조군만 검증한 사본입니다. | `e6785b8740c7f90646a8e699a0b1aff02ea6e548af9f161445cbef1c4b05c296` |

실제 실행 파일은 `tests/e2e/six-flow-rehearsal.mjs`입니다. 이 폴더 사본은 코드/경로 이력 확인용이며 이 위치에서 실행하지 않습니다. helper는 변경하지 않았으며 SHA-256은 `8715302c4649af946bf53c59368bb08664223bea884a6b837315ac44f7638def`입니다.

검증 입력은 과거 `rehearsal-2026-09-21T10-03-54-814Z/results.json`이며 SHA-256 `7f520e90a73dbab95c2749a05e6c1cc243ec1ce43e2e93982dffea1d15ca5da4`를 실행 전후 대조했습니다. 원자료는 변경하지 않았습니다. 이후 실제 리허설에서는 version/파일별 SHA/크기/Node version/관측시각과 소스 사본이 새 실행 디렉터리에 생성됩니다. v2로 전체 6회를 다시 실행한 기록은 아직 없습니다.
