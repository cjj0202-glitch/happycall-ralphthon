# Vercel 계정 인증 완료와 메인 배포 인수인계

관측: 2026-09-21 17:57~18:09 KST, pc1/CJJ. 계정 연결 담당 작업 작성. 비밀번호·OTP·기기 인증 코드·토큰 값은 포함하지 않습니다.

**후속 관측(2026-09-22 04:01):** 메인이 최신3cf7b0a의 보호된 읽기 전용 Preview를 실제 배포·HTTP 검증했습니다. [최신 배포 보고](protected-preview-refresh-20260922.md)를 따릅니다. 저장소는03:47 조회0건, 접수API503으로 영속 저장·최종 Production·전체 업무 흐름은 미완료입니다. 아래 계정 담당 보고는18시대 이력이며 그 이후 배포가 없다는 뜻으로 읽지 않습니다.

**18시대 결론:** Vercel 로그인과 Enterprise `g-28` 로컬 연결은 완료됐습니다. 메인이 18:07경 시도한 private Blob 생성은 **권한 오류 403**으로 거절됐습니다. 계정 연결 담당의 후속 읽기 조회에서도 당시 계정이 볼 수 있는 연결 저장소/Blob은 각각 0건이었습니다. 당시 영속 저장소 준비와 실제 배포는 완료되지 않았습니다.

## 최신 사용자 지시와 역할

사용자가 이 작업에 “버셀 드디어 로그인 성공했어. 버셀로 서버 배포할 수 있도록 세팅을 해줘봐”라고 요청했습니다. 이어 메인프로젝트 작업에 전달하고 마크다운 인수인계를 만들도록 요청했습니다. 이 후속 지시로 현재 대상은 **Vercel**이며, 88ba3b1의 개인 AWS 전환은 과거 결정입니다.

계정 연결 담당은 브라우저/CLI 인증, 팀/프로젝트 조회, 확정된 프로젝트의 로컬 연결을 맡습니다. 메인은 서버 패키지·영속 저장·키 주입·Blob 생성/연결·실배포·통합 검증·중앙 문서 정합을 맡습니다. docs/12와 다른 담당자의 작업 파일은 이 작업에서 수정하지 않습니다.

## 완료된 사실

- [x] 브라우저 `Authorization Successful`, 계정 `hackathon02-1948` 확인
- [x] 현재 PC에서 새 `vercel login` 승인, 정상 종료 코드 0 확인
- [x] `vercel whoami` 결과 `hackathon02-1948` 확인
- [x] `vercel teams list --json`으로 **52g Studio / Enterprise** 확인
- [x] 두 후보 프로젝트의 존재와 설정을 읽기 전용으로 대조
- [x] 사용자 전달 실제 팀 보고를 메인이 대조해 G-28로 확정
- [x] 저장소 루트를 기존 Enterprise `g-28`에 연결하고 CLI 재조회로 검증
- [x] Blob 생성 시도 결과 및 연결 저장소 읽기 조회 결과 확인 — 생성 403, 조회 가능한 저장소 0건
- [ ] 권한 있는 팀 관리자의 private Blob 생성/연결 조치 및 서버 환경변수 실측
- [ ] Preview/Production 배포 및 제품 흐름 검증

브라우저 로그인·CLI 인증·로컬 프로젝트 링크가 완료됐습니다. 실제 서버 배포와 GitHub 자동 배포 연결은 아직 완료하지 않았습니다.

## 메인이 바로 사용할 연결 정보

| 항목 | 검증된 값 |
|---|---|
| CLI | Vercel 59.23.2, Node 24.18.0 |
| 사용자 | `hackathon02-1948` |
| Enterprise 팀 이름 | `52g Studio` |
| **명시할 scope** | **`52g-studio`** |
| 팀 ID | `team_VXOpli8PNx0SDCGSdsjjDoJw` |
| 팀 membership | `CONTRIBUTOR`, confirmed=true |
| CLI가 저장한 인증 파일 | `C:/Users/choi8/AppData/Roaming/com.vercel.cli/Data/auth.json` |
| 제품 저장소 | `C:/00.프로젝트/happycall-ralphthon` |
| 확정 프로젝트 | **`g-28` / `prj_VUk0C5e3thVOU9GgT8pc9tAoCczs`** |
| 로컬 연결 파일 | `C:/00.프로젝트/happycall-ralphthon/.vercel/project.json` |
| CLI 자동 생성한 OIDC 환경 파일 | `C:/00.프로젝트/happycall-ralphthon/.env.local` |

