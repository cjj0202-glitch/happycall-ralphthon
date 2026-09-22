"""Mux recorded browser video with observed original audio timing and stage captions.

python scripts/render_two_case_demo.py .local/demo-video/<run>/timeline.json
Use --audio-offset-ms for measured recording-epoch correction. Never infer fake narration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = (ROOT / ".local/demo-video").resolve()
FFMPEG = Path("C:/Users/choi8/AppData/Local/Programs/Python/Python314/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe")


def decoded_duration(file: Path, ffmpeg: Path) -> float:
    """Measure decoded samples, including MP3 gapless trim; never trust supplied duration."""
    decoded = subprocess.run([str(ffmpeg), "-hide_banner", "-nostdin", "-v", "error", "-i", str(file),
                              "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "48000", "-f", "s16le", "pipe:1"],
                             capture_output=True, check=True, timeout=60)
    duration = len(decoded.stdout) / 96000
    if not duration:
        raise SystemExit(f"No decoded audio samples: {file}")
    return duration


def finite_number(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise SystemExit(f"Invalid {label}: expected finite number")
    return float(value)


def narration_plan(manifest_path: Path, data: dict, ffmpeg: Path, occupied: list, total: float) -> list:
    """Place each unchanged CLOVA clip at an exact observed stage, rejecting collisions."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source") != "CLOVA Dubbing":
        raise SystemExit('Narration manifest source must be "CLOVA Dubbing"')
    if not isinstance(manifest.get("projectUrl"), str) or not manifest["projectUrl"].startswith("https://clovadubbing.naver.com/project/"):
        raise SystemExit("Provide the actual CLOVA project URL in the narration manifest")
    clips = manifest.get("clips")
    if not isinstance(clips, list) or not clips:
        raise SystemExit("Narration manifest clips must be a nonempty list")
    result = []
    for clip in clips:
        file = (manifest_path.parent / clip["file"]).resolve()
        if not file.is_relative_to(OUTPUT_ROOT) or file.suffix.lower() not in (".wav", ".mp3"):
            raise SystemExit("Narration must be a WAV/MP3 inside .local/demo-video")
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if clip.get("sha256") and clip["sha256"] != digest:
            raise SystemExit(f"Narration hash mismatch: {file}")
        matches = [stage for stage in data["stages"] if stage["title"] == clip["stageTitle"]]
        occurrence = clip.get("occurrence", 1)
        if type(occurrence) is not int or not 1 <= occurrence <= len(matches):
            raise SystemExit(f"Stage occurrence not found: {clip['stageTitle']} #{occurrence}")
        offset = finite_number(clip.get("offsetSeconds", 0), "narration offsetSeconds")
        gain = finite_number(clip.get("gainDb", manifest.get("gainDb", 0)), "narration gainDb")
        if offset < 0 or not -60 <= gain <= 12:
            raise SystemExit("Narration offset must be nonnegative; constant gain must be -60..12 dB")
        start = (matches[occurrence - 1]["epochMs"] - data["recordingEpochMs"]) / 1000 + offset
        duration = decoded_duration(file, ffmpeg)
        end = start + duration
        if start < 0 or end > total:
            raise SystemExit(f"Narration would be trimmed by recording: {file.name} [{start:.3f}, {end:.3f}]")
        for other in occupied:
            if start < other["endSeconds"] and end > other["startSeconds"]:
                raise SystemExit(f"Narration collision: {file.name} [{start:.3f}, {end:.3f}] overlaps {other['label']} [{other['startSeconds']:.3f}, {other['endSeconds']:.3f}]. Choose another stage or offset; no automatic retiming.")
        occupied.append({"label": file.name, "startSeconds": start, "endSeconds": end})
        result.append({"file": str(file), "sha256": digest, "source": manifest["source"], "projectUrl": manifest["projectUrl"],
                       "stageTitle": clip["stageTitle"], "occurrence": occurrence, "startSeconds": start,
                       "durationSeconds": duration, "endSeconds": end, "delayMs": round(start * 1000), "gainDb": gain,
                       "playbackRate": 1, "timeStretch": False})
    return result


