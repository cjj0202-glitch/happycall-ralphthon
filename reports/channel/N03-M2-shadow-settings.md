# N03-M2 기존 공간 후보의 렌더 설정 보충

pc3는 현재 주변 공간 후보 작업을 유지합니다. 새 구현 카드를 추가하는 내용이 아니라 pc1의 실제 렌더 관측을 같은 후보에 연결하는 기술 입력입니다.

동일 d67b2c7/B 기하에서 메인이 32→96 samples 대표3장을 비교했고 바닥 입자는 일부 줄지만 발판 입자가 남았습니다. 이어 frame133만 **shadow_ray_count 1→4**로 바꾸자 발판 입자가 뚜렷하게 줄었습니다. 실제 Blender4.5.14 RNA 최대값은4이며 8은 지원하지 않습니다. Cycles CPU16+OIDN도 같은 장면으로 비교했으나 금속 반사에 거친 흔적이 있어 이번 다음 후보는 **EEVEE 96 samples / shadow rays4 / threads2**로 선택합니다.

- 실제 렌더: EEVEE 한 장28.453초, Cycles 한 장34.953초. 288영상·짧은 동작은 아직 미실행입니다. 기존기하/재질/광원/카메라 대조15/15입니다.
- 비교 PNG3개와 SHA/크기 manifest: [후보 Release](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/tag/demo-wms-blender-representatives-20260921)의 `B-eevee32-rays1-frame0133.png`, `B-eevee96-rays4-frame0133.png`, `B-cycles16-denoised-frame0133.png`, `shadow-review-manifest.json`.
- 정본 증거: `reports/media/pc3-sampling-review.md`, `reports/media/pc3-engine-shadow-review.md`. pc1 렌더 결과이며 pc3 실제실행으로 합산하지 않습니다.

공간 옵션과 **독립된 명시 옵션**으로 `--shadow-rays`를 추가해 기본1을 유지하고 EEVEE 실제 RNA의 범위1~4만 허용해 주세요. 설정 요청값과 실제 readback을 report에 모두 적습니다. Cycles에는 EEVEE값을 적용했다고 표기하지 않으며 거짓 readback/허용범위초과를 거부합니다. 나머지 조명·재질·샘플은 기존값을 기본으로 보존합니다.

메인은 주변 환경을 포함한 동일 대표3프레임을 먼저 렌더하고, 중앙 분기 시야와 기하/궤적을 확인한 뒤 B의 [3,6)초 72프레임 검토로 확장합니다. 원천센터 복제·업무토트/귀책 확정·288 최종 승인으로 확대하지 않습니다. 현재 소유 파일·21:25~21:35 첫 결과 목표·기존 #9 인계 규칙을 유지합니다.