인증 파일은 존재만 확인했으며 내용을 출력하거나 Git에 복사하지 않았습니다. 같은 PC·Windows 사용자에서 메인은 CLI를 바로 사용할 수 있습니다. 다른 노트북으로 인증 파일을 복사하지 않습니다.

현재 CLI 기본 팀은 개인 Hobby입니다. 행사 리소스 작업에는 **`--scope 52g-studio`를 항상 명시**합니다. 현재 membership 표시는 실제 프로젝트 관리 권한이나 Blob 생성 성공의 대체 증거가 아닙니다.

```powershell
Set-Location 'C:/00.프로젝트/happycall-ralphthon'
vercel whoami
vercel teams list --json
```

## 프로젝트 번호 대조와 최종 선택 근거

기존 안내의 `g-23`과 메인에게 전달된 PC 보고의 `g-28`이 상충합니다. 그룹 계정은 여러 팀이 공유하므로 계정 접근 가능 여부만으로 우리 팀 프로젝트를 정하지 않습니다. 다음은 두 후보에 한정한 `GET /v9/projects/{name}` 읽기 결과입니다.

| 항목 | g-23 | g-28 |
|---|---|---|
| 프로젝트 ID | `prj_NcLHu3CP6TAPtt5JJfmMGmcBFvsp` | `prj_VUk0C5e3thVOU9GgT8pc9tAoCczs` |
| accountId | 위 Enterprise 팀 ID | 위 Enterprise 팀 ID |
| Git link | null | null |
| latestDeployments | 0개 | 0개 |
| rootDirectory / framework | null / null | null / null |
| Node | 24.x | 24.x |
| 배포 보호 설정 | all_except_custom_domains | all_except_custom_domains |

두 프로젝트가 모두 비어 있어 Git 저장소를 통한 귀속 판별은 불가능했습니다. 이후 메인이 사용자에게 직접 전달받은 pc3 등록 보고를 대조했습니다. 그 원문에는 **팀 G-28 / hostname LAPTOP-U2AL73UH / GitHub mcjun86-oss / 정준화**가 있었고, 같은 hostname·GitHub가 이 HappyCall 팀의 pc3로 `channel/pcs.json`에 등록되어 있습니다. 메인이 이 사용자 전달 소속 증거를 공유 계정의 g-23 관리자 변경 이메일보다 우선하여 **기존 g-28만 연결**하도록 확정했습니다. 다른 프로젝트는 변경하지 않았습니다.

메인이 준비 중인 **Python ASGI + Next 정적 출력 + 동일 원본 API** 단일 패키지는 저장소 루트를 배포 루트로 사용합니다. 과거 `apps/web`만 링크하는 예시를 적용하지 않았습니다. 실제 링크 명령은 `--team`과 `--scope`를 같은 팀으로 명시했고 성공했습니다. CLI가 `--team` 폐기 예정 경고를 표시했으므로 후속 명령은 아래처럼 `--scope`를 사용합니다.

```powershell
# 현재 PC는 이미 연결 완료. 다른 PC에서 동일 대상 연결 시 사용합니다.
vercel link --yes --scope 52g-studio --project prj_VUk0C5e3thVOU9GgT8pc9tAoCczs --cwd 'C:/00.프로젝트/happycall-ralphthon'
vercel project inspect --scope 52g-studio --json
```

