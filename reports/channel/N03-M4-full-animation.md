# N03-M4 / P1 — 검수한 물류 장면의 전체12초 렌더 지원

## 결론
pc3 정준화 / LAPTOP-U2AL73UH / mcjun86-oss는 검수된 장면을 전체288프레임으로 만드는 실행 경로를 구현합니다. pc1이 실제 렌더를 실행합니다. 이번 카드는 원격 PC에 새 렌더 설치나 정책 차단 작업을 넘기는 것이 아닙니다.

## 왜 지금
기준 생성기 `33fa0e4edeb88c0d4ad5e9cc0194ffc7e96cebcd`, pc3 수신검사 결과 `c7fd1c06a4bd167d7d02fc1b3c9869193eec76d2`, 공유 main `1d517cb0e95d62adc74123e842784b0a36c9787d`입니다. 저장소는 `D:/hwana/Work/happycall-ralphthon`입니다. N03-M3 실제 수신 결과를 받았고 독립 대조 중입니다. 이 카드에서는 그 완료 주장을 대신하지 않습니다.

메인에서 동일 장면의 720p72장 및 1080p 대표1/133/288을 실제 렌더·열람했습니다. 1080p 대표3장은131.391초, frame당38.676~43.006초입니다. 전체288장은 약186~206분 추정으로 실행 시간이 필요하므로 후속 코드 작업을 시작합니다. 보고서 `reports/media/pc3-1080p-representative-review.md`를 공유합니다. 합성 CG 후보의 제작 승인이지 실사·최종제품 품질 인수는 아닙니다.

## 해줘야 할 일
소유는 `scripts/media_pc3/build_scene.py`, 신규 `scripts/media_pc3/full_render_gate.py`, `scripts/media_pc3/test_full_render_gate.py`, 기존 look/environment CLI 가드 테스트의 해당 부분, `reports/pc3/full-render-*`입니다. 다른 작업자가 있으므로 타인 변경을 되돌리지 마세요. 기하·재질·빛·카메라·동작·tracks 수식은 바꾸지 않습니다.

현재 nonbaseline look/environment의 animation 금지 기본값은 보존하되, 메인이 발급한 실제 검토 receipt 파일과 기대 SHA를 명시하면 검수한 조합만 animation을 허용하세요. `--animation-review`와 `--animation-review-sha256`를 함께 요구하고 임의 approved=true만으로 통과시키지 않습니다.

receipt에는 현재 생성기/의존파일/layout/fixture 바이트·SHA, camera=cctv, resolution=[1920,1080], engine=eevee,samples=96,shadowRays=4,look=contrast_material_v1,environmentDetail=staging_v1,threads=2,fps=24,frames=288, 검토한 대표3PNG와72장 report의 실제 바이트·SHA 및 역할을 넣습니다. 경로는 receipt 부모 기준 상대경로로 한정하고 경로이탈/링크/중복을 거부합니다. 메인이 새 코드 diff와 증거를 확인한 뒤 실제 receipt와 기대 SHA를 발급하므로 pc3가 인수 true receipt를 발급하지 않습니다. 테스트용 receipt는 명백한 인공 fixture로 구분합니다.

receipt 내용과 실행 입력/소스/검토 증거 파일을 실제 읽어 대조한 뒤, 기존 output mkdir/render 전에 검증합니다. 실제 build 후 첫 렌더 전에 scene readback으로 해상도100%·고정카메라·EEVEE96·shadow4·FIXED2가 일치하는지도 확인하세요. overview animation 금지는 계속 유지합니다. 대표/short/기존baseline 경로는 기존 계약을 보존합니다.

렌더 보고서에 fixture digest, 실제 threads/readback, 검토 receipt digest를 추가해 후속 검사에서 요청값과 실측을 구분할 수 있게 합니다. 최초 설계에 사용자 결과·UX(메인 실행)·계약·반례를 짧게 기록하고 코드로 진행하세요. 1080p 새 렌더나 긴 실험은 pc1만 수행합니다.

## 실행 명령
본인 저장소 whoami·Git 상태·기준SHA 확인 후 기존 브랜치를 사용합니다. 순수 Python 테스트에서 CLI/receipt/readback stub을 검증하고 실제 Blender 실행으로 표현하지 않습니다. 명시 소유 파일만 커밋·push하여 원격 SHA를 대조합니다.

## 검증 방법 + 기대값
정상 완전한 인공 receipt 하나는 허용해야 합니다. receipt없음/기대SHA불일치/파일변조/입력변경/필수파일누락/설정변경/경로이탈·symlink/다른카메라/실제readback불일치는 첫 렌더 전에 거부해야 합니다. 과거 대표·short와baseline 회귀를 보존하고 핵심가드를 무력화한 변이 하나가 실제 잡히는지 확인합니다. 첫 결과20분·완성코드40분 목표입니다.

## 중단 조건 + 인계
문서 수를 늘리기보다 전체 영상을 만들 수 있는 최소 실행 코드를 제출하세요. 원천자료·키·유료호출·설치·서버·브라우저·제품manifest·실제최종receipt·Release 변경은 없습니다. 권한거부/파일소유충돌은 중단하고 회신합니다. #9에 ACK와 새SHA·파일목록·테스트실측·변이·한계·메인receipt 작성 예시를 보내세요. full288/최종UI등록/N03완료는 실행 후 별도입니다.
