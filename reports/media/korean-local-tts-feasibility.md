# 한국어 로컬 TTS 후보 조사: Supertonic 3

- 조사 시각: 2026-09-21 22:07~22:10 KST
- 조사자: pc1 / CJJ의 독립 조사 에이전트 `korean_tts_options`
- 대상: 사용자 지적에 따른 한국어 통화 음성 교체 후보. Typecast·수퍼톤 클라우드 API 비교는 메인 담당입니다.
- 실행 범위: 공식 웹 문서·공개 저장소·공개 모델 메타데이터 조회, 로컬 `find_spec`·메모리 조회. 설치 0회, 모델 다운로드 0회, 합성 0회, 과금 0회, 서버·브라우저 실행 0회입니다.

## 결론

수퍼톤이 공개한 Supertonic 3는 한국어 `ko`와 Windows CPU 추론을 지원하므로, 계정·API 키 없이 짧은 대사를 비교할 수 있는 로컬 후보입니다. 현재 공식 저장소는 `supertone-oss-archive`로 이동해 보관 상태이며 공식 지원이 끝났습니다. 유지보수되는 서비스로 오해하지 않아야 합니다. 한국어 자연스러움은 아직 직접 합성·청취하지 않았으므로 기존 음원보다 우수하다고 판정하지 않습니다. [공식 저장소](https://github.com/supertone-oss-archive/supertonic)

수퍼톤 공식 회사 페이지의 서울 소재 법인 정보와 공식 모델 저작권 `Supertone Inc.`를 함께 확인했습니다. 따라서 국내 기업이 개발·공개한 모델이라는 출처는 확인되지만, 모든 프리셋을 한국인 원어민 화자로 분류할 근거는 없습니다. [회사](https://www.supertone.ai/en) · [모델 카드](https://huggingface.co/supertone-oss-archive/supertonic-3/blob/aafc6e32416a594460b32413efc49d7fe4ce6d46/README.md)

## 현재 사용 가능성과 고정 버전

| 항목 | 확인 결과 | 근거 |
|---|---|---|
| 원래 저장소 | `supertone-inc/supertonic`에서 보관 저장소로 연결 | [원래 주소](https://github.com/supertone-inc/supertonic) |
| 보관 상태 | GitHub 표시: 2026-09-09 archived/read-only | [저장소](https://github.com/supertone-oss-archive/supertonic) |
| 조사한 코드 SHA | `1e9799e964ea4c0dad7cde993b65c3c813a7b373` | [고정 커밋](https://github.com/supertone-oss-archive/supertonic/tree/1e9799e964ea4c0dad7cde993b65c3c813a7b373) |
| 모델 저장소 | `supertone-oss-archive/supertonic-3` | [모델](https://huggingface.co/supertone-oss-archive/supertonic-3) |
| 공식 다운로드 고정 revision | `aafc6e32416a594460b32413efc49d7fe4ce6d46` | [공식 다운로드 안내](https://github.com/supertone-oss-archive/supertonic#quick-start) |
| 로그인 필요 여부 | 모델 API 응답 `gated=false`; 공식 안내도 로그인 불필요 | [고정 revision 메타데이터](https://huggingface.co/api/models/supertone-oss-archive/supertonic-3/revision/aafc6e32416a594460b32413efc49d7fe4ce6d46?blobs=true) |
| 언어·음원 | 한국어 포함 31개 언어, 44.1kHz WAV | [모델 카드](https://huggingface.co/supertone-oss-archive/supertonic-3/blob/aafc6e32416a594460b32413efc49d7fe4ce6d46/README.md) |
| 프리셋 | `F1`~`F5`, `M1`~`M5` 총 10개. 한국어 입력 `ko`로 조합 가능 | [음성 파일 목록](https://huggingface.co/supertone-oss-archive/supertonic-3/tree/aafc6e32416a594460b32413efc49d7fe4ce6d46/voice_styles) |
| 추론 | ONNX Runtime, CPUExecutionProvider. 예제의 GPU 옵션은 코드에서 NotImplementedError | [고정 helper.py](https://github.com/supertone-oss-archive/supertonic/blob/1e9799e964ea4c0dad7cde993b65c3c813a7b373/py/helper.py) |
| 복제 목소리 | 공개 고정 화자 모델에는 공식 음성 복제 파이프라인 없음 | [공식 설명](https://github.com/supertone-oss-archive/supertonic#voice-cloning) |

공식 도움말에는 Supertone Play가 2026-08-31 종료됐고 신규 가입·구독·크레딧 구매는 2026-07-23 중단됐다고 적혀 있습니다. 5월 출시 기사에 남은 Play 링크를 현재 이용 가능한 서비스로 채택하지 않습니다. 클라우드 API의 별도 이용 가능성은 이 조사에서 판정하지 않았습니다. [공식 종료 공지](https://support.supertone.ai/hc/en-us/articles/16564749196815-Play-Plan-Features-Credits)

## 다운로드 분모와 무결성

아래 크기는 Hugging Face 고정 revision의 `siblings[].size` 합계입니다. 실제 파일 다운로드·디스크 사용량·모델 적재 RAM 측정값이 아닙니다.

| 범위 | 파일 바이트 합계 |
|---|---:|
| 4개 ONNX 모델 | 398,075,273 |
| `onnx/*`, `voice_styles/*`, `config.json`, `README.md`, `LICENSE` | 401,301,114 |
| 이미지·샘플 오디오 포함 전체 snapshot | 414,728,474 |

| 모델 파일 | 바이트 | 공개 LFS SHA-256 |
|---|---:|---|
| duration_predictor.onnx | 3,700,147 | `c3eb91414d5ff8a7a239b7fe9e34e7e2bf8a8140d8375ffb14718b1c639325db` |
| text_encoder.onnx | 36,416,150 | `c7befd5ea8c3119769e8a6c1486c4edc6a3bc8365c67621c881bbb774b9902ff` |
| vector_estimator.onnx | 256,534,781 | `883ac868ea0275ef0e991524dc64f16b3c0376efd7c320af6b53f5b780d7c61c` |
| vocoder.onnx | 101,424,195 | `085de76dd8e8d5836d6ca66826601f615939218f90e519f70ee8a36ed2a4c4ba` |

`F1`~`F5`, `M1`~`M5`의 voice JSON은 각각 약 290~292KB입니다. 임의로 연령·지역·상담용 적합성을 붙이지 않고 짧은 같은 대사로 선발합니다. 공개 샘플의 `alphonse` 등 커스텀 목소리를 기본 10종에 포함시키지 않습니다.

## 라이선스와 시연 음원 보존

코드는 MIT이고 가중치는 별도 OpenRAIL-M입니다. MIT만 보고 모델까지 무제한 사용 가능하다고 표시하지 않습니다. 모델 라이선스는 이용·배포 권한과 제한 용도를 규정하며, 제6조에서 생성 결과물에 대한 라이선서 권리를 주장하지 않는다고 설명합니다. 생성 WAV를 보존해 합성 업무 시연에 이용하는 것은 해당 제한을 지키는 전제의 후보 경로입니다. 모델 자체를 배포한다면 라이선스·고지·후속 이용 제한 전달 의무를 별도로 지켜야 합니다. [코드 라이선스](https://github.com/supertone-oss-archive/supertonic/blob/1e9799e964ea4c0dad7cde993b65c3c813a7b373/LICENSE) · [모델 라이선스](https://huggingface.co/supertone-oss-archive/supertonic-3/blob/aafc6e32416a594460b32413efc49d7fe4ce6d46/LICENSE)

이번 용도에서 특히 확인할 조건은 AI 생성 표시, 동의 없는 실제 인물 사칭 금지, 위해 목적 허위정보·개인정보 이용 금지입니다. `AI가 생성한 가상 상담 통화` 표시를 유지하고, 가상의 점포·화자를 쓰며 실직원 음성 복제를 하지 않습니다. 품질 평가 전 WAV를 제품 정본이나 Release 자산으로 올리지 않습니다.

## 이 PC의 환경 관측

명령은 `importlib.util.find_spec`만 호출했고 실제 패키지 import·설치·모델 적재는 하지 않았습니다.

| 런타임 | onnxruntime | numpy | soundfile | huggingface_hub |
|---|---|---|---|---|
| 프로젝트 `.venv`, Python 3.12.14 | 없음 | 없음 | 없음 | 없음 |
| Python314, Python 3.14.3 | 없음 | 있음 | 없음 | 없음 |

22:07:22 KST `Get-CimInstance Win32_OperatingSystem` 결과는 `FreePhysicalMemory=2,831,524 KiB`, `TotalVisibleMemorySize=16,585,728 KiB`입니다. 여유 RAM 약 2.70GiB라는 순간 관측이며 합성 최대 RAM은 미측정입니다. 기존 Blender·서버를 정지시키지 않았습니다.

공식 예제 의존성은 `onnxruntime==1.23.1`, `numpy>=1.26.0`, `soundfile>=0.12.1`, `librosa>=0.10.0`, `PyYAML>=6.0`입니다. 고정 `helper.py`와 `example_onnx.py`의 직접 외부 import는 numpy·onnxruntime·soundfile이지만, 첫 설치는 공식 requirements를 존중하는 경로가 재현하기 쉽습니다. [requirements](https://github.com/supertone-oss-archive/supertonic/blob/1e9799e964ea4c0dad7cde993b65c3c813a7b373/py/requirements.txt)

PyPI 1.23.1 메타데이터의 Windows AMD64 wheel은 CPython 3.10~3.13까지이고 3.14용은 없습니다. cp312 wheel은 13,467,773B입니다. 따라서 기존 앱 `.venv`를 변경하지 않는 별도 Python 3.12 환경을 우선 검토합니다. 공식 Quick Start 권장은 Python 3.11이며, 3.12에서의 전체 의존성 설치·실행 성공은 아직 미검증입니다. [PyPI 메타데이터](https://pypi.org/pypi/onnxruntime/1.23.1/json)

## 다음 실험용 정확한 명령과 2-thread 조건

아래는 미실행 절차입니다. 예제 CLI에는 thread 제한 인수가 없으므로 원본 CLI만으로 2-thread 제한을 달성했다고 보고하면 안 됩니다. 첫 샘플은 짧은 한국어 두 문장, 두 화자, 각 1회, `total_step=8`, `speed=1.0`, 직렬 처리로 제한합니다. 자연스러움 평가 전 10종 전수·긴 대본·자동 반복으로 확장하지 않습니다.

공식 명령에 기반한 Windows 격리 준비 예시는 다음과 같습니다. `<new-empty-local-dir>`은 메인이 충돌 없는 `.local` 하위 경로를 선택하고, 파일이 이미 있으면 덮어쓰지 않아야 합니다.

```powershell
git clone https://github.com/supertone-oss-archive/supertonic.git <new-empty-local-dir>
git -C <new-empty-local-dir> checkout --detach 1e9799e964ea4c0dad7cde993b65c3c813a7b373
& 'C:/00.프로젝트/happycall-ralphthon/.venv/Scripts/python.exe' -m venv <new-empty-local-dir>/.venv
& <new-empty-local-dir>/.venv/Scripts/python.exe -m pip install -r <new-empty-local-dir>/py/requirements.txt huggingface_hub
& <new-empty-local-dir>/.venv/Scripts/hf.exe download supertone-oss-archive/supertonic-3 --revision aafc6e32416a594460b32413efc49d7fe4ce6d46 --include 'onnx/*' 'voice_styles/*' config.json LICENSE README.md --local-dir <new-empty-local-dir>/assets
```

공식 단일 한국어 발화 예제는 `py` 디렉터리에서 아래와 같습니다. 이 명령 자체에는 thread 제한이 없습니다.

```powershell
../.venv/Scripts/python.exe example_onnx.py --n-test 1 --voice-style ../assets/voice_styles/F1.json --lang ko --total-step 8 --speed 1.0 --text '네, 사장님. 어느 상품이 다르게 들어왔는지 먼저 확인하겠습니다.' --save-dir ../candidate-audio
```

2-thread 실험은 원본 helper를 수정하지 않고 별도 어댑터에서 다음 공식 helper 구성요소를 직접 연결할 수 있습니다. 이는 공식 CLI 인수가 아니라 메인의 후속 구현 제안이며 아직 실행하지 않았습니다.

```python
from pathlib import Path
import onnxruntime as ort
import helper

onnx_dir = str(Path(model_dir) / "onnx")
opts = ort.SessionOptions()
opts.intra_op_num_threads = 2
opts.inter_op_num_threads = 1
opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
opts.add_session_config_entry("session.intra_op.allow_spinning", "0")
sessions = helper.load_onnx_all(onnx_dir, opts, ["CPUExecutionProvider"])
tts = helper.TextToSpeech(helper.load_cfgs(onnx_dir),
                        helper.load_text_processor(onnx_dir), *sessions)
```

4개 세션 각각에 위 설정이 전달되는지 `get_session_options()`와 `get_providers()`를 읽어 기록합니다. 세션당 thread 설정을 전체 OS 스레드가 정확히 2개라는 주장으로 바꾸지 않습니다. BLAS 등 별도 런타임의 스레드는 추가로 생길 수 있습니다. 기존 실행 중인 렌더와 경쟁하지 않게 직렬 실행하며 시작 직전 RAM을 다시 읽고 실제 합성 wall time·최대 working set·음원 길이를 기록합니다.

공식 코드에서 기본 난수 샘플링을 하므로 코드·모델 SHA만 같다고 PCM이 같다고 가정하지 않습니다. 후보 WAV와 발화별 텍스트·voice·speed·step·시각·SHA256를 묶어 보존합니다. 44.1kHz 원본을 보존한 뒤 제품에서 필요한 포맷으로 변환한 별도 파생본에 새 SHA를 부여합니다. 대본의 글자 수로 자막 시각을 만들지 않습니다.

## 인수 전 남은 품질 검증

1. 전문 대본 담당자의 사실 계약을 확정하고 `개/박스`, 수량 정정, 상품명, 시각의 발음을 확인합니다.
2. 같은 짧은 문장으로 F·M 후보를 생성하고 기존 음원과 비교합니다. 국내 모델이라는 이유로 자동 채택하지 않습니다.
3. 잡음·클리핑·과도한 무음·음량 차·문장 잘림을 실제 WAV 값으로 검사합니다. 음향 수치는 자연스러움의 대용치가 아닙니다.
4. 사람이 듣거나 실제 오디오를 소비할 수 있는 독립 평가자가 억양·감정·호흡·화자 구분을 판정합니다. 로컬 파일 생성 성공이나 ASR 일치만으로 한국어 자연스러움 PASS를 쓰지 않습니다.
5. 채택 후 새 음원 기준 STT→정제→사람 확인 흐름과 발화 경계·전체 자연 재생을 다시 검증합니다. 기존 v3 검증 결과를 새 대본·새 음원으로 소급하지 않습니다.

이 보고서는 로컬 후보의 실행 가능성 조사 완료이며, 한국어 음성 품질·통합 완료 보고가 아닙니다.
