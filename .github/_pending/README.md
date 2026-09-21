# 대기 중인 워크플로

`reply-gate.yml` 은 **회신 없이 닫힌 편지를 자동으로 다시 여는** Action 입니다
(규약 ⑦). 지금은 여기 있고 아직 동작하지 않습니다.

## 왜 여기 있나

레포를 만든 `gh` 토큰에 `workflow` 스코프가 없어 push 가 거부됐습니다.
클라이언트 쪽 게이트(`mail.py done --evidence`)는 이미 동작하므로 **없어도 돌아갑니다.**
다만 `gh issue close` 나 웹 UI 로 직접 닫으면 그 게이트를 지나갑니다.

## 켜는 법 — 메인 PC 에서 한 번

```bash
gh auth refresh -s workflow          # 브라우저에서 한 번 승인
git mv .github/_pending/reply-gate.yml .github/workflows/reply-gate.yml
git commit -m "ci: 회신 게이트 활성화"
git push
```

`Actions` 탭에 `reply-gate` 가 보이면 켜진 것입니다.
확인: 아무 편지나 코멘트 없이 닫아 보면 30초 안에 다시 열립니다.
