# 시제품 복구·정규화 통합 백엔드 회귀

2026-09-21 KST. 접수 멱등 키·응답 유실 조회, 분석 근거 정규화, 배포 모듈 및 외부 프런트 데이터 fingerprint가 함께 반영된 작업 트리에서 실행했습니다.

명령: `.venv/Scripts/python.exe -m pytest tests -q`

실측: **752 passed, 5 skipped, 5 warnings, 207 subtests passed in 55.58s**, exit 0. 5개 skip을 통과로 합산하지 않습니다. 기존 호환 라이브러리의 deprecated 경고 5개도 유지했습니다. 이 검사는 라이브 모델·원격 저장소·사람 사용성 검사가 아닙니다.

변경별 독립 근거:

- [접수 응답 유실·동일 키 재시도](intake-retry-independent.md): 실제 ASGI 201/200/201 및 동일 접수 1건, CAS 동시 경쟁에서 동일·상이 payload 구분.
- [분석 정규화 독립 재검](analysis-grounding-final-independent.md): 정상 진술 유지, 부정/미래/다른 상품 귀속 차단의 한정 반례.
- 배포 패키지 검사 61개는 별도 변경 단위에서도 통과했습니다. 새 런타임 모듈 2개 포함, 프런트에서 직접 import하는 fixture·media manifest·TMS overlay JSON을 빌드 지문에 포함합니다. 세 파일 각각의 변경/누락 6개 반례를 추가했습니다.

최종 브라우저 검사와 원격 배포 검사는 별도 증거를 따릅니다. 기존 8100/3100 프로세스를 재시작하거나 기존 상태를 삭제하지 않았습니다.
