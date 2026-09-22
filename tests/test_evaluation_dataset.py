"""Offline corpus/oracle/runner controls, not a measurement of model accuracy."""
from __future__ import annotations

import builtins
import copy
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import evaluate_demo_analysis as evaluation


@pytest.fixture
def dataset():
    return evaluation.load_dataset()


def by_id(dataset, cid):
    return next(row for row in dataset["rows"] if row["id"] == cid)


def authored_analysis(row):
    """Hand-labelled comparison fixture, not extraction and never a live result."""
    return {"summary": "합성 수작업 평가기 대조용 응답", "fields": {
        "storeId": row["expected"]["storeId"]["accepted"][0], "subject": "수작업 의미 검토가 필요한 문의 대상",
        "quantity": row["expected"]["quantity"]["accepted"][0], "unit": row["expected"]["unit"]["accepted"][0],
        "request": "수작업 의미 검토가 필요한 확인 요청"},
        "issues": [{"field": field, "message": "수작업으로 작성한 비교용 진단", "evidence": "비교용 인용"}
                   for field in row["safetyRubric"]["requiredIssueFields"]],
        "questions": ["독립 의미 검토에서 실제 적절성을 확인할 질문입니다."],
        "department": {"id": row["expected"]["departmentId"]["accepted"][0], "name": "대조용", "reason": "대조용"},
        "facts": [], "unknowns": [], "replyDraft": "담당자 확인이 필요합니다."}


def successful(row):
    return {"caseId": row["id"], "status": "success", "result": {"analysis": authored_analysis(row)}, "events": []}


def review_document(records):
    return {"datasetSha256": evaluation.FROZEN_DATASET_SHA256, "reviews": [
        {"caseId": cid, "resultSha256": evaluation.canonical_hash(record), "reviewerKind": "independent-ai",
         "reviewer": "offline-oracle-control-not-real-review", "fields": {
             "subject": {"verdict": "pass", "rationale": "평가기 대조군: 의미 통과를 사전 가정한 합성 판정"},
             "request": {"verdict": "pass", "rationale": "평가기 대조군: 의미 통과를 사전 가정한 합성 판정"}},
         "safety": {"verdict": "pass", "rationale": "평가기 대조군용 판정"}}
        for cid, record in records.items()]}


def test_frozen_dataset_has_exact_cohorts_and_all_required_rubrics(dataset):
    assert evaluation.validate_dataset(dataset) == []
    assert len(dataset["rows"]) == 32
    fixed = [row for row in dataset["rows"] if row["cohort"] == "fixed"]
    assert len(fixed) == 20
    assert sum(row["type"] == "missing" for row in fixed) == 10
    assert sum(row["type"] == "wrong" for row in fixed) == 10
    assert len({row["id"] for row in dataset["rows"]}) == 32
    assert len({row["text"] for row in dataset["rows"]}) == 32
    for row in dataset["rows"]:
        assert set(row["expected"]) == set(evaluation.FIELDS)
        assert all(row["expected"][field]["mode"] == "manual-review-required" for field in evaluation.MANUAL_FIELDS)
        assert row["safetyRubric"]["reviewMode"] == "manual-review-required"


@pytest.mark.parametrize("mutation,fragment", [
    (lambda d: d["rows"].pop(), "exactly fixed20"),
    (lambda d: d["rows"][0].update(id=d["rows"][1]["id"]), "duplicate id"),
    (lambda d: d["rows"][0].update(text=d["rows"][1]["text"]), "duplicate"),
    (lambda d: d["rows"][0].update(type="wrong"), "exactly fixed20"),
    (lambda d: d["rows"][0]["expected"].pop("unit"), "six explicit"),
    (lambda d: d["rows"][0]["expected"]["quantity"].update(accepted=[True]), "invalid accepted"),
    (lambda d: d["rows"][0]["expected"]["subject"].update(mode="one-of", accepted=["literal phrase"]), "semantic rubric"),
    (lambda d: d["rows"][0]["expected"]["request"].update(mustPreserve=[]), "semantic rubric"),
    (lambda d: d["rows"][0]["safetyRubric"].update(mustNotAssert=[]), "safety semantic rubric"),
    (lambda d: d.update(mode="audio-stt"), "text-only"),
    (lambda d: d["rows"][-2].update(tags=["ordinary"]), "boundary coverage"),
])
def test_validator_rejects_bad_structure_and_detects_frozen_oracle_changes(dataset, mutation, fragment):
    mutation(dataset)
    errors = evaluation.validate_dataset(dataset)
    assert any(fragment in error for error in errors)
    assert any("hash mismatch" in error for error in errors)


