"""Package a verified full PNG animation using explicitly supplied local tools.

No download, Blender render, registration or visual approval is performed.
Only a new output directory is written. Failed/partial output is never reused.
FFprobe is optional; FFmpeg full-frame decoding and MP4 timing checks are not.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess

try:
    from . import verify_full_animation as verifier
except ImportError:
    import verify_full_animation as verifier

common = verifier.common
require = common.require
same = common.same
Invalid = common.Invalid
VIDEO = "sorter-demo.mp4"
TRACKS = "sorter-demo.tracks.json"
DESCRIPTOR = "sorter-demo.tracks.descriptor.json"
REPORT = "candidate-report.json"
PARTIAL = "sorter-demo.partial.mp4"


def _result():
    return {"schemaVersion": "pc3-full-animation-media-candidate-v1", "valid": False, "status": "FAIL",
            "failures": [], "pending": [
                {"code": "VISUAL_REVIEW_PENDING", "detail": "Successful encoding/decoding does not approve visual quality, contact, occlusion, motion or flicker."},
                {"code": "SOURCE_RECEIPT_BYTES_NOT_RECHECKED", "detail": "M5 compares source and receipt declarations to independent expectations; it does not re-open their original files."},
                {"code": "FINAL_SCENE_READBACK_NOT_RUN", "detail": "Stored scene readback is pre-render evidence, not a new Blender inspection."},
                {"code": "AUTHENTICITY_UNVERIFIED", "detail": "Hashes and process output do not authenticate the issuer or prove the executing source commit."},
                {"code": "PRODUCT_REGISTRATION_PENDING", "detail": "No Release, product manifest, frontend or registration has been changed."}],
            "visualAccepted": False, "mainRegistration": False, "authenticityVerified": False,
            "encoded": False, "videoDecoded": False, "pixelDecoded": False, "assets": {}, "commands": [],
            "videoProbe": None, "decode": None, "mp4": None,
            "notice": "Candidate only. A decoded 12-second synthetic video and byte-identical tracks still require pc1 visual review and product integration."}


def _run(argv, timeout):
    """Explicit argv, no shell, no stdin, bounded execution, hidden on Windows."""
    done = subprocess.run(argv, shell=False, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
    require(type(done.stdout) is str and type(done.stderr) is str
            and len(done.stdout) <= 4*1024*1024 and len(done.stderr) <= 4*1024*1024,
            "Tool output is missing or exceeds the supported limit.", "PROCESS")
    require(done.returncode == 0, "Media tool returned a nonzero exit code.", "PROCESS")
    return done


def _execute(result, argv, timeout, role):
    record = {"role": role, "argv": [str(item) for item in argv], "timeoutSeconds": timeout}
    result["commands"].append(record)
    done = _run(record["argv"], timeout)
    record.update(returncode=done.returncode,
                  stdoutSha256=hashlib.sha256(done.stdout.encode("utf-8")).hexdigest(),
                  stderrSha256=hashlib.sha256(done.stderr.encode("utf-8")).hexdigest())
    return done


def _rational(value):
    require(type(value) is str and len(value) <= 64
            and re.fullmatch(r"-?\d+(?:\.\d+)?(?:/\d+)?", value), "Invalid media numeric metadata.", "METADATA")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError, OverflowError) as error:
        raise Invalid("METADATA", "Invalid media numeric metadata.") from error


def _input_metadata(text):
    """Read the Input #0 block, never Output rawvideo or progress messages."""
    starts = list(re.finditer(r"(?m)^Input #\d+,", text))
    require(len(starts) == 1 and text[starts[0].start():].startswith("Input #0,"),
            "Decoder metadata must describe exactly one input.", "METADATA")
    block = text[starts[0].start():]
    require("\nStream mapping:" in block, "Decoder input metadata boundary is missing.", "METADATA")
    block = block.split("\nStream mapping:", 1)[0]
    streams = [line.strip() for line in block.splitlines() if re.match(r"\s*Stream #", line)]
    require(len(streams) == 1 and re.match(r"Stream #0:0(?:\[.*?\])?(?:\([^)]*\))?: Video: h264(?:\s|\()", streams[0]),
            "Input must contain one H.264 video stream and no other streams.", "METADATA")
    line = streams[0]
    require(re.search(r"\byuv420p(?:\([^)]*\))?,\s*1920x1080\s+\[SAR 1:1 DAR 16:9\]", line)
            and re.search(r"(?:,\s*)24(?:\.0+)? fps,\s*24(?:\.0+)? tbr,", line),
            "Input pixel format, dimensions, aspect or frame rate differs.", "METADATA")
    clock = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?),\s*start:\s*(-?\d+(?:\.\d+)?),", block)
    require(clock is not None and int(clock[1]) == 0 and int(clock[2]) == 0
            and _rational(clock[3]) == 12 and _rational(clock[4]) == 0,
            "Input duration/start metadata differs from twelve seconds at zero.", "METADATA")
    return {"method": "ffmpeg-input-block", "codec": "h264", "pixelFormat": "yuv420p",
            "width": 1920, "height": 1080, "fps": 24, "startSeconds": 0,
            "displayedDurationSeconds": 12, "durationDisplayRounded": True,
            "notice": "Rounded Input duration is corroborated by exact MP4 clocks and all decoded frame timestamps."}


