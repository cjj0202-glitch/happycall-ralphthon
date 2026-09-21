# 빠른 통화 재생을 포함한 생산 묶음

2026-09-22 · pc1/CJJ · 고정 소스 `7b50ca3d408c2cc835f3fb53e65e33ff6fcc6d02`

03:41 생산 빌드와 새 묶음 생성은 각각1회 완료됐습니다. 이어진 로컬 래퍼의 마지막 미디어 검사는 manifest 구조를 잘못 가정해 **exit1**로 종료했습니다. 원본 실패를 보존했고 빌드·패키징을 반복하지 않았습니다. 실제 계약으로 생성물을 다시 읽은 메인 검사는 출력27/27·payload60/60·미디어16/16 일치를 확인했습니다. 외부 배포를 실행한 것은 아닙니다.

묶음: `C:/00.프로젝트/happycall-ralphthon/dist/deployment/20260921T184155433551Z-7b50ca3d408c`

## 실행·실패·재검 구분

실행 명령은 `.venv/Scripts/python.exe -B -X utf8 .local/playback-production-20260922.py 7b50ca3d408c2cc835f3fb53e65e33ff6fcc6d02`입니다. 이 ignored 로컬 래퍼는 기존 `scripts.build_deployment_bundle.run_build`와 `build_bundle`를 각각1회 호출합니다. 현재 builder는22,599B/SHA256 `1bd8704e87bb17158990a0fd937232f96341727075b7a1cdea5df8b803d092b7`이며 변경하지 않았습니다. 래퍼13,632B/SHA256 `c9d86323f48b75c38571505b6c0e35c707c50e20b138a7dfd8337d560cc42b74`도 실패 이후 수정하지 않았습니다.

| 실행 직전 KST | 단계 | 가용 물리 RAM bytes | 최소 bytes | 결과 |
|---|---|---:|---:|---|
|03:41:37.483001|run_build|2,690,256,896|1,610,612,736|함수 반환·완료 stamp 생성|
|03:41:55.433551|build_bundle|3,141,070,848|1,610,612,736|새 폴더·complete marker 생성|

빌드17.750초, 묶음2.156초입니다. SOURCE_FILES·TEMPLATES·FRONTEND_DATA_FILES·apps/web(추적 next-env 포함)·builder62파일을 고정 Git과 대조했습니다. 세 시점(전/빌드 후/묶음 후) 모두 Git 변경0·미추적0, raw54/62·LF정규화62/62 일치입니다. source fingerprint와62파일 raw inventory 지문도 세 시점 동일합니다. 기존 `.next-dev`·실행 API·상담 자료·예산 원장·키·이전 묶음은 변경하지 않았습니다.

실패 코드는 `FIXED_MANIFEST_FOUR_MEDIA_REQUIRED`입니다. 래퍼가 top-level `assets`에4파일을 기대했지만 정본은 음원2+영상1의3개와 MP4 아래 `tracks` descriptor입니다. `server/media_contract.py`의 `validate_media_manifest(..., require_synthetic=True)`가 이를 실물4파일로 확장합니다. 정본을 고치거나 검사를 생략하지 않고 실제 계약으로 별도 읽기 검사를 수행했습니다. 잘못된 래퍼는 향후 그대로 재사용하지 않습니다.

- 실패 원본: `.local/playback-production-20260921T184134498901Z-7b50ca3d408c.json` (`stopped-not-complete` 유지)
- 생성물 재검: `.local/playback-production-readback-20260922-0343.json` (exit0, 새 빌드0·새 묶음0)

## 생성물 실측

| 항목 | 실측 |
|---|---|
|정적 출력|27파일 / 6,881,209 bytes; JS16·CSS2|
|묶음 payload|60파일 / 12,954,926 bytes|
|marker 포함 전체|61파일 / 12,963,673 bytes|
|marker|8,747B / `e77e1ea06e2a365a07cc21ec8e307423f547bba178b20424c57608b72aae471b`|
|실제 payload inventory SHA|`99218426a652edafafbe08f32916df5501a846c8ab4541d7c47be78e5c77058e`|
|frontend source fingerprint|`60a39e97b6038c936bf1de701312d60e0c954bc9c2a50b7089f304d12ba681a0`|
|정적 출력 fingerprint|`d678c84ec72dc67cb3e4d5872a9b0da7c3dea1d4a76a42827e7da4191c788fe1`|
|완료 기록 digest|`aa7be5c88afd66e275184658f72d58bdd06fe77b731f1003594ede3dba56e9ab`|

메인은 실제 파일을 다시 읽어 marker의 경로·bytes·SHA·총량60개, out과 bundle-out27개, stamp의 recordDigest와 source/output 지문을 대조했습니다. 공용 미디어 계약으로4종을 펼쳐 public/out/bundle-public/bundle-out의16사본을 고정 Git manifest와 대조했습니다. WAV 원본·1080p 영상·tracks는 v4와 그대로입니다. runtime/template29사본은 현재 소스와29/29, 고정 Git은 raw28/29·LF정규화29/29입니다(data/fixtures/cases.json 줄바꿈 차이).

## 독립 검토와 한계

별도 읽기 전용 검토자가 builder를 import/실행하지 않고 정적 AST와 실제 파일로 대조했습니다. frontend35파일의 지문, Git62파일(raw54/LF62), 출력27/27, payload60/60, 소스 사본29/29와 미디어16/16이 일치했습니다. 실제 생성 JS `page-45b66b6648186293.js`에도 기본1.25와 playbackRate/onPlaybackRateChange 전달이 포함됐습니다. source/marker/생성물 결함은 재현하지 못했고, top-level4개를 기대한 로컬 래퍼 오류로 판정했습니다.

양성 대조 뒤 출력 count27→28 및 recordDigest 재서명, payload totalBytes+1의 메모리 변이2개를 각각 검출했습니다. 독립 검사기 첫 실행의 AST 명칭 참조 해석·Git raw 줄바꿈 기대도 보정해 최종 exit0(`de38c7`)을 확인했습니다. 이 보정은 제품·builder·artifact 수정이 아닙니다. 새 빌드·묶음·서버·브라우저·API 호출은0입니다.

이 범위의 로컬 생성물을 인수합니다. 전체 제어 흐름의 브라우저 재실행·음성 사람 청취·CLOVA 공식 파일·원격 영속 저장·최신 API 가동·외부 HTTPS·배포·공식 제출은 이 로컬 산출물로 완료 처리하지 않습니다.
