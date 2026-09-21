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
STAGED_REPORT = "candidate-report.staged.json"
PARTIAL = "sorter-demo.partial.mp4"
IDENTITY_MATRIX = (65536, 0, 0, 0, 65536, 0, 0, 0, 1073741824)


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
            "notice": "Candidate only. A decoded 12-second synthetic video and byte-identical tracks still require pc1 visual review and product integration. "
                      "Consumers must call validate_candidate, not trust this report alone. Checks are finite snapshots; concurrent or later changes are not permanently prevented."}


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


def _zero_rotation(value):
    if type(value) is str:
        require(re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value) is not None,
                "Malformed rotation metadata.", "TRANSFORM")
        value = _rational(value.removeprefix("+"))
        require(value == 0, "Display rotation must be zero.", "TRANSFORM")
    else:
        require(common.number(value) and value == 0, "Display rotation must be a finite numeric zero.", "TRANSFORM")


def _text_transform(block):
    for line in block.splitlines():
        text = line.strip()
        key = re.match(r"([A-Za-z_][A-Za-z0-9_ ]*)\s*[:=]", text)
        transform_key = key and any(token in key[1].lower() for token in ("matrix", "rotat", "orientation", "crop", "transform"))
        if transform_key or re.match(r"(?:displaymatrix|display_matrix|matrix|rotate|rotation|orientation|crop|cropping|display_orientation)\b", text, re.I):
            known = re.fullmatch(r"displaymatrix:\s*rotation of ([+-]?\d+(?:\.\d+)?) degrees", text, re.I)
            rotate = re.fullmatch(r"rotate\s*:\s*([+-]?\d+(?:\.\d+)?)", text, re.I)
            require(known is not None or rotate is not None, "Unknown or malformed display transform metadata.", "TRANSFORM")
            _zero_rotation((known or rotate)[1])


def _probe_matrix(value):
    require(type(value) is str and len(value) <= 1024, "Malformed display matrix metadata.", "TRANSFORM")
    rows = [line.strip() for line in value.splitlines() if line.strip()]
    require(len(rows) == 3, "Display matrix must contain exactly three rows.", "TRANSFORM")
    matrix = []
    for index, row in enumerate(rows):
        match = re.fullmatch(r"([0-9a-fA-F]{8}):\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)", row)
        require(match is not None and int(match[1], 16) == index,
                "Malformed display matrix row.", "TRANSFORM")
        matrix.extend(int(match[item]) for item in (2, 3, 4))
    require(tuple(matrix) == IDENTITY_MATRIX, "Display matrix must be identity.", "TRANSFORM")


def _probe_transform(value):
    """Inspect coordinate-bearing keys even when outside standard side_data."""
    require(type(value) is dict, "Malformed transform metadata object.", "TRANSFORM")
    for key, item in value.items():
        lowered = key.lower()
        if lowered in ("rotate", "rotation"):
            _zero_rotation(item)
        elif lowered == "displaymatrix":
            _probe_matrix(item)
        elif any(token in lowered for token in ("matrix", "rotation", "rotate", "orientation", "crop", "transform")):
            raise Invalid("TRANSFORM", "Unknown display transform metadata field.")
        elif lowered == "tags":
            _probe_transform(item)
        elif lowered == "side_data_list":
            require(type(item) is list, "Malformed side-data metadata.", "TRANSFORM")
            displays = 0
            for side in item:
                require(type(side) is dict and type(side.get("side_data_type")) is str,
                        "Malformed side-data entry.", "TRANSFORM")
                kind = side["side_data_type"]
                if kind == "Display Matrix":
                    displays += 1
                    require(set(side) == {"side_data_type", "displaymatrix", "rotation"} and displays == 1,
                            "Display matrix side data is incomplete or duplicated.", "TRANSFORM")
                    _probe_matrix(side["displaymatrix"])
                    _zero_rotation(side["rotation"])
                else:
                    require(kind == "CPB properties", "Unknown side data cannot establish an unchanged display coordinate system.", "TRANSFORM")
                    _probe_transform({k: v for k, v in side.items() if k != "side_data_type"})