def _framehash(text):
    headers, rows = {}, []
    wanted = {"format": "frame checksums", "version": "2", "hash": "SHA256", "tb 0": "1/24",
              "media_type 0": "video", "codec_id 0": "rawvideo", "dimensions 0": "1920x1080", "sar 0": "1/1"}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            key, separator, value = line[1:].partition(":")
            if separator and key.strip() in wanted:
                key = key.strip()
                require(key not in headers, "Duplicate decoded stream header.", "DECODE")
                headers[key] = value.strip()
            elif re.match(r"(?:tb|media_type|codec_id|dimensions|sar)\s+\d+", key):
                raise Invalid("DECODE", "Unexpected decoded stream header.")
            continue
        fields = [item.strip() for item in line.split(",")]
        require(len(fields) == 6 and all(re.fullmatch(r"\d+", item) for item in fields[:5])
                and re.fullmatch(r"[0-9a-f]{64}", fields[5]), "Malformed decoded frame checksum row.", "DECODE")
        stream, dts, pts, duration, size = map(int, fields[:5])
        frame = len(rows)
        require(stream == 0 and dts == pts == frame and duration == 1 and size == 3110400,
                "Decoded frame order, timestamp, duration or pixel byte count differs.", "DECODE")
        rows.append(fields[5])
    require(headers == wanted and len(rows) == 288,
            "Full decode must yield exactly 288 1080p yuv420p frames at 24 fps.", "DECODE")
    return {"frameCount": 288, "timeBase": "1/24", "firstPts": 0, "lastPts": 287, "frameDuration": 1,
            "durationSeconds": 12, "width": 1920, "height": 1080, "decodedFrameBytes": 3110400,
            "frameSha256": rows, "method": "ffmpeg-full-eof-framehash", "pixelFormat": "yuv420p"}


def _probe_json(raw):
    value = common.parse_json(raw.encode("utf-8"))
    streams, fmt = value.get("streams"), value.get("format")
    require(type(streams) is list and len(streams) == 1 and type(streams[0]) is dict and type(fmt) is dict,
            "FFprobe must report exactly one video stream.", "METADATA")
    stream = streams[0]
    require(stream.get("codec_type") == "video" and stream.get("codec_name") == "h264"
            and stream.get("pix_fmt") == "yuv420p" and type(stream.get("width")) is int and stream["width"] == 1920
            and type(stream.get("height")) is int and stream["height"] == 1080,
            "FFprobe video codec/format/resolution differs.", "METADATA")
    require(all(_rational(stream.get(key)) == 24 for key in ("r_frame_rate", "avg_frame_rate"))
            and stream.get("nb_frames") == "288" and stream.get("nb_read_frames") == "288"
            and _rational(stream.get("duration")) == 12 and _rational(fmt.get("duration")) == 12
            and _rational(stream.get("start_time")) == 0 and _rational(fmt.get("start_time")) == 0,
            "FFprobe frame count, exact duration, FPS or start time differs.", "METADATA")
    return {"method": "ffprobe-json-count-frames", "codec": "h264", "pixelFormat": "yuv420p",
            "width": 1920, "height": 1080, "fps": 24, "frameCount": 288, "durationSeconds": 12, "startSeconds": 0}