def clock(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def ass_clock(seconds: float) -> str:
    ticks = max(0, round(seconds * 100))
    hours, remainder = divmod(ticks, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, centis = divmod(remainder, 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centis:02}"


def ass_text(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def write_ass(directory: Path, data: dict, total: float, *, captions: bool, clova_footer: bool) -> None:
    # Explicit 1080p coordinates avoid SRT's legacy PlayRes/style scaling ambiguity.
    margin = 38 if clova_footer else 18
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""
    header += f"Style: Stage,Malgun Gothic,30,&H00FFFFFF,&H00FFFFFF,&H60000000,&H60000000,0,0,0,0,100,100,0,0,3,6,0,2,50,50,{margin},1\n"
    header += "Style: Footer,Malgun Gothic,15,&H00FFFFFF,&H00FFFFFF,&H60000000,&H60000000,0,0,0,0,100,100,0,0,3,3,0,2,30,30,5,1\n"
    header += "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    lines = [header]
    if captions:
        for i, item in enumerate(data["stages"]):
            start = (item["epochMs"] - data["recordingEpochMs"]) / 1000
            end = (data["stages"][i + 1]["epochMs"] - data["recordingEpochMs"]) / 1000 if i + 1 < len(data["stages"]) else total
            text = "{\\b1\\fs30}" + ass_text(item["title"]) + "{\\b0\\fs26}\\N" + ass_text(item["detail"])
            lines.append(f"Dialogue: 0,{ass_clock(start)},{ass_clock(end)},Stage,,0,0,0,,{text}\n")
    if clova_footer:
        lines.append(f"Dialogue: 1,0:00:00.00,{ass_clock(total)},Footer,,0,0,0,,해설 음성: CLOVA Dubbing · 통화 음성: 별도 합성 시연 자료\n")
    (directory / "stages.ass").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline", type=Path)
    parser.add_argument("--ffmpeg", type=Path, default=FFMPEG)
    parser.add_argument("--audio-offset-ms", type=float, default=0)
    parser.add_argument("--no-captions", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--narration-manifest", type=Path, help='JSON: source="CLOVA Dubbing", projectUrl, clips=[{file, stageTitle, occurrence:1, offsetSeconds:0, gainDb:0}]')
    parser.add_argument("--clova-footer", action="store_true", help="Keep CLOVA attribution visible throughout the rendered video")
    args = parser.parse_args()
    timeline_path = args.timeline.resolve()
    if not timeline_path.is_relative_to(OUTPUT_ROOT):
        raise SystemExit("Timeline/output must stay inside .local/demo-video")
    data = json.loads(timeline_path.read_text(encoding="utf-8"))
    if not data.get("complete") or data.get("failure") or data.get("errors"):
        raise SystemExit("Incomplete or failed recording; inspect timeline before rendering")
    raw = Path(data["rawVideo"]).resolve()
    if not raw.is_relative_to(OUTPUT_ROOT) or not raw.is_file():
        raise SystemExit("Recorded raw video is missing or outside the output workspace")
    epoch = data["recordingEpochMs"]
    total = (data["endEpochMs"] - epoch) / 1000
    directory = timeline_path.parent
    output = directory / ("two-case-demo-clova.mp4" if args.narration_manifest else "two-case-demo.mp4")
    if output.exists():
        raise SystemExit("Output already exists; preserve it and select a new recording directory")
    cues = []
    for i, item in enumerate(data["stages"]):
        start = (item["epochMs"] - epoch) / 1000
        end = (data["stages"][i + 1]["epochMs"] - epoch) / 1000 if i + 1 < len(data["stages"]) else total
        cues.append(f"{i + 1}\n{clock(start)} --> {clock(end)}\n{item['title']}\n{item['detail']}\n")
    subtitles = directory / "stages.srt"
    subtitles.write_text("\n".join(cues), encoding="utf-8")
    command = [str(args.ffmpeg), "-hide_banner", "-nostdin", "-n", "-i", str(raw)]
    filters, tracks = [], []
    audio_plan, occupied = [], []
    for index, audio in enumerate(data["audio"], start=1):
        file = Path(audio["file"]).resolve()
        if hashlib.sha256(file.read_bytes()).hexdigest() != audio["sha256"]:
            raise SystemExit(f"Audio hash mismatch: {file}")
        events = [e for e in data["audioEvents"] if f"{audio['caseId']}.wav" in e["src"]]
        playing = [e for e in events if e["type"] == "playing"]
        if len(playing) != 1 or not any(e["type"] == "ended" for e in events):
            raise SystemExit("Audio must have one uninterrupted natural full playback; inspect timeline")
        event = playing[0]
        rate = event["playbackRate"]
        if rate != 1.5:
            raise SystemExit(f"Unexpected audio playback rate: {rate}")
        delay_ms = round(event["epochMs"] - epoch - event["currentTime"] / rate * 1000 + args.audio_offset_ms)
        if delay_ms < 0:
            raise SystemExit("Negative audio start; inspect recording timing")
        command += ["-i", str(file)]
        # atempo changes duration while preserving pitch. No additional voice effects or normalization.
        filters.append(f"[{index}:a]atempo={rate},adelay={delay_ms}:all=1[a{index}]")
        tracks.append(f"[a{index}]")
        audio_plan.append({"file": str(file), "delayMs": delay_ms, "playbackRate": rate})
        occupied.append({"label": audio["caseId"] + " original call", "startSeconds": delay_ms / 1000,
                         "endSeconds": delay_ms / 1000 + decoded_duration(file, args.ffmpeg) / rate})
    narration = narration_plan(args.narration_manifest.resolve(), data, args.ffmpeg, occupied, total) if args.narration_manifest else []
    if args.clova_footer and not narration:
        raise SystemExit("CLOVA attribution requires actual narration clips, not an empty source claim")
    for index, clip in enumerate(narration, start=len(audio_plan) + 1):
        command += ["-i", clip["file"]]
        # Preserve downloaded CLOVA speed and pitch: only fixed gain and placement delay.
        filters.append(f"[{index}:a]volume={clip['gainDb']}dB,adelay={clip['delayMs']}:all=1[a{index}]")
        tracks.append(f"[a{index}]")
    filters.append("".join(tracks) + f"amix=inputs={len(tracks)}:normalize=0,apad[aout]")
    command += ["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", "[aout]"]
    if not args.no_captions or args.clova_footer:
        write_ass(directory, data, total, captions=not args.no_captions, clova_footer=args.clova_footer)
        command += ["-vf", "ass=stages.ass"]
    command += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-t", str(total), "-movflags", "+faststart", str(output)]
    plan = {"command": command, "cwd": str(directory), "audio": audio_plan, "narration": narration, "totalSeconds": total,
            "audioOffsetMs": args.audio_offset_ms, "recordingEpochMethod": data["epochMethod"],
            "notice": "Real browser recording; subtitles are editorial stage labels. Call audio uses pitch-preserving 1.5x. CLOVA narration retains original speed/pitch, with optional fixed gain only. All speech intervals checked for collisions."}
    (directory / "render-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.plan_only:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    with (directory / "ffmpeg.log").open("w", encoding="utf-8") as log:
        subprocess.run(command, cwd=directory, stdout=log, stderr=subprocess.STDOUT, check=True)
    print(output)


if __name__ == "__main__":
    main()
