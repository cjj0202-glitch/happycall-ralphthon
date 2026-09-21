# N03 WMS 합성 미디어 후보

`generate_candidates.py`는 기존 독립 합성 fixture의 두 case에서 피킹·분기·출고 이벤트를 읽어 **공정별 별도 MP4 6개**를 만듭니다. Python 코드가 그린 애니메이션이며 실제 CCTV, 실제 이동 궤적, AI 영상 모델 출력이 아닙니다. 유료 API·외부 생성 서비스 호출은 없습니다.

## 실행

Python 3.10+와 `requirements.txt`의 Pillow/imageio-ffmpeg, 한국어 Malgun 또는 NotoSansCJK 글꼴이 필요합니다. 가상환경/의존성 설치는 D:의 작업 경로를 사용합니다.

```powershell
python -m pip install --target .local/media-pc3-deps --cache-dir D:/hwana/Cache/pip -r scripts/media_pc3/requirements.txt
$env:PYTHONPATH = (Resolve-Path .local/media-pc3-deps).Path
python scripts/media_pc3/generate_candidates.py
python scripts/media_pc3/generate_candidates.py --verify-only
python -m unittest discover -s scripts/media_pc3 -p 'test_*.py' -v
```

출력은 `.local/pc3-media/*.mp4`와 디코딩한 6프레임의 contact sheet, `generation-result.json`입니다. 영상 전체 프레임 수·크기·fps·길이·움직임을 실제 디코딩하고 파일 SHA256·바이트 수를 잽니다. `data/overlays/pc3-wms.json`만 Git 후보 입력이며 바이너리는 Git/Release에 올리지 않습니다. 동일 버전/글꼴이면 재현 가능하나 FFmpeg·글꼴 버전이 다른 경우 바이트 해시가 달라질 수 있으므로 생성한 파일 자체를 재검증합니다.

## 통합 계약

- overlay의 `mediaCandidates`는 `candidate-not-registered` 상태입니다. **WmsScene이 overlay를 자동 병합해서 재생하면 안 됩니다.** 메인이 소스·해시·실제 URL 재생을 검토하고 fixture/manifest에 명시 등록한 뒤에만 재생할 수 있습니다.
- `/demo/pc3/*.mp4`는 제안 URL입니다. 본 스크립트는 public/demo 복사, 업로드, fixture/manifest 편집을 하지 않으므로 지금 URL은 설치되어 있지 않습니다.
- 현재 등록은 CASE-0002의 W-W3 → `sorter-demo.mp4` 하나 그대로입니다. 새 분기 후보는 별도 ID/가상 camera/URL이고 기존 영상을 대체하지 않습니다.
- event/case/system/time은 fixture와 정확히 일치해야 합니다. 한 공정 기록의 tote를 다른 공정으로 추정 복사하지 않습니다. CASE-0001 출고와 두 case 분기에 선택 공정 tote가 없으므로 null 및 `needs_review`를 보존합니다. `relations.pickingToteId`와 `shippingToteId`는 대조용 별도 필드입니다.
- 관계를 확인할 store/order/businessDate/asOf, 원본 이벤트 및 공정행을 유지합니다. 해당 stage 이벤트가 없으면 자산을 만들지 않고 `unregistered`에 남깁니다. 시각 불일치·시간대 누락·asOf 이후 이벤트는 생성 전에 거부합니다.
- 움직이는 도형과 가상 카메라는 설명을 위해 새로 그린 것입니다. 같은 사건·구간으로 등록하더라도 실제 사건·귀책의 입증 자료가 되지 않습니다.
