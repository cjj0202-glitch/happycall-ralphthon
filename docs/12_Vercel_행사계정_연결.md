# Vercel 행사 계정·배포 대상 정본

현재 대상은 **52g Studio / g-28**입니다(DEC-021). 이 메인 대화의 실제 pc3 준비 보고에 있는 팀 G-28과 등록 신원 LAPTOP-U2AL73UH / mcjun86-oss를 대조해 선택했습니다. 과거 g-23 예시는 실행값으로 쓰지 않습니다.

최신 배포 관측은 [2026-09-22 보호 Preview 갱신](../reports/deployment/protected-preview-refresh-20260922.md)입니다. 고정3cf7b0a를 실제 Preview로 배포하고 원격 정적27/27·인증·영상 Range를 확인했습니다. 접수API는 저장소 미구성503이며 최종 Production·전체 저장 흐름은 미완료입니다.

## 확인한 계정과 프로젝트

| 항목 | 검증한 값 |
|---|---|
| CLI 계정 | hackathon02-1948 |
| 팀 / 명시 scope | 52g Studio / `52g-studio` |
| 팀 ID | `team_VXOpli8PNx0SDCGSdsjjDoJw` |
| 프로젝트 | `g-28` |
| 프로젝트 ID | `prj_VUk0C5e3thVOU9GgT8pc9tAoCczs` |
| CLI | 59.23.2 |

18:00 KST 실제 CLI 로그인, 18:03 프로젝트 로컬 연결을 확인했습니다. 현재 root `.vercel/project.json`을 다시 대조하고, 모든 CLI에 `--scope 52g-studio`를 명시합니다. 기본 개인 Hobby scope를 사용하지 않습니다. 다른 팀 프로젝트는 수정하지 않습니다. 인증정보 값은 Git/편지/보고서에 기록하지 않습니다.

## 배포할 파일과 실행 순서

제품은 Next 정적 export와 Python ASGI를 한 origin에 묶습니다. `apps/web`만 배포하면 API와 접근제어가 빠지므로 그 경로를 프로젝트 Root Directory로 설정하지 않습니다. 검증된 패키저로 만든 **새 `dist/deployment/<시각>-<SHA>` 폴더**가 배포 입력입니다.

```powershell
# 메인 저장소에서 프런트엔드 빌드 완료 기록 작성
.venv/Scripts/python.exe scripts/build_deployment_bundle.py --build
# 새 배포 폴더 생성; 출력 경로를 다음 단계에서 사용
.venv/Scripts/python.exe scripts/build_deployment_bundle.py
```

패키저는 완료한 build·소스 지문·public/out 미디어 SHA256·합성 fixture 일치를 검증합니다. 서버 실행 파일은 허용 목록으로 복사하며 `.env*`, `.local`, 운영 원천, 원본 로그를 제외합니다. 기존 패키지는 덮어쓰지 않습니다. [설계와 실행 검사](../reports/deployment/bundle-design.md), [독립 검토](../reports/deployment/bundle-independent.md).

메인은 해당 새 폴더에서 명시 project ID/scope로 Preview를 배포합니다. 환경값은 stdin으로 서버 비밀 환경에 입력하고 명령문·출력에 비밀을 붙이지 않습니다. 화면/미디어/API에는 공유 데모 접근제어가 있으며 Vercel의 프로젝트 보호 설정도 유지합니다. 이는 실제 상담원·경영주 역할별 인증의 완성을 뜻하지 않습니다.

## 영속 저장 차단과 완료 기준

18시대 실제 Blob 생성 요청은 **403 권한 부족**으로 거부됐습니다. 현재 계정에서 보이는 저장소 목록은 0개이며, 팀 전체에 없다는 뜻은 아닙니다. [계정 보고](../reports/deployment/account-auth-status.md)의 관리자 조치가 필요합니다. 다른 계정·도구로 같은 거부를 우회하지 않습니다.

Vercel 런타임은 로컬 JSON 저장으로 자동 후퇴하지 않고, 공유 상담 상태/예산 원장이 준비되지 않으면 API를 503으로 닫습니다. 그동안 정적 화면·합성 미디어를 확인하는 제한 Preview를 검증할 수 있지만 전체 흐름 완료로 세지 않습니다. 과금 API 키는 영속 원장이 준비되기 전에 배포하지 않습니다.

최종 통과는 실제 URL에서 인증·미디어·통화/텍스트 두 흐름·revision 충돌·상태 지속·원장 원자갱신·실패/복구를 검증한 뒤입니다. 로그인/빌드/Preview URL 발급은 각각 별도 관측입니다. 최종 Production 승격과 09시 인계는 이 결과를 근거로 판단합니다.

## 이전 인증 관측과 출처

15:21 이메일 재요청 횟수 제한, 17:36 개인 AWS 요청, 17:48 Vercel 재시도, 17:54 양쪽 인증 미완료는 당시 관측입니다. 17:58 Vercel 배포 재지정·18:00 성공이 후속 사실입니다. 이전 실패를 성공으로 소급하거나 같은 로그인·설치 거부를 반복하지 않습니다. 자세한 이력은 [Vercel 연결 기록](../reports/vercel-link.md), [개인 AWS 기록](aws-personal-setup.md), [계정 인계](../reports/deployment/account-auth-status.md)를 보존합니다.

행사 계정의 출처는 [공식 Notion 안내](https://gsholdings.notion.site/vercel-3e2f800bd1c1800cb3d9e5fc29aefeca)와 저장한 [본문](official/2026-09-21/vercel-guide.dom.txt)·[상단](official/2026-09-21/vercel-guide.png)·[중간](official/2026-09-21/vercel-guide-02.png)·[하단](official/2026-09-21/vercel-guide-03.png)입니다. 이 문서 정리로 원본 캡처·이전 커밋·실패 증거는 삭제하지 않았습니다.
