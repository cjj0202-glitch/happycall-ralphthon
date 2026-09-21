# N03 미디어 후보 prerelease 공유 검증

2026-09-21 19:08:11 KST, pc3 / LAPTOP-U2AL73UH / mcjun86-oss 실측.

pc1 `cjj0202-glitch`의 [배정 #9](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9) 2026-09-21T10:03:28Z 댓글(`IC_kwDOUjPZqM8AAAABVz753g`)에서 지정한 태그·범위에 따라 합성 MP4 6개와 후보 메타데이터 1개만 공유했습니다. 시작 시 해당 Release와 Git 태그는 모두 존재하지 않았고, 대상 결과 커밋이 원격에 존재함을 확인했습니다.

- **Release:** [demo-media-20260921-wms-candidates-v1](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/tag/demo-media-20260921-wms-candidates-v1)
- 대상 커밋: `577a31b8511c9bb73a1f66c5763077cd776ef6a7`
- Release ID: `392854432`, `prerelease=true`, `draft=false`
- 실제 공개 시각: **2026-09-21 19:08:07 KST** (`2026-09-21T10:08:07Z`)
- 공개 후 Git 태그가 위 결과 커밋을 직접 가리키는지 API로 재조회: 일치
- 자산 수 **7/7**, 원격 bytes·GitHub SHA256 digest 대조 **7/7**, 신규 다운로드 bytes·SHA256 대조 **7/7**
- 다운로드 메타데이터의 관계키·시각·구간·기존 등록 보존 및 MP4 해시 검증: PASS

## 자산 실측

| 파일 | bytes | SHA256 |
|---|---:|---|
| case-0001-picking.mp4 | 69153 | `94b5076150c739dc13fe1d10c370c040dd8a49f4848e581cedaca98536d63cc7` |
| case-0001-sorting.mp4 | 80031 | `f2b21ea3fb2ab5427a581c4e66a8625711f43ed9155fbcf36b8aad2b7757812c` |
| case-0001-shipping.mp4 | 70888 | `dffdf1d94c9324aaecf8a04dacf9d4701d4a356d0a8696c3c008cba307717857` |
| case-0002-picking.mp4 | 71660 | `57e8d39e9c4d0c5de2889f6d87dbb5d9cc4c56d843194b39e1e47f2012c3b9f7` |
| case-0002-sorting.mp4 | 80507 | `0482a749d028f2f1a9d6b76cda2a7ad252914fcc3051e6b005239ca23eb11414` |
| case-0002-shipping.mp4 | 71341 | `ebbcca8b7eaba36efc89a79c170332c47123a490db8cb616879d97ed627eeb3c` |
| pc3-wms.json | 16435 | `fb4b94e2c70fb33b4e97669cecc8aabb6dbeee5118fc16f55b8e5ba2e69742d0` |

MP4 총 **443,580 bytes**, 메타데이터 포함 **460,015 bytes**. 각 자산의 실제 다운로드 URL·GitHub digest·수신 경로·비교 결과는 [media-release.json](media-release.json)에 있습니다.

## 수행과 재현

1. 실제 GitHub 계정과 pc1 댓글, 지정 결과 커밋, 태그·Release 부재를 확인했습니다.
2. `python scripts/media_pc3/generate_candidates.py --verify-only`로 로컬 후보를 검증했습니다.
3. 명시한 7개 경로만 지정 커밋을 대상으로 draft prerelease에 올렸습니다. 전체 원격 자산 이름·개수·bytes·GitHub digest를 대조한 뒤 prerelease를 공개했습니다. 자산 교체나 `--clobber`를 사용하지 않았습니다.
4. 기존 파일이 없는 새 `D:\hwana\Downloads\happycall-pc3-wms-candidates-v1` 폴더에 `gh release download`로 7개 자산을 내려받았습니다.
5. 로컬 원본 ↔ GitHub digest ↔ 새 다운로드의 bytes·SHA256을 각각 비교했습니다. 내려받은 `pc3-wms.json`이 원본과 같고, 해당 메타데이터의 관계와 6개 다운로드 MP4 해시가 모두 맞는지 `validate_overlay`로 확인했습니다.

읽기 전용 재조회 명령:

```powershell
gh release view demo-media-20260921-wms-candidates-v1 --repo cjj0202-glitch/happycall-ralphthon --json tagName,targetCommitish,isPrerelease,isDraft,url,assets
gh api repos/cjj0202-glitch/happycall-ralphthon/git/ref/tags/demo-media-20260921-wms-candidates-v1
python scripts/media_pc3/generate_candidates.py --verify-only
```

검증 스크립트는 이 PC의 `.local/pc3-media/verify_release_share.py`, 원격 draft 대조 기록은 `.local/pc3-media/remote-draft-verified.json`에 있습니다. 표준 GitHub Release의 자동 소스 아카이브 외에 직접 업로드한 자산은 위 7개뿐입니다.

## 한계와 유지한 경계

공유한 영상은 코드 애니메이션 후보입니다. 실제 CCTV·AI 영상 모델 생성 결과·실제 사건이나 귀책의 증거가 아닙니다. 각 6초·18fps·960×540·H.264이며, 생성 단계에서 648프레임을 전수 디코딩했습니다. 이번 다운로드 검증은 그 파일들과 바이트가 같음을 확인한 것이며, 다른 PC의 브라우저 재생·사람 평가를 대신하지 않습니다.

이 prerelease는 정본 등록이나 메인 최종 인수가 아닙니다. 후보의 URL은 여전히 제안 URL이며 public 설치를 수행하지 않았습니다. 기존 음성 v2 Release·정본 manifest·fixture·public 자산은 변경하지 않았습니다. 운영 원천자료·원본 세션 로그·키는 업로드하지 않았습니다. 커밋·push·이슈 회신은 이 하위 작업에서 수행하지 않았습니다.
