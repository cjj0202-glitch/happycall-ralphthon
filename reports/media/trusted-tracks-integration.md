# 등록된 CCTV 좌표의 제품 화면 연결

2026-09-21 22:39 KST · pc1/CJJ의 로컬 보조 작업 · 기준 main `663bbe5` · 메인 인수 전

**WmsScene의 영상 열기에서 manifest 좌표 등록을 Inspector까지 전달하도록 수정했습니다.** 현재 manifest에는 좌표가 없으므로 기존 영상 재생만 유지됩니다. 새 1080p 영상·좌표를 등록하거나 실제 브라우저에서 재생한 결과는 아닙니다.

## 설계와 범위

- 사용자 결과: 등록된 공정 영상을 열 때 검증된 좌표가 함께 전달되고, 좌표 등록에 문제가 있으면 영상은 유지하면서 좌표 표시만 중지합니다.
- 신뢰 경계: 빌드 입력 `data/demo-media-manifest.json`의 `sorter-demo.mp4.tracks`만 좌표 등록원입니다. 접수의 `caseData.media[].tracks`는 채택하지 않으며 Inspector에 전달하는 영상 등록 객체에도 복사하지 않습니다.
- 등록 계약: `schemaVersion=oneflow-cctv-tracks-v1`, 경로는 정확히 `/demo/sorter-demo.tracks.json`, 정수 바이트 1~10,000,000, 소문자 SHA256 64자리, `videoSha256`은 부모 영상 SHA와 일치해야 합니다. 등록 속성이 없으면 기존 영상 전용 동작, 속성은 있으나 null/형식 불량이면 명시적인 좌표 등록 오류입니다.
- 사건 관계: 기존 사건·공정·시각·카메라·등록 구간 검증 후 canonical fixture의 분류 실적 슈트와 출고 도크를 별도 `processAnchor`로 전달합니다. 실제 값은 CASE-0002의 `wms.sorting.rsltChuteNo=CH-02`, `wms.shipping.dock=D-02`입니다. 원본 이벤트에 값을 덧붙여 원문인 것처럼 표시하지 않습니다.
- 좌표 검증: 기대 슈트·도크가 없으면 검증을 생략하지 않고 차단합니다. 기존 standalone Inspector의 명시적인 이벤트 chuteId/dockId 입력은 유지합니다. 시각 객체의 `businessToteId:null` 경계, 시간·해상도·길이·프레임 수 검사는 그대로 유지합니다.
- UX: 등록 오류는 WMS 영상 카드와 Inspector에 표시합니다. 영상 재시도와 좌표 네트워크 재시도는 유지하되, 잘못된 빌드 등록에는 불필요한 재다운로드 버튼 대신 자산 등록 확인 안내를 표시합니다.

작은 Bolt의 병목은 좌표 props가 부모 화면에서 끊기는 한 지점이었습니다. 실제 TS 모듈과 클릭 핸들러를 순수 실행해 전달을 확인했으며, 사람 사용성 관찰이나 브라우저 검증으로 세지 않습니다.

## 실행과 실패 보존

Node 실행 파일: `C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe` (v24.19.0). 아래 첫 두 명령은 저장소 루트, 마지막은 `apps/web`에서 실행했습니다.

```powershell
& 'C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' tests/e2e/cctv-trusted-tracks-unit.mjs
& 'C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' tests/e2e/cctv-inspector-step-unit.mjs
& 'C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' node_modules/typescript/bin/tsc --noEmit --incremental false
```

| 검사 | 기대 | 최종 실측 |
|---|---|---|
| 좌표 등록·관계·실제 JSX 클릭/props 순수 실행 | 유효 등록 연결, 잘못된 등록 차단, 미등록 재생 경로 유지 | **49/49** (변이 4개 포함) |
| 이전/다음 프레임 순수 함수 회귀 | 시작·중간·끝·부분 구간·좌표 없는 경우 경계 유지 | **14/14**, 이전 clamp 제거 변이 검출 1/1 |
| TypeScript | 컴파일 오류 0 | exit 0, 진단 0 |
| 소유 코드 diff 공백 검사 | 오류 0 | exit 0, 공백 오류 0; Git의 LF→CRLF 안내는 존재 |

최초 좌표 검사에서는 앞의 미등록/미신뢰 메타데이터 검사 2개 통과 후 정상 등록 대조군이 실패했습니다. 기존 범용 JSON 경로 정규식이 `sorter-demo.tracks.json`의 중간 점을 거부했습니다. 승인한 정확한 파일명 예외를 명시하되 범용 경로 허용 범위를 넓히지 않아 수정했습니다. 최초 타입 검사에는 검증 후 `unknown` 값을 `ProcessAnchor`로 전달할 때 진단 1개가 있었으며 검증된 문자열 타입을 명시한 뒤 동일 명령이 통과했습니다. 처음 두 테스트를 연속 호출한 셸의 마지막 종료코드는 0이었지만 앞 검사의 실패 출력을 확인했고 이를 통과로 집계하지 않았습니다.

네 변이는 ① 슈트 일치 검사 제거 ② 도크 일치 검사 제거 ③ 정확한 파일명 검사 제거 ④ 실제 클릭 핸들러의 좌표 props 전달 제거입니다. 각 변이에서 같은 반례가 허용되거나 연결이 끊기는 결과를 관측하여 검사기의 판별력을 확인했습니다.

순수 실행 결과는 `.local/cctv-trusted-tracks-1789997962973/results.json`, 프레임 회귀 결과는 `.local/cctv-step-unit-1789997931681/results.json`에 있습니다. 테스트 좌표 288개는 검사기에서 만든 인공 좌표이며 렌더 장면 정합 증거가 아닙니다. 3초 영상에 288프레임/12초 좌표를 붙이는 경우와 다른 해상도는 모두 거부했습니다.

## 수정 파일과 고정 해시

| 파일 | SHA256 |
|---|---|
| `apps/web/lib/cctv-tracks.ts` | `db2d6bac5b8d353b9fb85741879cdd72442df920b3c60bb619995f7ca9ffdfd4` |
| `apps/web/components/WmsScene.tsx` | `d87c23f6d762271c31d386bc654ad10a15d165951488a6e93c4404d9bd6b66ef` |
| `apps/web/components/CctvInspector.tsx` | `92b2a68e3630344a93aa8307d15e84cbbd175dbd19dfb4e80cac7a9337bc652e` |

추가 파일: `tests/e2e/cctv-trusted-tracks-unit.mjs`, 이 보고서. manifest·fixture·Python 배포 코드·공통 작업표는 변경하지 않았습니다. 커밋은 메인이 담당합니다.

## 남은 인수

서버 시작 0, 브라우저 시작 0, 네트워크 호출 0, 빌드 실행 0입니다. 기존 정책 거부를 우회하지 않았습니다. 메인이 실제 전체 영상과 동일한 좌표를 SHA로 등록하고 Python 다운로드/배포 경로를 통합한 뒤 빌드·독립 검증해야 합니다. 최종 등록 자산의 실제 브라우저 재생·좌표 정렬·사람 검수와 배포 완료는 미검증입니다.
