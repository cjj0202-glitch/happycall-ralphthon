"""Frozen synthetic TEXT evaluation. Default: validate/plan only, no keys or API.

Only --run-live lazily imports LiveAnalyzer and reads the existing local ledger.
No result is an audio/STT-quality or human-usability measurement.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import uuid

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "tests/evaluation/oneflow-cases.json"
LOCAL_EVALUATION_ROOT = ROOT / ".local/evaluation"
FROZEN_DATASET_SHA256 = "71c852da9497be8dacb744c49e62299f5ebc5d45ba1df4ea086683a2bd467884"
FIELDS = ("storeId", "subject", "quantity", "unit", "request", "departmentId")
MANUAL_FIELDS = ("subject", "request")
AUTO_FIELDS = ("storeId", "quantity", "unit", "departmentId")
DEPARTMENTS = [{"id": "delivery", "name": "배송 운영"}, {"id": "warehouse", "name": "출고 운영"},
               {"id": "cs", "name": "고객 지원"}]
RESERVATION_ESTIMATE_CENTS = 15
REQUIRED_BOUNDARY_TAGS = {"profanity", "irrelevant-speech", "explicit-zero", "unknown-receipt", "order-vs-receipt",
    "unit-correction", "multiple-products-ambiguous", "stt-store-typo-simulation", "pack-size-no-conversion",
    "counselor-reentry", "evidence-absence", "prompt-injection", "temporal-scope"}


class EvaluationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def canonical_hash(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def dataset_hash(dataset: dict) -> str:
    return canonical_hash({key: value for key, value in dataset.items() if key != "frozenSha256"})


def _strings(value) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def _numeric(value) -> bool:
    try:
        return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def validate_dataset(dataset) -> list[str]:
    """Validate corpus/oracle integrity, never model extraction accuracy."""
    errors = []
    if not isinstance(dataset, dict):
        return ["dataset must be an object"]
    if dataset.get("datasetId") != "oneflow-synthetic-text-t27-v2" or dataset.get("version") != 2:
        errors.append("unsupported frozen dataset version")
    if dataset.get("mode") != "text-only" or dataset.get("language") != "ko-KR":
        errors.append("scope must remain Korean synthetic text-only")
    if not isinstance(dataset.get("provenance"), str) or "independently-authored-synthetic" not in dataset["provenance"]:
        errors.append("independent synthetic provenance required")
    if dataset.get("fieldOrder") != list(FIELDS) or dataset.get("targetAccuracy") != .9:
        errors.append("six fields and 90 percent target are fixed")
    if dataset.get("rubricVersion") != "pre-output-v1":
        errors.append("pre-output rubric version required")
    if dataset.get("cohorts") != {"fixed": {"count": 20, "missing": 10, "wrong": 10}, "boundary": {"count": 12}}:
        errors.append("cohort declarations must be fixed20/boundary12 and missing10/wrong10")
    try:
        actual_hash = dataset_hash(dataset)
    except (TypeError, ValueError):
        actual_hash = None
    if actual_hash != FROZEN_DATASET_SHA256 or dataset.get("frozenSha256") != FROZEN_DATASET_SHA256:
        errors.append("frozen input/oracle/rubric hash mismatch; do not relabel after seeing output")
    rows = dataset.get("rows")
    if not isinstance(rows, list):
        return errors + ["rows must be a list"]
    ids, texts, boundary_tags = set(), set(), set()
    counts = {"fixed": 0, "boundary": 0, "fixed-missing": 0, "fixed-wrong": 0}
    for index, row in enumerate(rows):
        prefix = f"row {index}"
        if not isinstance(row, dict):
            errors.append(prefix + " must be an object")
            continue
        cid, cohort, kind = row.get("id"), row.get("cohort"), row.get("type")
        if not isinstance(cid, str) or not re.fullmatch(r"(?:FIX-[MW]\d{2}|EDGE-\d{2})", cid) or cid in ids:
            errors.append(prefix + " invalid or duplicate id")
        else:
            ids.add(cid)
        if cohort not in ("fixed", "boundary") or kind not in ("missing", "wrong"):
            errors.append(prefix + " invalid cohort/type")
        else:
            counts[cohort] += 1
            if cohort == "fixed":
                counts["fixed-" + kind] += 1
        text = row.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 8000 or text in texts:
            errors.append(prefix + " blank/duplicate/oversized synthetic input")
        else:
            texts.add(text)
        tags = row.get("tags")
        if not _strings(tags):
            errors.append(prefix + " tags required")
        elif cohort == "boundary":
            boundary_tags.update(tags)
        context = row.get("context", {})
        store = context.get("store", {}) if isinstance(context, dict) else {}
        if (not isinstance(store, dict) or store.get("id") != "SYN-EVAL-" + str(cid)
                or not isinstance(store.get("name"), str) or not store["name"].startswith("가상 ")):
            errors.append(prefix + " independently fictional store required")
        if (not isinstance(context, dict) or set(context) != {"store", "intake", "evidence"}
                or not isinstance(context.get("intake"), dict) or context.get("evidence") != []):
            errors.append(prefix + " allowed synthetic context only; no real evidence")
        expected = row.get("expected")
        if not isinstance(expected, dict) or set(expected) != set(FIELDS):
            errors.append(prefix + " six explicit expectations required")
            continue
        for name in FIELDS:
            oracle = expected[name]
            if not isinstance(oracle, dict):
                errors.append(prefix + ":" + name + " oracle must be an object")
                continue
            if name in MANUAL_FIELDS:
                if (oracle.get("mode") != "manual-review-required" or "accepted" in oracle
                        or not _strings(oracle.get("mustPreserve")) or not _strings(oracle.get("mustNotInvent"))):
                    errors.append(prefix + ":" + name + " independent semantic rubric required")
                continue
            accepted = oracle.get("accepted")
            if (oracle.get("mode") != "one-of" or not isinstance(accepted, list) or not accepted
                    or not isinstance(oracle.get("basis"), str) or not oracle["basis"].strip()):
                errors.append(prefix + ":" + name + " explicit accepted values and basis required")
                continue
            for value in accepted:
                valid = (value is None or _numeric(value)) if name == "quantity" else (
                    value in (None, "EA", "BOX") if name == "unit" else (
                    isinstance(value, str) and value in ("delivery", "warehouse", "cs", "") if name == "departmentId"
                    else value is None or (isinstance(value, str) and value.startswith("SYN-EVAL-"))))
                if not valid:
                    errors.append(prefix + ":" + name + " invalid accepted value")
        safety = row.get("safetyRubric", {})
        if (not isinstance(safety, dict) or safety.get("reviewMode") != "manual-review-required"
                or not _strings(safety.get("mustPreserve")) or not _strings(safety.get("mustNotAssert"))
                or type(safety.get("questionRequired")) is not bool
                or not isinstance(safety.get("requiredIssueFields"), list)
                or any(field not in FIELDS for field in safety.get("requiredIssueFields", []))):
            errors.append(prefix + " safety semantic rubric required")
    if counts != {"fixed": 20, "boundary": 12, "fixed-missing": 10, "fixed-wrong": 10}:
        errors.append("corpus must contain exactly fixed20 (missing10/wrong10) plus separate boundary12")
    if not REQUIRED_BOUNDARY_TAGS <= boundary_tags:
        errors.append("required boundary coverage missing")
    return errors


def load_dataset(path: Path = DATASET_PATH) -> dict:
    dataset = json.loads(path.read_text(encoding="utf-8-sig"))
    errors = validate_dataset(dataset)
    if errors:
        raise ValueError("; ".join(errors))
    return dataset


def build_case(row: dict) -> dict:
    """Explicit allowlist: never pass expected, rubrics or a replay/STT answer."""
    return {"id": row["id"], "channel": "text", "synthetic": True, "type": row["type"],
            "text": row["text"], "store": copy.deepcopy(row["context"]["store"]),
            "intake": copy.deepcopy(row["context"]["intake"]), "evidence": []}


def _schema_valid(analysis) -> bool:
    # These modules define a pure schema; no live analyzer/client/key reader imports.
    from jsonschema import Draft202012Validator
    from server.analysis_schema import ANALYSIS_SCHEMA
    try:
        canonical_hash(analysis)  # JSON cannot represent NaN/Infinity or arbitrary objects.
        return not any(Draft202012Validator(ANALYSIS_SCHEMA).iter_errors(analysis))
    except (ValueError, TypeError):
        return False


def _matches(actual, expected) -> bool:
    if expected is None:
        return actual is None
    if _numeric(expected):
        return _numeric(actual) and actual == expected
    return type(actual) is type(expected) and actual == expected


def score_case(row: dict, record: dict | None, review: dict | None = None) -> dict:
    status = "not-run" if record is None else record.get("status", "error")
    if status != "success":
        status = "error" if status != "not-run" else status
        return {"fields": {name: status for name in FIELDS}, "safety": status, "structuralSafetyFailures": []}
    result = record.get("result")
    analysis = result.get("analysis") if isinstance(result, dict) else None
    if not _schema_valid(analysis):
        return {"fields": {name: "invalid-output" for name in FIELDS}, "safety": "invalid-output", "structuralSafetyFailures": []}
    actual = {**analysis["fields"], "departmentId": analysis["department"]["id"]}
    fields = {}
    for name in AUTO_FIELDS:
        fields[name] = "correct" if any(_matches(actual[name], value) for value in row["expected"][name]["accepted"]) else "incorrect"
    for name in MANUAL_FIELDS:
        fields[name] = ({"pass": "correct", "fail": "incorrect"}[review["fields"][name]["verdict"]]
                        if review else "manual-review-required")
    rubric = row["safetyRubric"]
    structural = []
    if rubric["questionRequired"] and not any(question.strip() for question in analysis["questions"]):
        structural.append("required-question-absent")
    for name in rubric["requiredIssueFields"]:
        if not any(issue["field"] == name and issue["evidence"].strip() for issue in analysis["issues"]):
            structural.append("required-issue-evidence-absent:" + name)
    safety = "fail" if structural else (review["safety"]["verdict"] if review else "manual-review-required")
    return {"fields": fields, "safety": safety, "structuralSafetyFailures": structural}


def validate_reviews(document: dict, records: dict[str, dict]) -> dict[str, dict]:
    if not isinstance(document, dict) or document.get("datasetSha256") != FROZEN_DATASET_SHA256 or not isinstance(document.get("reviews"), list):
        raise ValueError("Manual review dataset/hash format invalid")
    reviews = {}
    for review in document["reviews"]:
        if not isinstance(review, dict):
            raise ValueError("Manual review must be an object")
        cid = review.get("caseId")
        if not isinstance(cid, str) or cid not in records or cid in reviews:
            raise ValueError("Manual review case unknown or duplicated")
        record = records[cid]
        if record.get("status") != "success" or review.get("resultSha256") != canonical_hash(record):
            raise ValueError("Manual review must match this successful result hash")
        if review.get("reviewerKind") not in ("human", "independent-ai") or not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
            raise ValueError("Independent reviewer identity and kind required")
        fields = review.get("fields")
        if not isinstance(fields, dict) or set(fields) != set(MANUAL_FIELDS):
            raise ValueError("Both semantic fields require explicit reviews")
        for verdict in [*fields.values(), review.get("safety")]:
            if (not isinstance(verdict, dict) or verdict.get("verdict") not in ("pass", "fail")
                    or not isinstance(verdict.get("rationale"), str) or not verdict["rationale"].strip()):
                raise ValueError("Every semantic/safety verdict needs an independent rationale")
        reviews[cid] = review
    return reviews


def summarize(dataset: dict, records: dict[str, dict], reviews: dict[str, dict] | None = None) -> dict:
    reviews = reviews or {}
    report = {"datasetSha256": FROZEN_DATASET_SHA256, "scope": "synthetic-text-six-field-evaluation; not audio/STT quality",
              "cohorts": {}, "cases": [], "apiDispatchAttempts": 0, "apiSuccesses": 0, "reservationCount": 0,
              "reservedCents": 0, "reviewerKinds": sorted({review["reviewerKind"] for review in reviews.values()})}
    for cohort, planned in (("fixed", 20), ("boundary", 12)):
        counts = {state: 0 for state in ("correct", "incorrect", "manual-review-required", "not-run", "error", "invalid-output")}
        per_field = {name: dict(counts) for name in FIELDS}
        safety = {state: 0 for state in ("pass", "fail", "manual-review-required", "not-run", "error", "invalid-output")}
        for row in (row for row in dataset["rows"] if row["cohort"] == cohort):
            record = records.get(row["id"])
            verdict = score_case(row, record, reviews.get(row["id"]))
            for name, state in verdict["fields"].items():
                counts[state] += 1
                per_field[name][state] += 1
            safety[verdict["safety"]] += 1
            events = record.get("events", []) if record else []
            reservations = [event for event in events if event.get("kind") == "reserved"]
            report["apiDispatchAttempts"] += sum(event.get("kind") == "api-dispatch" for event in events)
            report["apiSuccesses"] += sum(event.get("kind") == "api-success" for event in events)
            report["reservationCount"] += len(reservations)
            report["reservedCents"] += sum(event["cents"] for event in reservations)
            report["cases"].append({"caseId": row["id"], "cohort": cohort, "status": record.get("status", "error") if record else "not-run",
                                    "fields": verdict["fields"], "safety": verdict["safety"],
                                    "structuralSafetyFailures": verdict["structuralSafetyFailures"],
                                    "errorCode": record.get("error", {}).get("code") if record else None})
        total = planned * len(FIELDS)
        complete = counts["correct"] + counts["incorrect"] == total
        accuracy = counts["correct"] / total if complete else None
        report["cohorts"][cohort] = {"plannedCases": planned, "plannedCells": total, "automatableCells": planned * 4,
            "manualSemanticCells": planned * 2, "counts": counts, "perField": per_field, "safetyCounts": safety,
            "accuracy": accuracy, "target": .9 if cohort == "fixed" else None,
            "targetStatus": ("met" if accuracy >= .9 else "not-met") if cohort == "fixed" and complete else "not-determined"}
    return report


def _write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _safe_error(exc: Exception) -> dict:
    code = getattr(exc, "code", "EVALUATION_ERROR")
    if not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9_]{1,80}", code):
        code = "EVALUATION_ERROR"
    return {"code": code, "type": type(exc).__name__}


def _code_hashes() -> dict:
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
        "scripts/evaluate_demo_analysis.py", "server/live.py", "server/claim_grounding.py", "server/request_grounding.py", "server/transcript_provenance.py", "server/analysis_schema.py",
        "server/budget.py", "server/runtime_config.py")}


class Recorder:
    def __init__(self, run_dir: Path):
        self.run_dir, self.case_id = run_dir, None
        self.events: list[dict] = []
        self.raw_model_outputs: list[dict] = []

    def event(self, kind: str, **details):
        event = {"at": datetime.now(timezone.utc).isoformat(), "caseId": self.case_id, "kind": kind, **details}
        self.events.append(event)
        with (self.run_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
            handle.flush()


def _validate_local_ledger(path: Path) -> None:
    if not path.is_file():
        raise EvaluationError("EVALUATION_BUDGET_LEDGER_MISSING", "Existing local budget ledger required; no reset/bootstrap")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise EvaluationError("EVALUATION_BUDGET_LEDGER_INVALID", "Existing local budget ledger unreadable") from None
    if not isinstance(data, dict) or "initialReservedCents" in data or not isinstance(data.get("entries"), list):
        raise EvaluationError("EVALUATION_BUDGET_LEDGER_INVALID", "Existing local budget ledger format invalid")
    ids = set()
    for entry in data["entries"]:
        if (not isinstance(entry, dict) or not isinstance(entry.get("requestId"), str) or not entry["requestId"]
                or entry["requestId"] in ids or type(entry.get("reservedCents")) is not int or entry["reservedCents"] <= 0
                or entry.get("state") not in ("reserved", "completed", "failed-cost-uncertain")):
            raise EvaluationError("EVALUATION_BUDGET_LEDGER_INVALID", "Existing local budget reservations invalid")
        ids.add(entry["requestId"])


class RecordingBudget:
    def __init__(self, budget, recorder: Recorder):
        self.budget, self.recorder = budget, recorder

    def _call(self, operation, *args):
        # The same FileLock is reentrant; missing/corrupt local state must not reset.
        with self.budget.lock:
            _validate_local_ledger(self.budget.path)
            return operation(*args)

    def status(self):
        return self._call(self.budget.status)

    def reserve(self, cents, purpose):
        try:
            request_id = self._call(self.budget.reserve, cents, purpose)
        except Exception as exc:
            self.recorder.event("reservation-rejected", error=_safe_error(exc))
            raise
        self.recorder.event("reserved", requestId=request_id, cents=cents, purpose=purpose)
        return request_id

    def finish(self, request_id, success):
        try:
            self._call(self.budget.finish, request_id, success)
        except Exception as exc:
            self.recorder.event("finish-error", requestId=request_id, error=_safe_error(exc))
            raise
        self.recorder.event("finished", requestId=request_id, success=success, reservationRetained=True)


def tracked_client(client, recorder: Recorder):
    def create(**kwargs):
        recorder.event("api-dispatch", endpoint="chat.completions", model=kwargs.get("model"))
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as exc:
            recorder.event("api-error", error=_safe_error(exc))
            raise
        recorder.event("api-success", endpoint="chat.completions")
        choices = getattr(response, "choices", [])
        message = getattr(choices[0], "message", None) if choices else None
        values = {"content": getattr(message, "content", None), "refusal": getattr(message, "refusal", None),
                  "finishReason": getattr(choices[0], "finish_reason", None) if choices else None,
                  "responseId": getattr(response, "id", None)}
        recorder.raw_model_outputs.append({"caseId": recorder.case_id,
                                          **{key: value if isinstance(value, str) else None for key, value in values.items()}})
        return response
    def no_audio(**kwargs):
        raise RuntimeError("Text evaluation must not dispatch audio/STT")
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
                           audio=SimpleNamespace(transcriptions=SimpleNamespace(create=no_audio)))


def _live_runtime(budget_path: Path, recorder: Recorder):
    # Called exclusively by the explicit live branch, never import/validate/tests.
    _validate_local_ledger(budget_path)
    from server.budget import Budget
    from server.live import LiveAnalyzer, demo_client
    budget = RecordingBudget(Budget(path=budget_path), recorder)
    analyzer = LiveAnalyzer(budget=budget, client_factory=lambda: tracked_client(demo_client(), recorder))
    return analyzer, budget


def execute_live(dataset: dict, rows: list[dict], budget_path: Path, measured_head: str) -> Path:
    if validate_dataset(dataset):
        raise ValueError("Frozen dataset validation required before live execution")
    by_id = {row["id"]: row for row in dataset["rows"]}
    if (not rows or len({row["id"] for row in rows}) != len(rows)
            or any(row != by_id.get(row["id"]) for row in rows)):
        raise ValueError("Selected live inputs must exactly match the frozen dataset")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", measured_head):
        raise ValueError("Explicit externally measured 40-character HEAD required")
    if not budget_path.is_absolute():
        raise ValueError("Existing absolute local budget path required")
    _validate_local_ledger(budget_path)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:10]
    run_dir = LOCAL_EVALUATION_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    _write_json(run_dir / "dataset.json", dataset)
    recorder = Recorder(run_dir)
    manifest = {"runId": run_id, "startedAt": datetime.now(timezone.utc).isoformat(), "mode": "text-only-demo-live",
                "datasetSha256": FROZEN_DATASET_SHA256, "measuredHead": measured_head.lower(),
                "headSource": "operator-supplied measurement", "headVerifiedByRunner": False,
                "codeSha256Before": _code_hashes(), "selectedCaseIds": [row["id"] for row in rows], "status": "running"}
    _write_json(run_dir / "manifest.json", manifest)
    records = {}
    try:
        analyzer, budget = _live_runtime(budget_path, recorder)
        manifest["budgetBefore"] = budget.status()
        _write_json(run_dir / "manifest.json", manifest)
        for row in rows:
            recorder.case_id = row["id"]
            event_start, output_start = len(recorder.events), len(recorder.raw_model_outputs)
            case = build_case(row)
            record = {"caseId": row["id"], "cohort": row["cohort"], "type": row["type"], "input": case,
                      "inputSha256": canonical_hash({"case": case, "departments": DEPARTMENTS}),
                      "textSha256": hashlib.sha256(row["text"].encode("utf-8")).hexdigest(),
                      "expected": copy.deepcopy(row["expected"]), "status": "running"}
            recorder.event("analysis-invocation")
            try:
                record["result"] = analyzer.analyze(copy.deepcopy(case), copy.deepcopy(DEPARTMENTS))
                record["status"] = "success"
            except Exception as exc:
                record["status"], record["error"] = "error", _safe_error(exc)
            record["events"] = copy.deepcopy(recorder.events[event_start:])
            record["rawModelOutputs"] = copy.deepcopy(recorder.raw_model_outputs[output_start:])
            records[row["id"]] = record
            _write_json(run_dir / (row["id"] + ".json"), {"record": record, "resultSha256": canonical_hash(record)})
            if record.get("error", {}).get("code") in {"BUDGET_LIMIT", "API_KEY_MISSING", "DEMO_POLICY_REQUIRED", "DEMO_CONFIG_UNAVAILABLE",
                                                        "EVALUATION_BUDGET_LEDGER_MISSING", "EVALUATION_BUDGET_LEDGER_INVALID"}:
                manifest["stoppedBecause"] = record["error"]["code"]
                break
            if any(event.get("kind") == "api-error" and event.get("error", {}).get("type") in
                   {"AuthenticationError", "PermissionDeniedError", "RateLimitError"} for event in record["events"]):
                manifest["stoppedBecause"] = "PROVIDER_ACCESS_OR_LIMIT"
                break
        manifest["budgetAfter"] = budget.status()
        manifest["status"] = "complete-with-errors" if any(record["status"] == "error" for record in records.values()) else "completed"
    except Exception as exc:
        manifest["status"], manifest["error"] = "interrupted", _safe_error(exc)
    finally:
        manifest["finishedAt"] = datetime.now(timezone.utc).isoformat()
        manifest["completedCaseIds"] = list(records)
        try:
            manifest["codeSha256After"] = _code_hashes()
            manifest["codeChangedDuringRun"] = manifest["codeSha256Before"] != manifest["codeSha256After"]
        except OSError as exc:
            manifest["codeMeasurementError"] = _safe_error(exc)
        _write_json(run_dir / "manifest.json", manifest)
        _write_json(run_dir / "summary.json", summarize(dataset, records))
    return run_dir


def summarize_run(run_dir: Path, review_path: Path | None = None) -> tuple[dict, dict]:
    dataset = load_dataset(run_dir / "dataset.json")
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("datasetSha256") != FROZEN_DATASET_SHA256:
        raise ValueError("Run manifest dataset hash mismatch")
    records = {}
    for row in dataset["rows"]:
        path = run_dir / (row["id"] + ".json")
        if not path.is_file():
            continue
        envelope = json.loads(path.read_text(encoding="utf-8"))
        record = envelope.get("record")
        if (not isinstance(record, dict) or record.get("caseId") != row["id"]
                or envelope.get("resultSha256") != canonical_hash(record)
                or record.get("input") != build_case(row) or record.get("expected") != row["expected"]):
            raise ValueError("Stored result/input/oracle hash mismatch")
        records[row["id"]] = record
    reviews = validate_reviews(json.loads(review_path.read_text(encoding="utf-8")), records) if review_path else {}
    return summarize(dataset, records, reviews), manifest


def _selected_rows(dataset, cohort, case_ids):
    if case_ids and (len(case_ids) != len(set(case_ids)) or not set(case_ids) <= {row["id"] for row in dataset["rows"]}):
        raise ValueError("Unknown or duplicate selected case IDs")
    rows = [row for row in dataset["rows"] if (cohort == "all" or row["cohort"] == cohort)
            and (not case_ids or row["id"] in case_ids)]
    if not rows or case_ids and {row["id"] for row in rows} != set(case_ids):
        raise ValueError("Selected case IDs and cohort do not agree")
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--run-live", action="store_true")
    action.add_argument("--summarize-run", type=Path)
    action.add_argument("--validate", action="store_true")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--cohort", choices=("fixed", "boundary", "all"), default="all")
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--budget-path", type=Path)
    parser.add_argument("--measured-head")
    parser.add_argument("--manual-review", type=Path)
    parser.add_argument("--redacted-report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.manual_review and not args.summarize_run:
            raise ValueError("Manual review applies only to --summarize-run")
        if args.redacted_report and not (args.run_live or args.summarize_run):
            raise ValueError("Result report requires a live run or an existing run summary")
        if args.summarize_run:
            report, manifest = summarize_run(args.summarize_run, args.manual_review)
        else:
            dataset = load_dataset(args.dataset)
            rows = _selected_rows(dataset, args.cohort, args.case_id)
            if not args.run_live:
                print(json.dumps({"status": "validated-plan-only", "datasetSha256": FROZEN_DATASET_SHA256,
                    "fixedCases": 20, "boundaryCases": 12, "selectedCases": len(rows),
                    "plannedFixedCells": 120, "automaticFixedCells": 80, "manualFixedCells": 40,
                    "plannedReservationCents": len(rows) * RESERVATION_ESTIMATE_CENTS,
                    "modelCalls": 0, "keyReads": 0, "modelAccuracy": "not-measured"}, ensure_ascii=False))
                return 0
            if args.budget_path is None or not args.measured_head:
                raise ValueError("--run-live requires --budget-path and --measured-head")
            run_dir = execute_live(dataset, rows, args.budget_path, args.measured_head)
            report, manifest = summarize_run(run_dir)
            print(json.dumps({"runId": manifest["runId"], "localArtifacts": str(run_dir), "status": manifest["status"]}, ensure_ascii=False))
        if args.redacted_report:
            if args.redacted_report.exists():
                raise ValueError("Refuse to overwrite an existing report")
            args.redacted_report.parent.mkdir(parents=True, exist_ok=True)
            _write_json(args.redacted_report, report)
        print(json.dumps(report, ensure_ascii=False))
        if (manifest.get("status") == "interrupted" or any(row["status"] == "error" for row in report["cases"])
                or any("invalid-output" in row["fields"].values() for row in report["cases"])):
            return 1
        return 0
    except (OSError, ValueError, TypeError) as exc:
        # Validation details never include SDK exception bodies or credentials.
        print(json.dumps({"status": "evaluation-not-completed", "error": _safe_error(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
