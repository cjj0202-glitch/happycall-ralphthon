"""Offline receipt-label evaluator; no language extraction, network, or demo-store writes.

Expected fields below are manually authored from the supplied utterances. Passing
these tests validates the evaluator, not the LLM's ability to extract those fields.
"""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jsonschema import Draft202012Validator

from server.analysis_schema import ANALYSIS_SCHEMA


BEFORE = Path(__file__).resolve().parents[1] / "reports/e2e/live-analysis-before.json"
MANUAL_RUBRIC = (
    "Check receipt product and latest customer correction against the transcript.",
    "Check issue meaning: distinguish order/receipt and do not subtract mixed units/products.",
    "Check quoted evidence actually supports the correction; nonempty text is insufficient.",
    "Check unknowns, questions and reply do not invent physical receipt or completed actions.",
)


def _schema_errors(analysis):
    return list(Draft202012Validator(ANALYSIS_SCHEMA).iter_errors(analysis))


def _field_matches(name, actual, expected):
    return actual == expected


def evaluate_analysis(analysis, expected_receipt_fields, *, required_issue_fields=(), require_question=False):
    """Compare output to an external human oracle, never infer an oracle from text."""
    if set(expected_receipt_fields) != {"quantity", "unit"}:
        raise ValueError("The human oracle must explicitly supply quantity and unit, including nulls")
    schema_errors = _schema_errors(analysis)
    failures = [{"code": "schema", "path": list(error.absolute_path), "message": error.message}
                for error in schema_errors]
    document = analysis if isinstance(analysis, dict) else {}
    fields = document.get("fields")
    fields = fields if isinstance(fields, dict) else {}
    for name in ("quantity", "unit"):
        actual, expected = fields.get(name), expected_receipt_fields[name]
        if not _field_matches(name, actual, expected):
            failures.append({"code": "receipt_field", "field": name, "expected": expected, "actual": actual})
    issues = document.get("issues")
    issues = issues if isinstance(issues, list) else []
    for name in required_issue_fields:
        if not any(isinstance(issue, dict) and issue.get("field") == name
                   and isinstance(issue.get("evidence"), str) and issue["evidence"].strip()
                   for issue in issues):
            failures.append({"code": "issue_evidence_missing", "field": name})
    questions = document.get("questions")
    if require_question and not (isinstance(questions, list)
                                and any(isinstance(q, str) and q.strip() for q in questions)):
        failures.append({"code": "question_missing"})
    return {"schemaValid": not schema_errors, "automatedChecksPassed": not failures,
            "failures": failures, "manualReviewRequired": list(MANUAL_RUBRIC)}


def authored_response(quantity, unit):
    """Explicit test output, not an LLM response or extraction implementation."""
    return {"summary": "수작업 평가용 응답", "fields": {
        "storeId": None, "subject": "수령 상품 확인", "quantity": quantity, "unit": unit, "request": None},
        "issues": [], "questions": [], "department": {"id": "", "name": "", "reason": ""},
        "facts": [], "unknowns": [], "replyDraft": "담당자 확인이 필요합니다."}


# Each utterance is provenance for human labels, not input parsed by the evaluator.
SEMANTIC_CASES = (
    ("latest_customer_correction", "점주: 2박스, 아니 1박스요. 상담원: 1개군요.", 1, "BOX", 2, "BOX"),
    ("explicit_zero", "비스킷은 실제로 0개 받았습니다.", 0, "EA", None, "EA"),
    ("receipt_unknown", "18개 주문했지만 받았는지 몇 개인지 아직 모릅니다.", None, None, 18, "EA"),
    ("reversed_units", "2박스를 주문했지만 실제로는 낱개 18개를 받았습니다.", 18, "EA", 2, "BOX"),
    ("no_conversion", "휴지 2박스를 받았고 한 박스에는 12개가 들어 있습니다.", 2, "BOX", 24, "EA"),
    ("multiple_targets", "휴지 1박스와 비스킷 6개를 받았는데 무엇이 문제인지 아직 모릅니다.",
     None, None, 7, "EA"),
)


class AnalysisSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = json.loads(BEFORE.read_text(encoding="utf-8-sig"))

    def test_actual_failure_passes_schema_but_fails_receipt_oracle(self):
        self.assertEqual(self.before["requestId"], "edde4b9b-76e2-49b2-913e-0286e8865c76")
        self.assertEqual(self.before["originalCounselorInput"]["quantity"], 1)
        self.assertEqual(self.before["originalCounselorInput"]["unit"], "EA")
        result = evaluate_analysis(self.before["analysis"], self.before["expectedReceiptFields"])
        self.assertTrue(result["schemaValid"])
        self.assertFalse(result["automatedChecksPassed"])
        self.assertEqual({f["field"] for f in result["failures"]}, {"quantity", "unit"})
        self.assertEqual({f["field"]: f["actual"] for f in result["failures"]}, {"quantity": 18, "unit": "EA"})

    def test_prompt_only_retry_still_fails_same_wav_receipt_oracle(self):
        after = json.loads(BEFORE.with_name("live-analysis-after.json").read_text(encoding="utf-8"))
        self.assertEqual(after["requestId"], "fa902a32-9237-414e-bc6a-f5551cf02881")
        self.assertEqual(after["wavSha256"], self.before["wav"]["sha256AtCapture"])
        result = evaluate_analysis(after["analysis"], {"quantity": 1, "unit": "BOX"})
        self.assertTrue(result["schemaValid"])
        self.assertEqual({failure["field"] for failure in result["failures"]}, {"quantity", "unit"})
        self.assertFalse(result["automatedChecksPassed"])

    def test_authored_correction_and_nonempty_issue_evidence(self):
        response = authored_response(1, "BOX")
        response["issues"] = [{"field": "unit", "message": "입력 EA를 수령 BOX로 정정해야 합니다.",
                               "evidence": "아니요. 휴지 1개가 아니라 한 박스예요."}]
        result = evaluate_analysis(response, {"quantity": 1, "unit": "BOX"}, required_issue_fields=("unit",))
        self.assertTrue(result["automatedChecksPassed"])
        self.assertEqual(result["manualReviewRequired"], list(MANUAL_RUBRIC))
        for evidence in ("", "   "):
            with self.subTest(evidence=evidence):
                response["issues"][0]["evidence"] = evidence
                result = evaluate_analysis(response, {"quantity": 1, "unit": "BOX"}, required_issue_fields=("unit",))
                self.assertEqual(result["failures"][0]["code"], "issue_evidence_missing")

    def test_labeled_semantic_cases_accept_expected_and_reject_mutated_output(self):
        for name, utterance, quantity, unit, wrong_quantity, wrong_unit in SEMANTIC_CASES:
            with self.subTest(case=name, utterance=utterance):
                expected = {"quantity": quantity, "unit": unit}
                good = authored_response(quantity, unit)
                self.assertTrue(evaluate_analysis(good, expected)["automatedChecksPassed"])
                bad = authored_response(wrong_quantity, wrong_unit)
                result = evaluate_analysis(bad, expected)
                self.assertTrue(result["schemaValid"])
                self.assertFalse(result["automatedChecksPassed"])
                self.assertTrue(all(f["code"] == "receipt_field" for f in result["failures"]))

    def test_unknown_requires_question_only_when_requested_by_human_rubric(self):
        response = authored_response(None, None)
        expected = {"quantity": None, "unit": None}
        result = evaluate_analysis(response, expected, require_question=True)
        self.assertEqual(result["failures"], [{"code": "question_missing"}])
        response["questions"] = ["어떤 상품의 실제 수령 수량을 확인할까요?"]
        self.assertTrue(evaluate_analysis(response, expected, require_question=True)["automatedChecksPassed"])

    def test_issue_wording_cannot_be_certified_by_structural_checks(self):
        response = copy.deepcopy(self.before["analysis"])
        response["fields"].update(self.before["expectedReceiptFields"])
        # Known wrong issue prose survives: evidence presence must not claim semantic correctness.
        result = evaluate_analysis(response, self.before["expectedReceiptFields"], required_issue_fields=("unit",))
        self.assertTrue(result["automatedChecksPassed"])
        self.assertTrue(result["manualReviewRequired"])

    def test_incomplete_oracle_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_analysis(authored_response(1, "BOX"), {"quantity": 1})

    def _assert_controls(self):
        expected = {"quantity": 1, "unit": "BOX"}
        self.assertTrue(evaluate_analysis(authored_response(1, "BOX"), expected)["automatedChecksPassed"])
        for quantity, unit in ((18, "BOX"), (1, "EA")):
            self.assertFalse(evaluate_analysis(authored_response(quantity, unit), expected)["automatedChecksPassed"])
        for actual, wanted in ((None, 0), (0, None)):
            self.assertFalse(evaluate_analysis(authored_response(actual, "EA"),
                             {"quantity": wanted, "unit": "EA"})["automatedChecksPassed"])
        malformed = authored_response(1, "BOX")
        malformed["unrecognized"] = True
        self.assertFalse(evaluate_analysis(malformed, expected)["automatedChecksPassed"])

    def test_positive_negative_boundary_and_schema_controls(self):
        self._assert_controls()

    def test_controls_detect_evaluator_check_removal_and_zero_null_collapse(self):
        original = _field_matches
        mutations = {
            "omit_quantity_check": lambda n, a, e: True if n == "quantity" else original(n, a, e),
            "omit_unit_check": lambda n, a, e: True if n == "unit" else original(n, a, e),
            "collapse_zero_null": lambda n, a, e: (a or 0) == (e or 0) if n == "quantity" else original(n, a, e),
        }
        for name, replacement in mutations.items():
            with self.subTest(mutation=name), patch(__name__ + "._field_matches", replacement):
                with self.assertRaises(AssertionError):
                    self._assert_controls()
        with self.subTest(mutation="omit_schema_check"), patch(__name__ + "._schema_errors", return_value=[]):
            with self.assertRaises(AssertionError):
                self._assert_controls()