def _boxes(stream, start, end):
    boxes, cursor = [], start
    while cursor < end:
        require(end-cursor >= 8 and len(boxes) < 10000, "Truncated/excessive MP4 box header.", "MP4")
        stream.seek(cursor)
        header = stream.read(8)
        require(len(header) == 8, "Truncated MP4 box header.", "MP4")
        size, kind = struct.unpack(">I4s", header)
        header_size = 8
        if size == 1:
            extended = stream.read(8)
            require(len(extended) == 8, "Truncated extended MP4 box.", "MP4")
            size, header_size = struct.unpack(">Q", extended)[0], 16
        elif size == 0:
            size = end-cursor
        require(header_size <= size <= end-cursor, "MP4 box size escapes its parent.", "MP4")
        boxes.append((kind, cursor+header_size, cursor+size, cursor))
        cursor += size
    require(cursor == end, "MP4 box boundaries differ.", "MP4")
    return boxes


def _one(boxes, kind):
    matches = [box for box in boxes if box[0] == kind]
    require(len(matches) == 1, "Required MP4 box is missing or duplicated.", "MP4")
    return matches[0]


def _payload(stream, box, maximum=1024*1024):
    size = box[2]-box[1]
    require(size <= maximum, "MP4 metadata exceeds the supported limit.", "MP4")
    stream.seek(box[1])
    data = stream.read(size)
    require(len(data) == size, "Truncated MP4 metadata.", "MP4")
    return data


def _clock(data):
    require(len(data) >= 20 and data[0] in (0, 1), "Unsupported MP4 clock metadata.", "MP4")
    if data[0] == 0:
        scale, duration = struct.unpack_from(">II", data, 12)
    else:
        require(len(data) >= 32, "Truncated 64-bit MP4 clock.", "MP4")
        scale, duration = struct.unpack_from(">IQ", data, 20)
    require(scale > 0 and duration == scale*12, "MP4 clock duration must be exactly twelve seconds.", "MP4")
    return scale, duration


