# 해피콜 OneFlow 5분 발표 초안

[PDF 5장](happycall-five-minute-draft.pdf) · [300초 구성](storyboard.md) · [발표 대본·조작 순서](speaker-script.md) · [장별 증거](evidence-map.md) · [장애 복구 계획](failure-recovery.md)

문서 기준 main e1ef36f, pc4 증거 d784171. 최신 제품 전체 실행을 의미하지 않습니다. 음성/텍스트 인입, 사람 확인, WMS/TMS, 센터 회신과 경영주 조회를 설명합니다. 두 Bolt와 실제 Goal, 검사기 실패·수정·재검증을 연결했습니다.

**300초는 시간 배분 계획입니다. 사람 낭독·실제 제품 조작 리허설은 NOT_RUN입니다.** 발표 전 pc1이 사용할 최종 빌드/미디어와 상태를 확인하고 리허설해야 합니다. 본 카드에서는 새 서버·브라우저·설치·제품 테스트·유료 API 실행을 하지 않았습니다.

PDF는499,964바이트(약0.48MiB)이며 최대5페이지·90MiB 조건 안입니다. 설치된 ReportLab과 맑은 고딕, Poppler로 생성·렌더했습니다. 한글 폰트 내장과 ToUnicode, 58개 텍스트 영역·3개 화면 발췌의 겹침/페이지 경계, 5장 시각 검토를 확인했습니다. 실제 PNG 원본은 그대로 두고 PDF 표시 범위만 pdf-layout.json에 기록했습니다. `rendered/`는 발표자료 검수용이며 새 제품 캡처가 아닙니다.

남은 한계는 자료에 큰 본문으로 표시했습니다: 성공 토스트 잔류 P2, 요청 과잉 철회 P2, 오프라인 전체 처리0/1 BLOCKED, 원격 영속 저장 미연결·최종 배포 미완료, 수정 CCTV 브라우저 미실행, 새v3 부모 흐름 및 사람 검증 미확인. 공식 제출·외부 메시지는 수행하지 않았습니다.

재생성은 설치된 Python의 reportlab/pypdf/Pillow와 C:/Windows/Fonts/malgun.ttf·malgunbd.ttf를 사용하여 `build_pdf.py`를 실행합니다. 예시는 이 PC 기준이며 별도 설치를 수행하는 스크립트가 아닙니다. 재렌더는 기존 Poppler의 `pdftoppm -scale-to 1600 -png happycall-five-minute-draft.pdf rendered/page`입니다. 원본19문서/3이미지 해시는 input-manifest.json과 assets/manifest.json, PDF/레이아웃/폰트 검수는 qa.json과 pdf-layout.json에 있습니다.
