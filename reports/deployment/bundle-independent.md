# 별도 배포 패키지 독립 검토

2026-09-21 18:25 KST, pc1/CJJ. 읽기 전용 `bundle_adversarial`가 최종 코드·설계·실제 out을 검토하고 재현한 결과를 메인이 기록했습니다. 대상은 `scripts/build_deployment_bundle.py`, `deploy/vercel/` 두 파일, 해당 테스트 및 배포 ASGI입니다. 검토자는 제품·원본 out·계정·키를 수정하지 않았습니다.

재현된 결함은 0건입니다. `.venv/Scripts/python.exe -B -m pytest tests/test_deployment_bundle.py -q -p no:cacheprovider`는 **55 passed, 64.86초**입니다. 별도 `tests/test_deployment_app.py`는 **119 passed / Windows 실물 링크 권한으로 3 skipped, 10.22초**입니다. 메인도 bundle+launcher를 묶어 **62 passed, 61.68초**로 재실행했습니다.

검토자는 실제 out의 HTML 2개에서 참조한 로컬 자산 9개의 존재를 확인했습니다. 현재 완료 기록·입력 검증은 `bundle._payload(Path.cwd(), Path.cwd()/bundle.MEDIA_MANIFEST)`로 53파일, 12,630,082 B, out 26파일을 반환했습니다. 이는 패키지 입력 바이트이며 Python 설치 의존성을 포함한 원격 함수 크기가 아닙니다.

기존 테스트 외에 임시 repo에서 `Path.open`의 세 번째 `xb` 호출에 OSError를 주입했습니다. 실제 결과는 다음과 같습니다.

```json
{"failure":"BUNDLE_WRITE_FAILED_INCOMPLETE_OUTPUT_PRESERVED","partialDirectories":1,"partialFiles":2,"completeMarkers":0,"retry":"OUTPUT_ALREADY_EXISTS","preserved":true}
```

부분 쓰기 결과를 성공 manifest로 승격하지 않고, 동일 경로 재시도도 기존 바이트를 보존하며 거부했습니다. 원격 Vercel rewrite·ASGI·Range, 최종 설치 크기, 영속 저장·실모델 동작은 미검증입니다. 로컬 검토 통과를 배포 성공으로 사용하지 않습니다.
