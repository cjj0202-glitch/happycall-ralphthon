# N03-M5 — 전체 CCTV 결과를 제품 연결 전에 검사

2026-09-21 pc1 배정. N03-M4 소스 검토와 실제 첫 프레임 진입을 확인한 뒤의 후속 카드입니다. 전체 렌더는 pc1에서 진행 중이며 이번 카드가 최종 영상 인수를 뜻하지 않습니다.

| 배정 항목 | 계약 |
|---|---|
| 사용자 결과 | 완주한1080p CCTV와 같은 시간축의 좌표만 제품에 연결할 수 있도록, 렌더 출력의 누락·변조·다른 버전 혼입을 실행 가능한 검사로 발견 |
| 담당·소유 | pc3 / LAPTOP-U2AL73UH / mcjun86-oss. 신규 `scripts/media_pc3/verify_full_animation.py`, `scripts/media_pc3/test_full_animation_package.py`, `reports/pc3/full-output-*`만 편집. 기존 검사기는 읽기 전용으로 재사용 가능. 타인 변경을 되돌리지 않음 |
| 기준·입력 | pc3 소스 `a39cd664758575a81e1fcce437db245f60fc2c1b`, 공유 main `7dedb4ab009ba9f2892b3f95d0caa0e3022dd873`. 기존 `verify_render_package.py`는720p/72장 계약이므로 그대로 적용하지 않음 |
| 기대값 | EEVEE96/shadow4/FIXED2, 1920×1080 100%,24fps,프레임1..288,검수 receipt와 소스·layout·fixture 해시 일치. 현재 generator가 출력하는 실제 schema/필드명을 먼저 읽어 사용 |
| 검증 | 인공 정상 묶음,1장누락/프레임중복/바이트변조/다른해상도/이전72장보고서/다른입력해시/좌표누락·범위위반/링크·경로이탈/실제readback불일치. 핵심가드 제거 변이 최소1개. 정상과 반례를 모두 발화 확인 |
| 인계 | 기존 #9에 ACK·20~40분 내 첫 결과·최종SHA·소유경로·재현명령·실측분모·미실행을 회신. 메인 실제288장 대조와 화면 연결이 남음 |

검사 입력은 완주한 animation 폴더와 메인이 별도로 고정한 expected manifest 경로입니다. expected manifest에는 실제 생성기6개·layout·fixture·receipt의 바이트/해시와 위 설정을 담습니다. 검사할 보고서가 자신의 기대해시를 정하지 않습니다. 기대 파일 양식과 명령을 예시로 남기되 pc3가 실제 검수 승인이나 실제 결과해시를 만들지 않습니다.

실제 PNG288개의 이름·크기·SHA·PNG 구조/CRC/해상도, report의288개 순번/시간((frame-1)/24), tracks288행과 전체 frameCount/fps/resolution/사건 앵커/정규화좌표, blend 및 tracks 파일 해시, sourceDependencies5개와 fixture/receipt/sceneReadback을 대조하세요. 기존 안전한 파일 읽기 함수를 사용해도 되지만720p 상수를 바꾸거나 old checker를 느슨하게 만들지 않습니다. 쓰기·렌더·인코딩 없이 읽고 결과JSON을 출력하는 작은 도구로 만드세요. 픽셀 디코딩·시각품질·MP4 인코딩 검사는 pc1 후속이며 구조검사를 그 완료로 표현하지 않습니다.

전체 렌더 입력·소스는 이미 고정됐습니다. 생성기·장면·카메라·동작·fixture·제품manifest·Release·frontend를 수정하지 않습니다. 실제 Blender 실행·설치·외부API·브라우저·서버·다운로드·배포·키 접근이 없는 코드/인공fixture 검사 카드입니다. N03-M4 실제 renderer를 재실행하거나 새로운288프레임 작업을 시작하지 마세요. 권한 차단은 우회하지 말고 보고합니다.
