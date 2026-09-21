"""Create an offline review page only for a comparable representative A/B pair."""
from __future__ import annotations

import argparse
import base64
from html import escape
import json
from pathlib import Path
import sys

from compare_representatives import Invalid, match_bytes, read_fixed


FRAMES = ((1, 0.0, "진입"), (133, 5.5, "분기"), (288, 287 / 24, "도착·정지"))
CHECKS = ("물성 구분: 바닥·강철·벨트·노란 가드", "가드·벨트·바닥 접촉과 간섭",
          "상자의 진입·분기·도착 판독", "그림자 입자와 접촉 경계 보존")


def build_html(a_dir: Path, b_dir: Path, comparison: dict) -> str:
    """Embed original PNG bytes; a machine comparison never accepts visual quality."""
    if (comparison.get("comparable") is not True
            or comparison.get("failures") != []
            or comparison.get("visualAccepted") is not False):
        raise ValueError("A/B comparison failed or visualAccepted is not false; no page created.")
    rows = []
    for frame, elapsed, phase in FRAMES:
        cells = []
        name = f"frame-{frame:04d}.png"
        for key, label, directory in (("A", "A · baseline", Path(a_dir)), ("B", "B · contrast_material_v1", Path(b_dir))):
            raw = read_fixed(directory.resolve(strict=True), name)
            try:
                match_bytes(raw, comparison["imageDigests"][key][name], name)
            except (Invalid, KeyError) as exc:
                raise ValueError("Image changed since comparison or verified digest is missing.") from exc
            if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError(f"Expected original PNG: {directory / name}")
            uri = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
            alt = escape(f"{label}, frame {frame}; synthetic scene, visual review pending", quote=True)
            cells.append(f'<div class="cell"><h3>{escape(label)}</h3><details class="picture">'
                         f'<summary><img src="{uri}" alt="{alt}"><span>클릭하여 원본 크기로 확대 / 접기</span>'
                         '</summary></details></div>')
        rows.append(f'<section><h2>프레임 {frame} · 경과 {elapsed:.6f}초 · {escape(phase)}</h2>'
                    f'<div class="pair">{"".join(cells)}</div></section>')
    checklist = "".join(f'<label><input type="checkbox"> 미검사 — {escape(item)}</label>' for item in CHECKS)
    details = escape(json.dumps(comparison, ensure_ascii=False, indent=2))
    sources = f'A: {escape(str(Path(a_dir).resolve()))}<br>B: {escape(str(Path(b_dir).resolve()))}'
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; object-src 'none'">
<title>합성 장면 A/B — 시각 검수 미완료</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#101820;color:#edf2f7;font:16px/1.5 system-ui,sans-serif}}
main{{max-width:1600px;margin:auto;padding:24px}}h1{{font-size:26px}}h2{{font-size:20px}}h3{{font-size:16px}}
.notice{{border:2px solid #f6bd60;padding:16px;background:#28251d}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
section{{margin:32px 0}}.cell{{min-width:0;padding:12px;background:#1c2935;border:1px solid #496174}}
.picture{{max-width:100%;overflow:auto}}summary{{cursor:pointer}}.picture summary{{cursor:zoom-in}}
.picture[open] summary{{cursor:zoom-out}}img{{display:block;max-width:100%;height:auto}}.picture[open] img{{max-width:none}}
label{{display:block;margin:8px 0}}input{{margin-right:10px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}
.sources{{overflow-wrap:anywhere;color:#bdcedd}}span{{font-size:14px;color:#bdcedd}}
@media(max-width:700px){{main{{padding:12px}}.pair{{gap:8px}}.cell{{padding:6px}}h3{{font-size:13px}}}}
</style></head><body><main>
<h1>합성 장면 A/B 비교 · SYNTHETIC SCENE / NOT CCTV</h1>
<div class="notice"><strong>시각 검수 미완료 / VISUAL REVIEW PENDING · visualAccepted=false</strong>
<p>기계적 비교 조건만 통과했습니다. HTML 생성은 렌더 실행·화질 검수·인수 성공을 뜻하지 않습니다.
실제 사건 복원이나 business tote 추적이 아닙니다. 픽셀 디코딩과 렌더 출처 진위는 이 뷰어가 검증하지 않습니다.</p></div>
<p>같은 geometry와 렌더 조건의 원본 PNG를 편집 없이 나란히 표시합니다. 경과 시간은 합성 시연용이며 사건 시각과 별개입니다.
각 이미지를 클릭하면 원본 픽셀 크기로 확대됩니다. 큰 이미지는 칸 안에서 스크롤합니다.</p>
<p class="sources">{sources}</p>
{"".join(rows)}
<section><h2>시각 검수 체크리스트 — 자동 인수 체크=false</h2>{checklist}
<p>체크는 현재 화면의 메모이며 저장·자동 인수에 반영되지 않습니다. 세 프레임을 모두 비교하여 별도 검수 기록을 남기세요.
아직 개선을 확인하지 않았으며 72/288프레임 확장을 승인하는 화면이 아닙니다.</p></section>
<details><summary>기계적 비교 결과와 한계</summary><pre>{details}</pre></details>
</main></body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", type=Path, required=True)
    parser.add_argument("--b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New .html file; parent directory must exist.")
    args = parser.parse_args()
    try:
        if args.output.suffix.lower() != ".html" or args.output.exists():
            raise ValueError("--output must name a new .html file; existing files are never overwritten.")
        if any(args.output.resolve().is_relative_to(folder.resolve()) for folder in (args.a, args.b)):
            raise ValueError("--output must be outside both input directories; inputs remain unchanged.")
        from compare_representatives import compare_runs
        comparison = compare_runs(args.a, args.b)
        page = build_html(args.a, args.b, comparison)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(page)
        print(json.dumps({"output": str(args.output.resolve()), "comparable": True,
                          "visualAccepted": False, "rendererInvoked": False}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, ImportError, Invalid) as exc:
        print(f"Review page refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