def test_recomputing_embedded_hash_cannot_hide_relabelled_oracle(dataset):
    by_id(dataset, "EDGE-05")["expected"]["quantity"]["accepted"] = [18]
    dataset["frozenSha256"] = evaluation.dataset_hash(dataset)
    assert dataset["frozenSha256"] != evaluation.FROZEN_DATASET_SHA256
    assert any("hash mismatch" in error for error in evaluation.validate_dataset(dataset))


def test_pre_run_subject_hint_fix_preserves_oracles_and_wrong_intake_controls(dataset):
    history = dataset["candidateHistory"][0]
    assert history["actualModelCalls"] == 0
    assert history["sha256"] == "431c6a4083235001b97524ea29ccfdf711adc6b6f84388788975cd75294a67cc"
    assert evaluation.canonical_hash({row["id"]: row["expected"] for row in dataset["rows"]}) == history["expectedSectionsSha256"]
    assert all(row["context"]["intake"]["subject"] != row["expected"]["subject"]["mustPreserve"][0] for row in dataset["rows"])
    wrong_quantity = by_id(dataset, "EDGE-09")["context"]["intake"]
    assert wrong_quantity["subject"] == "새벽잼" and wrong_quantity["quantity"] == 2
    assert "3" not in wrong_quantity["subject"]
    wrong_unit = by_id(dataset, "EDGE-05")["context"]["intake"]
    assert wrong_unit["subject"] == "별숲휴지" and wrong_unit["unit"] == "EA"


def test_live_case_is_a_text_allowlist_without_expected_rubric_or_stt_answer(dataset):
    row = by_id(dataset, "EDGE-05")
    row["replayAnalysis"] = {"secretOracleMarker": "must-not-pass"}
    row["sourceText"] = "must-not-pass"
    row["transcript"] = [{"text": "must-not-pass"}]
    case = evaluation.build_case(row)
    assert case["channel"] == "text"
    assert case["text"] == row["text"]
    assert set(case) == {"id", "channel", "synthetic", "type", "text", "store", "intake", "evidence"}
    assert "must-not-pass" not in json.dumps(case)
    assert "expected" not in case and "sourceText" not in case and "transcript" not in case
    case["store"]["name"] = "changed outside"
    assert row["context"]["store"]["name"] != "changed outside"


@pytest.mark.parametrize("args", [[], ["--validate"], ["--cohort", "fixed"], ["--case-id", "EDGE-05"],
    ["--budget-path", "C:/never-read-budget.json", "--measured-head", "a" * 40]])
def test_default_plan_calls_no_live_runtime_or_key_imports_and_writes_nothing(args, monkeypatch, tmp_path, capsys):
    forbidden = Mock(side_effect=AssertionError("No live runtime without --run-live"))
    monkeypatch.setattr(evaluation, "_live_runtime", forbidden)
    monkeypatch.setattr(evaluation, "LOCAL_EVALUATION_ROOT", tmp_path / "not-created")
    original_import = builtins.__import__
    blocked = []
    def guarded_import(name, *a, **kw):
        if name in {"server.live", "server.budget", "server.runtime_config", "scripts.demo_openai_env", "openai"}:
            blocked.append(name)
            raise AssertionError("Key/model module imported during plan")
        return original_import(name, *a, **kw)
    monkeypatch.setattr(builtins, "__import__", guarded_import)
    assert evaluation.main(args) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["modelCalls"] == 0 and output["keyReads"] == 0
    assert output["modelAccuracy"] == "not-measured"
    assert output["plannedFixedCells"] == 120
    assert output["automaticFixedCells"] == 80 and output["manualFixedCells"] == 40
    assert blocked == []
    forbidden.assert_not_called()
    assert not (tmp_path / "not-created").exists()