class ClaimProjectionTests(unittest.TestCase):
    """Pure projection and provenance checks; authored claims are not LLM evidence."""

    def setUp(self):
        from server.live import normalize_analysis
        from server.analysis_schema import MODEL_ANALYSIS_SCHEMA
        self.normalize = normalize_analysis
        self.model_schema = MODEL_ANALYSIS_SCHEMA
        self.departments = [{"id": "warehouse", "name": "출고 운영"}]
        self.transcript = [
            {"speaker": "B", "text": "가상새봄점입니다."},
            {"speaker": "B", "text": "비스킷 18개를 주문했습니다."},
            {"speaker": "B", "text": "아니요. 휴지 한 박스가 왔어요."},
        ]
        self.case = {"id": "PROJECTION-ONLY", "store": {"id": "SYN-ST02", "name": "가상 새봄점"},
            "intake": {"storeId": "SYN-ST02", "subject": "휴지 오출고", "quantity": 1, "unit": "EA", "request": "확인"},
            "sourceText": "SOURCE_SCRIPT_TRAP", "replayAnalysis": {"summary": "REPLAY_ANSWER_TRAP"},
            "expected": {"quantity": 999, "unit": "PALLET"},
            "received": {"quantity": 888, "unit": "PALLET"},
            "evidence": [
                {"id": "EV-FACT", "system": "WMS", "label": "출고 스캔", "value": "휴지 1 BOX",
                 "source": "합성 원천 ROW-7", "status": "fact"},
                {"id": "EV-UNKNOWN", "system": "WMS", "label": "귀책", "value": "UNKNOWN_VALUE_TRAP",
                 "source": "미확인", "status": "unknown"},
            ]}
        self.model = {"summary": "MODEL_ALIAS_TRAP", "fields": {"subject": "휴지 오출고", "request": "확인"},
            "draftContext": {"subjectQuote": "휴지 한 박스가 왔어요.", "requestQuotes": []},
            "orderedClaim": {"product": "비스킷", "quantity": 18, "unit": "EA", "evidenceQuote": "비스킷 18개를 주문했습니다."},
            "receivedClaim": {"product": "휴지", "quantity": 1, "unit": "BOX", "evidenceQuote": "휴지 한 박스가 왔어요."},
            "storeClaim": {"name": "가상새봄점", "evidenceQuote": "가상새봄점입니다."},
            "issues": [], "questions": [], "department": {"id": "warehouse", "name": "임의 별칭", "reason": "출고 확인"},
            "unknowns": [], "replyDraft": "확인 예정입니다."}
        Draft202012Validator(self.model_schema).validate(self.model)

    def project(self):
        result = self.normalize(self.model, self.transcript, self.case, self.departments)
        Draft202012Validator(ANALYSIS_SCHEMA).validate(result)
        return result

    def test_projection_uses_received_claim_and_preserves_inputs(self):
        before = copy.deepcopy((self.model, self.transcript, self.case, self.departments))
        result = self.project()
        self.assertEqual((result["fields"]["quantity"], result["fields"]["unit"]), (1, "BOX"))
        self.assertEqual(result["fields"]["storeId"], "SYN-ST02")
        self.assertEqual(result["department"]["name"], "출고 운영")
        self.assertEqual((self.model, self.transcript, self.case, self.departments), before)

    def test_missing_or_forged_quote_cannot_fall_back_to_fixture_values(self):
        for quote in (None, "", " ", "SOURCE_SCRIPT_TRAP", "휴지 두 박스가 왔어요.",
                      "주문했습니다. 아니요. 휴지 한 박스가 왔어요."):
            with self.subTest(quote=quote):
                self.model["receivedClaim"]["evidenceQuote"] = quote
                result = self.project()
                self.assertIsNone(result["fields"]["quantity"])
                self.assertIsNone(result["fields"]["unit"])
                self.assertTrue(any(q.strip() for q in result["questions"]))

    def test_quote_edges_trim_but_internal_text_is_not_rewritten(self):
        self.model["receivedClaim"]["evidenceQuote"] = "  휴지 한 박스가 왔어요.  "
        self.assertEqual(self.project()["fields"]["quantity"], 1)
        self.model["receivedClaim"]["evidenceQuote"] = "휴지 한  박스가 왔어요."
        self.assertIsNone(self.project()["fields"]["quantity"])

    def test_unknown_product_leaves_receipt_unconfirmed(self):
        self.model["receivedClaim"]["product"] = None
        result = self.project()
        self.assertIsNone(result["fields"]["quantity"])
        self.assertIsNone(result["fields"]["unit"])
        self.assertTrue(result["questions"])

    def test_zero_and_partial_unknown_values_are_preserved(self):
        self.transcript.append({"speaker": "B", "text": "휴지는 실제로 0개 받았습니다."})
        claim = self.model["receivedClaim"]
        claim.update(quantity=0, unit="EA", evidenceQuote="휴지는 실제로 0개 받았습니다.")
        self.assertEqual(self.project()["fields"]["quantity"], 0)
        claim.update(quantity=None, unit="BOX", evidenceQuote="휴지 한 박스가 왔어요.")
        result = self.project()
        self.assertIsNone(result["fields"]["quantity"])
        self.assertEqual(result["fields"]["unit"], "BOX")

    def test_store_claim_needs_matching_actual_quote_and_exact_master_name(self):
        variants = (
            ({"name": "가산세범점", "evidenceQuote": "가산세범점입니다."}, "가산세범점입니다."),
            ({"name": "가상새봄점", "evidenceQuote": "가상새봄점입니다."}, "가산세범점입니다."),
            ({"name": "가상새봄점", "evidenceQuote": "휴지 한 박스가 왔어요."}, "가상새봄점입니다."),
        )
        for claim, spoken in variants:
            with self.subTest(claim=claim, spoken=spoken):
                self.model["storeClaim"] = claim
                self.transcript[0]["text"] = spoken
                result = self.project()
                self.assertIsNone(result["fields"]["storeId"])
                self.assertTrue(result["questions"])

    def test_facts_are_rendered_from_fact_rows_only(self):
        result = self.project()
        self.assertEqual(len(result["facts"]), 1)
        rendered = "\n".join(result["facts"])
        for key in ("id", "system", "label", "value", "source"):
            self.assertIn(self.case["evidence"][0][key], rendered)
        for excluded in ("EV-UNKNOWN", "UNKNOWN_VALUE_TRAP", "MODEL_ALIAS_TRAP", "임의 별칭"):
            self.assertNotIn(excluded, rendered)
        self.case["evidence"] = []
        self.assertEqual(self.project()["facts"], [])

    def test_old_model_fields_and_facts_are_rejected_by_internal_schema(self):
        for field, value in (("quantity", 18), ("unit", "EA"), ("storeId", "SYN-ST02")):
            with self.subTest(injected_field=field):
                invalid = copy.deepcopy(self.model)
                invalid["fields"][field] = value
                self.assertTrue(list(Draft202012Validator(self.model_schema).iter_errors(invalid)))
        invalid = copy.deepcopy(self.model)
        invalid["facts"] = ["MODEL_FACT_INJECTION"]
        self.assertTrue(list(Draft202012Validator(self.model_schema).iter_errors(invalid)))

    def test_input_mismatch_issues_are_derived_and_model_diagnoses_removed(self):
        self.model["issues"] = [{"field": field, "message": "MODEL_DIAGNOSIS_" + field, "evidence": "MODEL_QUOTE"}
                                for field in ("quantity", "unit", "storeId", "subject")]
        result = self.project()
        issue_text = json.dumps(result["issues"], ensure_ascii=False)
        for field in ("quantity", "unit", "storeId"):
            self.assertNotIn("MODEL_DIAGNOSIS_" + field, issue_text)
        self.assertIn("MODEL_DIAGNOSIS_subject", issue_text)
        unit_issues = [issue for issue in result["issues"] if issue["field"] == "unit"]
        self.assertTrue(unit_issues)
        self.assertTrue(all(issue["evidence"].strip() for issue in unit_issues))
        self.assertFalse([issue for issue in result["issues"] if issue["field"] == "quantity"])
        self.case["intake"]["unit"] = "BOX"
        self.assertFalse([issue for issue in self.project()["issues"] if issue["field"] in ("quantity", "unit")])

    def test_existing_quote_is_not_proof_of_claim_semantic_correctness(self):
        self.model["receivedClaim"].update(quantity=18, unit="EA")
        # The quote exists, but its meaning does not support this model-authored claim.
        result = evaluate_analysis(self.project(), {"quantity": 1, "unit": "BOX"})
        self.assertFalse(result["automatedChecksPassed"])
        self.assertEqual({f["field"] for f in result["failures"]}, {"quantity", "unit"})

    def test_unclear_or_different_intake_target_is_not_diagnosed_as_quantity_error(self):
        for subject in ("오출고", "비스킷", None):
            with self.subTest(subject=subject):
                self.case["intake"].update(subject=subject, quantity=18)
                result = self.project()
                self.assertFalse([issue for issue in result["issues"] if issue["field"] in ("quantity", "unit")])
                self.assertTrue(any("수령 상품 휴지" in question for question in result["questions"]))

    def test_live_analyzer_wiring_uses_claim_schema_without_fixture_answers(self):
        """Mock transport verifies wiring only, never actual LLM extraction quality."""
        from server.live import LiveAnalyzer
        self.case.update(channel="text", text="\n".join(segment["text"] for segment in self.transcript),
                         expectedReceiptFields={"quantity": 777, "unit": "ORACLE_TRAP"})
        client, budget = Mock(), Mock()
        budget.reserve.return_value = "offline-wiring-only"
        client.chat.completions.create.return_value = Mock(choices=[Mock(
            finish_reason="stop", message=Mock(refusal=None, content=json.dumps(self.model, ensure_ascii=False)))])
        with patch("server.live.OpenAI", side_effect=AssertionError("Real API construction forbidden")):
            result = LiveAnalyzer(budget=budget, client_factory=lambda: client).analyze(self.case, self.departments)
        client.audio.transcriptions.create.assert_not_called()
        client.chat.completions.create.assert_called_once()
        arguments = client.chat.completions.create.call_args.kwargs
        payload = json.loads(arguments["messages"][1]["content"])
        self.assertEqual(set(payload), {"transcript", "syntheticStoreMaster",
                                       "syntheticEvidence", "allowedDepartments"})
        self.assertNotIn("counselorInputToCheck", payload)
        self.assertEqual(payload["transcript"][0]["text"], self.case["text"])
        schema = arguments["response_format"]["json_schema"]["schema"]
        self.assertEqual(schema, self.model_schema)
        self.assertEqual(set(schema["properties"]["fields"]["properties"]), {"subject", "request"})
        self.assertNotIn("facts", schema["properties"])
        for sentinel in ("SOURCE_SCRIPT_TRAP", "REPLAY_ANSWER_TRAP", "PALLET", "ORACLE_TRAP"):
            self.assertNotIn(sentinel, arguments["messages"][1]["content"])
        self.assertEqual(result["analysis"]["fields"]["quantity"], 1)
        self.assertEqual(result["analysis"]["fields"]["unit"], "BOX")
        budget.finish.assert_called_once_with("offline-wiring-only", True)


if __name__ == "__main__":
    unittest.main()
