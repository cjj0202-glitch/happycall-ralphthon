# N04-D3 — 알림 전달 첫 Bolt: 저장 경계와 중복 방지

2026-09-22 pc4 장준호 / GitHub j324rst-svg. [배정 #10](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/10#issuecomment-5768490008), [착수 회신](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/10#issuecomment-5768501544).

## 결과와 이번 범위

런타임에 연결하지 않은 `DeliveryCoordinator` 초안과 독립 합성 테스트를 작성했습니다. 발송 후보만 전달해서는 fake 호출을 만들 수 없고, 주입된 임시 저장소에서 저장 완료된 동일 의도를 읽은 뒤에만 가짜 전송이 가능합니다. 같은 의도 재탐색은 같은 메모리 작업을 반환하며 다른 사건·논리 수신자·채널은 분리됩니다.

**실제 Teams/Kakao 전송·외부 수신은 0입니다.** `accepted/fake_transport_only`는 메모리 FakeTransport의 기록만 뜻합니다. 실제 의도·주소·키·운영 원장·런타임 프로세스를 읽거나 연결하지 않았습니다. GitHub 편지 확인·승인된 회신·브랜치 공유는 제품 발송 검증과 별도입니다.

| 기준 | 값 |
|---|---|
| 메인이 지정한 공통 코드 기준 | f043c60b357c5341e80959c748036b28d032bd18 |
| D2 설계 / 작업 전 HEAD | 535e2f218725daefcf4b447831fef07497c0d2e6 |
| 브랜치 | work/pc4-n04-tms-qa |
| 새 소유 파일 | server/notification_delivery.py, tests/test_notification_delivery.py, reports/pc4/notification-first-bolt.md |
| 검증 범위 | D01/D03/D06/D07 4개 검사군과 동일 D03의 commit 가드 제거 변이 |
| 미실행 | D15/D19 포함 나머지 27개 검사군, 영속 delivery CAS·재시작·실제 provider/계정/상세 링크/수신/브라우저 |

독립 검토자는 `296cba5…`와 `f043c60…`의 알림 관련 10개 의존 파일이 동일함을 확인했습니다. 기존 service/API·11필드 outbox·UI·빌드 목록은 수정하지 않았습니다. 작성 branch에 아직 없는 공통 notifications 모듈을 import하지 않도록 표준 라이브러리만 사용했으며, 그 기준 스키마와 식별 규칙을 명시적으로 대조했습니다.

## 병목 하나와 구현 선택

가설은 “commit 이전 dispatch와 같은 의도의 재탐색으로 거짓/중복 발송이 생기지 않는다”입니다. 첫 실험은 합성 입력과 임시 파일 source, 메모리 전달 기록으로 제한했습니다. 사용자/운영 recipient registry, worker 개통, 네트워크 adapter는 만들지 않았습니다.

1. 후보와 저장 행을 각각 11필드로 엄격 검증합니다. schemaVersion/revision의 bool 거부, 채널·역할 조합, counselor의 caseId 해시, canonical ID, timezone, 저장 revision 상한, snapshot 사건 일치, 후보와 저장 행 일치를 확인합니다. 저장소 전체를 마이그레이션하거나 의도를 생성하지 않습니다.
2. `SyntheticBinding`의 사건·역할·논리 참조·채널이 후보와 일치해야 합니다. 합성 case/binding 접두어와 immutable DTO를 사용하며, 검증 오류는 원래 입력 대신 고정 reason만 내보냅니다.
3. `CommittedCaseSource.read_committed()`는 성공한 commit의 분리된 snapshot만 반환해야 하는 **신뢰하는 주입 의존성**입니다. 후보의 committed 플래그는 사용하지 않습니다. 테스트 source는 staged 파일을 절대 읽지 않고 `os.replace` 이후 committed 파일만 읽습니다. 거짓 source를 제공해도 안전하다는 암호학적 보장은 아닙니다.
4. 저장 의도가 없으면 `not_committed/stored_intent_not_found`, 조회 예외이면 `blocked/committed_read_failed`로 호출0을 유지합니다. 조회 장애를 저장 실패의 증거로 바꾸지 않습니다.
5. 같은 coordinator 인스턴스의 lock 안에서 per-intent activeD와 queued 작업을 생성하고, activeD·작업 동일성·queued 상태를 검사한 후 fake 호출합니다. 동일 의도는 재호출해도 자동 재발송하지 않으며 이미 배정된 binding 변경은 blocked입니다.
6. FakeTransport에는 식별 해시·합성 binding·종류·역할·채널만 보냅니다. 원문·연락처·URL·인증값을 담을 본문 필드가 없습니다. accepted 기록은 복제 가능한 메모리 관찰일 뿐 원격 도달 증거가 아닙니다.

**D2 전체 DeliveryEnvelope를 구현한 결과가 아닙니다.** 메모리 lock/activeD는 같은 인스턴스 안에서만 작동합니다. 재시작·다른 프로세스·다른 인스턴스의 중복을 막지 못하며, durable unique/CAS·lease/fencing·예약 복구·공급자 대조는 이번 범위 밖입니다. D2의 이름을 사용했다는 이유로 해당 안전성을 달성했다고 보지 않습니다.

## 실제 검증 입력과 기대/실측

2026-09-22 07:49 KST, Windows / Python 3.12.14에서 주 작성자가 최종 동일 명령을 실행했습니다. **unittest 메서드 5/5 통과(0.047초), 검사군 4/31 실행**, 변이 검출은 동일 D03의 대조입니다. 각 테스트의 네트워크 trap 실측은 0이며 실제 provider 호출도 0입니다.

| 검사군 | 합성 입력 / 기대 | 실측 |
|---|---|---|
| D01 | SYN-D3-001 handoff / Teams center, commit 후 1회 fake 수락 | calls1 / records1 / accepted·fake_transport_only. 저장 bytes 불변, snapshot의 합성 raw_text sentinel은 결과·호출·기록에 없음 |
| D03 | 동일 의도의 후보만 존재 / staged만 존재 / os.replace 저장 실패: 각각 호출·작업 0 | 세 조건 모두 calls0 / records0 / not_committed·stored_intent_not_found. staged 파일은 source에서 읽지 않음 |
| D03 보조 | commit 완료 뒤 source 읽기 예외: 미저장을 단정하지 않고 차단 | calls0 / records0 / blocked·committed_read_failed. 저장 bytes 보존, 합성 오류 상세 미노출 |
| D06 | 최초 처리 후 같은 의도 3회 재탐색, 이어 binding 변경 | 같은 D 유지, 총 calls1 / records1. 변경 binding은 blocked·binding_changed, 기존 결과 보존 |
| D07 | SYN-D3-FINAL의 final Teams counselor·Kakao owner 및 SYN-D3-OTHER의 Teams center | 3개의 서로 다른 D, calls3 / records3 / 각각 accepted. owner 재탐색 후 총호출3 유지 |

위 fixture 4개의 canonical intent ID는 공통 기준과 동일한 `296cba500808147046ebc4326e44e1ffc70a8629`의 실제 `_identifier` 함수와 메모리 대조하여 **4/4 일치**했습니다. 합성 sentinel 검사는 D01/D03 보조 경계이며 D11 전체를 실행했다고 세지 않습니다.

## 변이 대조: 같은 실패 입력을 앞뒤로 비교

잘못된 대조군은 테스트 중에만 `_committed_intent`를 “후보를 그대로 반환”하도록 교체합니다. 이 변경 하나로 commit 확인을 생략하여, 실패한 저장 뒤에도 dispatch로 진입하게 만듭니다. 제품 소스 파일을 변이본으로 덮어쓰지 않습니다.

동일 `replace_failure` D03 oracle을 정상 → 가드 제거 → 원복 순서로 실행합니다. 실측은 정상 calls0/records0/not_committed → 변이 calls1/records1/accepted로 “미commit intent는 transport를 부르면 안 됨” assertion 실패 검출 → 패치 해제 후 calls0/records0/not_committed 재통과입니다. 같은 oracle에서 세 결과를 모두 assertion으로 확인했습니다. 이 실패를 검출하는 테스트가 통과했다는 것과 변이 코드가 정상이라는 것은 반대입니다.

## 독립 검토와 실제 수정

주 작성자와 다른 pc4 보조 에이전트가 고정 코드/새 모듈을 읽고 합성 메모리 반례를 수행했습니다. tests 파일도 주 작성자와 다른 보조 에이전트가 독립 임시 파일 source·식별 fixture·oracle로 작성했습니다. 두 에이전트는 원격 PC 또는 실제 사람 관찰로 세지 않습니다.

P2 지적: 기존 코드가 source 조회 예외를 `not_committed`라고 반환했습니다. 이미 commit·첫 fake 수락이 끝난 같은 I를 재조회할 때 읽기만 실패하면, 이 표현은 미저장 단정이 됩니다. 주 작성자는 상태를 `blocked/committed_read_failed`로 한 군데 수정했습니다.

독립 검토자가 수정본으로 같은 입력을 재대조한 실측은 첫 결과 accepted, 다음 조회 실패 blocked/committed_read_failed, fake 누적호출1, 기존 accepted record 보존, 원시 예외 노출 false, 네트워크0입니다. 조회 실패 차단(calls0/records0)은 D03 테스트에 보존했고, 기존 accepted 기록 보존(calls누적1)은 별도의 합성 메모리 재대조에서 확인했습니다. 실제 D15/D19 전송 결과 유실 검사로 확대하지 않습니다. 검토자는 이번 코드 경계에서 추가 차단 문제를 발견하지 못했습니다.

## 재현 명령과 증거 식별

작업 루트의 Start-HappyCall.ps1을 dot-source하면 저장소로 이동하고 도구 PATH를 준비합니다. 신규 테스트는 표준 라이브러리만 사용합니다.

```powershell
. .\Start-HappyCall.ps1
python -B -m unittest tests.test_notification_delivery -v
git diff --cached --check
```

테스트의 모든 source 파일은 TemporaryDirectory 안에서 만들고 정리합니다. 운영 `.local/cases-store.json`이나 실제 접수 원장을 사용하지 않습니다. import와 각 검사 동안 socket/DNS·urllib·http.client의 외부 진입점을 trap하고 시도 횟수를 확인합니다. 실제 provider 호출, API 서버 기동, UI 조작, 과금 호출은 없습니다.

검증한 파일 bytes의 SHA-256:

- `server/notification_delivery.py`: `b5e782b0e294a6f76d6a882b5ad1d44345e18baca10bee02f3de8b7c2320d30b`
- `tests/test_notification_delivery.py`: `397a03a4e75aefbe01323bf0d2f0b80aec6977a92a037eb4f81900f2890880ca`

이 해시는 아래 보고서 편집 이후에도 변경되지 않은 검증 대상 코드/테스트를 식별합니다. 세 파일의 최종 Git commit과 원격 SHA 대조는 #10 결과 댓글에 기록합니다.

## 인계

07:48 기준 메인 후속 댓글(5768564617)에 따라 현재 D3 결과를 보존하고 새 확장은 보류합니다. 이미 완료한 이 네 검사군과 세 파일을 인계하며, Vercel 기존 접근 여부 확인은 별도의 읽기 전용 업무로 처리합니다.

pc1은 이 세 파일과 고정 기준의 호환성을 검증해 인수합니다. 공용 런타임에 연결하지 않은 초안이라는 경계를 유지합니다. 인수 후 다음 카드 없이 D15/D19 또는 다른 27개 검사군·provider 연결을 임의로 이어가지 않습니다. 09:00 이후에는 새 구현을 시작하지 않고 현재 결과·미달을 인계합니다.

원본 로그·키·실제 연락처는 게시하지 않습니다. 원격 branch SHA와 결과 회신은 #10에 별도 기록하며, push 성공을 메인 수신/인수 완료로 주장하지 않습니다. TEST 왕복·최신 전체 흐름 6회·실제 메시지 수신·N04 전체 완료는 별도입니다. 배정→작동 초안→양성/실패 대조→변이 검출→독립 지적→같은 입력 재검 기록을 남기되 득점·공식 제출·새 Goal 실행을 선언하지 않습니다.
