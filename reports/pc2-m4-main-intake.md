# N02-M4 미디어 전달·응답 메인 인수

2026-09-21 23:54 KST · pc1/CJJ · 원격 ceec704755c3558be03be72938b6cb369bbb1d3b

MP4에 등록된 좌표 파일만 다운로드·export·배포 묶음·인증된 응답으로 전달하는 코드를 통합했습니다. 원격 PC에서 실행하지 못한 ASGI를 메인의 기존 환경에서 실제 실행하다 Windows 파일 검증 결함을 발견해 수정했습니다. 이번 인수는 전달 코드와 합성 검사 범위이며 새 최종영상 등록·실행서버 교체·최종배포는 아닙니다.

## 선별 반영

기준 main663bbe5와 현재main의 소유7파일 내용이 같음을 확인하고, 원격7제품/테스트+10보고서=17파일을 Git blob 원바이트로 반영했습니다. 전체브랜치 merge/원커밋 cherry-pick은 하지 않았습니다. 원커밋 부모 기준 patch는3파일 충돌했고663→ceec 차이는 apply-check를 통과했습니다. 상세는 `pc2-m4-main-code-review.md`입니다.

인수 중 deployment_app.py/test_deployment_app.py/test_deployment_bundle.py 3파일을 보정했습니다. 따라서 최종17파일 중14개만 원격원바이트이며 이3개는 메인 보정본입니다. 원격보고서10개의 과거 NOT_RUN 기록은 수정하지 않고 아래 메인 실측과 구분합니다.

## 실제 실패와 수정

1. 최초 ASGI23개는14PASS/9ERROR였습니다. 이후3모듈 pytest는8FAIL/155PASS/2SKIP/86ERROR,116.80초였습니다. 다수 초기화 실패는 실제 파일의 path stat/handle fstat 사이 ctime 의미가 달라 같은파일을 변경으로 오인한 것입니다. `pc2-m4-windows-snapshot-repair.md`에 실제값과 결정적 재현을 보존했습니다.
2. 파일 식별·크기·mtime·링크수·birthtime 네 관측 비교와 각 제공자별 ctime 전후 비교를 유지하도록 최소 보정했습니다. 독립 검토에서도 실제3파일×10회가 원본0/30반환→수정30/30원바이트 반환으로 바뀌었고, 공통필드18반례/ctime2반례/디렉터리·초과크기·경로재검 실패가 거부됐습니다. 링크/해시/불변응답 AST는 원격과 동일합니다.
3. 기존 bundle의 해시 가드 제거 변이검사는 길이가 달라 앞선 크기 가드에서 막혀 해시 가드 검출을 증명하지 못했습니다. 반례를 동일 길이 한바이트 변경으로 바꾸자 원본은 거부하고 해시 가드를 제거한 변이는 잘못 허용해 검출됐습니다. 제품 가드를 느슨하게 만들지 않았습니다.
4. 최종3모듈에는 isolated child Python stderr의 인코딩 보조스레드 경고가 남았습니다. 경고를 오류로 승격한 단독검사로 실제 실패를 재현했습니다. `-I`가 PYTHONUTF8 환경값을 무시하므로 테스트 자식에 `-X utf8`와 reader `encoding=utf-8`을 명시했습니다. 같은 단독검사는 경고를 오류로 둔 상태에서1/1PASS가 됐습니다. stderr를 버리거나 decode errors를 무시하지 않았습니다.

## 검증 분모

| 실행 | 결과 | 범위/한계 |
|---|---|---|
| 인수 전 고립 fetch/bundle |34PASS/1SKIP| 원격 코드, 기존 main 환경; 실제 다운로드 없음 |
| 보정 후 ASGITransport |23/23PASS,1.539초| 등록JSON GET/HEAD, MP4 Range, 같은영상결합, 누락/변조/링크, 불변바이트, 인증·API 보존; 서버포트 없음 |
| Windows 결정적 회귀 |16/16PASS| 원수정 전1FAIL/13PASS; ctime 가드제거 변이2 포함 |
| 배포앱 모듈 |155PASS/3SKIP| 전체158,9.98초 |
| 메인3모듈 pytest 재실행 |263PASS/4SKIP/0FAIL/0ERROR,111.55초| 총267.6 warnings 중1개가 뒤에서 수정한 자식stderr 인코딩 경고,5개는 기존 의존성 deprecation |
| bundle 기존4가드 변이 단독 |1테스트PASS,11.88초| 각4변이를 실제 검출 |
| isolated runtime 엄격 재검 |1/1PASS,9.06초| `-W error::pytest.PytestUnhandledThreadExceptionWarning`; 인코딩 보정 후 별도 실행 |

3모듈 재현: `.venv/Scripts/python.exe -B -X utf8 -m pytest tests/test_demo_media_upgrade.py tests/test_deployment_bundle.py tests/test_deployment_app.py -q`.

원시 초기/후속 출력은 `.local/pc2-m4-main-intake/pytest-initial.log`, `pytest-final.log`, `pytest-runtime-utf8-recheck.log`에 있습니다. 마지막 파일은 인코딩 수정 전 엄격검사의 실패 원문이며 최종PASS 로그로 바꿔 쓰지 않습니다. 최종 엄격PASS는 도구 실행 결과에 남았습니다. 건너뜀4개는 실제 Windows symlink 생성 권한 제한이며 통과가 아닙니다. 신규 검사의 Unix형 관측은 메모리주입이며 Unix호스트 실행이 아닙니다.

## 제품 연결과 남은 범위

- 현재 제품 manifest는 v3이며 최종 tracks 미등록입니다. 코드 인수만으로 새 좌표 파일이나1080p영상이 사용자에게 제공되지는 않습니다.
- 같은 영상의 원본 tracks는 이미 프런트 본문 계약과 맞으며 변환기를 새로 만들 필요가 없습니다. 완주 이후 MP4 해시/sidecar 해시·크기 등록이 필요합니다.
- 새 빌드/묶음은 별도 보고서에 기록합니다. 실행중 API8100·Next3100·Blender PID13052는 재시작하지 않았습니다. 새 서버·설치·키·외부API·Release/배포 작업0회입니다.
- 기존 API 재시작 자동승인 검토 거부와 저장소 연결 부족은 미해결입니다. 로컬 ASGI 통과를 원격 저장·완전한 업무흐름·배포 완료로 확대하지 않습니다.
