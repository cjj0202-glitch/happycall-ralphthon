"""Create an offline A/B or verified single-package review page; never render."""
from __future__ import annotations

import argparse
import base64
import hashlib
from html import escape
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

from compare_representatives import ANCHOR, CLOCK, Invalid, fingerprint, match_bytes, parse_json, read_fixed


FRAMES = ((1, 0.0, "진입"), (133, 5.5, "분기"), (288, 287 / 24, "도착·정지"))
CHECKS = ("물성 구분: 바닥·강철·벨트·노란 가드", "가드·벨트·바닥 접촉과 간섭",
          "상자의 진입·분기·도착 판독", "그림자 입자와 접촉 경계 보존")
PACKAGE_FRAMES = {"prepare": (), "representatives": (1, 133, 288),
                  "short": tuple(range(73, 145)), "animation": tuple(range(1, 289))}
PACKAGE_SELECTION = {"prepare": (), "representatives": (1, 133, 288),
                     "short": (73, 133, 144), "animation": (1, 133, 288)}
MAX_EMBED_BYTES = 16 * 1024 * 1024
MAX_METADATA_BYTES = 4 * 1024 * 1024


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


def _package_directory(path: Path) -> Path:
    """Reject links before resolving any directory in the input path."""
    absolute = Path(path).absolute()
    for item in (absolute, *absolute.parents):
        info = item.lstat()
        if not stat.S_ISDIR(info.st_mode) or item.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Package input and its parents must be real directories, not links.")
    return absolute.resolve(strict=True)


def _verified_file(directory: Path, descriptor: dict, keep: bool = False, limit: int | None = None) -> bytes:
    """Rehash every input; retain only metadata and selected images, in bounded memory."""
    item = fingerprint(descriptor)
    path = directory / item["name"]
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or path.is_symlink() or info.st_nlink != 1
            or getattr(info, "st_file_attributes", 0) & 0x400 or info.st_size != item["bytes"]):
        raise ValueError(f"Package input changed or is not a regular file: {item['name']}")
    if limit is not None and item["bytes"] > limit:
        raise ValueError("Review embedding memory limit exceeded; no page created.")
    digest, size, chunks = hashlib.sha256(), 0, []
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise ValueError("Package file changed while opening it.")
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > item["bytes"] or (limit is not None and size > limit):
                raise ValueError("Package file changed size or exceeded the memory limit.")
            digest.update(chunk)
            if keep:
                chunks.append(chunk)
    if size != item["bytes"] or digest.hexdigest() != item["sha256"]:
        raise ValueError(f"Package input changed since verification: {item['name']}")
    return b"".join(chunks)