def _input_metadata(text):
    """Read the Input #0 block, never Output rawvideo or progress messages."""
    starts = list(re.finditer(r"(?m)^Input #\d+,", text))
    require(len(starts) == 1 and text[starts[0].start():].startswith("Input #0,"),
            "Decoder metadata must describe exactly one input.", "METADATA")
    block = text[starts[0].start():]
    require("\nStream mapping:" in block, "Decoder input metadata boundary is missing.", "METADATA")
    block = block.split("\nStream mapping:", 1)[0]
    _text_transform(block)
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
    _probe_transform(stream)
    _probe_transform(fmt)
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


def _identity_matrix(data, offset, label):
    require(type(data) is bytes and len(data) >= offset+36, "Missing or truncated " + label + " matrix.", "TRANSFORM")
    matrix = struct.unpack_from(">9i", data, offset)
    require(matrix == IDENTITY_MATRIX, "MP4 display matrix must be identity: " + label, "TRANSFORM")
    return list(matrix)


def _movie_transform(data):
    require(len(data) >= 4 and data[0] in (0, 1), "Unsupported movie-header transform version.", "TRANSFORM")
    offset = 36 if data[0] == 0 else 48
    require(len(data) >= offset+64, "Truncated movie-header display metadata.", "TRANSFORM")
    return _identity_matrix(data, offset, "mvhd")


def _track_transform(data):
    require(len(data) >= 4 and data[0] in (0, 1), "Unsupported track-header transform version.", "TRANSFORM")
    offset = 40 if data[0] == 0 else 52
    matrix = _identity_matrix(data, offset, "tkhd")
    require(len(data) >= offset+44 and struct.unpack_from(">II", data, offset+36) == (1920 << 16, 1080 << 16),
            "Track display dimensions must be exactly 1920x1080 without scaling.", "TRANSFORM")
    return matrix


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
        movie_header = _payload(stream, _one(movie, b"mvhd"))
        movie_scale, _ = _clock(movie_header)
        _movie_transform(movie_header)
        trak = _one(movie, b"trak")
        track = _boxes(stream, trak[1], trak[2])
        _track_transform(_payload(stream, _one(track, b"tkhd")))
        mdia = _one(track, b"mdia")
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
        extensions = _boxes(stream, entry[1]+78, entry[2])
        require(all(box[0] in (b"avcC", b"pasp", b"btrt", b"colr") for box in extensions)
                and len({box[0] for box in extensions}) == len(extensions),
                "Unknown, cropped or duplicate video sample-entry extension.", "TRANSFORM")
        for extension in extensions:
            if extension[0] == b"pasp":
                aspect = _payload(stream, extension)
                require(len(aspect) == 8, "Malformed MP4 pixel aspect ratio.", "TRANSFORM")
                horizontal, vertical = struct.unpack(">II", aspect)
                require(horizontal == vertical and horizontal > 0, "MP4 pixels must remain square.", "TRANSFORM")
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
            "sampleCount": 288, "fps": 24, "movieTimeScale": movie_scale, "mediaTimeScale": scale, "durationSeconds": 12,
            "displayTransform": "identity", "displayWidth": 1920, "displayHeight": 1080}


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


def _publish_report(directory, identity):
    """Last fallible operation: atomically expose the already checked report.

    Windows rename refuses an existing destination. The explicit precheck also
    rejects it on other hosts, but is not a permanent cross-process lock. A
    consumer must validate the whole folder again at the time it is consumed.
    """
    _directory_identity(directory, identity)
    source = common._safe_path(directory / STAGED_REPORT)
    require(source.parent == directory and not os.path.lexists(directory / REPORT),
            "Success report destination is already occupied or unsafe.", "OUTPUT")
    os.rename(source, directory / REPORT)


