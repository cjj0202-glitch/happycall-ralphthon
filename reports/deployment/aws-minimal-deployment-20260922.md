# 개인 AWS 최소 배포 실측 — 2026-09-22

pc1 최제준/cjj0202-glitch가 사용자 최신 지시(DEC-026)에 따라 기존 게임의 개인 AWS에 배포했다. Vercel은 사용하지 않았다. 08:15~08:22 KST의 실제 HTTPS·유료 텍스트 분석 1회·업무 저장·별도 Lambda 실행 환경 검증 결과다.

## 주소와 고정 대상

- URL: https://yrvhgwajh4zcfalqsdidrnm32a0oeltw.lambda-url.ap-northeast-2.on.aws/
- 개인 계정 `704995468470`, profile `scmops-lab`, 서울 `ap-northeast-2`. 기존 게임 `dawn-return-line` S3/CloudFront와 SCM 자원은 변경하지 않았다.
- Lambda `happycall-oneflow-api`: Python 3.12/x86_64, 1024 MB, timeout240초, published version1. Function URL은 앱의 Basic 인증을 사용하며 `/healthz`만 공개한다.
- 전용 DynamoDB `happycall-oneflow-state`, PAY_PER_REQUEST. 실행 역할은 해당 테이블 GetItem/PutItem 및 전용 로그 쓰기만 허용한다. 로그 보존3일.
- 배포 제품 SHA `f4916ca5b55a599dc9ba430d4b9642f9c2f88fcf`, 원격 main 일치 확인. 뒤의 보고서 커밋은 제품 변경이 아니다.
- `dist/aws/20260921T231011867801Z-f4916ca5b55a/oneflow-lambda.zip`
- zip SHA256 `ac9db73a5860502e49a274efd59a704db10ac3894c66d038a0e5efafea90e11a`, Lambda CodeSha256 `rJ23OlhgUC5JonTv1ZpwTbEKw4lMZtA4oOXvr+qQ4Ro=` 일치.
- 압축33,351,349/해제58,945,022 bytes, 4,338파일·Linux 휠41개·의존 관계58개·ELF x86_64 7개 검증. 키·`.env`·`.local`은 zip에 포함하지 않았다.

접속 계정은 Git 제외 `.local/aws-deploy-20260922/access.json`과 같은 폴더의 `접속안내.md`에 보관한다. API 키는 서버 환경에만 연결하며 공개 화면·Git·보고서에 싣지 않는다.

## 실제 검증

| 검사 | 결과 |
|---|---|
| Lambda 상태/코드 대조 | Active, LastUpdateStatus Successful, 업로드 zip 해시 일치 |
| HTTPS 인증·화면·API·미디어 | 19/19 통과: 공개 health200, 미인증 화면/API401, 인증 HTML·JS/CSS8개·API200, `.env`404 |
| 실제 음성2개/영상1개 | 전량 다운로드 후 로컬 고정 파일과 바이트/SHA 일치, 영상 Range0–1023은206/1024bytes |
| 접수 중복 방지 | 같은 UUID 두 번 제출 시201, 동일 사건/응답, 신규1건만 생성 |
| 실제 OpenAI 연결 | `gpt-4.1-mini`, 텍스트 분석1회, HTTP200, 클라이언트 측 전체6.625초. STT 호출0 |
| 업무 흐름 | 6/6 통과: 낡은 revision409/내용불변, 담당확인2→이관3→센터회신4→종결5, 경영주 재조회 동일 |
| 원본 보존 | 기본 합성2건 deep-equal 유지, 분석 이후 원문·전사·분석·근거 불변, 최종 총3건 |
| 별도 Lambda 환경 | 미호출 published version1을 직접 호출, cold-start Init Duration1286.25ms. 같은 사건/revision5 완전 일치. 원래 HTTPS 재조회도 동일 |
| 공유 비용 원장 | DynamoDB strong read에서 baseline2920+새 completed 예약15=2935센트, health29.35/30달러 동일 |

새 사건 `INT-53E58A50`은 합성 배송 도착 확인이다. 원문의 현재 위치·도착 예정 시각 요청이 보존됐고 수량/단위는 null이다. 모델 답변은 실제 차량 위치·도착 시간·배송 완료를 지어내지 않고 미확인으로 표시했다. 담당 부서는 delivery였으며 API 검증에서 담당 확인 상태를 저장한 뒤 센터로 전달했다. 최종 회신에는 실제 물류 조치를 실행하지 않은 합성 검증임을 명시했다.

실제 AI requestId는 `ce328805-0e0a-4260-be65-888d671ac0ae`, 예산 예약 state는 completed다. 15센트는 보수적 예약액이며 실제 공급자 청구액이 아니다. 과거104건 원본 원장은 복원하지 않았고 최신 공개 관측29.20달러를 이월했다. 남은 보수 한도는65센트이며 모든 PC의 독자 유료 호출은 중지 상태다. 재검 자동 과금은 하지 않는다.

## 로컬 검사와 한계

- 부모 메인 서버 관련113 passed/기존 deprecation warning5개. 패키지의 Function URL 합성 이벤트13/13은 별도 로컬 검증이며 실제 HTTPS19건과 합산하지 않는다.
- 처음 가상환경 Python으로 패키징할 때 pip 미설치로 실패했다. 시스템 Python으로 다시 생성해 성공했고 최종 산출물만 배포했다.
- 첫 HTTPS 검사에서 httpx 기본 인증서 저장소가 이 PC의 인증서 체인을 신뢰하지 못했다. Windows 신뢰 저장소를 사용하는 `ssl.create_default_context()`로 TLS 검증을 유지해 통과했다. 인증서 검증을 끄지 않았다.
- Codex 내장 브라우저는 해당 URL 탐색을 `ERR_BLOCKED_BY_CLIENT`로 거절했다. 따라서 AWS 화면의 브라우저 렌더링·클릭 검수는 완료로 세지 않는다. 외부 HTTPS의 HTML/정적 파일/API/미디어 실측과 기존 로컬 브라우저 검수는 통과했다. 일반 브라우저에서 Basic 로그인으로 열 수 있도록 로컬 접속 안내를 제공한다.
- 알림 의도4개는 모두 `not_connected`다. 실제 Teams/카카오 전송·수신은 연결하지 않았다.
- 합성 시연용 초안이다. 실제 고객/통화/물류 데이터, 공식 음원 검수, 운영용 사용자별 인증, 공식 제출은 미완료다. DynamoDB 단일 문서350KiB 제한이 있어 대규모 운영 저장소는 후속 작업이다.

원본 실행 결과와 재현 스크립트는 Git 제외 `.local/aws-deploy-20260922/`의 `deployment.json`, `final-status.json`, `http-checks.json`, `live-attempt.json`, `workflow-checks.json`, `case-completed.json`, `persistence-checks.json`에 보존한다. 최초 생성 Pending은 deployment.json, 최종 Active/Successful은 final-status.json으로 구분한다. `live_once.py`는 기존 시도가 있으면 재호출하지 않는다. 기존 `.local/main-resume-20260922/replay-state`와 다른 PC의 키·원장·원본 로그는 보존한다.
