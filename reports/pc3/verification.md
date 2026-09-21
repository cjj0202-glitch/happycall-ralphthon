# N03 구현·검증 인계

2026-09-21 18:48 KST / pc3 `LAPTOP-U2AL73UH` / GitHub `mcjun86-oss`.
실제 checkout `D:\hwana\Work\happycall-ralphthon`, branch `work/pc3-n03-wms-scenes`, 기준 `d4b4a8137fbc608911e9f6f71bd4b5e289e0a958`. 배정은 [#9](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9). 결과 SHA는 이 보고서를 포함한 커밋과 같은 이슈의 결과 회신을 대조한다.

## 구현한 사용자 결과

`WmsScene` 기본 export는 `caseData: CaseData`, `onLinkEvidence(id): Promise<void>|void`, `onBack():void`를 제공한다. 두 합성 사건의 공정 선택·다음 행동·피킹/출고 비교·슈트 대조·원본 펼치기·근거 연결·읽기 전용 상태를 구현했다. CASE1 미수령 진술과 출고 기록, CASE2 비스킷18EA/휴지1BOX 및 토트A/B를 구분한다. 수량 미확인을 0으로 채우거나 EA/BOX를 차감하지 않는다.

공정 설명 이동은 기본 정지이며 시작/일시정지·모션 감소·키보드를 지원한다. 사건·시각·revision·데이터 교체 시 열린 영상과 화면 상태가 초기화된다. 기존 등록 영상은 CASE2/W-W3 한 건만 재생한다. 정본 등록값과 실제 파일 bytes/SHA256을 확인한 후 Blob URL로 재생하고, 잘못된 관계/구간/중복·404·해시 변조를 차단한다. 오류 후 재시도와 원본 확인, Escape/닫기 후 초점 복귀를 제공한다.

피킹/분기/출고 6개 새 영상은 별도 코드 애니메이션 **후보**로 생성했다. 443,580 bytes, SHA/관계키/생성방식은 [media-candidates.md](media-candidates.md)와 overlay에 있다. 실제 CCTV·AI 영상 모델 결과·귀책 증거로 표시하지 않는다.

## 실제 실행 결과

| 검사 | 명령 / 환경 | 기대 | 실측 |
|---|---|---|---|
| TypeScript | apps/web에서 `node node_modules/typescript/bin/tsc --noEmit` | 오류0 | exit0 |
| Next production build | apps/web에서 `node node_modules/next/dist/bin/next build` | 컴파일·타입·정적생성 성공 | exit0, 정적5페이지 생성 |
| 실제 컴포넌트 브라우저 | tests/remote/pc3에서 `node run.mjs`, Chrome153.0.8010.48 | 2case×3폭, 반례·재생·조작 | **49/49 PASS**, 소스변경0, 외부요청0 |
| 독립 계약/SSR | `node tests/remote/pc3/registration-review.cjs` | 기존 결함 재현 및 후보등록 회귀 | **24/24 PASS**, fixture/manifest 파일 불변 |
| 미디어 계약 | `python -m unittest discover -s scripts/media_pc3 -p 'test_*.py' -v` | 잘못된 관계/메타데이터 거부 | **8/8 PASS**, 20개 하위 변이 포함 |
| 신규 후보 파일 | `python scripts/media_pc3/generate_candidates.py --verify-only` | 6개 메타·bytes·SHA 일치 | PASS |
| 생성 영상 디코딩 | generate_candidates.py, Pillow12.3.0/FFmpeg7.1 | 실제 H264·움직임·프레임 | 6개×108=648프레임, 각6초/18fps/960×540 |
| 기존 Release 수신 | `python scripts/fetch_demo_media.py --upgrade-approved` 후 `--verify-only` | verified3/missing0 | 3/0, v2 자산 SHA 일치 |

브라우저 최종 실행: 18:47:00–18:47:07 KST. 결과는 [browser-results.json](browser-results.json). WmsScene SHA256 `d9f1dbe73480cc0081e927bef8bd790b5163c0980790e3595b00ea181aed67e1`, CSS `6c6129347b80868d6aa7d12ac47a0ab938cf67850752e8e6266a64e75665c9bd`.

브라우저 49개에는 390/921/1365px 6화면, 8개 이벤트의 선택·다음 행동, 미등록 영상7개, 23개 연결 변형 거부, 원본 시각 역전 보존, null/0, EA/BOX, 정상 동영상·404 복구·동일크기 변조, 사건 전환, 모션 감소, 근거 실패·중복·저장 후 성공, 이관 읽기 전용·키보드가 포함된다. 분모를 단위 테스트 개수나 전체 제품 정확도와 합산하지 않는다.

실제 등록 영상 duration=12초, currentTime `0.000851 → 0.271008`, 재생 중 paused=false와 video error 없음. 바이트/hash 확인 후 실제 재생을 관측했으며 파일 존재만으로 통과시키지 않았다. 로컬 스크린샷9개는 `.local/pc3-tests/2026-09-21T09-47-00-012Z/`에 보존한다. 원본 이미지/영상은 Git에 올리지 않는다. 동일 하네스로 재생성 가능하다.

## 발견 → 수정 → 동일 조건 재검

| 관측한 결함 | 수정 | 재검 |
|---|---|---|
| 전날 picking/shipping/sorting와 당일 event 영상 혼합 허용 | 정본 공정시각·관계 대조 | 계약/브라우저 거부 PASS |
| event.caseId/system 및 nested relations 날짜/asOf 충돌 무시 | 정의한 관계키·등록 relations 대조 | 동일 변이 거부 PASS |
| 다른 사건 E-M3를 CASE2 callback에 전달 가능 | 사건별 등록 evidence ID·내용 대조, 버튼/핸들러 이중 차단 | 활성버튼0/callback0 PASS |
| W-W2 누락 시 W-W3을 소터 투입으로 설명 | 등록 event ID의 공정 매핑, 원본 순서 유지 | 분기/출고 제목·다음 행동 PASS |
| 신규 후보를 정본 등록해도 nested 경로·tote/null로 거부 | 안전한 하위 경로, 해당 공정 tote, null 정규화 | 미등록6개 차단/메모리 명시등록6개 허용 |
| 분기 후보 그림의 계획/실적 갈래 오해 가능 | 한 대조행으로 수정·전체 재생성 | 648프레임·contact sheet·해시 재검 |

최초 브라우저 run은 43 PASS/3 FAIL이었다. 2개는 숨겨진 빈 status의 테스트 locator 오류, 1개는 실행 중 소스 변경 검출이었다. 두 번째 run은 경고2개에 단일 locator를 쓴 테스트 오류1개가 남았다. 기대값을 완화하지 않고 status 텍스트·경고 목록을 관측하도록 하네스를 수정했다. 모든 실패 출력은 `.local/pc3-tests/`에 보존했고 고정된 최종 소스로 49/49를 확인했다.

## 재현·메인에게 필요한 통합

1. 이 branch 소스와 공용 기준을 받는다. apps/web에서 `npm ci`; tests/remote/pc3에서 `npm ci`. cache/대형 의존성은 해당 PC의 D: 선호를 적용한다.
2. 기존 미디어 `python scripts/fetch_demo_media.py --upgrade-approved` 및 `--verify-only`로 3개 자산을 검증한다. 다른 파일은 강제로 덮어쓰지 않는다.
3. 루트에서 `node tests/remote/pc3/registration-review.cjs`, 해당 테스트 폴더에서 `node run.mjs`. 설치된 Chrome/Edge 또는 PC3_CHROMIUM을 사용하고 개인 브라우저 프로필은 사용하지 않는다.
4. pc1이 WmsScene을 공용 셸에 연결한다. page.tsx/LogisticsView/types/API/fixture/manifest는 이번 변경에 포함하지 않았다. build 성공은 이 연결 완료를 뜻하지 않는다.
5. 후보 Release 태그와 공개 경로를 pc1이 검토한다. 같은 event의 기존/신규 분기 영상을 둘 다 활성화하면 의도적으로 중복 차단된다. 기존 유지+후보보류 또는 명시적 하나의 활성등록 교체를 선택한다.

## 완료와 남은 한계

검증된 **컴포넌트·미디어 후보 인계본**이다. 메인의 셸/API 통합·실제 배포 URL·전체2흐름×3회·20입력·12경계·실제 사람 사용성/청취·원격 TEST 왕복은 미완료다. 현재 fixture는 원천 event의 실물 카메라/토트 연결키가 없으며 검증 범위는 합성 등록 관계다. 실제 운영 자료는 사용하지 않았다.

기준 이후 hub의 `9fd67ba` 야간 스킬·docs27을 fetch/show로 읽었으며 작업 branch를 임의 merge/rebase하지 않았다. 같은 PC의 독립 코드/브라우저 검토를 다른 물리 PC 실적으로 세지 않는다. 과금API·배포·정책거부 재시도·중앙 작업표 변경·자기 인수/이슈종결은 수행하지 않았다. 본인 watcher PID33460 하나와 기존 pc3 heartbeat를 유지한다.

활용20: 실행·실패·수정·생성 방법과 파일해시. Goal20: 실제 메인 Goal 별도, 새 Goal을 만들지 않음. 위임30: #9 사용자 결과·소유권·재현계약. 검증30: 기대/실측·반례·수정/재검. 이는 평가자료 연결이며 점수 확보 선언이 아니다.