def validate_candidate(candidate_dir: Path) -> dict:
    """Consumer check: report alone is insufficient; no media decoder is run.

    All four files must be present, unchanged during this read, and bound to the
    stored checks. Failure/staged/partial/temp/unknown files always disqualify
    the directory. This finite snapshot does not authenticate the producer or
    prevent a concurrent/later writer; revalidate at each consumption boundary.
    """
    result = {"schemaVersion": "pc3-full-animation-media-consumption-v1", "valid": False, "status": "FAIL",
              "failures": [], "visualAccepted": False, "mainRegistration": False, "authenticityVerified": False,
              "videoDecoded": False, "pixelDecoded": False, "inputDigests": [],
              "pending": ["Fresh media decoding is not performed by this consumer check.",
                          "Visual acceptance and product registration remain with pc1.",
                          "Checks are a finite snapshot, not producer authentication or a permanent filesystem lock."]}
    try:
        directory = common._safe_path(candidate_dir, directory=True)
        names = {VIDEO, TRACKS, DESCRIPTOR, REPORT}
        require({path.name for path in directory.iterdir()} == names,
                "Candidate directory is incomplete, failed or contains unexpected files.", "INVENTORY")
        info = directory.stat()
        identity = info.st_dev, info.st_ino
        stamps = {name: verifier._stamp(directory / name) for name in names}
        raw, report_digest = common._file(directory, REPORT, read=True, limit=4*1024*1024)
        report = common.parse_json(raw)
        require(report.get("schemaVersion") == "pc3-full-animation-media-candidate-v1"
                and report.get("valid") is True and report.get("status") == "PASS_WITH_PENDING"
                and report.get("failures") == [], "Candidate report does not record successful machine checks.", "REPORT")
        require(all(report.get(key) is False for key in ("visualAccepted", "mainRegistration", "authenticityVerified"))
                and all(report.get(key) is True for key in ("encoded", "videoDecoded", "pixelDecoded")),
                "Candidate acceptance/decode flags differ from the required pending contract.", "REPORT")
        pending = report.get("pending")
        required_codes = {item["code"] for item in _result()["pending"]}
        require(type(pending) is list and len(pending) == len(required_codes)
                and all(type(item) is dict and set(item) == {"code", "detail"}
                        and type(item["code"]) is str and type(item["detail"]) is str and item["detail"] for item in pending)
                and {item["code"] for item in pending} == required_codes,
                "Candidate must retain the complete pending-review limitations.", "REPORT")
        assets = report.get("assets")
        require(type(assets) is dict and set(assets) == {"video", "tracks", "tracksDescriptor"},
                "Candidate asset declarations are incomplete.", "REPORT")
        actual_assets, track_raw, descriptor_raw = {}, None, None
        for key, name in (("video", VIDEO), ("tracks", TRACKS), ("tracksDescriptor", DESCRIPTOR)):
            declared = verifier._descriptor(assets[key], name)
            data, actual = common._file(directory, name, read=key != "video")
            require(same(actual, declared), "Candidate asset bytes differ from the report.", "ASSET")
            actual_assets[key] = actual
            if key == "tracks":
                track_raw = data
            elif key == "tracksDescriptor":
                descriptor_raw = data
        descriptor = common.parse_json(descriptor_raw)
        expected_descriptor = {"schemaVersion": "oneflow-cctv-tracks-v1", "url": "/demo/sorter-demo.tracks.json",
                               "bytes": actual_assets["tracks"]["bytes"], "sha256": actual_assets["tracks"]["sha256"],
                               "videoSha256": actual_assets["video"]["sha256"]}
        require(same(descriptor, expected_descriptor) and type(descriptor.get("bytes")) is int
                and same(report.get("tracksDescriptor"), expected_descriptor),
                "Five-field tracks descriptor is not bound to the actual final assets.", "DESCRIPTOR")
        verifier._tracks(common.parse_json(track_raw))
        sources = report.get("inputDigests")
        require(type(sources) is list and len(sources) == 291, "Original input digest inventory is incomplete.", "REPORT")
        parsed_sources = [verifier._descriptor(item) for item in sources]
        require({item["name"] for item in parsed_sources} == verifier.NAMES,
                "Original input digest names differ from the complete animation contract.", "REPORT")
        original_tracks = next(item for item in parsed_sources if item["name"] == "tracks.json")
        require(original_tracks["bytes"] == actual_assets["tracks"]["bytes"]
                and original_tracks["sha256"] == actual_assets["tracks"]["sha256"],
                "Copied tracks differ from the original input declaration.", "ASSET")
        verifier._descriptor(report.get("expectationsFileDigest"))
        require(type(report.get("sourceCommit")) is str and re.fullmatch(r"[0-9a-f]{40}", report["sourceCommit"]),
                "Candidate source declaration is malformed.", "REPORT")
        decoded = report.get("decode")
        fixed = {"frameCount": 288, "timeBase": "1/24", "firstPts": 0, "lastPts": 287, "frameDuration": 1,
                 "durationSeconds": 12, "width": 1920, "height": 1080, "decodedFrameBytes": 3110400,
                 "method": "ffmpeg-full-eof-framehash", "pixelFormat": "yuv420p"}
        require(type(decoded) is dict and all(key in decoded and same(decoded[key], value)
                and (type(value) is not int or type(decoded[key]) is int) for key, value in fixed.items()),
                "Stored full-decode metadata differs from the complete animation contract.", "DECODE")
        hashes = decoded.get("frameSha256")
        require(type(hashes) is list and len(hashes) == 288 and all(type(item) is str and re.fullmatch(r"[0-9a-f]{64}", item) for item in hashes),
                "Stored decoded-frame checksum inventory is incomplete.", "DECODE")
        live_mp4 = _mp4(directory / VIDEO)
        declared_mp4 = report.get("mp4")
        legacy_keys = set(live_mp4) - {"displayTransform", "displayWidth", "displayHeight"}
        require(type(declared_mp4) is dict and legacy_keys <= declared_mp4.keys() <= live_mp4.keys()
                and all(same(value, live_mp4[key]) for key, value in declared_mp4.items()),
                "Actual MP4 timing/display metadata differs from the report.", "MP4")
        digests = [report_digest, *actual_assets.values()]
        require(all(verifier._stamp(directory / name) == stamp for name, stamp in stamps.items()),
                "Candidate changed during consumer validation.", "INPUT_CHANGED")
        _assert_outputs(directory, identity, digests)
        result.update(valid=True, status="PASS_WITH_PENDING", inputDigests=digests, assets=actual_assets,
                      tracksDescriptor=descriptor, mp4=live_mp4)
    except Exception as error:
        common._failure(result, error)
    return result