def build_package_html(package_dir: Path, verification: dict) -> str:
    """Use a verifier result, recheck its complete file snapshot, and embed a stated subset."""
    if (not isinstance(verification, dict)
            or verification.get("schemaVersion") != "pc3-render-package-verification-v1"
            or verification.get("valid") is not True or verification.get("status") != "PASS_WITH_PENDING"
            or verification.get("failures") != []
            or any(verification.get(key) is not False for key in
                   ("visualAccepted", "pixelDecoded", "videoDecoded", "authenticityVerified"))):
        raise ValueError("A valid package verification with pending visual acceptance is required.")
    mode, source = verification.get("mode"), verification.get("sourceCommit")
    if not isinstance(mode, str) or mode not in PACKAGE_FRAMES or not isinstance(source, str) or not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("Unsupported package mode or source commit.")
    images, videos, descriptors = verification.get("images"), verification.get("videos", []), verification.get("inputDigests")
    if not all(isinstance(value, list) for value in (images, videos, descriptors)):
        raise ValueError("Verified image, video and input digest lists are required.")
    expected_frames = PACKAGE_FRAMES[mode]
    if len(images) != len(expected_frames):
        raise ValueError("Image denominator does not match the verified mode.")
    indexed = {}
    for image, frame in zip(images, expected_frames):
        if (not isinstance(image, dict) or type(image.get("frame")) is not int or image["frame"] != frame
                or image.get("name") != f"frame-{frame:04d}.png"
                or type(image.get("elapsedSeconds")) not in (int, float)
                or not math.isfinite(image["elapsedSeconds"])
                or not math.isclose(image["elapsedSeconds"], (frame - 1) / 24, rel_tol=0, abs_tol=1e-9)):
            raise ValueError("Verified image frame, name or illustrative elapsed time is inconsistent.")
        indexed[image["name"]] = fingerprint(image)
    for video in videos:
        item = fingerprint(video)
        if not item["name"].endswith(".mp4") or item["name"] in indexed:
            raise ValueError("Invalid or duplicate explicitly verified video name.")
        indexed[item["name"]] = item
    expected_names = set(indexed) | {"render-report.json", "tracks.json", "case-0002-ww3.blend"}
    by_name = {}
    for descriptor in descriptors:
        item = fingerprint(descriptor)
        if item["name"] in by_name:
            raise ValueError("Duplicate verified input digest.")
        by_name[item["name"]] = item
    if set(by_name) != expected_names or any(by_name[name] != item for name, item in indexed.items()):
        raise ValueError("Verified input list or image/video binding is inconsistent.")
    directory = _package_directory(package_dir)
    if {path.name for path in directory.iterdir()} != expected_names:
        raise ValueError("Package contents changed after verification.")
    selected = {f"frame-{frame:04d}.png" for frame in PACKAGE_SELECTION[mode]}
    if sum(by_name[name]["bytes"] for name in selected) > MAX_EMBED_BYTES:
        raise ValueError("Selected PNG bytes exceed the review embedding memory limit.")
    saved = {}
    for name, descriptor in by_name.items():
        metadata = name in ("render-report.json", "tracks.json")
        keep = metadata or name in selected
        saved_value = _verified_file(directory, descriptor, keep, MAX_METADATA_BYTES if metadata else MAX_EMBED_BYTES if keep else None)
        if keep:
            saved[name] = saved_value
    report, tracks = parse_json(saved["render-report.json"]), parse_json(saved["tracks.json"])
    if (report.get("eventAnchor") != ANCHOR or tracks.get("eventAnchor") != ANCHOR
            or report.get("clockMode") != CLOCK or tracks.get("clockMode") != CLOCK
            or type(report.get("renderedFrameCount")) is not int or report["renderedFrameCount"] != len(expected_frames)):
        raise ValueError("Verified package metadata is inconsistent with its event or image denominator.")
    anchor = report.get("eventAnchor", {})
    fixed_time = escape(str(anchor.get("occurredAt", "미확인")))
    cards = []
    for frame in PACKAGE_SELECTION[mode]:
        name = f"frame-{frame:04d}.png"
        raw = saved[name]
        if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Verified image is not a PNG.")
        uri = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
        cards.append(f'<section><h2>프레임 {frame} · 시연 +{(frame - 1) / 24:.6f}초</h2>'
                     f'<details class="picture"><summary><span>Enter/클릭: 원본 크기로 확대·접기</span>'
                     f'<img src="{uri}" alt="합성 원본 프레임 {frame}, 시각 검수 미완료"></summary></details></section>')
    count = len(expected_frames)
    summary = f"표시 PNG {len(cards)} / 검증 목록 PNG {count} · 좌표 {len(tracks.get('frames', []))}행"
    no_images = '<p class="notice">prepare: PNG 0장. 장면 준비 metadata이며 렌더·영상 완료가 아닙니다.</p>' if not count else ""
    metadata = {"verification": verification, "renderReport": report, "tracks": tracks}
    escaped_metadata = escape(json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False))
    checklist = "".join(f'<label><input type="checkbox"> 미검사 — {escape(item)}</label>' for item in CHECKS)
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; object-src 'none'">
<title>합성 렌더 패키지 검수 — 미완료</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#101820;color:#edf2f7;font:16px/1.5 system-ui,sans-serif}}
main{{max-width:1400px;margin:auto;padding:24px}}h1{{font-size:25px}}h2{{font-size:20px}}
.notice{{border:2px solid #f6bd60;padding:16px;background:#28251d}}section{{margin:24px 0}}
.picture{{max-width:100%;overflow:auto}}summary{{cursor:pointer;padding:8px}}summary:focus-visible{{outline:3px solid #f6bd60}}
img{{display:block;max-width:100%;height:auto}}.picture[open] img{{max-width:none}}label{{display:block;margin:8px 0}}
pre,p{{overflow-wrap:anywhere}}pre{{white-space:pre-wrap}}@media(max-width:700px){{main{{padding:12px}}}}
</style></head><body><main><h1>합성 패키지 · SYNTHETIC SCENE / NOT CCTV</h1>
<p class="notice"><strong>시각 검수 미완료 / VISUAL REVIEW PENDING · visualAccepted=false</strong><br>
파일·메타데이터 대조 결과입니다. 이 페이지 생성은 렌더 실행, 동영상 완성, 픽셀 품질 또는 정본 인수의 증거가 아닙니다.</p>
<p>모드: {escape(mode)} · {summary}<br>생성 소스 주장: {escape(source)} (출처 진위 검증 아님)</p>
<p>고정 사건 시각: {fixed_time}<br>시연 경과초는 (frame−1)/24이며 사건 시각과 별개입니다.
CASE-0002 / W-W3 / SYN-CAM-02 · 업무 토트 미확인(null).</p>
<p>bbox 출처는 synthetic-scene-ground-truth이며 실제 측정·AI 검출이 아닙니다. occlusionTested=false.
전체 metadata와 선택된 원본 PNG를 구분합니다. 일부 PNG만 표시하므로 모든 프레임의 시각 검수가 아닙니다.
동영상 {len(videos)}개는 파일 해시 대조만 했으며 재생·디코딩하지 않았습니다. short는 72장이고 12초 완성이 아닙니다.</p>
{no_images}{''.join(cards)}<section><h2>검수 메모 — 자동 인수 체크=false</h2>{checklist}
<p>체크는 이 화면에만 적용되고 저장·자동 인수에 반영되지 않습니다.</p></section>
<details><summary>전체 메타데이터와 PENDING / NOT_RUN 항목</summary><pre>{escaped_metadata}</pre></details>
</main></body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--a", type=Path)
    choice.add_argument("--package", type=Path)
    parser.add_argument("--b", type=Path)
    parser.add_argument("--expectations", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New .html file; parent directory must exist.")
    args = parser.parse_args()
    if (args.a is not None and (args.b is None or args.expectations is not None)
            or args.package is not None and (args.b is not None or args.expectations is None)):
        parser.error("Choose --a/--b together, or --package/--expectations together; do not mix modes.")
    try:
        if args.output.suffix.lower() != ".html" or args.output.exists():
            raise ValueError("--output must name a new .html file; existing files are never overwritten.")
        inputs = (args.a, args.b) if args.a is not None else (args.package,)
        if any(args.output.resolve().is_relative_to(folder.resolve()) for folder in inputs):
            raise ValueError("--output must be outside both input directories; inputs remain unchanged.")
        if args.package is not None:
            from verify_render_package import Invalid as PackageInvalid, load_expectations, verify_package
            try:
                expectations = load_expectations(args.expectations)
                expectation_dir = _package_directory(args.expectations.parent)
                if args.expectations.stat().st_size > MAX_METADATA_BYTES:
                    raise ValueError("Expectation metadata exceeds the review memory limit.")
                expectation_bytes = read_fixed(expectation_dir, args.expectations.name)
                if json.dumps(parse_json(expectation_bytes), sort_keys=True) != json.dumps(expectations, sort_keys=True):
                    raise ValueError("Expectations changed while loading them.")
                expectation_digest = {"name": args.expectations.name, "bytes": len(expectation_bytes),
                                      "sha256": hashlib.sha256(expectation_bytes).hexdigest()}
                verification = verify_package(args.package, expectations)
            except PackageInvalid as exc:
                raise ValueError(f"{exc.code}: {exc.detail}") from exc
            page = build_package_html(args.package, verification)
            _verified_file(expectation_dir, expectation_digest, limit=MAX_METADATA_BYTES)
            result = {"valid": True, "mode": verification["mode"]}
        else:
            from compare_representatives import compare_runs
            comparison = compare_runs(args.a, args.b)
            page = build_html(args.a, args.b, comparison)
            result = {"comparable": True}
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(page)
        print(json.dumps({"output": str(args.output.resolve()), **result,
                          "visualAccepted": False, "rendererInvoked": False}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, ImportError, Invalid) as exc:
        print(f"Review page refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
