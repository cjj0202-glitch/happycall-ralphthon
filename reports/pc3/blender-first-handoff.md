# N03-M2 첫 결과: 장면 생성 코드·렌더 인계

2026-09-21 20:02 KST / pc3 LAPTOP-U2AL73UH / mcjun86-oss. [pc1 후속 배정](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5759286998), 공유 기준 `e5469aa99bb266c5a977b80c097223275ac6fc9b`, 기존 작업 결과 `d6aa6b38ab18836789eb77e9034560a5e7890eef` 위 첫 단위다.

**구현 코드와 독립 수치 검증을 전달한다. 이 PC에서는 Blender 미발견으로 실제 장면 생성·대표3프레임·MP4 렌더를 실행하지 않았다.** pc1이 배정문에 제공한 동일 코드 렌더 대안을 사용한다. 메인 검수 전 긴 렌더와 최종 인수를 진행하지 않는다.

## 전달 파일과 구현

- `scripts/media_pc3/build_scene.py`: 독립 layout을 읽는 Blender 생성기. 롤러·벨트·분기 가드·철재 프레임·다리/바닥·골판지·파란 정지 용기·랙·콘크리트·조명을 구성한다. 공유 고정 CCTV와 별도 overview를 둔다. 같은 장면의 288개 투영 bbox/궤적·blend·실측 렌더/해시 보고서를 출력하도록 구현했다.
- `scripts/media_pc3/scene_contract.py`: 원본 fixture·W-W3 관계와 고정 합성 좌표·카메라를 검증한다. seed20260921, 반경1m의 연속 분기, 0–3 접근/3–6 분기/6–10 슈트/10–12 정지. 업무 토트 null과 고정 사건시각을 보존한다.
- `scripts/media_pc3/BLENDER.md`: 실제 Blender 경로 확인, prepare/720p 대표3장/짧은72장/최종288장 명령, FFmpeg 후보 인코딩, 출력·미검증 한계.
- `tests/remote/pc3/test_scene_contract.py`: Python 표준 라이브러리만 쓰는 계약·좌표·경계·반례 검사.
- [상세설계](blender-design.md), [실제 환경](blender-capability.md), [독립 수학 투영](blender-projection-review.json).

생성기 구현은 bpy API 호환성 성공 보고가 아니다. 렌더 파일을 만들었다고 기록하지 않았고, 원본 업무 도면·화면을 복제하거나 외부로 전송하지 않았다. `.local/pc3-blender/input/`의 독립 좌표와 합성 참고 PNG만 읽었다. WmsScene/공용 UI·server/fixture/manifest/public/기존 v1 Release는 이번 변경에 포함하지 않았다.

## 기대·실측

| 검사 | 기대 | 실측 |
|---|---|---|
| Python 문법 컴파일 | 오류0 | build_scene/scene_contract `py_compile` exit0 |
| 순수 계약·운동 | 12검사, 정상양성+80불량변이, 288프레임 유한/단조/경계연속 | **12/12 PASS**, unittest0.282초 |
| 입력 관계 | CASE2/W-W3/02:33KST/CH02/D02/CAM02/null 정확일치 | PASS; 다른 사건·미래시각·카메라·토트변조 거부 |
| 고정 camera/zone 드리프트 | 카메라/6구역의 유한 정상형태 변경도 거부 | 기존49+추가31=80변이 거부 |
| 독립 핀홀·상자 계산 | 경로 물체가 화면/선언 지지구조 안에 위치 | 903공간표본·21,672꼭짓점: 프레임 이탈0, 검사한 지지모서리 이탈0, 지정 가드 AABB 중첩0 |
| Blender/renderer/벤치마크 | 실제 도구·버전·시간 관측 | **미실행**. 확인 범위 내 실행파일 없음 |
| 실제 장면·3PNG·blend·MP4·렌더 bbox | 실제 렌더로 확인 | **미생성·미검증**, pc1 렌더 대기 |

수학 투영의 bbox 범위는 x0.247744–0.597864/y0.113700–0.829304다. 이는32mm/36mm수평센서/16:9/정방픽셀을 가정한 독립 계산이며 Blender 행렬·모디파이어·가림·픽셀 윤곽 검증이 아니다. 주생성기를 호출하지 않은 수학 검사다. 결과 분모를 실제 렌더 프레임 수로 표현하지 않는다.

처음 단위검사에서 종점 y가 `4.499999999999998`로 원래 경계 밖에 아주 작게 나가는 부동소수 오차를 발견했다. 선언된 종점 경계로 한정하고 동일 검사를 다시 통과했다. 카메라와 구역의 고정 계약을 추가 대조한 뒤 최종12개를 재실행했다. Blender가 없다는 사실을 숨기기 위해 bpy 모의 객체의 실행을 렌더 성공으로 세지 않았다.

## pc1의 다음 실행과 검수

저장소 루트와 실제 `$blenderExe` 경로를 해당 PC에서 확인하고 [실행 설명](../../scripts/media_pc3/BLENDER.md)을 따른다. 첫 대표3장 명령:

```powershell
& $blenderExe --background --factory-startup --python-exit-code 1 --python scripts/media_pc3/build_scene.py -- --layout planning/media/scene-layout-v1.json --fixture data/fixtures/cases.json --output .local/pc3-blender/representatives-01 --mode representatives --resolution 1280 720 --samples 32
```

기대 결과는 `frame-0001.png`, `frame-0133.png`, `frame-0288.png`, `case-0002-ww3.blend`, `tracks.json`, `render-report.json`이다. 현재 존재한다는 뜻이 아니다. 1/133/288은 시연0/5.5/11.958333초이고 고정 사건시각은 `2026-09-18T02:33:00+09:00`이다. 영상은 실제 CCTV가 아니며 추후 통합 UI에서도 고정 사건시각과 `시연 +초`를 분리한다.

pc1은 실제 버전·엔진·소요시간·3장과 가드 관통/부유·물성·조명·워터마크·실제 bbox·가림을 검수한다. 시각 게이트 통과 전 최종288장 렌더와 신규 후보 등록을 진행하지 않는다. 대표3장 시각 피드백을 받으면 같은 소유 범위에서 수정하고 동일3장을 재검수한다. 실제 출력은 별도 후보 Release+SHA로 공유하고 기존 후보/정본을 덮지 않는다.

현재 pc3 하드웨어 실측은 i7-8550U 4코어/8스레드, RAM7.92GiB, UHD620/MX150(WMI보고2GiB), D여유793.55GiB다. 렌더 지원·VRAM 가용·소요시간은 모델명으로 추정하지 않았다. 이 첫 인계가 N03-M2 시각 게이트·영상·UI 통합·프로젝트 최종 완료를 뜻하지 않으며 TEST 왕복도 별도 미완료다.
