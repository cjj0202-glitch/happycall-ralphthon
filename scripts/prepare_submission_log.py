"""Build a local NOT-APPROVED JSONL candidate; never approve or upload it.

Input must be a fixed snapshot. Policy: {"redact_leaf_sha256": [sha256, ...],
"redact_store_code_sha256": [sha256, ...]} (second key is optional),
where each digest covers the decoded string's UTF-8 bytes, not JSON quoting.
Only standard-library modules are used. Input is streamed one JSON event at a
time; memory usage is bounded by the largest event, not total log size.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from collections import Counter


LOCAL_ROOT = Path(__file__).resolve().parents[1] / ".local"
CANDIDATE = "candidate.NOT-APPROVED.jsonl"
CHANGES = "changes.NOT-APPROVED.jsonl"
MANIFEST = "manifest.NOT-APPROVED.json"
PROTECTED = frozenset({
    "timestamp", "time", "date", "datetime", "id", "type", "role", "name",
    "model", "effort", "reasoning_effort", "encrypted_content", "call_id",
    "created_at", "updated_at", "started_at", "completed_at", "finished_at",
    "duration_ms", "status", "namespace", "comp_hash", "sender", "recipient",
})
MEDIA_TYPES = frozenset({
    "image", "audio", "video", "input_image", "output_image", "image_url",
    "input_audio", "output_audio", "audio_url", "input_video", "output_video",
})
MEDIA_PAYLOAD_FIELDS = frozenset({
    "data", "base64", "b64_json", "payload", "image", "audio", "video", "url",
})


class PreparationError(Exception):
    """Only constant codes may be stored here; never exception/input text."""


class Number:
    """Preserve JSON number lexemes, including arbitrary precision and -0."""

    def __init__(self, token):
        self.token = token


class Policy(frozenset):
    def __new__(cls, leaves=(), store_codes=()):
        instance = super().__new__(cls, leaves)
        instance.store_codes = frozenset(store_codes)
        return instance


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def leaf_bytes(value: str) -> bytes:
    try:
        return value.encode("utf-8")
    except UnicodeError:
        raise PreparationError("INVALID_UNICODE") from None


def protected(key):
    lowered = key.lower()
    return lowered in PROTECTED or lowered.endswith(("_id", "_ids", "_timestamp"))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PreparationError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def invalid_constant(_):
    raise PreparationError("NONFINITE_JSON_NUMBER")


def parse_event(raw):
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object, parse_int=Number,
                           parse_float=Number, parse_constant=invalid_constant)
    except PreparationError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise PreparationError("INVALID_JSON") from None
    if not isinstance(value, dict):
        raise PreparationError("NONOBJECT_EVENT")
    return value


def encode(value):
    """Serialize without altering numeric literals or object key order."""
    if isinstance(value, Number):
        return value.token
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + encode(v)
                              for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(encode(v) for v in value) + "]"
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def no_links(path):
    """Reject symlinks and Windows junction/reparse points in every component."""
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) &
            getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise PreparationError("LINK_PATH_REJECTED")


def checked_paths(input_path, output_dir, policy_path):
    source = Path(os.path.abspath(input_path))
    output = Path(os.path.abspath(output_dir))
    local = Path(os.path.abspath(LOCAL_ROOT))
    for path in (source, output, local):
        no_links(path)
    if not source.is_file():
        raise PreparationError("INPUT_NOT_REGULAR_FILE")
    if source.stat().st_nlink != 1:
        raise PreparationError("LINK_PATH_REJECTED")
    if output == local or not output.is_relative_to(local):
        raise PreparationError("OUTPUT_OUTSIDE_LOCAL")
    if output.exists():
        raise PreparationError("OUTPUT_ALREADY_EXISTS")
    if not output.parent.is_dir():
        raise PreparationError("OUTPUT_PARENT_MISSING")
    if policy_path is not None:
        policy_path = Path(os.path.abspath(policy_path))
        no_links(policy_path)
        if not policy_path.is_file() or policy_path.stat().st_nlink != 1:
            raise PreparationError("POLICY_NOT_REGULAR_FILE")
    return source, output, policy_path


def load_policy(path):
    if path is None:
        return Policy(), None
    try:
        raw = path.read_bytes()
        data = json.loads(raw, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError):
        raise PreparationError("INVALID_POLICY") from None
    if (not isinstance(data, dict) or "redact_leaf_sha256" not in data
            or set(data) - {"redact_leaf_sha256", "redact_store_code_sha256"}
            or not isinstance(data["redact_leaf_sha256"], list)
            or not isinstance(data.get("redact_store_code_sha256", []), list)):
        raise PreparationError("INVALID_POLICY")
    hashes = data["redact_leaf_sha256"]
    stores = data.get("redact_store_code_sha256", [])
    if any(not isinstance(x, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", x)
           for x in hashes + stores):
        raise PreparationError("INVALID_POLICY")
    return Policy((x.lower() for x in hashes), (x.lower() for x in stores)), sha(raw)


PATTERNS = (
    ("INLINE_MEDIA", re.compile(r"data:[A-Za-z0-9.+/-]*(?:;[^,\s]{1,200})?,[^\s\"'<>\\)]+"), 0),
    ("OPENAI_KEY", re.compile(r"(?<![A-Za-z0-9_-])sk-(?:(?:proj|svcacct)-)?[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])"), 0),
    ("GITHUB_TOKEN", re.compile(r"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})(?![A-Za-z0-9_])"), 0),
    ("AWS_ACCESS_KEY", re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"), 0),
    ("AWS_SECRET", re.compile(r"(?i)(?<![A-Za-z0-9_])aws[_ -]?(?:secret[_ -]?access[_ -]?key|session[_ -]?token)(?![A-Za-z0-9_])[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9/+=]{20,})"), 1),
    ("URL_CREDENTIAL", re.compile(r"(?<![A-Za-z0-9_])[a-zA-Z][a-zA-Z0-9+.-]{1,20}://([^\s/@]+(?::[^\s/@]*)?)@"), 1),
    ("BEARER_TOKEN", re.compile(r"(?i)(?<![A-Za-z0-9_])Bearer[ \t]+([A-Za-z0-9._~+/-]{8,}={0,2})"), 1),
    ("BASIC_AUTH", re.compile(r"(?i)(?<![A-Za-z0-9_])Basic[ \t]+([A-Za-z0-9+/]+={0,2})"), 1),
    ("JWT", re.compile(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9_-]{2,}\.[A-Za-z0-9_-]{2,}\.[A-Za-z0-9_-]+)(?![A-Za-z0-9_.-])"), 1),
    ("EMAIL_CANDIDATE", re.compile(r"(?<![A-Za-z0-9_.!#$%&'*+/=?^`{|}~-])[A-Za-z0-9.!#$%&'*+/=?^`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}(?![A-Za-z0-9_-])"), 0),
    ("KR_MOBILE_CANDIDATE", re.compile(r"(?<!\d)(?:01[016789][- .]?\d{3,4}[- .]?\d{4}|\+82[- .]?(?:\(0\))?10[- .]?\d{4}[- .]?\d{4})(?!\d)"), 0),
)
STORE_CODE = re.compile(r'''(["']?storeCode["']?\s*[:=]\s*["'])([^"'\r\n]{1,200})(["'])''', re.I)


def valid_basic(token):
    try:
        decoded = base64.b64decode(token, validate=True).decode("utf-8")
        return ":" in decoded and len(decoded) > 1 and not any(ord(c) < 32 for c in decoded)
    except (ValueError, UnicodeError, binascii.Error):
        return False


def valid_jwt(token):
    try:
        parts = token.split(".")
        return all(isinstance(json.loads(base64.urlsafe_b64decode(
            p + "=" * (-len(p) % 4))), dict) for p in parts[:2])
    except (ValueError, UnicodeError, binascii.Error):
        return False


def pure_base64(value):
    if not value or len(value) % 4 or not re.fullmatch(r"[A-Za-z0-9+/]*={0,2}", value):
        return False
    try:
        return bool(base64.b64decode(value, validate=True))
    except (ValueError, binascii.Error):
        return False


def redact_text(value, policy, media=False):
    if sha(leaf_bytes(value)) in policy:
        return "[REDACTED:CORPORATE_SOURCE]", ["CORPORATE_SOURCE"]
    if media and pure_base64(value):
        return "[REDACTED:EMBEDDED_MEDIA]", ["EMBEDDED_MEDIA"]
    # Scan large inline media once, then only scan the surrounding free text.
    hits, segments, offset = [], [], 0
    for match in PATTERNS[0][1].finditer(value):
        start, end = match.span()
        segments.append((offset, value[offset:start]))
        hits.append((start, end, "INLINE_MEDIA"))
        offset = end
    segments.append((offset, value[offset:]))
    for base, segment in segments:
        for match in STORE_CODE.finditer(segment):
            if sha(leaf_bytes(match.group(2))) in getattr(policy, "store_codes", ()):
                start, end = match.span(2)
                hits.append((base + start, base + end, "LEGACY_STORE_ID"))
    for kind, pattern, group in PATTERNS[1:]:
        for base, segment in segments:
            for match in pattern.finditer(segment):
                token = match.group(group)
                if kind == "BASIC_AUTH" and not valid_basic(token):
                    continue
                if kind == "JWT" and not valid_jwt(token):
                    continue
                start, end = match.span(group)
                hits.append((base + start, base + end, kind))
    # Merge overlapping findings so replacing an outer match cannot leak a tail.
    merged = []
    for start, end, kind in sorted(hits):
        if merged and start < merged[-1][1]:
            old_start, old_end, kinds = merged[-1]
            merged[-1] = (old_start, max(old_end, end), kinds | {kind})
        else:
            merged.append((start, end, {kind}))
    result, offset, kinds = [], 0, set()
    for start, end, found in merged:
        marker = ("[REDACTED_LEGACY_STORE_ID]" if found == {"LEGACY_STORE_ID"}
                  else "[REDACTED:" + "+".join(sorted(found)) + "]")
        result.extend((value[offset:start], marker))
        offset = end
        kinds.update(found)
    result.append(value[offset:])
    return "".join(result), sorted(kinds)


def path_key(path, key):
    # Unusual object keys may themselves contain credentials; never echo them.
    if (re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", key)
            and not redact_text(key, frozenset())[1]):
        return path + "." + key
    return path + "[key-sha256=" + sha(leaf_bytes(key)) + "]"


def audit_entry(line, path, kind, before, after):
    before_bytes, after_bytes = leaf_bytes(before), leaf_bytes(after)
    return {"line": line, "jsonpath": path, "kind": kind,
            "before_sha256": sha(before_bytes), "after_sha256": sha(after_bytes),
            "before_bytes": len(before_bytes), "after_bytes": len(after_bytes)}


def transform(value, policy, line, audit, counts, path="$", key="", media=False,
              inherited_protection=False, opaque=False):
    locked = inherited_protection or protected(key)
    opaque = opaque or key.lower() == "encrypted_content"
    if isinstance(value, dict):
        if isinstance(value.get("type"), str):
            media = media or value["type"] in MEDIA_TYPES
        result = {}
        for child_key, child_value in value.items():
            child_path = path_key(path, child_key)
            key_kinds = [] if opaque else redact_text(child_key, policy)[1]
            if key_kinds:
                child_path = path + "[key-sha256=" + sha(leaf_bytes(child_key)) + "]"
                counts["unresolved_key_count"] += 1
                for kind in key_kinds:
                    audit(audit_entry(line, child_path, "UNRESOLVED_KEY:" + kind,
                                      child_key, child_key))
            result[child_key] = transform(child_value, policy, line, audit, counts,
                                          child_path, child_key, media, locked, opaque)
        return result
    if isinstance(value, list):
        return [transform(v, policy, line, audit, counts, f"{path}[{i}]", key,
                          media, locked, opaque) for i, v in enumerate(value)]
    if not isinstance(value, str):
        return value
    counts["string_leaves"] += 1
    if opaque:
        counts["opaque_unreviewed_leaves"] += 1
        return value
    changed, kinds = redact_text(value, policy, media and key.lower() in MEDIA_PAYLOAD_FIELDS)
    if locked:
        counts["protected_string_leaves"] += 1
        if kinds:
            counts["unresolved_protected_leaves"] += 1
            for kind in kinds:
                audit(audit_entry(line, path, "UNRESOLVED_PROTECTED:" + kind, value, value))
        return value
    if changed != value:
        counts["changed_leaves"] += 1
        for kind in kinds:
            counts["redaction_" + kind] += 1
            audit(audit_entry(line, path, kind, value, changed))
    return changed


def assert_preserved(before, after, locked=False):
    if type(before) is not type(after):
        raise PreparationError("PRESERVATION_TYPE_FAILURE")
    if isinstance(before, dict):
        if list(before) != list(after):
            raise PreparationError("PRESERVATION_KEYS_FAILURE")
        for key in before:
            assert_preserved(before[key], after[key], locked or protected(key))
    elif isinstance(before, list):
        if len(before) != len(after):
            raise PreparationError("PRESERVATION_COUNT_FAILURE")
        for a, b in zip(before, after):
            assert_preserved(a, b, locked)
    elif isinstance(before, Number):
        if before.token != after.token:
            raise PreparationError("PRESERVATION_NUMBER_FAILURE")
    elif not isinstance(before, str) or locked:
        if before != after:
            raise PreparationError("PRESERVATION_VALUE_FAILURE")


def fingerprint(info):
    # Windows ctime is creation time and can settle after a freshly written file.
    # Identity/size/mtime plus the second full digest verify the fixed snapshot.
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def prepare(input_path, output_dir, policy_path=None):
    source, output, policy_path = checked_paths(input_path, output_dir, policy_path)
    policy, policy_sha = load_policy(policy_path)
    output.mkdir()  # Exclusive: never reuse or overwrite an existing directory.
    candidate = output / (CANDIDATE + ".partial")
    changes = output / (CHANGES + ".partial")
    counts = Counter({"events": 0, "changed_leaves": 0, "string_leaves": 0,
                      "protected_string_leaves": 0, "unresolved_protected_leaves": 0,
                      "unresolved_key_count": 0, "opaque_unreviewed_leaves": 0, "audit_entries": 0})
    input_digest, output_digest, audit_digest = (hashlib.sha256() for _ in range(3))
    source_bytes = candidate_bytes = audit_bytes = 0
    with source.open("rb") as src, candidate.open("xb") as dst, changes.open("xb") as ledger:
        initial = fingerprint(os.fstat(src.fileno()))

        def audit(entry):
            nonlocal audit_bytes
            raw = (json.dumps(entry, ensure_ascii=True, separators=(",", ":")) + "\n").encode("utf-8")
            ledger.write(raw)
            audit_digest.update(raw)
            audit_bytes += len(raw)
            counts["audit_entries"] += 1

        for line, raw in enumerate(src, 1):
            input_digest.update(raw)
            source_bytes += len(raw)
            if not raw.strip():
                raise PreparationError("BLANK_JSONL_LINE")
            event = parse_event(raw)
            result = transform(event, policy, line, audit, counts)
            assert_preserved(event, result)
            rendered = leaf_bytes(encode(result)) + b"\n"
            dst.write(rendered)
            output_digest.update(rendered)
            candidate_bytes += len(rendered)
            counts["events"] += 1
        if not counts["events"]:
            raise PreparationError("EMPTY_INPUT")
        if initial != fingerprint(os.fstat(src.fileno())) or initial != fingerprint(source.stat()):
            raise PreparationError("INPUT_CHANGED")
        # A second streamed digest detects in-place edits that metadata alone misses.
        src.seek(0)
        check_digest = hashlib.sha256()
        while chunk := src.read(1024 * 1024):
            check_digest.update(chunk)
        if check_digest.digest() != input_digest.digest() or initial != fingerprint(os.fstat(src.fileno())):
            raise PreparationError("INPUT_CHANGED")
        for handle in (dst, ledger):
            handle.flush()
            os.fsync(handle.fileno())
    manifest = {
        "status": "NOT-APPROVED", "format_version": 1,
        "input_sha256": input_digest.hexdigest(), "input_bytes": source_bytes,
        "candidate_sha256": output_digest.hexdigest(), "candidate_bytes": candidate_bytes,
        "changes_sha256": audit_digest.hexdigest(), "changes_bytes": audit_bytes,
        "policy_sha256": policy_sha, "policy_leaf_count": len(policy),
        "policy_store_code_count": len(policy.store_codes),
        "counts": dict(sorted(counts.items())),
        "review": {"corporate_source_coverage": "HASH_MATCHES_ONLY" if policy_path is not None else "NOT_PROVIDED",
                   "free_text_semantic_review": "NOT_PERFORMED",
                   "encrypted_content": "OPAQUE_UNREVIEWED",
                   "external_submission": "NOT_PERFORMED"},
    }
    staged_manifest = output / (MANIFEST + ".partial")
    with staged_manifest.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    candidate.rename(output / CANDIDATE)
    changes.rename(output / CHANGES)
    staged_manifest.rename(output / MANIFEST)  # Completion marker is published last.
    return manifest


class QuietParser(argparse.ArgumentParser):
    def error(self, _message):
        raise PreparationError("INVALID_ARGUMENTS")


def main(argv=None):
    try:
        parser = QuietParser(description=__doc__)
        parser.add_argument("--input", required=True)
        parser.add_argument("--output-dir", required=True)
        parser.add_argument("--policy")
        args = parser.parse_args(argv)
        result = prepare(args.input, args.output_dir, args.policy)
        print(json.dumps({"status": result["status"], "counts": result["counts"],
                          "input_sha256": result["input_sha256"],
                          "candidate_sha256": result["candidate_sha256"]}, sort_keys=True))
        return 0
    except PreparationError as error:
        print("ERROR:" + error.args[0], file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, RecursionError, OverflowError):
        print("ERROR:PREPARATION_FAILED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
