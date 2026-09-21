# 모바일 접수 선택·목록 복귀 검증

2026-09-22 00:33~00:39 KST · pc1/CJJ · 기준 `866a738cfa260f3a5d73a945a118b93d555e70e4`

모바일 목록에서 접수를 고르면 해당 작업 영역으로 바로 이동하고, 상담/센터 단계 메뉴의 `접수 목록으로` 링크로 돌아오도록 구현했습니다. 화면 전환 자체는 저장·사람 확인·이관·회신을 실행하지 않습니다.

## 실패 관측과 설계

390×844에서 CASE-0001 클릭 후 포커스는 목록 버튼에 남고 사건 제목 top747.5px, 통화 영역 top985.5px였습니다. 화면 높이844px 안에 통화 기능이 없었습니다. 클릭에서만 일회성 RAF를 예약하고 렌더 후 현재 사건·역할·업무 뷰·폭을 대조하여 작업 영역에 focus와 instant scroll을 실행합니다. 동일 접수 재클릭에도 동작합니다. 새 hook/state나 컴포넌트 key 변경은 없습니다.

기존 `key={active.id}`와 초안·저장·revision·음성 완료 로직은 그대로입니다. 검색·필터 변경은 새 이동 요청을 만들지 않습니다. 목록 복귀는 native fragment 링크이므로 query/queue/selected를 변경하지 않습니다. WMS/TMS 화면에는 목록 복귀 링크를 추가하지 않습니다.

모바일 메뉴 높이는128px로 측정됐습니다. 문서 scroll-padding은192px이며 업무 단계에는 이 안전 영역이 적용됩니다. 메뉴보다 앞에 있는 목록/작업영역만 토큰 계산의 음수 scroll-margin으로 상쇄해 top16px에 도착합니다. 데스크톱 메뉴·96px 보정은 유지됩니다.

## 기존 IAB 실제 UI 결과

| 조건 | 기대 | 실측 |
|---|---|---|
| 390px 다른 접수 선택 | 선택 사건 작업으로 이동 | CASE-0002, focus=selected-work, top16px, 통화 영역 top314.5px |
| 390px 같은 접수 재선택 | 같은 사건으로 다시 이동 | focus=selected-work, top16px, 음원49.75초 정보 유지 |
| 목록 복귀 | 목록 포커스·선택 보존 | focus=work-queue, top16px, CASE-0002 유지 |
| CASE-0002 검색→Enter 선택→복귀 | 검색어·선택 유지 | query=CASE-0002, CASE-0002 유지, 선택 시 작업 포커스 |
| 0건 검색 | 검색창에 포커스 유지 | queue0건, 검색 결과 없음, focus=input[type=search] |
| 검색 지우기 | 기존 선택 복구 | query빈값, CASE-0002 복구 |
| 센터 선택→회신→목록 | 센터·사건·전체 필터 유지 | center/CASE-0002/전체22, 회신 top290.969>메뉴bottom128 |
| 768×1024 | 모바일 동작 | 작업top16, 링크flex, 문서753/753px |
| 769×900 | 데스크톱 비이동 | focus=queue-case selected, 링크none, 문서754/754px |
| 1280×900 | 데스크톱 비이동 | focus=queue-case selected, 링크none, 문서1265/1265px |
| 메뉴 증가 후 Tab12/ShiftTab12 | 고정 메뉴에 가리지 않음 | 24/24 visible, 최소top221.805>메뉴bottom128 |
| 센터 WMS/TMS 진입·복귀 | 같은 사건·역할 유지 | 두 화면 모두 CASE-0002/center, 잘못된 목록 링크0개, 센터 복귀 |
| 경영주 미저장 초안 | 기존 문장 유지 | 기존 합성 미도착 문의 전체 문장 일치 |

390px 문서도 clientWidth375/scrollWidth375로 가로 넘침이 없습니다. native 목록/단계 앵커와 키보드 Enter를 실제 UI로 조작했습니다. 필드 편집·새 접수·AI 호출·회신 저장을 실행하지 않았습니다. 음원 시각은0초 상태였으므로 실제 재생 도중 재선택의 청취 품질·완료 상태까지 검증한 것으로 쓰지 않습니다.

도구 조작 중 빈 문자열 fill은 검색어를 지우지 않아 다음 단계 링크가 발견되지 않았습니다. 실제 DOM에서 검색어가 남아 있음을 확인하고 제품의 `검색 지우기` 버튼으로 복구했습니다. TMS 복귀 버튼은 WMS와 달리 `←`를 포함하므로 첫 exact locator가 불일치했습니다. DOM의 실제 라벨로 선택해 복귀를 확인했습니다. 두 도구 선택 오류를 제품 결함이나 통과로 숨기지 않습니다.

## 코드·독립 검증

- `node tests/e2e/role-workflow-unit.mjs`: 기존87/87, 변이7/7. 결과 `.local/role-workflow-unit-1790004952416/results.json`.
- `node apps/web/node_modules/typescript/bin/tsc --noEmit --project apps/web/tsconfig.json`: exit0.
- 독립 worker의 새 `mobile-work-navigation-unit.mjs`: 실제 selectCase AST와 JSX 바인딩89/89, 변이9/9. 결과 `.local/mobile-work-navigation-unit-1790005016492/results.json`. 데스크톱/768↔769, 사건·역할·WMS/TMS 경합, 대상 사라짐, 같은 건 재클릭 및 빠른 다른 건 선택을 다룹니다. DOM/scheduler double이며 실제 렌더 증거는 위 메인 UI 검사입니다.
- 독립 explorer가 실제 diff를 검토하여 key 유지·조건부 focus·native 복귀·CSS 여백 계산을 대조했습니다. 한 프레임 사이 다른 입력으로 포커스를 옮기고 사건/역할/뷰는 유지되는 경합은 미재현 후보로 남습니다. 현재 실측 결함은 아닙니다.
- `git diff --check`: 통과. 조직 토큰 게이트의 앞선 외부 소비처 E601 실패는 해결하지 않았으며 [직전 보고서](ux-v2-responsive-focus-review.md)에 범위와 실측을 보존했습니다. 이번 변경에 색/폰트 리터럴은 없습니다.

이번 변경의 생산 빌드·배포 묶음·외부 배포는 별도 단계입니다. 최종 통화/영상 교체와 실제 새 접수 전체 저장 흐름 검증이 남아 있습니다.
