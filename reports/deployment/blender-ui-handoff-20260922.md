# 3D 공정 확인 UI 배포 인계

제품 커밋: `129c706b7a0ab63646eea565f3572b668001c084` (main 푸시 확인).

## 반영 내용

WMS 피킹·출고 비교 → 3D 소터 공정 확인 → 접근/분기/슈트/정지 구간 탐색 → 원본 대조로 이어진다. 작은 화면도 비교값을 영상보다 위에서 볼 수 있다. 등록된 기존 Blender 12초 영상과 좌표를 사용하며 실제 CCTV나 귀책 판단으로 표시하지 않는다.

검증: production export 성공, 공정 단위검사 36개와 오류 변이 검출 2개, 실제 Edge 브라우저 19개 검사 통과. `reports/validation/blender-investigation-20260922.md` 참조.

## CJJ에서 만든 Lambda 번들

- 원본: `dist/aws/20260922T015436269336Z-129c706b7a0a/oneflow-lambda.zip`
- 전달본: `C:/Users/choi8/Downloads/ai-go-blender-129c706-lambda.zip`
- SHA256: `0ba76a089a5741564c1b53a8d49162747e2f61f9e762c164a221fc64af530db4`
- 압축 33,362,163 bytes / 확장 58,993,057 bytes / 4,338파일
- 생성 검사와 별도 `--verify` 모두 `verified-local-only`; Downloads 복사본 SHA도 일치.

이 ZIP은 아직 AWS에 배포하지 않았다. 사용자가 지정한 다른 배포 PC에서 기존 개인 계정과 함수의 일치를 확인한 뒤 코드만 갱신한다. 인증·환경변수·DynamoDB·누적 사용량 원장을 보존한다. 기존 배포 URL이 이번 UI를 포함한다고 가정하지 않는다.

최신 main에서 직접 재빌드할 경우 `AI-GO_다른PC_배포인계.md`의 명령을 사용한다. 배포 후 CASE-0002 WMS의 3D 버튼, 4단계 이동, 12초 전체 재생, 피킹·출고 비교를 별도 시연 상태에서 검증하고 실제 배포 SHA/코드 해시/URL/결과를 기록한다. 유료 API는 이번 검증에 필요하지 않다.
