# N02-M5 메인 코드 인수 — 2026-09-22 01:05 KST

pc2 결과 `1fab3ba0d4c4fd819d38acb8b0d87c228a9b8b5a`의 신규 8파일만 검토해 main `37de103d1f69959baca9a19e0b1a9ea679c06e23`로 반영했습니다. branch 전체를 병합하지 않았습니다. 기존 M4 보정·공용 fixture·API·제품 미디어는 유지됩니다.

메인은 Git 원바이트를 새 `.local/remote-media-intake-1fab3ba-3a223f1`에 추출해 다음 인공 입력 검사만 실행했습니다.

```powershell
python -B -X utf8 -m unittest discover -s tests/media_pc2 -p test_clova_timeline.py -v
```

Python 3.14 / Windows, **82개 실행 중 81 PASS·1 SKIP**, 46.114초, exit 0. 실제 symlink 생성은 Windows 권한 부족으로 건너뛰었고 보안 설정을 변경하지 않았습니다. 인공 PCM·원본 불변·타임라인 경계·잘못된 SHA·관측 누락·기존 출력 거절 및 SHA 가드 변이 검출을 재현했습니다. 검사기/테스트 SHA256은 각각 `577031deb93695eb375c8c49db7cb96eb3588bfc0a346d78469021827233c6a5`, `4939c444589ff5d048311abe3209a1c0b80eb270c9f804db1f92b5b34c8a24ba`로 원격 실행값·메인 반영 후 바이트와 같습니다.

별도 읽기 검토자는 카드와 코드·provenance를 대조해 새 인수 차단 결함을 찾지 못했습니다. 다음 한계를 인수에 포함합니다.

- 출력 I/O 중단에는 일부 후보 파일이 남을 수 있습니다. 최종 `validation.json`의 PASS와 입력 descriptor 대조 없이 인수하지 않습니다.
- 입력 원형 불변은 전후 해시·파일 identity 관측입니다. 마지막 검사 이후의 동시 변경까지 잠그는 보장은 아닙니다.
- 실제 symlink·junction/FSCTL 공격과 공식 음질·STT·제품 재생은 이번 통과 범위가 아닙니다.

공식 전체 WAV **0/2**, 공식 관측 타임라인 **0/20**의 실제 파일 검증은 미실행입니다. 코드·인공 검사 범위만 인수하며 N02 전체·음질 승인·Release·공용 타임라인 등록·TEST를 완료 처리하지 않습니다.

pc2 제출은 #8에서 00:38:58, pc3 제출은 #9에서 00:26:29 KST에 이미 존재했습니다. 메인은 01:01 직접 댓글 원본을 대조해 확인했습니다. 같은 PC의 상주 감시와 `watch --once`가 하나의 `.mailbox_state.pc1.json`을 공유하는 구조를 확인했으며, 무출력을 새 결과 없음으로 해석했던 이전 안내를 정정합니다. 탐지 상태와 처리 완료는 별도이며 후속 카드에서 소비자별 감지 상태를 분리합니다.
