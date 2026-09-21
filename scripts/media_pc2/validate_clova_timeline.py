"""Offline N02-M5 metadata validator. Never edits, converts, or plays audio.

All candidates require independent pc1 review. No metadata check proves speech,
speaker identity, listening quality, STT, or application playback behavior.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from fractions import Fraction

SCRIPT_SHA256 = "47ae253daf158335e92fa136f3e9ba8b3af118fb278b66fcf137e91c3242ade6"
SCRIPT_BYTES = 25175
SCRIPT_SCHEMA = "oneflow-korean-call-v5-fast-candidate-2"
CASE_IDS = ("CASE-0001", "CASE-0002")
OUTPUT_ROOT = Path(__file__).resolve().parents[2] / ".local" / "clova-v5-intake"
MAX_INPUT_BYTES = 128 * 1024 * 1024


class ValidationError(Exception):
    def __init__(self, code, field, detail):
        super().__init__(f"{code}: {field}: {detail}")
        self.code, self.field, self.detail = code, field, detail


def require(condition, code, field, detail):
    if not condition:
        raise ValidationError(code, field, detail)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_path(value):
    path = Path(value)
    require(".." not in path.parts, "UNSAFE_PATH", str(path), "Parent traversal is forbidden")
    require(not str(path).startswith(("\\\\", "//")), "UNSAFE_PATH", str(path), "Local paths only")
    path = path.absolute()
    for part in reversed((path, *path.parents)):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode) and
                not (getattr(info, "st_file_attributes", 0) & 0x400),
                "LINK_PATH", str(part), "Symlinks and Windows reparse points are forbidden")
    return path


def identity(info):
    # Windows path.stat and fstat can report different ctime: compare each stream
    # before/after separately. Common identity includes birth time where present.
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_nlink, getattr(info, "st_birthtime_ns", None))


def read_snapshot(path):
    path = checked_path(path)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
            "UNSAFE_INPUT", str(path), "Require one regular file, without hardlinks")
    require(0 < before.st_size <= MAX_INPUT_BYTES, "INPUT_SIZE", str(path), "Input size outside limit")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as handle:
        opened = os.fstat(handle.fileno())
        require(identity(before) == identity(opened), "INPUT_CHANGED", str(path), "Path/open identity changed")
        data = handle.read(MAX_INPUT_BYTES + 1)
        closed = os.fstat(handle.fileno())
    checked_path(path)
    after = path.stat()
    require(identity(before) == identity(after) == identity(opened) == identity(closed)
            and before.st_ctime_ns == after.st_ctime_ns
            and opened.st_ctime_ns == closed.st_ctime_ns and len(data) == before.st_size,
            "INPUT_CHANGED", str(path), "Input changed while reading")
    return data, {"path": str(path), "bytes": len(data), "sha256": digest(data),
                  "identity": identity(after), "pathCtimeNs": after.st_ctime_ns}


def json_document(data, field):
    def pairs(items):
        obj = {}
        for key, value in items:
            require(key not in obj, "JSON_DUPLICATE_KEY", field, f"Duplicate key: {key!r}")
            obj[key] = value
        return obj
    def bad_constant(value):
        raise ValidationError("JSON_NONFINITE", field, value)
    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=bad_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValidationError("JSON_INVALID", field, str(exc)) from exc
    require(isinstance(result, dict), "JSON_OBJECT", field, "Expected object")
    pending = [(result, 0)]
    while pending:
        item, depth = pending.pop()
        require(depth <= 100, "JSON_DEPTH", field, "JSON nesting limit is 100")
        if isinstance(item, str):
            try:
                item.encode("utf-8")
            except UnicodeError as exc:
                raise ValidationError("JSON_UNICODE", field, "Unpaired Unicode surrogate") from exc
        elif isinstance(item, float):
            require(math.isfinite(item), "JSON_NONFINITE", field, "Nonfinite JSON number")
        elif isinstance(item, dict):
            pending.extend((v, depth + 1) for pair in item.items() for v in pair)
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
    return result


def match_descriptor(raw, expected, field):
    require(isinstance(expected, dict), "DESCRIPTOR", field, "Expected independent descriptor")
    require(type(expected.get("bytes")) is int and expected["bytes"] > 0
            and isinstance(expected.get("sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", expected["sha256"]) is not None,
            "DESCRIPTOR", field, "Require positive bytes and lowercase SHA256")
    require(len(raw) == expected["bytes"] and digest(raw) == expected["sha256"],
            "HASH_MISMATCH", field, "Independent bytes/SHA256 mismatch")


def number(value, field):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            "INVALID_TIME", field, "Require finite nonnegative number; bool/string/null forbidden")
    return value


def provenance(doc, field):
    require(isinstance(doc.get("source"), str) and bool(doc["source"].strip()),
            "PROVENANCE", field + ".source", "Source is required")
    try:
        stamp = datetime.fromisoformat(doc["observedAt"].replace("Z", "+00:00"))
        require(stamp.utcoffset() is not None, "PROVENANCE", field + ".observedAt", "Timezone required")
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ValidationError("PROVENANCE", field + ".observedAt", "ISO8601 time with timezone required") from exc


def inspect_wav(data, field):
    require(len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE",
            "WAV_HEADER", field, "Require RIFF/WAVE")
    require(struct.unpack_from("<I", data, 4)[0] + 8 == len(data),
            "WAV_TRUNCATED", field, "RIFF size differs from actual file size")
    offset, fmt, payload, chunks = 12, None, None, []
    while offset < len(data):
        require(offset + 8 <= len(data), "WAV_CHUNK", field, "Truncated chunk header")
        name, size = struct.unpack_from("<4sI", data, offset)
        start, end = offset + 8, offset + 8 + size
        require(end + (size % 2) <= len(data), "WAV_TRUNCATED", field, "Chunk or padding truncated")
        chunks.append({"id": name.decode("ascii", errors="replace"), "bytes": size})
        if name == b"fmt ":
            require(fmt is None and payload is None and size >= 16,
                    "WAV_FORMAT", field, "Invalid/duplicate/misordered fmt chunk")
            fmt = struct.unpack_from("<HHIIHH", data, start)
        elif name == b"data":
            require(payload is None and fmt is not None, "WAV_DATA", field, "Require exactly one data chunk after fmt")
            payload = data[start:end]
        offset = end + size % 2
    require(fmt is not None and payload is not None, "WAV_FORMAT", field, "Missing fmt or data")
    code, channels, rate, byte_rate, align, bits = fmt
    facts = {"container": "RIFF/WAVE", "formatCode": code, "channels": channels,
             "sampleRate": rate, "bitsPerSample": bits, "blockAlign": align,
             "byteRate": byte_rate, "dataBytes": len(payload), "chunks": chunks}
    if code != 1 or bits != 16:
        return {**facts, "status": "UNSUPPORTED", "decodedFrameCount": None, "decodedDurationSeconds": None}
    require(channels > 0 and rate > 0 and align == channels * 2 and byte_rate == rate * align,
            "WAV_FORMAT", field, "Invalid PCM16 rate/channel/blockAlign/byteRate")
    require(len(payload) > 0 and len(payload) % align == 0,
            "WAV_FRAMES", field, "Empty or incomplete PCM16 frame")
    frames = len(payload) // align
    return {**facts, "status": "SUPPORTED_PCM16", "sampleWidthBytes": 2,
            "decodedFrameCount": frames, "decodedDurationSeconds": frames / rate,
            "measurement": "Complete uncompressed PCM data length / blockAlign; no speech boundary detection"}


def make_timeline(script, obs, audio, unresolved):
    require(script.get("schemaVersion") == SCRIPT_SCHEMA, "SCRIPT_SCHEMA", "script", "Unexpected script schema")
    cases = script.get("cases")
    observed = obs.get("cases")
    require(isinstance(cases, list) and isinstance(observed, list)
            and [c.get("caseId") for c in cases if isinstance(c, dict)] == list(CASE_IDS)
            and [c.get("caseId") for c in observed if isinstance(c, dict)] == list(CASE_IDS),
            "CASE_ORDER", "cases", "Require exactly two cases in fixed order")
    require(len(cases) == len(observed) == 2, "CASE_COUNT", "cases", "Exactly two cases required")
    for case in observed:
        for index, turn in enumerate(case.get("turns", [])):
            if isinstance(turn, dict) and (turn.get("gapObservationStatus") == "unresolved"
                    or (turn.get("officialGapAfterSeconds") is None and index != 9)):
                unresolved.append(f"{case['caseId']}.turns[{index}].officialGapAfterSeconds")
    require(not unresolved, "UNRESOLVED_GAP", "observations", "Missing middle gap is never inferred from proposed pause")
    result = []
    for case, actual in zip(cases, observed):
        case_id = case["caseId"]
        canonical, turns = case.get("turns"), actual.get("turns")
        require(isinstance(canonical, list) and isinstance(turns, list)
                and len(canonical) == len(turns) == 10, "TURN_COUNT", case_id, "Exactly ten turns required")
        starts, gaps = [], []
        for index, (fixed, turn) in enumerate(zip(canonical, turns)):
            field = f"{case_id}.turns[{index}]"
            require(isinstance(turn, dict), "TURN_OBJECT", field, "Require object")
            for key in ("id", "speaker", "text", "spokenText"):
                require(turn.get(key) == fixed[key], "TURN_MISMATCH", field + "." + key, "Must equal fixed script at this position")
            require(turn.get("editorInputText") == fixed["spokenText"],
                    "EDITOR_INPUT", field, "Editor input must equal spokenText, not display text")
            starts.append(number(turn.get("startSeconds"), field + ".startSeconds"))
            gap, status = turn.get("officialGapAfterSeconds"), turn.get("gapObservationStatus")
            if index == 9 and status == "not_displayed" and gap is None:
                gaps.append(None)
            else:
                require(status == "observed", "GAP_STATUS", field, "Only final turn permits not_displayed/null")
                gaps.append(number(gap, field + ".officialGapAfterSeconds"))
        # Decimal UI numbers are compared as exact fractions. Binary float
        # subtraction must not turn an exactly zero-length interval into PASS.
        duration = Fraction(audio[case_id]["decodedFrameCount"], audio[case_id]["sampleRate"])
        derived = []
        for index, (fixed, turn) in enumerate(zip(canonical, turns)):
            start = Fraction(str(starts[index]))
            final = index == 9
            if not final:
                require(start < Fraction(str(starts[index + 1])), "START_ORDER", case_id, "Starts must strictly increase")
            end = duration if final else Fraction(str(starts[index + 1])) - Fraction(str(gaps[index]))
            require(0 <= start < end <= duration, "TIME_BOUNDS", fixed["id"], "Require 0 <= start < derived end <= decoded EOF")
            require(final or end <= Fraction(str(starts[index + 1])), "TIME_OVERLAP", fixed["id"], "End exceeds next start")
            derived.append({"id": fixed["id"], "speaker": fixed["speaker"], "text": fixed["text"],
                            "spokenText": fixed["spokenText"], "editorInputText": turn["editorInputText"],
                            "startSeconds": starts[index], "officialGapAfterSeconds": gaps[index],
                            "gapObservationStatus": turn["gapObservationStatus"], "endSeconds": float(end),
                            "endExactFraction": {"numerator": end.numerator, "denominator": end.denominator},
                            "endIsDerived": True,
                            "endFormula": "decodedFrameCount / sampleRate" if final else "nextStartSeconds - officialGapAfterSeconds",
                            "endOperands": {"frames": audio[case_id]["decodedFrameCount"], "sampleRate": audio[case_id]["sampleRate"]}
                            if final else {"nextStartSeconds": starts[index + 1], "officialGapAfterSeconds": gaps[index]},
                            "observationSource": obs["source"], "observedAt": obs["observedAt"]})
        result.append({"caseId": case_id, "audio": audio[case_id], "turns": derived})
    return result


def prepare_output(output, input_paths):
    root = checked_path(OUTPUT_ROOT)
    path = checked_path(output)
    require(root.is_dir(), "OUTPUT_ROOT", str(root), "Create the intake root explicitly first")
    require(path != root and path.is_relative_to(root), "OUTPUT_ESCAPE", str(path), "Output must stay under .local/clova-v5-intake")
    require(path.parent.is_dir(), "OUTPUT_PARENT", str(path), "Output parent must already exist")
    require(not os.path.lexists(path), "OUTPUT_EXISTS", str(path), "A fresh output run is required")
    for item in input_paths:
        if not isinstance(item, (str, os.PathLike)):
            continue  # Invalid input types are reported in the safe new run.
        source = Path(item).absolute()
        require(path != source and not source.is_relative_to(path), "OUTPUT_COLLISION", str(path), "Inputs cannot be inside output")
    path.mkdir(exist_ok=False)
    return path, path.stat()


def write_new(output, output_stat, name, value):
    with output_directory(output):
        checked_path(output)
        now = output.stat()
        require((now.st_dev, now.st_ino) == (output_stat.st_dev, output_stat.st_ino),
                "OUTPUT_CHANGED", str(output), "Output directory identity changed")
        data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
        with (output / name).open("xb") as stream:
            stream.write(data)


@contextmanager
def output_directory(path):
    """Pin Windows directory ancestors without granting delete sharing.

    This blocks rename/junction replacement between verification and exclusive
    file creation. Fail closed on other OSes: no untested race guarantee.
    This is a per-handle sharing mode, not an ACL or security setting change.
    """
    require(os.name == "nt", "OUTPUT_PLATFORM", str(path), "Output publication currently supports Windows only")
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes, close.restype = (wintypes.HANDLE,), wintypes.BOOL
    handles = []
    try:
        path = checked_path(path)
        for part in reversed((path, *path.parents)):
            # FILE_LIST_DIRECTORY is needed for Windows share-mode enforcement;
            # FILE_READ_ATTRIBUTES alone did not prevent an actual rename.
            # READ sharing only also excludes competing directory WRITE handles.
            handle = create(str(part), 0x1, 1, None, 3, 0x02000000 | 0x00200000, None)
            if handle == ctypes.c_void_p(-1).value:
                raise ValidationError("OUTPUT_LOCK", str(part), f"Cannot pin output directory: Windows error {ctypes.get_last_error()}")
            handles.append(handle)
            checked_path(part)
            require(part.is_dir(), "OUTPUT_PARENT", str(part), "Directory required")
        yield
    finally:
        for handle in reversed(handles):
            close(handle)


def validate(script, wavs, expected, observations, output):
    # Parent locks cover run creation; child locks cover the whole validation
    # and publication, not only a check immediately before writing.
    parent = checked_path(output).parent
    with output_directory(parent):
        mapped = wavs if isinstance(wavs, dict) else {}
        folder, folder_stat = prepare_output(output, (script, expected, observations, *mapped.values()))
        with output_directory(folder):
            return _validate(script, wavs, expected, observations, folder, folder_stat)


def _validate(script, wavs, expected, observations, folder, folder_stat):
    """Validate a read-only input set, then create a never-accepted candidate.

    Unsafe output raises ValidationError without writing. Safe-run input failures
    return a REJECTED/UNSUPPORTED validation.json and no candidate files.
    """
    inputs = {"script": script, "expected": expected, "observations": observations,
              **(wavs if isinstance(wavs, dict) else {})}
    report = {"schemaVersion": "clova-timeline-validation-v1", "status": "REJECTED", "candidate": False,
              "accepted": False, "origin": "unverified", "createdAt": datetime.now(timezone.utc).isoformat(),
              "errors": [], "unresolved": [], "inputs": {}, "audio": {},
              "officialAudio": {"status": "NOT_RUN", "verified": 0, "total": 2},
              "officialTimeline": {"status": "NOT_RUN", "verified": 0, "total": 20},
              "limitations": ["End times are derived, not measured speech endpoints.",
                              "UI resolution is 0.01s, not a +/-0.01s accuracy guarantee.",
                              "Metadata equality does not verify speech, speakers, listening, STT or UI.",
                              "Descriptors must be independently supplied; this tool cannot authenticate their author.",
                              "No audio copies, conversion, normalization, playback or external calls."]}
    raw, snapshots, candidates = {}, {}, None
    try:
        # The pinned script is checked before any observation or candidate is trusted.
        raw["script"], snapshots["script"] = read_snapshot(script)
        report["inputs"]["script"] = dict(snapshots["script"])
        require(len(raw["script"]) == SCRIPT_BYTES and digest(raw["script"]) == SCRIPT_SHA256,
                "SCRIPT_HASH", "script", "Pinned Git blob bytes/SHA256 mismatch; do not normalize line endings")
        require(isinstance(wavs, dict) and set(wavs) == set(CASE_IDS), "WAV_MAPPING", "wavs", "Explicit two-case mapping required")
        for key in ("expected", "observations", *CASE_IDS):
            raw[key], snapshots[key] = read_snapshot(inputs[key])
            report["inputs"][key] = dict(snapshots[key])
        require(len({(s["identity"][0], s["identity"][1]) for s in snapshots.values()}) == len(inputs),
                "INPUT_ALIAS", "inputs", "Each input must be a separate file")
        fixed = json_document(raw["script"], "script")
        descriptors = json_document(raw["expected"], "expected")
        obs = json_document(raw["observations"], "observations")
        require(descriptors.get("schemaVersion") == "clova-timeline-input-descriptors-v1"
                and obs.get("schemaVersion") == "clova-timeline-observations-v1",
                "SCHEMA", "inputs", "Unknown input schema")
        origin = descriptors.get("origin")
        require(origin in ("artificial", "official_clova") and obs.get("origin") == origin,
                "ORIGIN", "inputs", "Explicit matching artificial/official_clova origin required")
        report["origin"] = origin
        match_descriptor(raw["script"], descriptors.get("script"), "script")
        match_descriptor(raw["observations"], descriptors.get("observations"), "observations")
        provenance(obs, "observations")
        provenance(descriptors["observations"], "expected.observations")
        for key in ("source", "observedAt"):
            require(obs[key] == descriptors["observations"][key], "PROVENANCE", key, "Independent observation provenance mismatch")
        require(type(obs.get("uiResolutionSeconds")) in (int, float) and obs["uiResolutionSeconds"] == 0.01,
                "UI_RESOLUTION", "observations", "Record 0.01 second display resolution without accuracy claim")
        wav_descriptors = descriptors.get("wavs")
        require(isinstance(wav_descriptors, list) and len(wav_descriptors) == 2
                and all(isinstance(d, dict) for d in wav_descriptors)
                and [d.get("caseId") for d in wav_descriptors] == list(CASE_IDS),
                "DESCRIPTOR_CASES", "wavs", "Independent descriptors require exact case order")
        for case_id, descriptor in zip(CASE_IDS, wav_descriptors):
            match_descriptor(raw[case_id], descriptor, case_id)
            report["audio"][case_id] = inspect_wav(raw[case_id], case_id)
        if any(a["status"] == "UNSUPPORTED" for a in report["audio"].values()):
            report["status"] = "UNSUPPORTED"
            report["errors"].append({"code": "UNSUPPORTED_WAV", "field": "wavs", "detail": "Only PCM16 is measured; no automatic conversion"})
        else:
            candidates = make_timeline(fixed, obs, report["audio"], report["unresolved"])
    except ValidationError as exc:
        report["errors"].append({"code": exc.code, "field": exc.field, "detail": exc.detail})
    except (OSError, KeyError, TypeError, ValueError, OverflowError) as exc:
        report["errors"].append({"code": "INPUT_ERROR", "field": "inputs", "detail": str(exc)})
    # Re-read all opened inputs before publishing, including the independent
    # descriptor. Compare bytes AND stable identity; preserve failure evidence.
    for key, first in snapshots.items():
        try:
            _, last = read_snapshot(inputs[key])
            same = (first["sha256"] == last["sha256"] and first["identity"] == last["identity"]
                    and first["pathCtimeNs"] == last["pathCtimeNs"])
            report["inputs"][key]["afterSha256"] = last["sha256"]
            report["inputs"][key]["unchanged"] = same
            require(same, "INPUT_CHANGED", key, "Input changed during validation")
        except (OSError, ValidationError) as exc:
            report["errors"].append({"code": "INPUT_CHANGED", "field": key, "detail": str(exc)})
    if candidates is not None and not report["errors"]:
        report.update(status="PASS", candidate=True)
        report["checks"] = {"rawWavUnchanged": 2, "scriptAlignedTurns": 20, "derivedIntervals": 20}
        if report["origin"] == "official_clova":
            report["officialAudio"].update(status="METADATA_PASS", verified=2)
            report["officialTimeline"].update(status="METADATA_PASS", verified=20)
        metadata = {"status": "candidate", "accepted": False, "origin": report["origin"],
                    "uiResolutionSeconds": 0.01, "unresolved": [], "inputs": report["inputs"],
                    "limitations": report["limitations"]}
        write_new(folder, folder_stat, "timeline-candidate.json", {"schemaVersion": "clova-timeline-candidate-v1", **metadata, "cases": candidates})
        fixture = [{"caseId": c["caseId"], "transcript": [{k: t[k] for k in ("id", "speaker", "text", "startSeconds", "endSeconds")} for t in c["turns"]]} for c in candidates]
        write_new(folder, folder_stat, "fixture-candidate.json", {"schemaVersion": "clova-fixture-proposal-v1", **metadata, "cases": fixture})
    elif report["status"] != "UNSUPPORTED" or any(e["code"] != "UNSUPPORTED_WAV" for e in report["errors"]):
        report["status"] = "REJECTED"
    # Written last: consumers must require this PASS and still seek pc1 review.
    write_new(folder, folder_stat, "validation.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog="Output must be a new run under .local/clova-v5-intake. Existing run is never reused. No official inputs are bundled.")
    for flag in ("script", "case-0001-wav", "case-0002-wav", "expected", "observations", "output"):
        parser.add_argument("--" + flag, required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = validate(args.script, dict(zip(CASE_IDS, (args.case_0001_wav, args.case_0002_wav))),
                          args.expected, args.observations, args.output)
    except (ValidationError, OSError) as exc:
        print(json.dumps({"status": "REJECTED", "candidate": False, "accepted": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({k: report[k] for k in ("status", "candidate", "accepted", "origin", "errors", "unresolved")}, ensure_ascii=False))
    return {"PASS": 0, "REJECTED": 2, "UNSUPPORTED": 3}[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
