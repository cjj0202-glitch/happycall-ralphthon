"""Render six local-only, explicitly procedural WMS MP4 candidates and an overlay.

Use the pinned dependencies in requirements.txt. Does not publish, install into
public/demo, register media, or change the existing CASE-0002 W-W3 sorter clip.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from media_contract import (ROOT, FIXTURE, OVERLAY, NOTICE, SECONDS, FPS, WIDTH, HEIGHT,
                            build_candidates, read_fixture, validate_overlay)


def generate() -> dict:
    import imageio_ffmpeg
    import PIL
    from PIL import Image, ImageDraw, ImageFont

    fixture = read_fixture()
    candidates, missing = build_candidates(fixture)
    output = ROOT / ".local/pc3-media"
    output.mkdir(parents=True, exist_ok=True)
    font_path = next((p for p in [Path("C:/Windows/Fonts/malgun.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc")] if p.is_file()), None)
    if font_path is None:
        raise RuntimeError("Korean font required (Malgun or NotoSansCJK); no silent missing-glyph output")
    fonts = {size: ImageFont.truetype(str(font_path), size) for size in (14, 17, 19, 22, 28)}
    colors = {"picking": "#77E2CC", "sorting": "#8AB6FC", "shipping": "#F6C179"}
    contact_frames = []

    def line(d, xy, value, size=17, color="#DCE9F4"):
        d.text(xy, str(value), fill=color, font=fonts[size])

    def frame_for(item, index):
        image = Image.new("RGB", (WIDTH, HEIGHT), "#111E30")
        draw = ImageDraw.Draw(image)
        accent = colors[item["stage"]]
        progress = index / (SECONDS * FPS - 1)
        record, event = item["source"]["processRecord"], item["source"]["event"]
        draw.rectangle((0, 0, WIDTH, 87), fill="#1B3045")
        line(draw, (25, 17), "합성 공정 설명 · 코드 애니메이션", 28)
        line(draw, (26, 56), f"{item['caseId']}  /  {event['id']}  /  {item['cameraId']}", 17, accent)
        line(draw, (25, 104), event["label"], 22, accent)
        line(draw, (25, 141), f"기록 발생시각 {event['time']}  ·  영상 경과 {index/FPS:04.1f}초", 17)
        line(draw, (25, 172), f"{item['relations']['storeId']}  |  {item['relations']['orderId']}  |  {event['location']}", 17)
        draw.rounded_rectangle((25, 217, 935, 399), radius=12, fill="#1B2C40", outline="#39516A", width=2)
        if item["stage"] == "picking":
            for x in (73, 140, 207):
                draw.rectangle((x, 242, x + 52, 358), outline="#6D8EAB", width=3)
                for y in (273, 310):
                    draw.line((x, y, x + 52, y), fill="#6D8EAB", width=2)
            start, end = (274, 305), (779, 305)
            line(draw, (83, 365), "피킹 셀", 17)
            line(draw, (722, 365), "가상 스캔 위치", 17)
            draw.line((774, 250, 774, 351), fill=accent, width=3)
            line(draw, (356, 239), "피킹 기록의 상품·단위를 보존", 19, accent)
        elif item["stage"] == "sorting":
            start, end = (125, 310), (771, 263)
            draw.line((104, 310, 492, 310, 773, 263), fill="#66809B", width=13)
            draw.line((492, 310, 775, 359), fill="#66809B", width=13)
            line(draw, (424, 226), f"계획 {record.get('schdChuteNo', '미확인')} / 실적 {record.get('rsltChuteNo', '미확인')}", 17)
            line(draw, (665, 366), "다른 분기 (개념)", 17)
            line(draw, (90, 237), "토트 연결은 미확인", 19, accent)
            if progress <= .5:
                start, end = (125, 310), (492, 310)
                progress *= 2
            else:
                start, end = (492, 310), (771, 263)
                progress = (progress - .5) * 2
        else:
            start, end = (117, 316), (720, 316)
            draw.line((100, 338, 755, 338), fill="#66809B", width=13)
            draw.rectangle((744, 246, 871, 360), outline=accent, width=3)
            line(draw, (766, 270), record.get("dock", "미확인"), 22, accent)
            line(draw, (119, 242), "출고 스캔 ≠ 점포 인도 완료", 19, accent)
        x = round(start[0] + (end[0] - start[0]) * progress)
        y = round(start[1] + (end[1] - start[1]) * progress)
        draw.rounded_rectangle((x - 24, y - 20, x + 24, y + 18), radius=5, fill=accent)
        draw.line((x - 14, y - 7, x + 14, y - 7), fill="#243C53", width=3)
        tote = item["relations"]["toteId"]
        product = record.get("product") or "공정 상품 미확인"
        quantity, unit = record.get("quantity"), record.get("unit")
        amount = "수량·단위 미확인" if quantity is None or unit is None else f"{quantity} {unit}"
        line(draw, (25, 414), f"선택 공정 토트: {tote or '미확인 (다른 공정 토트로 채우지 않음)'}", 17)
        line(draw, (25, 442), f"{product}  ·  {amount}  |  이동은 개념 연출, 실제 추적 아님", 17)
        draw.rectangle((0, 483, WIDTH, HEIGHT), fill="#3A3326")
        line(draw, (25, 492), "실제 CCTV / AI 영상 모델 결과가 아닙니다. 원인·작업자 귀책 미확인.", 19, "#F9D59F")
        line(draw, (25, 520), "후보 자산 · 메인 검토 및 등록 전 · 시스템 근거로 직접 채택하지 않습니다", 14, "#F9D59F")
        return image

    for item in candidates:
        path = output / Path(item["url"]).name
        writer = imageio_ffmpeg.write_frames(str(path), (WIDTH, HEIGHT), fps=FPS,
            codec="libx264", pix_fmt_in="rgb24", pix_fmt_out="yuv420p", quality=8,
            macro_block_size=1, output_params=["-preset", "fast", "-movflags", "+faststart"], ffmpeg_log_level="error")
        writer.send(None)
        try:
            for index in range(SECONDS * FPS):
                writer.send(frame_for(item, index).tobytes())
        finally:
            writer.close()
        # Decode every frame of the written file; generated source frames alone
        # cannot prove that the encoded MP4 plays or moves.
        reader = imageio_ffmpeg.read_frames(str(path), pix_fmt="rgb24")
        info = next(reader)
        sample_indices = {0, SECONDS * FPS // 3, 2 * SECONDS * FPS // 3, SECONDS * FPS - 1}
        samples, decoded = [], 0
        for index, raw in enumerate(reader):
            decoded += 1
            if index in sample_indices:
                samples.append(hashlib.sha256(raw).hexdigest())
            if index == SECONDS * FPS // 2:
                contact_frames.append(Image.frombytes("RGB", (WIDTH, HEIGHT), raw))
        item["bytes"] = path.stat().st_size
        item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        item["validation"] = {"decodedFrames": decoded, "distinctSampleFrames": len(set(samples)),
                              "width": info["size"][0], "height": info["size"][1],
                              "fps": info["fps"], "durationSeconds": info["duration"], "codec": info["codec"]}
        print(f"DECODED {item['id']} frames={decoded} bytes={item['bytes']}", flush=True)
    existing = [{"caseId": case["id"], "media": case.get("media", [])} for case in fixture["cases"]]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    overlay = {"schemaVersion": "pc3-wms-media-candidates-v1", "synthetic": True,
               "integrationStatus": "candidate-not-registered", "notice": NOTICE,
               "sourceHead": head, "sourceFixtureSha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
               "generatedAt": datetime.now(timezone.utc).isoformat(),
               "reproductionRuntime": {"python": sys.version.split()[0], "Pillow": PIL.__version__,
                   "imageioFfmpeg": imageio_ffmpeg.__version__, "ffmpeg": imageio_ffmpeg.get_ffmpeg_version(),
                   "fontFile": font_path.name, "fontSha256": hashlib.sha256(font_path.read_bytes()).hexdigest()},
               "generator": "scripts/media_pc3/generate_candidates.py", "mediaCandidates": candidates,
               "unregistered": missing, "existingRegistrationUnchanged": existing}
    validate_overlay(overlay, fixture, output)
    sheet = Image.new("RGB", (WIDTH * 2, HEIGHT * 3))
    for index, image in enumerate(contact_frames):
        sheet.paste(image, ((index % 2) * WIDTH, (index // 2) * HEIGHT))
    sheet.save(output / "decoded-contact-sheet.jpg", quality=92)
    (output / "generation-result.json").write_text(json.dumps(overlay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OVERLAY.parent.mkdir(parents=True, exist_ok=True)
    OVERLAY.write_text(json.dumps(overlay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"candidateCount": len(candidates), "unregisteredCount": len(missing), "overlay": str(OVERLAY),
            "outputDirectory": str(output), "verification": "all encoded frames decoded; hashes matched"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Revalidate metadata and local bytes without rendering")
    args = parser.parse_args()
    if args.verify_only:
        overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
        if overlay["sourceFixtureSha256"] != hashlib.sha256(FIXTURE.read_bytes()).hexdigest():
            raise ValueError("Fixture changed; regenerate/review candidates before adoption")
        validate_overlay(overlay, read_fixture(), ROOT / ".local/pc3-media")
        print("PASS: candidate metadata, relationships, encoded validation records and local byte hashes")
    else:
        print(json.dumps(generate(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
