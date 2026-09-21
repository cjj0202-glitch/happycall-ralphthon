# N02 실제 CallReview 독립 브라우저 검증

`harness.tsx`는 제품의 `apps/web/components/CallReview.tsx`, 실제 CSS module, tokens/globals를 직접 import합니다. 컴포넌트 로직·스타일을 복제하지 않으며 공용 page/package/fixture/manifest/API를 변경하지 않습니다. 원본 합성 fixture의 복사본과 명시적인 경계 입력을 deep freeze해 전달합니다.

## 실행

앱과 기존 E2E 의존성이 설치되어 있어야 합니다. 별도 패키지는 추가하지 않습니다.

```powershell
# 저장소 루트에서 Node 실행 경로를 본인 환경에 맞춘다.
node tests/remote/pc2/run.mjs
```

기본 브라우저는 설치된 Edge headless입니다. 필요하면 `N02_BROWSER_CHANNEL=chrome` 또는 `E2E_CHROMIUM`에 실제 설치된 Chromium 실행 파일을 지정합니다. 실행기는 브라우저를 다운로드하지 않습니다.

수정한 경계만 재검할 때 `N02_CHECK_FILTER`에 검사 ID 정규식을 지정할 수 있습니다. 필터 결과는 별도 `reports/pc2/browser-focused-results.json`에 저장하여 전체 결과를 보존합니다. JSON의 `checkFilter`를 함께 보고하며 일부 검사 결과를 전체 통과로 사용하지 않습니다. 최종 인수 실행에서는 필터를 해제합니다.

1. Next 내장 webpack/CSS module compiler와 앱 TypeScript/React로 `.local/pc2-harness/`에 bundle을 생성합니다.
2. 자신만의 `127.0.0.1:3122` 서버를 엽니다. 포트가 사용 중이면 실패하며 다른 프로세스를 종료하지 않습니다.
   브라우저 제어 WebSocket도 `host: '127.0.0.1'`로 제한합니다. 모든 인터페이스 수신을 기본값으로 사용하지 않습니다.
3. 기존 v2 WAV 두 파일의 SHA를 manifest와 대조하고 두 브라우저 페이지에서 **실제 1배속 전체 재생**합니다. 시간 점프·가짜 ended·배속으로 대체하지 않습니다.
4. 짧은/무음/0초/손상 WAV는 테스트 서버 메모리에서만 생성합니다. 404도 직접 제공합니다. 구간 시각은 제어 시험용이며 실제 STT 정렬 증거가 아닙니다.
5. 각 판정의 기대·실측·오류와 원본 해시를 `reports/pc2/browser-results.json`에 남깁니다. 이전 판정·음원 측정·실패는 `previousRuns`에 보존합니다. 스크린샷은 `reports/pc2/screenshots/`이며 같은 이름은 최신 실행 화면으로 갱신합니다.
6. 실행 종료 시 자신의 BrowserServer 프로세스와 HTTP 연결만 닫습니다. 단계별 종료 결과와 10초 제한을 기록하고 자신의 BrowserServer 닫기가 지연되면 그 인스턴스의 kill만 사용합니다. 타인 PID·공용 서버를 종료하지 않습니다. 실패가 하나라도 있으면 exit code1입니다.

외부 요청과 GET/HEAD 외 요청은 막고 시도 자체를 실패로 기록합니다. 실제 API, 유료 STT/TTS/LLM, 외부 실데이터, 부모 앱 저장·이관은 호출하지 않습니다. 헤드리스 재생 완료는 OS 스피커 출력·사람 청취 명료도·실제 Silent Test를 뜻하지 않습니다. 비교 대상은 현재 `caseData.intake`이며 상위 서버가 과거 입력을 덮어쓴 경우 원본을 복원하는 검사가 아닙니다.

수용 시나리오는 `reports/pc2/scenario-test-plan.md`와 구조화 결과를 함께 읽습니다. N02 컴포넌트 검증 수를 프로젝트 전체 20입력·12경계·6회 완주 분모로 바꾸지 않습니다.

## 추가 반례의 범위

현재 기본 실행은 26개 판정입니다. C01은 WAV별 2개, C07은 누락/404/손상/0초별 4개, C12는 폭별 3개이며 나머지 ID는 각각 1개입니다. C15는 외부 요청·페이지 오류 검사입니다. C16~C20은 disabled 중 재생, 구간 밖 seek, RAF 중단/visibility, 완료 후 사건·음원 변경, 텍스트 접수의 추가 경계입니다.

C06은 대화록 영역 안의 정확한 출처 문구를 검사합니다. 먼저 명시적인 합성 제어 입력으로 replay/demo-live/미확인/analysisMode fallback을 검사한 다음, `reports/e2e/normalized-voice-live.json`에 이미 저장된 합성 CASE-0002의 실제 STT 응답 14구간을 읽습니다. 이 저장 응답에서 A/B 라벨과 서로 다른 표시색, 정정 발화, null 점포를 확인하며 새로운 STT API를 호출하지 않습니다. 단순 합성 시각 입력을 실제 STT 성능 증거로 사용하지 않습니다.

C18은 실제 짧은 WAV의 디코더·시계·trusted timeupdate를 유지한 채 requestAnimationFrame만 억제합니다. 구간 끝을 0.8초로 지정하고 정지 여부 및 native played 범위가 1.15초 이하인지 확인합니다. 이는 최대 350ms의 이벤트 지연을 허용하는 기술적 판정이며 샘플 단위의 정확한 절단을 뜻하지 않습니다. 실제 탭 전환 뒤 visibility를 관측하지만 headless에서 계속 visible이면 `realHiddenTabVerified=false`로 남깁니다. 별도의 hidden 속성/visibilitychange 주입은 선택 구간 정지·hidden 중 재시작 차단·전체 재생 비간섭만 검사하며 실제 브라우저 백그라운드 시험과 구분합니다.

추가 영향 검사의 재현 예시:

```powershell
$env:N02_CHECK_FILTER='^(C02|C05|C06|C09|C11|C16|C17|C18|C19|C20)'
node tests/remote/pc2/run.mjs
Remove-Item Env:N02_CHECK_FILTER
```