def _mp4(path):
    path = common._safe_path(path)
    before = verifier._stamp(path)
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1
                and before == (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns),
                "MP4 changed before inspection.", "INPUT_CHANGED")
        top = _boxes(stream, 0, opened.st_size)
        require(all(box[0] in (b"ftyp", b"moov", b"mdat", b"free") for box in top),
                "Unexpected/fragmented MP4 top-level box.", "MP4")
        _one(top, b"ftyp")
        moov, mdat = _one(top, b"moov"), _one(top, b"mdat")
        require(moov[3] < mdat[3] and mdat[2] > mdat[1], "MP4 is empty or is not faststart (moov before mdat).", "MP4")
        movie = _boxes(stream, moov[1], moov[2])
        movie_scale, _ = _clock(_payload(stream, _one(movie, b"mvhd")))
        trak = _one(movie, b"trak")
        mdia = _one(_boxes(stream, trak[1], trak[2]), b"mdia")
        media = _boxes(stream, mdia[1], mdia[2])
        handler = _payload(stream, _one(media, b"hdlr"))
        require(len(handler) >= 12 and handler[8:12] == b"vide", "MP4 track must be video.", "MP4")
        scale, _ = _clock(_payload(stream, _one(media, b"mdhd")))
        minf = _one(media, b"minf")
        stbl = _one(_boxes(stream, minf[1], minf[2]), b"stbl")
        table = _boxes(stream, stbl[1], stbl[2])
        stsd = _one(table, b"stsd")
        header = _payload(stream, stsd)
        require(len(header) >= 8 and struct.unpack_from(">I", header, 4)[0] == 1,
                "MP4 must have one video sample description.", "MP4")
        entries = _boxes(stream, stsd[1]+8, stsd[2])
        require(len(entries) == 1, "MP4 contains unexpected sample descriptions.", "MP4")
        entry = _one(entries, b"avc1")
        description = _payload(stream, entry)
        require(len(description) >= 78 and struct.unpack_from(">HH", description, 24) == (1920, 1080),
                "MP4 sample entry is not 1920x1080 AVC.", "MP4")
        timing = _payload(stream, _one(table, b"stts"))
        require(len(timing) >= 8, "MP4 sample timing is missing.", "MP4")
        count = struct.unpack_from(">I", timing, 4)[0]
        require(0 < count <= 288 and len(timing) == 8+count*8 and scale % 24 == 0,
                "Invalid MP4 sample timing table.", "MP4")
        total = 0
        for offset in range(8, len(timing), 8):
            samples, delta = struct.unpack_from(">II", timing, offset)
            require(samples > 0 and delta == scale//24, "MP4 sample timing is not constant 24 fps.", "MP4")
            total += samples
        require(total == 288, "MP4 sample table must contain exactly 288 frames.", "MP4")
    require(verifier._stamp(path) == before, "MP4 changed during inspection.", "INPUT_CHANGED")
    return {"faststart": True, "videoTracks": 1, "sampleEntry": "avc1", "width": 1920, "height": 1080,
            "sampleCount": 288, "fps": 24, "movieTimeScale": movie_scale, "mediaTimeScale": scale, "durationSeconds": 12}


def _new_output(path, inputs):
    path = Path(path)
    require(".." not in path.parts, "Output parent traversal is forbidden.", "OUTPUT")
    parent = common._safe_path(path.parent, directory=True)
    output = parent / common._safe_name(path.name)
    require(not os.path.lexists(output), "Output already exists; failed or partial output cannot be reused.", "OUTPUT")
    for item in inputs:
        require(not output.is_relative_to(item) and not item.is_relative_to(output),
                "Output must not overlap any input, source or tool location.", "OUTPUT")
    return output


def _assert_inputs(package, manifest, manifest_digest, digests, stamps, tools):
    require({path.name for path in package.iterdir()} == verifier.NAMES, "Input package inventory changed.", "INPUT_CHANGED")
    for expected in digests:
        path = package / expected["name"]
        require(verifier._stamp(path) == stamps[path.name], "Input package timestamp/identity changed.", "INPUT_CHANGED")
        _, actual = common._file(package, path.name)
        require(same(actual, expected), "Input package bytes changed during packaging.", "INPUT_CHANGED")
    _, actual = common._file(manifest.parent, manifest.name)
    require(same(actual, manifest_digest), "Independent expectations changed during packaging.", "INPUT_CHANGED")
    for path, expected in tools:
        _, actual = common._file(path.parent, path.name)
        require(same(actual, expected), "Media tool bytes changed during packaging.", "INPUT_CHANGED")


def _directory_identity(directory, expected):
    current = common._safe_path(directory, directory=True).stat()
    require((current.st_dev, current.st_ino) == expected,
            "Owned output directory identity changed.", "OUTPUT")


def _assert_outputs(directory, identity, descriptors):
    _directory_identity(directory, identity)
    require({path.name for path in directory.iterdir()} == {item["name"] for item in descriptors},
            "Final output inventory changed before publication.", "OUTPUT")
    for expected in descriptors:
        _, actual = common._file(directory, expected["name"])
        require(same(actual, expected), "Final output bytes changed before publication.", "OUTPUT")
    _directory_identity(directory, identity)


def _write_new(directory, name, data, markers=None, *, directory_identity=None):
    common._safe_path(directory, directory=True)
    if directory_identity is not None:
        _directory_identity(directory, directory_identity)
    path = directory / name
    with path.open("xb") as stream:
        opened = os.fstat(stream.fileno())
        if markers is not None:
            markers.append((path, opened.st_dev, opened.st_ino))
        stream.write(data)
    _, digest = common._file(directory, name)
    require(digest["bytes"] == len(data) and digest["sha256"] == hashlib.sha256(data).hexdigest(),
            "New output bytes differ from the intended payload.", "OUTPUT")
    if directory_identity is not None:
        _directory_identity(directory, directory_identity)
    return digest


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def package_full_animation(package_dir: Path, expectations_path: Path, output_dir: Path,
                           ffmpeg_path: Path, ffprobe_path: Path | None = None, *, timeout=600) -> dict:
    """Validate, encode and fully decode into a new candidate directory only."""
    result, output, markers = _result(), None, []
    try:
        require(type(timeout) is int and 1 <= timeout <= 3600, "Timeout must be 1..3600 seconds.", "OPTIONS")
        package = common._safe_path(package_dir, directory=True)
        manifest = common._safe_path(expectations_path)
        require(not manifest.is_relative_to(package), "Expectations must be independent and outside the package.", "PATH")
        raw, manifest_digest = common._file(manifest.parent, manifest.name, read=True, limit=2*1024*1024)
        expected = common.parse_json(raw)
        checked = verifier.verify_full_animation(package, expected)
        require(checked.get("valid") is True and checked.get("status") == "PASS_WITH_PENDING"
                and checked.get("failures") == [] and len(checked.get("inputDigests", [])) == 291,
                "M5 full-animation verification failed; no encoder was started.", "M5")
        stamps = {item["name"]: verifier._stamp(package / item["name"]) for item in checked["inputDigests"]}
        tools = []
        for supplied in (ffmpeg_path, ffprobe_path):
            if supplied is not None:
                try:
                    tool = common._safe_path(supplied)
                    _, digest = common._file(tool.parent, tool.name)
                except Exception as error:
                    raise Invalid("TOOL", "Explicit media executable is unavailable or unsafe; no installation is attempted.") from error
                require(tool.suffix.lower() not in (".bat", ".cmd", ".ps1"), "Shell scripts are not media executables.", "TOOL")
                tools.append((tool, digest))
        require(ffmpeg_path is not None and tools, "An existing explicit FFmpeg executable is required.", "TOOL")
        ffmpeg = tools[0][0]
        ffprobe = tools[1][0] if ffprobe_path is not None else None
        forbidden = [package, manifest, Path(__file__).resolve().parent, *[path.parent for path, _ in tools]]
        proposed = _new_output(output_dir, forbidden)
        _assert_inputs(package, manifest, manifest_digest, checked["inputDigests"], stamps, tools)
        proposed.mkdir()
        output = common._safe_path(proposed, directory=True)
        directory_identity = output.stat().st_dev, output.stat().st_ino
        result.update(outputDirectory=str(output), sourceCommit=expected["sourceCommit"],
                      expectationsFileDigest=manifest_digest, inputDigests=checked["inputDigests"],
                      tools=[{"path": str(path), **digest} for path, digest in tools])
        encode = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-framerate", "24",
                  "-start_number", "1", "-i", str(package / "frame-%04d.png"), "-map", "0:v:0", "-an",
                  "-frames:v", "288", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-aspect", "16:9", "-crf", "18",
                  "-preset", "medium", "-threads", "2", "-fps_mode", "passthrough", "-movflags", "+faststart",
                  str(output / PARTIAL)]
        _execute(result, encode, timeout, "encode")
        _, video_digest = common._file(output, PARTIAL)
        require(video_digest["bytes"] > 0, "Encoder did not produce a nonempty video.", "ENCODE")
        result["encoded"] = True
        result["mp4"] = _mp4(output / PARTIAL)
        decode = [str(ffmpeg), "-hide_banner", "-loglevel", "info", "-nostdin", "-xerror", "-err_detect", "explode",
                  "-threads", "2", "-i", str(output / PARTIAL), "-map", "0:v:0", "-an", "-sn", "-dn",
                  "-c:v", "rawvideo", "-threads", "2", "-fps_mode", "passthrough", "-f", "framehash", "-hash", "sha256", "pipe:1"]
        decoded = _execute(result, decode, timeout, "decode-all-frames")
        result["videoProbe"] = _input_metadata(decoded.stderr)
        result["decode"] = _framehash(decoded.stdout)
        if ffprobe is not None:
            probe = [str(ffprobe), "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(output / PARTIAL)]
            result["ffprobe"] = _probe_json(_execute(result, probe, timeout, "probe").stdout)
        _, after_video = common._file(output, PARTIAL)
        require(same(video_digest, after_video), "Video changed during validation.", "INPUT_CHANGED")
        result["videoDecoded"] = result["pixelDecoded"] = True
        _assert_inputs(package, manifest, manifest_digest, checked["inputDigests"], stamps, tools)
        require((common._safe_path(output, directory=True).stat().st_dev, output.stat().st_ino) == directory_identity
                and {path.name for path in output.iterdir()} == {PARTIAL}, "Output directory changed during packaging.", "OUTPUT")
        # The output directory is new, and -n/exclusive writes prohibit reuse.
        require(not os.path.lexists(output / VIDEO), "Final video already exists.", "OUTPUT")
        (output / PARTIAL).rename(output / VIDEO)
        video_digest["name"] = VIDEO
        track_raw, track_digest = common._file(package, "tracks.json", read=True)
        original_tracks = next(item for item in checked["inputDigests"] if item["name"] == "tracks.json")
        require(same(track_digest, original_tracks), "Tracks changed before their byte-for-byte copy.", "INPUT_CHANGED")
        copied = _write_new(output, TRACKS, track_raw, directory_identity=directory_identity)
        descriptor = {"schemaVersion": "oneflow-cctv-tracks-v1", "url": "/demo/sorter-demo.tracks.json",
                      "bytes": copied["bytes"], "sha256": copied["sha256"], "videoSha256": video_digest["sha256"]}
        _assert_inputs(package, manifest, manifest_digest, checked["inputDigests"], stamps, tools)
        _assert_outputs(output, directory_identity, [video_digest, copied])
        descriptor_digest = _write_new(output, DESCRIPTOR, _json_bytes(descriptor), markers,
                                       directory_identity=directory_identity)
        result["assets"] = {"video": video_digest, "tracks": copied, "tracksDescriptor": descriptor_digest}
        result["tracksDescriptor"] = descriptor
        result.update(valid=True, status="PASS_WITH_PENDING")
        _assert_outputs(output, directory_identity, [video_digest, copied, descriptor_digest])
        # This is the last published file; no successful report precedes checks.
        report_digest = _write_new(output, REPORT, _json_bytes(result), markers, directory_identity=directory_identity)
        _assert_inputs(package, manifest, manifest_digest, checked["inputDigests"], stamps, tools)
        _assert_outputs(output, directory_identity, [video_digest, copied, descriptor_digest, report_digest])
    except Exception as error:
        if isinstance(error, subprocess.TimeoutExpired):
            error = Invalid("TIMEOUT", "Media tool exceeded its explicit timeout and was terminated.")
        common._failure(result, error)
        result.pop("tracksDescriptor", None)
        if output is not None:
            # Remove only success markers whose identity belongs to this call.
            # Partial media is retained for diagnosis, and the directory cannot be reused.
            try:
                safe_output = common._safe_path(output, directory=True)
                info = safe_output.stat()
                safe_cleanup = (info.st_dev, info.st_ino) == directory_identity
            except Exception:
                safe_cleanup = False
            for path, device, inode in reversed(markers) if safe_cleanup else []:
                try:
                    info = path.lstat()
                    if stat.S_ISREG(info.st_mode) and (info.st_dev, info.st_ino) == (device, inode):
                        path.unlink()
                except OSError:
                    pass
            if safe_cleanup:
                try:
                    _write_new(output, "failure.json", _json_bytes(result), directory_identity=directory_identity)
                except Exception:
                    pass
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--expectations", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ffmpeg", required=True, type=Path)
    parser.add_argument("--ffprobe", type=Path)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    result = package_full_animation(args.package, args.expectations, args.output, args.ffmpeg, args.ffprobe, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
