# 기존 P1 3건의 독립 적대 재검

2026-09-21 pc1, 독립 adversarial_system 에이전트가 최신 service/repository를 별도 TemporaryDirectory의 실제 JsonCaseRepository 두 인스턴스로 검사했습니다. NeverLive 주입, 공유 상태·유료 API 접근 없음. 이후 대기4의 별도 브라우저 재검은 reports/e2e/revision-reference-recheck.md에 있습니다.

원래 반례는 ① 낡은센터폼이 새 조치를 지우고 종결 ② 점포를 바꾸며 이전점포 근거로 이관 ③ 같은점포·제목의 다른날 문의에 과거 fixture 자동연결입니다. 이 세 반례는 아래처럼 차단됐습니다. 모든 가능한 결함이 없다는 판정은 아닙니다.

```text
BLOCK REVISION_REQUIRED 428 atomic=True
BLOCK STATE_CONFLICT 409 atomic=True
BLOCK ACTIONS_PENDING 422 atomic=True
FRESH_CLOSE closed revision=3 pendingActions=[]
BLOCK SOURCE_CONTEXT_MISMATCH 422 atomic=True
SAME_CONTEXT handed_off SYN-ST01 ['E-M1'] revision=1
DIFFERENT_DATE linked=None evidence=0 wms/tms/asOf=absent
EXPLICIT_SAME_CASE CASE-0001 evidence=3 asOf=2026-09-18T07:00:00+09:00
WRONG_REFERENCE INVALID_REFERENCE_CASE 422
REPLAY_AND_EVIDENCE analysisRevision=1 caseRevision=2 selected=['E-M1']
ISOLATED_RECHECK_COMPLETE no_network=True shared_store_touched=False
```

독립 즉석 재현은 `.venv/Scripts/python.exe -B -`로 실행했습니다. 본문 전체 스크립트를 저장하지 않았으므로 이 출력만으로 완전한 재현파일이 있다고 주장하지 않습니다. 저장된 회귀 재현은 다음 명령과 tests/test_demo_backend.py의 stale_center, stale_human_confirmation, linked_context, another_day, explicit_reference 테스트입니다.

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_demo_backend.py -v
```

독립 실행: 30 tests, 2.299초, OK. 메인 별도 `pytest tests/test_demo_backend.py tests/test_analysis_semantics.py -q`: 51 tests, 51 subtests, 5.60초 PASS. 후자는 모델 정확도 검증이 아니라 무과금 도메인·평가기·구조화 가드 검사입니다.

추가 브라우저 집중검사는 15 PASS / 4 NOT_RUN이고, 격리 서비스는14 PASS입니다. NOT_RUN은 기존 미디어/replay/케이스전환/3폭 반복이며 이전 검증과 구분합니다. 마지막 실행 내 검사 대상 SHA 일치, 화면의 낡은revision을 실제전송해409·저장보존·자동재시도없음을 확인했습니다.