def test_fresh_import_reads_no_files_and_imports_no_live_key_modules():
    source = r'''
import builtins
from pathlib import Path
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name in {"server.live", "server.budget", "server.runtime_config", "scripts.demo_openai_env", "openai"}:
        raise AssertionError("Forbidden live/key import")
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
Path.read_text = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Import performed a file read"))
from scripts import evaluate_demo_analysis
print("IMPORT_OK key_reads=0 api_calls=0")
'''
    result = subprocess.run([sys.executable, "-B", "-c", source], cwd=evaluation.ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "IMPORT_OK key_reads=0 api_calls=0"


def test_explicit_live_flag_still_requires_head_and_existing_budget_before_runtime(monkeypatch, tmp_path, capsys):
    forbidden = Mock(side_effect=AssertionError("Preflight must stop"))
    monkeypatch.setattr(evaluation, "_live_runtime", forbidden)
    monkeypatch.setattr(evaluation, "LOCAL_EVALUATION_ROOT", tmp_path / "runs")
    for args in (["--run-live"], ["--run-live", "--budget-path", str(tmp_path / "absent.json"), "--measured-head", "a" * 40]):
        assert evaluation.main(args) == 2
    forbidden.assert_not_called()
    assert not (tmp_path / "runs").exists()
    assert "evaluation-not-completed" in capsys.readouterr().out


def test_unit_order_null_zero_and_wrong_department_oracles_detect_real_differences(dataset):
    row = by_id(dataset, "EDGE-05")
    record = successful(row)
    score = evaluation.score_case(row, record)
    assert all(score["fields"][field] == "correct" for field in evaluation.AUTO_FIELDS)
    assert score["fields"]["subject"] == "manual-review-required"
    record["result"]["analysis"]["fields"].update(quantity=18, unit="EA")
    record["result"]["analysis"]["fields"]["storeId"] = "SYN-EVAL-WRONG"
    record["result"]["analysis"]["department"]["id"] = "delivery"
    wrong = evaluation.score_case(row, record)
    assert wrong["fields"]["quantity"] == wrong["fields"]["unit"] == wrong["fields"]["departmentId"] == "incorrect"
    assert wrong["fields"]["storeId"] == "incorrect"
    zero_row = by_id(dataset, "EDGE-02")
    zero = successful(zero_row)
    assert evaluation.score_case(zero_row, zero)["fields"]["quantity"] == "correct"
    zero["result"]["analysis"]["fields"]["quantity"] = None
    assert evaluation.score_case(zero_row, zero)["fields"]["quantity"] == "incorrect"
    unknown_row = by_id(dataset, "EDGE-03")
    unknown = successful(unknown_row)
    unknown["result"]["analysis"]["fields"]["quantity"] = 0
    assert evaluation.score_case(unknown_row, unknown)["fields"]["quantity"] == "incorrect"


@pytest.mark.parametrize("record,state", [(None, "not-run"), ({"status": "error"}, "error"),
    ({"status": "success"}, "invalid-output"), ({"status": "success", "result": {"analysis": {"fields": {}}}}, "invalid-output")])
def test_missing_results_cannot_match_nullable_expectations(dataset, record, state):
    scored = evaluation.score_case(by_id(dataset, "EDGE-03"), record)
    assert set(scored["fields"].values()) == {state}


def test_absent_field_boolean_and_nan_are_invalid_outputs_not_correct_nulls(dataset):
    row = by_id(dataset, "EDGE-03")
    for mutation in (lambda a: a["fields"].pop("quantity"), lambda a: a["fields"].update(quantity=True),
                     lambda a: a["fields"].update(quantity=float("nan"))):
        record = successful(row)
        mutation(record["result"]["analysis"])
        assert set(evaluation.score_case(row, record)["fields"].values()) == {"invalid-output"}


def test_same_six_fields_do_not_certify_fabricated_reply_or_department_reason(dataset):
    row = by_id(dataset, "EDGE-11")
    record = successful(row)
    record["result"]["analysis"].update(replyDraft="재배송과 보상이 이미 완료되었습니다.")
    record["result"]["analysis"]["department"]["reason"] = "CCTV로 특정 작업자 귀책을 확인했습니다."
    result = evaluation.score_case(row, record)
    assert all(result["fields"][field] == "correct" for field in evaluation.AUTO_FIELDS)
    assert result["safety"] == "manual-review-required"
    assert result["fields"]["request"] == "manual-review-required"


def test_required_question_and_issue_evidence_missing_are_separate_safety_failures(dataset):
    row = by_id(dataset, "EDGE-07")
    record = successful(row)
    record["result"]["analysis"]["questions"] = []
    record["result"]["analysis"]["issues"] = []
    score = evaluation.score_case(row, record)
    assert score["safety"] == "fail"
    assert set(score["structuralSafetyFailures"]) == {"required-question-absent", "required-issue-evidence-absent:storeId"}


def test_global_denominators_keep_partial_errors_and_manual_cells(dataset):
    fixed = [row for row in dataset["rows"] if row["cohort"] == "fixed"]
    records = {row["id"]: successful(row) for row in fixed}
    report = evaluation.summarize(dataset, records)
    group = report["cohorts"]["fixed"]
    assert group["plannedCells"] == 120
    assert group["counts"]["correct"] == 80 and group["counts"]["manual-review-required"] == 40
    assert group["accuracy"] is None and group["targetStatus"] == "not-determined"
    assert report["cohorts"]["boundary"]["plannedCells"] == 72
    assert report["cohorts"]["boundary"]["counts"]["not-run"] == 72
    records[fixed[0]["id"]] = {"status": "error"}
    del records[fixed[1]["id"]]
    report = evaluation.summarize(dataset, records)
    assert report["cohorts"]["fixed"]["counts"]["error"] == 6
    assert report["cohorts"]["fixed"]["counts"]["not-run"] == 6
    assert sum(report["cohorts"]["fixed"]["counts"].values()) == 120


def test_manual_review_requires_matching_output_hash_identity_and_rationale(dataset):
    row = by_id(dataset, "FIX-M01")
    records = {row["id"]: successful(row)}
    reviews = review_document(records)
    validated = evaluation.validate_reviews(reviews, records)
    assert evaluation.score_case(row, records[row["id"]], validated[row["id"]])["fields"]["request"] == "correct"
    for mutation in (lambda d: d["reviews"][0].update(resultSha256="bad"),
                     lambda d: d["reviews"][0].update(reviewer=""),
                     lambda d: d["reviews"][0]["fields"]["request"].update(rationale=""),
                     lambda d: d["reviews"].append(copy.deepcopy(d["reviews"][0]))):
        altered = copy.deepcopy(reviews)
        mutation(altered)
        with pytest.raises(ValueError):
            evaluation.validate_reviews(altered, records)


@pytest.mark.parametrize("wrong_count,target,correct", [(12, "met", 108), (13, "not-met", 107)])
def test_90_percent_boundary_requires_all_120_cells_with_separate_safety(dataset, wrong_count, target, correct):
    fixed = [row for row in dataset["rows"] if row["cohort"] == "fixed"]
    records = {row["id"]: successful(row) for row in fixed}
    for row in fixed[:wrong_count]:
        records[row["id"]]["result"]["analysis"]["fields"]["quantity"] = 999
    document = review_document(records)
    document["reviews"][0]["safety"] = {"verdict": "fail", "rationale": "수작업 반례: 허위 완료 문구"}
    reviews = evaluation.validate_reviews(document, records)
    report = evaluation.summarize(dataset, records, reviews)
    assert report["cohorts"]["fixed"]["counts"]["correct"] == correct
    assert report["cohorts"]["fixed"]["targetStatus"] == target
    assert report["cohorts"]["fixed"]["safetyCounts"]["fail"] == 1
    assert report["cohorts"]["boundary"]["accuracy"] is None


def test_recorded_failed_reservation_survives_without_any_api_dispatch(tmp_path, dataset):
    from server.budget import Budget
    from server.errors import DemoError
    from server.live import LiveAnalyzer
    ledger = tmp_path / "budget.json"
    ledger.write_text('{"entries": []}', encoding="utf-8")
    recorder = evaluation.Recorder(tmp_path)
    recorder.case_id = "offline-large-input"
    budget = evaluation.RecordingBudget(Budget(path=ledger), recorder)
    client = Mock()
    analyzer = LiveAnalyzer(budget=budget, client_factory=lambda: evaluation.tracked_client(client, recorder))
    case = evaluation.build_case(by_id(dataset, "EDGE-03"))
    case["evidence"] = [{"note": "x" * 21000}]
    with pytest.raises(DemoError) as caught:
        analyzer.analyze(case, evaluation.DEPARTMENTS)
    assert caught.value.code == "ANALYSIS_INPUT_LIMIT"
    events = recorder.events
    assert sum(event["kind"] == "reserved" for event in events) == 1
    assert sum(event["kind"] == "api-dispatch" for event in events) == 0
    assert events[-1]["kind"] == "finished" and events[-1]["success"] is False
    assert events[0]["requestId"] == events[-1]["requestId"]
    assert json.loads(ledger.read_text(encoding="utf-8"))["entries"][0]["state"] == "failed-cost-uncertain"
    assert budget.status()["reservedUsd"] == .15
    client.chat.completions.create.assert_not_called()


def test_trace_counts_failed_api_attempt_separately_and_never_records_exception_body(tmp_path):
    recorder = evaluation.Recorder(tmp_path)
    recorder.case_id = "offline-error"
    client = Mock()
    client.chat.completions.create.side_effect = TimeoutError("synthetic-credential-must-not-be-recorded")
    wrapped = evaluation.tracked_client(client, recorder)
    with pytest.raises(TimeoutError):
        wrapped.chat.completions.create(model="offline-model")
    assert [event["kind"] for event in recorder.events] == ["api-dispatch", "api-error"]
    assert "synthetic-credential" not in (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    with pytest.raises(RuntimeError):
        wrapped.audio.transcriptions.create()
    client.audio.transcriptions.create.assert_not_called()


def test_trace_preserves_model_content_and_refusal_metadata_without_request_headers(tmp_path):
    recorder = evaluation.Recorder(tmp_path)
    recorder.case_id = "offline-response"
    response = SimpleNamespace(id="offline-response-id", choices=[SimpleNamespace(finish_reason="stop",
        message=SimpleNamespace(content='{"synthetic":"output"}', refusal=None))])
    client = Mock()
    client.chat.completions.create.return_value = response
    assert evaluation.tracked_client(client, recorder).chat.completions.create(model="offline-model") is response
    assert [event["kind"] for event in recorder.events] == ["api-dispatch", "api-success"]
    assert recorder.raw_model_outputs == [{"caseId": "offline-response", "content": '{"synthetic":"output"}',
                                           "refusal": None, "finishReason": "stop", "responseId": "offline-response-id"}]


def test_existing_ledger_guard_rejects_absence_corruption_or_cloud_ledger(tmp_path):
    path = tmp_path / "budget.json"
    for value in (None, {}, {"entries": [{"requestId": "x", "reservedCents": -1, "state": "reserved"}]},
                  {"entries": [], "initialReservedCents": 100}):
        if value is not None:
            path.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises(ValueError):
            evaluation._validate_local_ledger(path)
    path.write_text('{"entries": []}', encoding="utf-8")
    evaluation._validate_local_ledger(path)


def test_injected_offline_run_records_inputs_outputs_failure_costs_and_redacted_summary(dataset, tmp_path, monkeypatch):
    from server.budget import Budget
    from server.errors import DemoError
    ledger = tmp_path / "real-test-budget.json"
    ledger.write_text('{"entries": []}', encoding="utf-8")
    monkeypatch.setattr(evaluation, "LOCAL_EVALUATION_ROOT", tmp_path / "runs")
    rows = [by_id(dataset, "FIX-M01"), by_id(dataset, "EDGE-05")]
    def offline_runtime(path, recorder):
        budget = evaluation.RecordingBudget(Budget(path=path), recorder)
        def analyze(case, departments):
            rid = budget.reserve(15, "analysis-text")
            recorder.event("api-dispatch", endpoint="offline-fake")
            if case["id"] == "EDGE-05":
                recorder.event("api-error", error={"code": "OFFLINE_FAILURE", "type": "DemoError"})
                budget.finish(rid, False)
                raise DemoError("LIVE_API_FAILED", "synthetic-sensitive-exception-body", 502)
            recorder.event("api-success", endpoint="offline-fake")
            budget.finish(rid, True)
            return {"analysis": authored_analysis(rows[0]), "requestId": rid, "mode": "demo-live"}
        return SimpleNamespace(analyze=analyze), budget
    monkeypatch.setattr(evaluation, "_live_runtime", offline_runtime)
    directory = evaluation.execute_live(dataset, rows, ledger, "a" * 40)
    report, manifest = evaluation.summarize_run(directory)
    assert manifest["measuredHead"] == "a" * 40 and manifest["headVerifiedByRunner"] is False
    assert len(manifest["codeSha256Before"]) == 8
    assert "server/transcript_provenance.py" in manifest["codeSha256Before"]
    assert "server/claim_grounding.py" in manifest["codeSha256Before"]
    assert "server/request_grounding.py" in manifest["codeSha256Before"]
    assert manifest["codeChangedDuringRun"] is False
    assert manifest["status"] == "complete-with-errors"
    assert report["reservationCount"] == 2 and report["reservedCents"] == 30
    assert report["apiDispatchAttempts"] == 2 and report["apiSuccesses"] == 1
    assert report["cohorts"]["fixed"]["plannedCells"] == 120
    assert report["cohorts"]["boundary"]["counts"]["error"] == 6
    assert report["cohorts"]["fixed"]["targetStatus"] == "not-determined"
    envelope = json.loads((directory / "EDGE-05.json").read_text(encoding="utf-8"))
    assert envelope["record"]["input"]["text"] == rows[1]["text"]
    assert envelope["record"]["expected"] == rows[1]["expected"]
    assert envelope["record"]["error"] == {"code": "LIVE_API_FAILED", "type": "DemoError"}
    assert any(event["kind"] == "reserved" for event in envelope["record"]["events"])
    assert "synthetic-sensitive" not in (directory / "EDGE-05.json").read_text(encoding="utf-8")
    report_text = json.dumps(report, ensure_ascii=False)
    assert all(row["text"] not in report_text for row in rows)
    assert "replyDraft" not in report_text and "input" not in report
    assert json.loads(ledger.read_text(encoding="utf-8"))["entries"][1]["state"] == "failed-cost-uncertain"
    assert sum(entry["reservedCents"] for entry in json.loads(ledger.read_text(encoding="utf-8"))["entries"]) == 30
    envelope["record"]["result"] = {"analysis": authored_analysis(rows[1])}
    (directory / "EDGE-05.json").write_text(json.dumps(envelope), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        evaluation.summarize_run(directory)


def test_invalid_live_dataset_stops_before_runtime_or_artifacts(dataset, tmp_path, monkeypatch):
    monkeypatch.setattr(evaluation, "LOCAL_EVALUATION_ROOT", tmp_path / "runs")
    forbidden = Mock(side_effect=AssertionError("oracle mutation must not reach live"))
    monkeypatch.setattr(evaluation, "_live_runtime", forbidden)
    dataset["rows"][0]["expected"]["quantity"]["accepted"] = [999]
    with pytest.raises(ValueError, match="Frozen dataset"):
        evaluation.execute_live(dataset, dataset["rows"], tmp_path / "absent.json", "a" * 40)
    assert not (tmp_path / "runs").exists()
    forbidden.assert_not_called()


@pytest.mark.parametrize("code", ["BUDGET_LIMIT", "API_KEY_MISSING", "EVALUATION_BUDGET_LEDGER_MISSING"])
def test_budget_key_or_missing_ledger_stops_remaining_inputs_as_not_run(dataset, tmp_path, monkeypatch, code):
    from server.errors import DemoError
    ledger = tmp_path / "budget.json"
    ledger.write_text('{"entries": []}', encoding="utf-8")
    monkeypatch.setattr(evaluation, "LOCAL_EVALUATION_ROOT", tmp_path / "runs")
    analyzer = Mock()
    analyzer.analyze.side_effect = DemoError(code, "static test error", 503)
    budget = Mock()
    budget.status.return_value = {"reservedUsd": 0, "limitUsd": 30}
    monkeypatch.setattr(evaluation, "_live_runtime", Mock(return_value=(analyzer, budget)))
    directory = evaluation.execute_live(dataset, dataset["rows"][:2], ledger, "a" * 40)
    report, manifest = evaluation.summarize_run(directory)
    analyzer.analyze.assert_called_once()
    assert manifest["stoppedBecause"] == code
    assert report["cohorts"]["fixed"]["counts"]["error"] == 6
    assert report["cohorts"]["fixed"]["counts"]["not-run"] == 114
    assert report["apiDispatchAttempts"] == 0


def test_provider_auth_failure_stops_without_retrying_next_input(dataset, tmp_path, monkeypatch):
    ledger = tmp_path / "budget.json"
    ledger.write_text('{"entries": []}', encoding="utf-8")
    monkeypatch.setattr(evaluation, "LOCAL_EVALUATION_ROOT", tmp_path / "runs")
    calls = []
    def runtime(path, recorder):
        def analyze(case, departments):
            calls.append(case["id"])
            recorder.event("api-dispatch", endpoint="offline-fake")
            recorder.event("api-error", error={"type": "AuthenticationError", "code": "EVALUATION_ERROR"})
            raise RuntimeError("synthetic-private-provider-error")
        budget = Mock()
        budget.status.return_value = {"reservedUsd": 0}
        return SimpleNamespace(analyze=analyze), budget
    monkeypatch.setattr(evaluation, "_live_runtime", runtime)
    directory = evaluation.execute_live(dataset, dataset["rows"][:2], ledger, "a" * 40)
    report, manifest = evaluation.summarize_run(directory)
    assert calls == [dataset["rows"][0]["id"]]
    assert manifest["stoppedBecause"] == "PROVIDER_ACCESS_OR_LIMIT"
    assert report["apiDispatchAttempts"] == 1 and report["apiSuccesses"] == 0
