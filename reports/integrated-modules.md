# 원격 3개 모듈 실제 셸 통합 검증

2026-09-21 pc1/CJJ. 기준 cc6c6d1, pc2 ef8f33e·pc3 d6aa6b3·pc4 1b82f1d의 컴포넌트를 명시 경로로 가져왔습니다. 최초 입력7파일은 Git blob과 SHA256 7/7 일치했습니다. 상세계약은 planning/integration-remote-modules.md입니다.

## 기능 단계 결과

`npm run typecheck` exit0 후 `python scripts/build_deployment_bundle.py --build`로 20:03:12 KST production export를 완료했습니다. source `7e76d4b0d5c84e80d5c6c6ab24c638d37b82ea4073b39d3032d0b3684f3894cc`, output `f6c1841bf603019f79494544477293eae1155178b74a6488ace20241f357141e`, 출력26파일입니다.

새 셸은 현재 intake와 reviewConfirmed를 함께 넘기고, 분석오류/저장오류를 구분하며, 사례·채널·음원별 실제 전체재생 완료 전에는 replay/live 분석을 모두 막습니다. WMS/TMS callback은 현재revision을 실제PATCH하여 성공한 뒤에만 resolve합니다. 결과 출처가 없는 분석을 replay로 추정하지 않습니다.

실행 정본: [새빌드 리허설](e2e/rehearsal-2026-09-21T11-04-35-056Z/results.json).

- 미도착3회+오출고3회 **6/6 PASS**, 실제 WAV 1배속 전체47.15/49.55초 각각3회, seek-ended replay/live차단6회.
- 새 WMS/TMS 실제근거저장→수정·확인→센터중간/최종회신→경영주재조회. 오출고 W-W3의 등록영상 해시검증 및12초재생3회.
- 별도 수동 텍스트접수2/2, 오프라인안전열람1/1. **오프라인 전체저장은0/1 BLOCKED**이며 완료로 세지 않습니다.
- HTTP200 46건/201 2건, 의도409 2건/422 24건. pageerror0·외부/유료호출0. 실행전후프런트변경false·백엔드변경0.
- runner 집계게이트8/8, 실제음성증거 대조14/14(정상/경계2·거부12). 기존API8100/3100조작0. 새격리상태는 보존하고 runner서버11440종료·8821~8824 LISTEN0확인.

## 메인의 별도 저장·분석 실패 대조

동일빌드의 별도8832 격리저장소에서 실제브라우저를 실행했습니다. 결과는 `.local/integration-safety-first.json`, `.local/integration-evidence-first.json`, `.local/integration-evidence-safety.json`입니다.

- 초기/seek-ended 음성게이트 disabled·API쓰기0, 자연1배속47.31초(played0–47.15) 뒤분석허용.
- 분석503를 주입해 현재입력보존·재시도허용. 실제replay재시도후 입력수정→상담원확인표시해제 확인.
- TMS저장503→거짓연결0·서버revision불변, 재시도actualPATCH revision1→2 E-M1추가.
- WMS저장503→거짓연결0·서버revision불변, 재시도actualPATCH revision2→3 E-M3추가. 상담복귀후표시근거2건.
- 외부요청0·pageerror0. 최초일회성하네스는 Playwright import경로, 중복TMS버튼선택자, WMS버튼명 오타로 실패했습니다. 이미통과한검사를재분류하지않고 실패원문보존후 각미도달부분을 실제locator로 재검사했습니다. 제품오류로 세거나실패를삭제하지 않았습니다.

## 인수 보류와 다음 작은 수정

독립실제UI검수에서 분석버튼이1440/1024/390폭의 y2748/2986/5051에 나타났고, 재생시작과각1787/1985/3902px 떨어졌습니다. 모바일접수편집시작5198px, 문서높이6701px입니다. **기능통과와별개로 작업동선 P1 후보를 수정한 뒤 새빌드에서 재검사합니다.** 현재상태를 고품질UI·최종N02~N04인수·최종배포 완료로 표시하지 않습니다.

실제한국어사람청취, 모델의미정확도, 운영WMS/TMS접속, Vercel영속저장,최종Production은 이검사의 범위밖입니다. 새Blender생산장면과음질후보는 별도작업입니다.
