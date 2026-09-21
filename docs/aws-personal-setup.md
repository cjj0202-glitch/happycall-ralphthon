# 개인 AWS 배포 준비 — 연결 진행 중

**후속 DEC-021:** 사용자가 17:58 Vercel 배포를 재지정했고 18:00 CLI 인증 성공이 확인되어 개인 AWS 준비는 보류합니다. 아래는 과거 준비·차단 이력입니다. AWS 리소스 생성·배포는 실행하지 않습니다.

2026-09-21 사용자 지시로 해커톤 호스팅 대상을 Vercel에서 개인 AWS 계정으로 전환했습니다. 이 지시는 이 해커톤에 한정하며 기존 회사 AWS 시스템·91 SCM 운영 배포를 재개한다는 뜻이 아닙니다.

> 후속 17:48 Vercel 로그인 재시도 요청과 17:54 양쪽 인증 미완료 확인은 DEC-019·docs/12에 정리했습니다. 아래는 개인 AWS 준비 이력이며 최종 호스트 확정 증거가 아닙니다.

## 진행 상태

- [x] 개인 AWS 전환 요청 확인
- [x] 현재 앱의 배포 의존성 점검
- [x] 서울 리전 콘솔에서 개인 이메일 로그인 화면 열기
- [ ] 개인계정 로그인과 MFA 완료
- [ ] 실제 계정 ID·리전·실행 주체 확인
- [ ] 배포 도구와 해당 계정의 권한 확인
- [ ] 서버 구성·예상 비용·종료 시점 확정
- [ ] 클라우드 주소·영속 저장·접근 인증·서버 비밀값 설정
- [ ] 배포 후 두 시나리오·미디어·상태 보존 검증

위 체크는 이 연결 작업의 기록입니다. 중앙 H01/H02는 Vercel을 전제로 한 기존 항목이므로 AWS 준비를 Vercel 완료로 기록하지 않습니다. 로그인 전에는 리소스나 유료 서버를 생성하지 않았습니다.

## 현재 PC와 로그인 관측

pc1(CJJ)에서 AWS CLI 명령과 기본 설치 경로, 사용자 `.aws` 폴더를 확인했으며 모두 발견되지 않았습니다. 공식 사용자용 AWS CLI MSI 설치 명령은 실행 전에 자동 승인 검토가 `blocked by policy`로 거부했습니다. 다운로드·설치 완료를 의미하지 않습니다. 동일 설치를 다른 수단으로 우회하지 않았습니다.

브라우저에서 개인 이메일을 루트 사용자 로그인 경로에 입력했습니다. 비밀번호 인증 실패 후 사용자 재시도에서 보안문자(CAPTCHA) 입력 화면으로 진행했습니다. 마지막 관측은 보안문자 불일치이며 계정 로그인·MFA·권한 확보는 미완료입니다. 보안문자는 사용자가 직접 진행합니다. 비밀번호·MFA·액세스 키·인증 토큰은 문서나 GitHub에 기록하지 않습니다.

로그인 뒤에는 콘솔의 CloudShell에서 미리 설치된 AWS CLI로 계정과 리전을 조회할 수 있습니다. 이는 이 PC의 CLI 설치 완료와 다릅니다. 회사 계정 설정이나 다른 프로젝트의 AWS 인증을 복사하지 않습니다.

```bash
# AWS CloudShell에서 읽기 전용으로 확인
aws sts get-caller-identity
aws configure get region
aws --version
```

계정 ID는 사용자가 선택한 개인계정과 대조합니다. 서울(`ap-northeast-2`)은 현재 열어 둔 콘솔 리전이며 리소스가 배포됐다는 증거는 아닙니다. CloudShell은 운영 웹 서버로 사용하지 않습니다.

## 코드에서 확인한 배포 조건

| 항목 | 현 상태 | 배포 준비에 필요한 조치 |
|---|---|---|
| 화면 | Next.js `output: export` | 정적 출력·JS·음성·영상 경로 검증 |
| API 주소 | 기본 `http://127.0.0.1:8100` | 실제 HTTPS API 주소로 빌드 설정 |
| API | Connexion 3 ASGI | 선택한 AWS 런타임의 시작점·헬스 체크 확인 |
| CORS | 로컬 3100 포트만 허용 | 실제 웹 출처만 추가 |
| 접수 상태 | `.local/cases-store.json`, FileLock | 재시작 후에도 보존되며 동시 갱신이 안전한 저장소 |
| API 예산 | `.local/demo-usage.json` | 모든 호출이 공유하는 예약 장부; 인스턴스별 분리 금지 |
| 실제 AI | 요청당 SDK 제한 90초, UI 제한 120초 | 실제 최대 처리 시간에 맞는 경로 또는 비동기 처리 |
| 화면 역할 | `X-Demo-Role` 시연 역할 | 인터넷 공개 시 실제 접근 제한; 헤더를 실제 인증으로 오인하지 않기 |
| OpenAI 키 | 서버 전용 로컬 파일 | 별도 승인된 서버 비밀값 주입; 정적 화면·빌드 결과에 포함 금지 |

AWS HTTP API 통합의 최대 제한은 30초입니다. 따라서 현재 동기식 AI 호출을 그 경로에 그대로 연결해 완료로 판정하지 않습니다. Lambda로 이식하려면 접수/예산 저장과 긴 작업 처리를 먼저 바꾸어야 합니다. 서버 종류는 실제 개인계정의 권한과 비용을 확인한 뒤 확정합니다. 이번 연결 작업에서 앱 구현을 임의 변경하지 않았습니다.

OpenAI 데모용 30달러 지침은 기존대로 유지합니다. AWS 서버 비용과 동일한 예산으로 해석하지 않습니다.

## 완료 판정

로그인은 콘솔 계정 표시와 STS 결과, 배포는 실제 HTTPS URL·API health·JS Content-Type·미디어 재생·접수→이관→회신·재시작 후 상태 보존으로 확인합니다. 로그인 성공만으로 서버 배포나 사람 시연 성공을 보고하지 않습니다.

공식 근거: [AWS 콘솔 자격증명을 이용한 CLI 로그인](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html), [AWS CLI 설치](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), [CloudShell](https://docs.aws.amazon.com/cloudshell/latest/userguide/welcome.html), [HTTP API 제한](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-quotas.html).
