# 통화 쉼 후보의 v3 정본 적용

2026-09-21 21:34 KST · pc1/CJJ. PC2 `6a13abec2a7d2f0c52e609aeb7e07f560512950f` 결과를 수신해 **쉼 0.20초 후보를 음원/시각 정본에 적용**했습니다. 최종 부모 서비스의 새 빌드 리허설은 아직 실행하지 않았으며, 사람 청취도 0회입니다.

## 수신 근거

PC2의 21:10:13~21:12:57 실제 Edge 검사18/18은 A/B 전체 1배속 자연 종료, B8발화 구간 정지, 끝 seek의 완료 금지, 음원 전환·잠금·3폭을 포함합니다. 메인은 보고 수치만 읽지 않고 아래를 대조했습니다.

- 증거/검사기 Git blob 13개 크기·SHA **13/13**.
- 실행 대상 bfc8543의 실제 컴포넌트/CSS/fixture 등 6파일 **6/6**.
- A/B 대응 발화8개의 PCM 바이트·SHA **8/8**.
- 실제 results의 18개 판정 및 full 재생 시간/played/자연 ended, 8구간 오차, 반례 checker 코드 확인. 모바일390 화면 직접 열람.

메인 수신 스크립트 `.local/pc2-media-m2-review-01/playback_intake.py`, 결과 `playback-intake-01/intake.json`은 **27/27**입니다. 이는 독립 재생18회를 새로 실행했다는 뜻이 아닙니다. 원격 하네스는 관측용 분석 버튼을 사용했고 제품의 부모 API 호출은 하지 않았습니다.

## 실제 적용과 보존

[v3 Release](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/tag/demo-media-20260921-audio-v3)는 21:32:30 KST 발행됐습니다. GitHub 제공 digest/크기와 메인의 독립 재다운로드를 각각 **3/3** 대조했습니다. 정본 파일은 CASE-0001·CASE-0002·sorter-demo 3개이며, 오출고 음원 하나만 바뀌었습니다.

- CASE-0002: 2,388,044 B, SHA `6fe83afb8552765ab92722b838d2a0905f507551c4f98c58fa62a515033abaa0`, **49.75초 / 24kHz / 모노 PCM16 / 1,194,000샘플**.
- 삽입: 기존 frame417000에 0샘플4800개. 4~8번 발화 양끝 +0.20초; 문장·화자·원래 PCM은 유지.
- CASE-0001과 영상은 v2와 같은 바이트입니다. 새 CCTV 생산 장면을 적용한 릴리스가 아닙니다.
- 기존 CASE-0002 v2는 `.local/demo-media-backups/20260921T123324Z-rpejryo0/`에 정확한 바이트로 보존됐습니다. v2 Release도 그대로 있습니다.

`fetch_demo_media.py`의 기존 승인 원본 해시 검사·백업·미지 파일 보호를 사용했습니다. 다른 파일은 덮지 않았고 다운로드 실패를 성공으로 바꾸지 않았습니다. CASE-0002 URL에 새 SHA query를 붙여 이전 캐시/재생 상태와 구분합니다. 부모와 CallReview의 `id/channel/audioUrl` 재설정 계약은 코드로 확인했으며, 새 부모 브라우저 실행 증거는 별도입니다.

## 검증과 남은 게이트

- 설치 후 `fetch_demo_media.py --verify-only`: **3개 일치, missing0/downloaded0**.
- 업그레이드/음량 처리 테스트: **49 passed / 2 Windows skip / 16 subtests**, 2.19초.
- 실제 설치 WAV를 읽는 ASGI: version URL의 전체 SHA/크기, Range206, HEAD 길이, 없는 파일404 **4/4**.
- 적용된 8발화·transcriptTiming은 수신 manifest와 동일하며 음원 SHA도 일치합니다.
- 유료 호출·새 음성 생성0. 전사 A/B1쌍은 앞선 [독립 보고](pc2-pause-independent-review.md)에 있으며 v3 전체 라이브 재평가로 세지 않습니다.

적용 상세/입력 보존/업그레이드 저널/ASGI 결과는 `.local/pc2-media-m2-review-01/adoption-v3/`에 있습니다. 적용 및 테스트는 실제 기대값과 assertion을 사용했으며, 사람 만족도·일반 STT 정확도·배포·최종 6회 흐름 완료를 주장하지 않습니다. 새 CCTV 조사 화면과 함께 새 빌드에서 부모 음원 버전 초기화·실제 전체 재생·접수 완료 흐름을 다시 검수합니다.
# 21:57 후속 정정 — 오프라인 예시 사본

새 CCTV/알림 수정 빌드의 배포 묶음 생성에서 `SYNTHETIC_FIXTURE_COPIES_DIFFER`로 실제 차단됐습니다. 정본 `data/fixtures/cases.json`은 v3인데 `apps/web/public/cases.json`과 이전 export는 v2였습니다. 경로 비교17개는 CASE-0002 audioUrl, 후반5발화 시작/끝, transcriptTiming 메타데이터이며 다른 사건/업무 필드 차이는 없었습니다. 이전 보고의 정본/설치 ASGI 검사만으로 오프라인 예시까지 검증됐다고 확대할 수 없습니다.

이전 public 원본을 `.local/v3-public-fixture-before-20260921T1257.json`에 보존한 뒤 검증한 합성 정본으로 동기화했습니다. 정본/public/export SHA는 모두 `5edf80669f7def9d3e10ceea910086c41026ff1252fbc638b97641562f3d84f4`(23,693B)입니다. **재빌드 후 동일 묶음 검사가 통과**하여 `dist/deployment/20260921T125713151092Z-e1ef36f174f9/`를 생성했습니다. 이는 dirty source fingerprint로 고정한 로컬 묶음이며 클라우드 배포가 아닙니다. 앞으로 미디어·자막 정본을 바꿀 때 public 예시 사본도 같이 맞추고 export 이후 이 기존 엄격 검사를 통과해야 합니다.