CLI 출력에서 `Linked 52g-studio/g-28`을 확인했고 로컬 파일의 projectId/orgId를 위 확정값과 대조했습니다. 이어 `vercel project inspect --scope 52g-studio --json`이 g-28과 52g Studio를 반환했습니다. 루트 `.vercel/project.json`과 자동 생성된 `.env.local`이 Git에서 제외되고 추적되지 않는 것을 확인했습니다. CLI가 덧붙인 중복 `.vercel`/`.env*` 규칙은 기존 `.env.demo.example` 예외를 덮을 수 있어 해당 자동 추가분만 제거하고 원래 ignore 규칙을 유지했습니다.

계정 연결 담당이 18:03까지 확인한 프로젝트의 원격 rootDirectory/framework는 null이고 기존 배포 보호도 유지됐습니다. 이후 원격 배포 설정은 메인 담당이므로 실행 직전 다시 조회합니다. 이 작업에서는 Blob·OpenAI 키·Basic 비밀번호를 주입하거나 Git 저장소 자동 배포를 연결하지 않았습니다.

## Blob 생성 403과 읽기 전용 후속 확인

메인 작업이 2026-09-21 18:07경 다음 생성 명령을 실행했고 결과를 전달했습니다. 종료 코드 1, `status:error`, `reason:api_error`, 메시지는 `Failed to create the store: You don’t have permission to create the blob. (403)`입니다. 생성된 store ID는 없습니다. 로그인 성공과 팀 리소스 생성 권한은 별개입니다.

```powershell
# 메인이 실행했고 403으로 실패한 명령. 권한 변경 없이 재시도하지 않습니다.
vercel storage create happycall-g28-state --type blob --access private --region icn1 --scope 52g-studio --json
```

계정 연결 담당은 같은 PC/계정에서 아래 두 조회만 수행했습니다. 두 명령 모두 종료 코드 0과 구조화된 응답 `{"stores":[]}`를 반환했습니다. CLI 로그인·팀·프로젝트 조회가 성공한 동일 환경이며, 오류를 빈 목록으로 변환한 결과가 아닙니다.

| 읽기 명령 | 결과 | 로컬 원문 위치(Git 제외) |
|---|---|---|
| `vercel storage status --project prj_VUk0C5e3thVOU9GgT8pc9tAoCczs --scope 52g-studio --json` | 조회 가능한 프로젝트 연결 저장소 0건 | `.local/vercel-storage-status.json` |
| `vercel storage list --type blob --scope 52g-studio --json` | 조회 가능한 팀 Blob 0건 | `.local/vercel-blob-list.json` |

