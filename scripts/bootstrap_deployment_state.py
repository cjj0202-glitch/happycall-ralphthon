"""Explicit, create-only deployment bootstrap; dry-run is entirely offline.

This carries a reviewed aggregate reservation forward. It does not recover the
old ledger's entries or establish that the supplied amount is its final total.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.cas_budget import CasBudget
from server.cas_repository import CasCaseRepository
from server.cas_store import CasConflict, CasValue
from server import intake_idempotency
from server.vercel_blob_store import VercelBlobCasStore, _validate_json_value
from server.dynamodb_store import DynamoDbCasStore, TABLE_NAME, encode_document

CASES_KEY = "oneflow/cases.json"
BUDGET_KEY = "oneflow/budget.json"
MAX_BYTES = 4 * 1024 * 1024


class BootstrapError(Exception):
    def __init__(self, code, *, created=0, attempted=0):
        super().__init__(code)
        self.code, self.created, self.attempted = code, created, attempted


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate member")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise ValueError("non-finite value")


def validate_cases(document):
    try:
        _validate_json_value(document)
        encoded = json.dumps(document, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > MAX_BYTES:
            raise ValueError
        checked = CasCaseRepository._document(CasValue(document, "offline-validation"))
        attempts = checked.get("intakeRequests", {})
        if not isinstance(attempts, dict):
            raise ValueError
        for digest in attempts:
            intake_idempotency.lookup(checked, digest)
        return copy.deepcopy(document)
    except Exception:
        raise BootstrapError("INVALID_CASES_INPUT") from None


def read_cases(path):
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs,
                           parse_constant=_invalid_constant)
    except Exception:
        raise BootstrapError("INVALID_CASES_INPUT") from None
    return validate_cases(value)


def _baseline(value):
    if type(value) is not int or value < 0:
        raise BootstrapError("INVALID_BASELINE")
    return value


def _budget_document(value, baseline):
    try:
        # Validation only: _document does not read, seed, or reserve.
        return CasBudget(None, initial_reserved_cents=baseline)._document(value)
    except Exception:
        raise BootstrapError("EXISTING_BUDGET_MISMATCH") from None


def _existing_cases(value, expected):
    try:
        actual = validate_cases(value.payload)
    except BootstrapError:
        raise BootstrapError("EXISTING_CASES_INVALID") from None
    if actual != expected:
        raise BootstrapError("EXISTING_CASES_MISMATCH")


def bootstrap(store, cases, baseline, *, resume_partial=False):
    """Apply through an injected raw CAS store, with no overwrite or retry.

    Two documents are not a transaction. Budget is created first. A one-document
    state is refused by default, and a missing budget is never reconstructed.
    """
    baseline = _baseline(baseline)
    cases = validate_cases(cases)
    created = attempted = 0
    try:
        existing_cases = store.read(CASES_KEY)
        existing_budget = store.read(BUDGET_KEY)
        if existing_cases is not None:
            _existing_cases(existing_cases, cases)
        budget = _budget_document(existing_budget, baseline) if existing_budget is not None else None
        if existing_cases is not None and existing_budget is None:
            raise BootstrapError("MISSING_EXISTING_BUDGET")
        if existing_budget is not None and existing_cases is None:
            if not resume_partial:
                raise BootstrapError("PARTIAL_STATE_REQUIRES_REVIEW")
            if budget["entries"]:
                raise BootstrapError("PARTIAL_STATE_NOT_PRISTINE")
        new_budget = {"schemaVersion": 1, "initialReservedCents": baseline,
                      "limitCents": 3000, "warnCents": 2500, "entries": []}
        for key, existing, payload in ((BUDGET_KEY, existing_budget, new_budget),
                                       (CASES_KEY, existing_cases, cases)):
            if existing is None:
                attempted += 1
                store.compare_and_swap(key, payload, None)
                created += 1
        # Never report success from PUT alone: read and validate both documents.
        final_cases = store.read(CASES_KEY)
        final_budget = store.read(BUDGET_KEY)
        if final_cases is None or final_budget is None:
            raise BootstrapError("READBACK_STATE_MISSING")
        _existing_cases(final_cases, cases)
        budget = _budget_document(final_budget, baseline)
        return {"status": "created" if created else "already_initialized",
                "createdDocuments": created, "attemptedWrites": attempted,
                "caseCount": len(cases["cases"]), "baselineReservedCents": baseline,
                "budgetEntryCount": len(budget["entries"]),
                "totalReservedCents": CasBudget._total(budget)}
    except BootstrapError as exc:
        raise BootstrapError(exc.code, created=created, attempted=attempted) from None
    except CasConflict:
        raise BootstrapError("CREATE_CONFLICT_REVIEW_REQUIRED", created=created, attempted=attempted) from None
    except Exception:
        # Even a PUT exception can mean the write reached the server. No retry,
        # deletion, rollback, raw exception, URL, credentials, or body is exposed.
        raise BootstrapError("REMOTE_STATE_UNCERTAIN", created=created, attempted=attempted) from None


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise BootstrapError("INVALID_ARGUMENTS")


def _parse_cents(value):
    if not re.fullmatch(r"[0-9]+", value):
        raise BootstrapError("INVALID_BASELINE")
    try:
        return int(value)
    except ValueError:
        raise BootstrapError("INVALID_BASELINE") from None


def main(argv=None, *, environ=None, store_factory=None):
    try:
        parser = _Parser(description=__doc__)
        parser.add_argument("--cases", required=True, help="Explicit JSON document path; never printed")
        parser.add_argument("--baseline-reserved-cents", required=True, type=_parse_cents)
        parser.add_argument("--backend", choices=("vercel-blob", "dynamodb"), default="vercel-blob")
        parser.add_argument("--apply", action="store_true", help="Enable remote read/create-if-absent")
        parser.add_argument("--confirm-baseline-reviewed", action="store_true",
                            help="Confirm old paid calls stopped; baseline source, limit, and no double counting reviewed")
        parser.add_argument("--resume-partial", action="store_true",
                            help="After review, complete a matching pristine budget-only initialization")
        args = parser.parse_args(argv)
        cases = read_cases(args.cases)
        baseline = _baseline(args.baseline_reserved_cents)
        if args.backend == "dynamodb":
            # Validate the smaller item bound before any environment access or write.
            try:
                encode_document(cases)
            except Exception:
                raise BootstrapError("DYNAMODB_CASES_TOO_LARGE_OR_INVALID") from None
        if not args.apply:
            print(json.dumps({"status": "dry_run_offline", "caseCount": len(cases["cases"]),
                              "baselineReservedCents": baseline, "createdDocuments": 0,
                              "attemptedWrites": 0}))
            return 0
        if not args.confirm_baseline_reviewed:
            raise BootstrapError("BASELINE_REVIEW_CONFIRMATION_REQUIRED")
        environment = os.environ if environ is None else environ
        if args.backend == "dynamodb":
            table = environment.get("ONEFLOW_DYNAMODB_TABLE")
            if not isinstance(table, str) or not TABLE_NAME.fullmatch(table):
                raise BootstrapError("INVALID_STORAGE_ENV")
            kwargs, default_factory = {"table_name": table}, DynamoDbCasStore
        else:
            token = environment.get("BLOB_READ_WRITE_TOKEN")
            store_id = environment.get("ONEFLOW_BLOB_STORE_ID")
            if (not isinstance(token, str) or not 0 < len(token) <= 8192
                    or any(not 33 <= ord(char) <= 126 for char in token)
                    or not isinstance(store_id, str)
                    or not re.fullmatch(r"(?:store_)?[A-Za-z0-9]{1,63}", store_id)):
                raise BootstrapError("INVALID_STORAGE_ENV")
            kwargs, default_factory = {"token": token, "store_id": store_id}, VercelBlobCasStore
        factory = default_factory if store_factory is None else store_factory
        result = None
        try:
            with factory(**kwargs) as store:
                result = bootstrap(store, cases, baseline, resume_partial=args.resume_partial)
        except BootstrapError:
            raise
        except Exception:
            raise BootstrapError("REMOTE_STATE_UNCERTAIN",
                                 created=result["createdDocuments"] if result else 0,
                                 attempted=result["attemptedWrites"] if result else 0) from None
        print(json.dumps(result))
        return 0
    except BootstrapError as exc:
        print(json.dumps({"status": "refused", "code": exc.code,
                          "createdDocuments": exc.created, "attemptedWrites": exc.attempted}))
        return 1
    except Exception:
        print(json.dumps({"status": "refused", "code": "BOOTSTRAP_FAILED"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
