# 보호된 읽기 전용 Preview 갱신

2026-09-22 pc1 · DEC-018/021의 배포 승인 · 최종 저장 연동과 구분

갱신 전 원격 Preview는 이전 `3c5e5a3` 소스·v2 음성/영상입니다. 최신 검증 묶음 `dist/deployment/20260921T185503517118Z-3cf7b0a9764a`으로 갱신하여 원격에서도 현재 역할별 작업대·v4 CCTV·빠른 재생을 확인할 수 있게 합니다. API 저장소가 없으면503을 반환하고 화면은 합성 예시 열람으로만 동작하는 기존 계약을 유지합니다. 로컬 API8100 재시작·새 로컬 서버/브라우저 금지의 우회 수단으로 사용하지 않습니다.

## 실행 전 실측

- 03:47 KST: g-28 storage status exit0, stores0. Blob403 생성 요청은 재시도하지 않았습니다.
- 03:50 KST: Vercel API의 project id `prj_VUk0C5e3thVOU9GgT8pc9tAoCczs`, account id `team_VXOpli8PNx0SDCGSdsjjDoJw`, name g-28 일치. rootDirectory/framework null, 보호 `all_except_custom_domains` 유지. 기존 자동화 접근 설정 존재 여부만 확인했습니다.
- Preview 환경 변수 이름은 ONEFLOW_STORAGE_BACKEND, ONEFLOW_ACCESS_PASSWORD, ONEFLOW_ACCESS_USER 세 개이며 모두 preview에만 있습니다. 값은 출력하지 않았고 새 키·환경·토큰·권한을 설정하지 않습니다.
- 새 묶음은 실제61파일이고 정적27/27·payload60/60·미디어16/16을 검증했습니다. 별도 검토자가 이전 묶음과 비교해 요청 코드/marker 두 파일만 바뀌었음을 확인했습니다.
- Vercel CLI59.23.2 `deploy --help` 및 `--dry`를 확인했습니다. 명시 project/scope/target으로 dry exit0,61파일12,964,126B, ignored0, frameworkOther입니다. 실제 파일의 경로·bytes·SHA1을 dry 목록과 마지막 대조합니다.

## 실행과 중단 조건

검증된 묶음에 `vercel deploy <bundle> --project <고정 project id> --scope 52g-studio --target preview --yes --json --no-wait`를 한 번 실행합니다. 실제 deployment ID/URL/target을 응답과 API로 대조하고 원격 BUILDING이면 같은 ID를 관측합니다. 의도와 달리 production이면 재시도·승격·별칭 수정 없이 중단하고 실제 상태를 남깁니다. 오류도 자동 반복하지 않습니다.

기존 프로젝트 보호와 서버 환경을 유지합니다. 새 OpenAI 키·Blob 권한·인증 토큰 생성/설정은 없습니다. 기존 인증값을 사용할 때도 검증된 같은 프로젝트 Preview origin에만 보내고 리다이렉트로 전달하지 않습니다. 비밀은 ignored 로컬 파일/메모리만 사용하며 로그·보고·Git·URL에 쓰지 않습니다.

검증은 실제 API target/READY, 무인증 보호, 기존 앱 인증의 유효성, health·정적HTML/JS/CSS·v4 파일 hash·Range, 저장소 미구성503·비밀/원장 비포함을 대조합니다. 실제 브라우저 신규 실행 없이 HTTP 검증 범위를 명시합니다. 기존 로컬 IAB의22접수·초안도 보존합니다. 원격 whole workflow·실모델·영속성·최종 Production·사람 검증은 이 Preview 인수 대상이 아닙니다.

## 실행 결과 연결

03:57 KST 실제 새 Preview의 READY·target=null을 확인했고, 04:01 HTTP 검사에서 정적27/27파일과 영상 Range2/2가 일치했습니다. API는503 STORAGE_CONFIG_INVALID입니다. [실제 배포·한정 인수 보고](../reports/deployment/protected-preview-refresh-20260922.md)에 결과와 한계를 기록합니다.
