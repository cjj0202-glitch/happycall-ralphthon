# N02-M2 첫 결과: 확인 상태 재현과 쉼 A/B 후보

2026-09-21 pc2 / 안영일 / MR-A83. 실제 배정은 [#8의 19:48 카드](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/8#issuecomment-5759286540), 기준 main e5469aa, 이번에 읽은 최신 main cc6c6d1이다. branch `work/pc2-n02-call-review`에서 최초 결과7ae648e와 문서 수정ef8f33e를 보존했다. 이번 첫 검토 목표는20:20, 최종 통합 후보 목표는22:00이며 공식9/22 12:00 마감·09:00 메인 인계와 구분한다.

**확인 상태 수정은 실제 React SSR로 재현·대조했고, 단위 정정 앞의 쉼만0.20초 늘린 후보1개를 만들었다.** 기술 기준은 통과했으나 사람이 더 잘 이해했는지는 아직 모른다. 기존 v2를 정본으로 유지한다.

## 설계와 작은 실험

- 사용자 과업: 상담원의 잘못된1EA 요약 뒤 경영주가1BOX로 정정하는 것을 구분한다. 주문18EA와 수령1BOX, 점포 미확인은 그대로 보존한다.
- UX 가설: 정정 발화 직전 화자 전환의 쉼을0.35→0.55초로 늘리면 차이를 알아듣기 쉬울 수 있다. 체감 개선은 사람이 듣기 전 확정하지 않는다.
- 계약: gain0dB, speed1.0, 모든 원본 PCM 샘플을 같은 순서로 보존한다. 분석 원문·대본·STT·현재 폼·AI 제안은 변경하지 않는다.
- 검증: 먼저 실제 경계가 무음인지 검사하고 한 번의 삽입만 허용한다. 작성된 WAV를 다시 읽어 원본 복원·타이밍·LUFS/peak·클리핑과 실패 입력 차단을 확인한다.

발화별 캐시는 이 PC에 없지만, 정본 전체 WAV17.20–17.55초의8,400샘플이 모두0임을 확인했다. 새로운 지시가 허용한 이 한 곳의 무음 삽입은 캐시 없이 가능하다. 발화 재합성·분리 재조합에는 이전에 요청한 캐시/metadata가 여전히 필요하다.

**입력 수신 갱신:** 메인의20:02 전달 댓글 이후 `demo-voice-sources-20260921` ZIP/manifest를 내려받아2/2 크기·SHA를 대조했다. ZIP의16/16 발화 PCM 실제 길이·해시와 v1 두 통화 재조립 바이트2/2가 일치했다. `python scripts/media_pc2/verify_source_package.py` 및 `audio-m2/source-receipt.json`에 증거가 있다. 스트리밍 헤더의 거대 프레임 수를 실제 길이로 쓰지 않았고 생성기는 재실행하지 않았다. 위 캐시 미보유는 최초 편집 당시 상태이며 이후 입력 의존성은 해소됐다. 이번 후보는 이미 승인 v2 전체 WAV로 만든 결과를 유지한다.

## P1 확인 상태: 실패와 수정 대조

`node tests/remote/pc2/confirmation-ssr.mjs`를19:59 KST에 실행했다. 실제 CallReview TSX를 메모리에서 컴파일해 React19.1.4의 renderToStaticMarkup으로 렌더한다. 현재 page의 field 콜백을 추출·실행하고 이전/수정 문서의 실제 reviewCase 표현식을 사용한다.

| 입력 | 기대 | 실측 |
|---|---|---|
| 기존7ae 예시: 저장6/true→편집999/부모false | 기존 결함 재현 |999와 확인완료 문구1개 동시 표시 |
| 수정 예시: 저장true/현재false | 확인완료0 |0 |
| 수정 예시: 저장false/현재true | 확인완료1 |1 |
| 수정 예시: false/false, true/true | 각각0,1 |각각0,1 |
| 현재 확인 prop을 다시 제거한 변이 | 오래된 표시 결함 검출 |문구1, 반례 검출 |
| 실행 전후 입력 SHA | 불변 |4파일 불변 |

7/7 확인 통과. 수량999·기존EA·원문·대화록을 보존했다. 결과는 `confirmation-ssr.json`. 이것은 실제 React **SSR 출력**이며 사용자 클릭·hydration·공용 부모 페이지 연결·저장/API 검증이 아니다. CSS 이름만 로컬 대체했고 제품 동작 함수는 복사하지 않았다. 실제 부모 통합과 브라우저 회귀는 메인 인수 항목이다.

## 후보와 기술 결과

기존 v2 CASE-0002의17.375초(417,000번째 프레임)에0.20초(4,800프레임)의0만 삽입했다. 삽입점 양옆25ms가0이 아니면 도구가 거부한다. A/B 발췌는 원본12.25–29.95초를 같은 내용으로 비교하며 B에만 그 쉼이 추가된다.

| 파일 | 길이 | 실측 LUFS | true peak | 디지털 rail |
|---|---:|---:|---:|---:|
| 정본 전체 A |49.55초|-17.9|-1.2dBTP|0 |
| 전체 후보 B |49.75초|-17.9|-1.2dBTP|0 |
| 같은 내용 A 발췌 |17.70초|-18.2|-2.4dBTP|0 |
| 같은 내용 B 발췌 |17.90초|-18.2|-2.4dBTP|0 |

이번 LUFS/true peak는 이 PC의 FFmpeg7.1 `ebur128=peak=true` 실제 측정이다. 전체·발췌 각각 A/B의 표시 정밀도0.1LU에서 차이0이며, 발화 PCM 진폭은 동일하다. 체감 음량이나 명료도 동등 판정은 아니다. RMS는 추가 무음으로 약0.018/0.049dB 낮아진다.

14/14 기술 검사, 변환 도구 반례6/6, 별도 디렉터리 재생성3/3 동일 SHA. 실제 작성된 WAV를 다시 읽어 추가0을 제거하면 원본1,189,200프레임이 정확히 복원된다. 끝1초도 동일하므로 **이 편집이 새로 자른 원본 샘플은0개**다. 원래 발음·문장 끝이 적절했는지까지 청취 완료로 판정하지 않는다. 측정·해시·분모·구간표·입력 전후 SHA는 `audio-m2/candidate.json`, 재생성 결과는 `audio-m2/reproducibility.json`, FFmpeg 원출력은 같은 폴더의4개txt다.

FFmpeg 진행 줄의 원래 뒤쪽 공백 때문에 최초 git diff --check가 실패했다. 원출력을 삭제·정리하지 않고 이 보고 폴더의 해당txt에만 byte 보존과 줄 끝 공백 예외를 지정했다. 제품 코드의 공백 검사는 유지한다.

배포할 후보 Release 이름은 `demo-media-20260921-pc2-pause020-v1`이며 아래3파일만 전달한다. 발행 및 GitHub digest 대조 완료 여부는 같은 #8 결과 회신의 실제 URL·SHA로 확인한다.

| 자산 | SHA256 |
|---|---|
| CASE-0002-pause020-v1.wav |6fe83afb8552765ab92722b838d2a0905f507551c4f98c58fa62a515033abaa0 |
| CASE-0002-units-A-v2.wav |7ce4984751d6b0a84ffdc6df3c899bcd1d40d3bcf9589c7495fe7e34940f3cc3 |
| CASE-0002-units-B-pause020.wav |538dd32890d4b3c57930192860441d4003390c9f6334c9b5845b73346d3a6ce4 |

## 재현과 부모 연결

저장소 루트에서 기존 도구를 활성화한 뒤:

```powershell
python -m pip install --target .local/audio-tools --only-binary=:all: --no-deps imageio-ffmpeg==0.6.0
node tests/remote/pc2/confirmation-ssr.mjs
python -m unittest discover -s scripts/media_pc2 -p test_pause_candidate.py -v
python scripts/media_pc2/make_pause_candidate.py --output-dir .local/pc2-n02-m2-pause-v1-recheck
```

새 생성 대상 폴더가 이미 있으면 거부한다. 보존된 결과를 지우지 말고 다른 `.local/` 후보 폴더를 지정한다. 위 두 번째 생성은 최초 파일을 덮지 않고 written-WAV 검증·재현성 확인을 위해 실행했다. 음원은 Git에 커밋하지 않는다. 측정 도구만 Git에서 제외된 로컬 폴더에 준비했고 전역 Python·PowerShell 정책·방화벽을 변경하지 않았다. FFmpeg는 파일을 읽어 null 출력으로 측정하고 종료하며 서버/브라우저를 시작하지 않는다. 도구의 [공식 패키지 설명](https://github.com/imageio/imageio-ffmpeg)과 [공식 ebur128 문서](https://ffmpeg.org/ffmpeg-filters.html#ebur128-1)를 참고했다.

후보 채택 시 pc1은 별도 URL/SHA를 연결해야 한다.17.375초 전은 원래 시각, 이후는+0.20초이며 생성 발화4 이후의 시작/끝을 같이 이동한다. 실제 STT 시각을 생성 시각으로 덮지 말고 같은 변환식을 해당 출처 시각에 적용한다. 삽입점을 걸치는 구간은 끝만 늘린다. 같은 사건이라도 URL이 바뀌면 부모 audioEnded를 초기화하고 후보 시간표로 구간/전체 재생 게이트를 다시 검증한다.

## 인수 전 남은 것

사람 청취0명/0회, 새 TTS/STT/LLM0회. 후보의 native 브라우저 재생/새 시간표 동작과 최종 부모 연결은 미실행이다. 제품 컴포넌트 SHA는기존e861bc8f로 불변이라 최초26건 증거를 유지하지만 새 후보의 재생 PASS로 확대하지 않는다. 추가 브라우저·HTTP 서버·보조 에이전트는 실행하지 않았다. 팝업 출처와 재발 여부는 미확인이다.

메인이 A/B를 확인해 개선이 없으면 v2를 유지하는 것이 정상 결과다. 사람 비교 또는 메인 선택 없이 두 통화 전체를 재편집하거나 공용 manifest를 교체하지 않는다. 이 첫 후보의 구현·기술 측정이 최종 음성 명료도 인수, 중앙 완료 처리 또는 별도 TEST 성공을 뜻하지 않는다.