def package_full_animation(package_dir: Path, expectations_path: Path, output_dir: Path,
                           ffmpeg_path: Path, ffprobe_path: Path | None = None, *, timeout=600) -> dict:
    """Validate, encode and fully decode into a new candidate directory only."""
    result, output = _result(), None
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
        descriptor_digest = _write_new(output, DESCRIPTOR, _json_bytes(descriptor),
                                       directory_identity=directory_identity)
        result["assets"] = {"video": video_digest, "tracks": copied, "tracksDescriptor": descriptor_digest}
        result["tracksDescriptor"] = descriptor
        result.update(valid=True, status="PASS_WITH_PENDING")
        _assert_outputs(output, directory_identity, [video_digest, copied, descriptor_digest])
        # The staged filename is never consumer success, even if its JSON is
        # complete. No successful report is exposed before every check below.
        report_digest = _write_new(output, STAGED_REPORT, _json_bytes(result), directory_identity=directory_identity)
        _assert_inputs(package, manifest, manifest_digest, checked["inputDigests"], stamps, tools)
        _assert_outputs(output, directory_identity, [video_digest, copied, descriptor_digest, report_digest])
        _publish_report(output, directory_identity)
        # Deliberately no fallible validation or filesystem operations here.
    except Exception as error:
        if isinstance(error, subprocess.TimeoutExpired):
            error = Invalid("TIMEOUT", "Media tool exceeded its explicit timeout and was terminated.")
        common._failure(result, error)
        result.pop("tracksDescriptor", None)
        if output is not None:
            # No cleanup/unlink is required for correctness. Partial/staged
            # files remain disqualifying, even when writing failure.json fails.
            try:
                safe_output = common._safe_path(output, directory=True)
                info = safe_output.stat()
                safe_cleanup = (info.st_dev, info.st_ino) == directory_identity
            except Exception:
                safe_cleanup = False
            if safe_cleanup:
                try:
                    _write_new(output, "failure.json", _json_bytes(result), directory_identity=directory_identity)
                except Exception:
                    pass
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--package", type=Path)
    mode.add_argument("--check-candidate", type=Path)
    parser.add_argument("--expectations", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ffmpeg", type=Path)
    parser.add_argument("--ffprobe", type=Path)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    if args.check_candidate:
        if any((args.expectations, args.output, args.ffmpeg, args.ffprobe)):
            parser.error("--check-candidate cannot be combined with encoding arguments")
        result = validate_candidate(args.check_candidate)
    else:
        if not all((args.expectations, args.output, args.ffmpeg)):
            parser.error("--package requires --expectations, --output and --ffmpeg")
        result = package_full_animation(args.package, args.expectations, args.output, args.ffmpeg, args.ffprobe, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