**판정 범위:** 현재 Contributor 계정의 조회 결과입니다. 팀 전체에 Blob이 전혀 없다는 증거로 확대하지 않습니다. 현재 계정이 바로 사용할 수 있는 기존 연결 저장소는 이 조회로 발견하지 못했습니다. 공식 [접근 역할 문서](https://vercel.com/docs/rbac/access-roles)도 Contributor의 지정 프로젝트 권한과 팀 수준 권한을 구분합니다. 정확한 권한 정책과 부여 방식은 팀 관리자가 확인해야 합니다.

생성 요청을 다른 도구·개인 Hobby·다른 계정으로 우회하지 않습니다. 계정 연결 담당은 재생성 시도, 권한 변경, 관리자에게 외부 메시지 발송을 하지 않았습니다. 저장소 준비 전에는 영속 저장·전역 예산 검증 완료나 live 배포 완료로 기록하지 않습니다.

### 메인이 관리자에게 전달할 요청 초안

> 52g Studio의 G-28 해커톤 프로젝트에서 private Blob 저장소 연결이 필요합니다. 현재 `hackathon02-1948` 계정은 Contributor이며 CLI 생성 요청이 403으로 거절됐습니다. 권한 있는 관리자가 `happycall-g28-state`(private, `icn1`)를 생성하고 `g-28` 프로젝트의 Preview/Production에 연결해 주세요. 프로젝트 ID는 `prj_VUk0C5e3thVOU9GgT8pc9tAoCczs`, 팀 ID는 `team_VXOpli8PNx0SDCGSdsjjDoJw`입니다. 이미 사용 가능한 G-28 전용 private 저장소가 있다면 해당 연결로 대체할 수 있습니다. 연결 결과와 store ID만 전달하고, 인증 토큰은 채팅에 보내지 말고 Vercel 서버 환경변수로 설정해 주세요. 인증 방식은 메인 배포 담당과 OIDC/토큰 호환성을 확인한 뒤 선택합니다.

이 문구는 인수인계용 초안이며 실제 관리자에게 발송한 기록이 아닙니다. 관리자 생성/연결 또는 적법한 권한 부여가 확인된 뒤 메인이 이어서 실행합니다.

## Blob 연결 도구와 후속 검증 — 메인 소유

설치된 CLI의 `storage create/connect/status --help`에서 아래 기능을 확인했습니다. CLI link가 자체 생성한 OIDC 환경 파일은 위 경로에 있습니다. 다음 연결 명령은 store와 권한을 확보한 뒤 사용합니다.

```powershell
vercel storage connect <store-id> --project prj_VUk0C5e3thVOU9GgT8pc9tAoCczs --environment preview --environment production --auth oidc --dry-run --scope 52g-studio
vercel storage connect <store-id> --project prj_VUk0C5e3thVOU9GgT8pc9tAoCczs --environment preview --environment production --auth oidc --yes --scope 52g-studio
```

현재 CLI의 기본 연결 방식은 OIDC입니다. 공식 문서상 `BLOB_STORE_ID`와 런타임 `VERCEL_OIDC_TOKEN`을 SDK가 사용하는 방식입니다. 단, 메인의 자체 Python HTTP 어댑터가 같은 갱신 경로를 지원하는지는 별도 검증해야 합니다. 정적 토큰 방식이 필요하면 CLI의 `--auth token --add-rw-token`을 명시해야 하며, 토큰 값은 서버 환경변수/무시된 로컬 파일로만 전달합니다. 생성·연결 출력에 비밀값이 포함될 가능성을 고려해 원문 전체를 채팅이나 로그에 출력하지 않습니다.

Blob 실제 인수는 최초 생성 경합·ETag 갱신 충돌·최신 읽기·전역 예산 보존까지 확인합니다. 세부 구현 정본은 [HTTP 계약](blob-http-contract.md), [어댑터 검증](blob-adapter.md)입니다. [공식 Blob 인증 문서](https://vercel.com/docs/vercel-blob/using-blob-sdk#authentication)를 함께 대조합니다.

## 메인에서 남은 순서

2026-09-21 21:03 KST 후속 읽기: 같은 `vercel storage status --project prj_VUk0C5e3thVOU9GgT8pc9tAoCczs --scope 52g-studio --json`을 조회했고 exit 0, `stores: []`였습니다. 생성 요청을 다시 보내지 않았습니다. 이 계정에 보이는 프로젝트 연결 저장소가 여전히 0건이며 관리자 연결 확인은 대기 중입니다.

2026-09-21 21:39 KST 동일 읽기 전용 조회도 exit0, `stores: []`입니다. 생성403을 다시 시도하거나 다른 계정·도구로 우회하지 않았습니다. 실제 저장소 연결/영속 상태 검증은 아직 미완료입니다.

1. 확정된 g-28의 루트 링크 결과를 확인하고, 검증된 ASGI 배포 설정을 적용합니다.
2. 팀 관리자 조치로 private Blob을 확보하고 연결을 재조회합니다. 서버 비밀값 설정 후 저장/예산 실환경 검증을 실행합니다. 403이 해소되기 전에도 UI·패키지·로컬 테스트는 계속할 수 있습니다.
3. Preview URL에서 API·정적 JS·미디어·두 업무 흐름을 검증한 후 Production으로 진행합니다.
4. 배포 보호 설정과 시연 접근제어를 실제 비로그인 브라우저에서 검증합니다. 기존 보호를 임의 해제하지 않습니다.

과거 인증 실패·AWS 검토 기록은 보존합니다. 중앙 문서의 최신 방향과 완료 표시는 메인이 이 실제 관측에 맞춰 갱신합니다.
