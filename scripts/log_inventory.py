"""Inventory only explicitly selected Codex JSONL files; never copy or upload logs."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inspect(path):
    size = path.stat().st_size
    digest = hashlib.sha256()
    lines, invalid, blank = 0, 0, 0
    with path.open("rb") as stream:
        for line in stream:
            digest.update(line)
            if not line.strip():
                blank += 1
                continue
            lines += 1
            try:
                if not isinstance(json.loads(line), dict):
                    invalid += 1
            except (ValueError, UnicodeError):
                invalid += 1
    return {"file": path.name, "bytes": size, "sha256": digest.hexdigest(),
            "json_lines": lines, "invalid_lines": invalid, "blank_lines": blank,
            "within_submission_file_limit": size <= 1024**3,
            "within_howlong_file_limit": size <= 256*1024**2}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    args = parser.parse_args()
    records = []
    for path in args.input:
        if path.suffix.lower() != ".jsonl" or not path.is_file():
            parser.error("Select existing .jsonl files only")
        records.append(inspect(path))
    total = sum(r["bytes"] for r in records)
    report = {"measured_at": datetime.now(timezone.utc).isoformat(), "files": records,
              "total_bytes": total, "duplicate_files": len(records)-len({r["sha256"] for r in records}),
              "submission_size_ok": total <= 10*1024**3 and all(r["within_submission_file_limit"] for r in records),
              "howlong_size_ok": len(records) <= 100 and total <= 512*1024**2 and all(r["within_howlong_file_limit"] for r in records),
              "secret_review": "NOT_PERFORMED", "event_semantics": "NOT_VERIFIED", "uploaded": False}
    output = ROOT / ".local/log-manifest.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Files={len(records)} bytes={total} invalid_lines={sum(r['invalid_lines'] for r in records)}")
    print("Metadata saved locally. No content printed, copied, or uploaded.")
    return 0 if all(r["json_lines"] and not r["invalid_lines"] for r in records) and report["submission_size_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
