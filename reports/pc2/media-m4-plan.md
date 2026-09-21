# N02-M4: 합성 CCTV와 좌표 파일 전달 설계

2026-09-21 22:39 KST, pc2/안영일/MR-A83. [배정](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/8#issuecomment-5761400803)은 고정 main `663bbe5bb0ae0a780e328dce9a69188112de8d0e`의 다운로드·배포 묶음·정적 전달 확장이다. 시작 브랜치 HEAD는 `f0f9d2ae1410a84f23fbcd5540c2645f4a94099b`다.

- 사용자 행동: 검증된 CCTV를 보는 사용자가 같은 영상에 묶인 좌표를 받는다. 미등록 JSON이나 다른 영상의 좌표를 받지 않는다.
- 상태: 기존3개만 등록/선택 tracks 등록/누락·변조/원본 업그레이드/부분 실패를 분리한다. 등록됐지만 준비되지 않은 파일은 성공으로 숨기지 않는다.
- 계약: 정본 MP4의 정확한 tracks descriptor만 신뢰한다. 공통 순수 validator가 고정 경로·schema·최대10MB·SHA·부모 영상 결합을 대조한다. case descriptor는 권한을 주지 않는다.
- 구현: fetch 담당은 원본 증명·백업·선택 다운로드, 정적 서버 담당은 기존 생성자 호환·정본 로드·정확한 한 경로, 총괄은 공통 계약·public/out/패키지 전달과 통합 검증을 맡는다. 같은 노트북 안 파일 소유를 분리한다.

기존 브랜치와 main의 merge 예측에는 CallReview 두 파일의 add/add 충돌이 있다. 무조건 합치지 않고 이번 소유 파일 중 차이가 있는 fetch/build/test_bundle 세 파일만 고정 main 원본에 맞췄다. 이들 외의 제품·정본 manifest·fixture·자산은 보존한다. 결과는 main 기준 차이도 별도로 대조하며 메인이 소유 파일만 인수할 수 있게 한다.

검증: 정상3개와 정상3개+sidecar 전달, schema/양수정수/상한/SHA/영상결합/미등록·추가JSON/누락/경로이탈·링크, MP4 source 증명·백업·부분 실패를 합성 바이트로 검사한다. ASGITransport는 소켓을 열지 않는다. 원본·public/out/패키지 bytes/SHA를 비교한다.

현재 Python에 pytest가 없음을 확인했다. 이번 카드의 설치 금지에 따라 설치하지 않는다. 표준 unittest와 기존 httpx/connexion 의존성으로 새 합성 검사를 실제 실행하며, 기존 pytest 전체 실행 여부는 구분한다. 실제 다운로드·새 미디어 등록·Release·배포·브라우저·서버·소켓·과금·키 읽기는0으로 유지한다.

첫 작은 결과 목표22:59, 코드 인계 목표23:19 KST(수신 후20/40분). 실제 결과와 실패·수정은 별도 기록한다. 메인의 기존 정책 거부나 로컬 상태 파일 갱신 거부를 우회하지 않는다. 이번 산출물은 새 카드 소유 경로의 독립 코드·검증 증거다.
