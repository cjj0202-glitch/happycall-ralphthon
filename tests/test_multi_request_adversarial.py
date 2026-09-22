"""Independent synthetic boundaries for the multi-request provenance contract.

Run: .venv/Scripts/python.exe -B -m unittest discover -s tests -p test_multi_request_adversarial.py -v
Only normalize_analysis is exercised: no client, server, fixture oracle, stored
model response, budget, key, or ledger is used to derive these expected values.
Authored against planning/multi-request-provenance.md at c20d411.
Initial pre-implementation baseline (c20d411 source bytes confirmed before/after run):
20 methods, 26 schema errors across 18 methods, 0 assertion failures; 14 passing
subtests. New-list requests are rejected because requestQuote is still required.
The two entirely passing methods check malformed/mixed schemas. This is an
expected red baseline, not a claim that request semantics have been exercised.
"""
import copy
import unittest
from unittest.mock import patch

from jsonschema import ValidationError

from server.errors import DemoError
from server.live import normalize_analysis
from test_analysis_repair import DEPARTMENTS, case_and_model, claim


INFO = "배송 시각을 알려 주세요."
LABEL = "상품 라벨을 확인해 주세요."
ORDER = "주문 내역을 알려 주세요."
RETURN = "반송 안내 요청입니다."


def segment(speaker, text):
    return {"speaker": speaker, "text": text}


class MultiRequestAdversarialTests(unittest.TestCase):
    def setUp(self):
        for name in ("OpenAI", "demo_client", "require_demo_api_key"):
            guard = patch("server.live." + name,
                          side_effect=AssertionError("API/key access forbidden in offline test"))
            guard.start()
            self.addCleanup(guard.stop)

    def inputs(self, rows, quotes):
        case, model = case_and_model()
        transcript = [segment("B", "가상물결점입니다.")] + copy.deepcopy(rows)
        case["text"] = "\n".join(row["text"] for row in transcript)
        model["orderedClaim"] = claim()
        model["receivedClaim"] = claim()
        model["fields"] = {"subject": "배송 문의의 후속 확인", "request": "MODEL_NOT_SOURCE"}
        model["draftContext"] = {"subjectQuote": rows[0]["text"] if rows else None,
                                 "requestQuotes": quotes}
        return case, model, transcript

    def project(self, case, model, transcript):
        before = copy.deepcopy((case, model, transcript))
        try:
            return normalize_analysis(model, transcript, case, DEPARTMENTS)
        finally:
            self.assertEqual((case, model, transcript), before,
                             "compatibility/projection must not mutate raw input or transcript")

    def assert_requests(self, result, quotes):
        self.assertEqual(result["fields"]["request"], "\n".join(quotes) if quotes else None)
        draft = result["replyDraft"]
        # Existing c20d411 draft presentation collapses whitespace and trims the
        # final full stop. The public source field above must still match exactly.
        displayed = [" ".join(quote.rstrip(".!?").split()) for quote in quotes]
        for quote in displayed:
            self.assertIn(quote, draft)
        if len(quotes) > 1:
            offsets = [draft.index(quote) for quote in displayed]
            self.assertEqual(offsets, sorted(offsets))

    def test_three_separated_requests_survive_in_transcript_order(self):
        correction = "별빛컵은 두 개가 아니라 두 박스예요. 단위를 제대로 적어 주세요."
        handling = "잘못 온 별빛컵의 처리 방법을 알려 주세요."
        ordered = "주문한 청록비누의 처리도 확인해 주세요."
        rows = [segment("B", correction), segment("A", "확인하겠습니다."),
                segment("B", handling), segment("A", "담당자에게 물어보겠습니다."),
                segment("B", ordered)]
        result = self.project(*self.inputs(rows, [ordered, correction, handling]))
        self.assert_requests(result, [correction, handling, ordered])

    def test_adjacent_correction_keeps_its_context_with_one_boundary_space(self):
        first = "별빛컵은 두 개가 아니라 두 박스예요."
        second = "단위를 제대로 적어 주세요."
        quote = first + " " + second
        args = self.inputs([segment("B", "  " + first + "  "),
                            segment("B", " " + second + " ")], [quote])
        self.assert_requests(self.project(*args), [quote])

    def test_other_or_unknown_speaker_and_empty_utterance_are_join_boundaries(self):
        first, second = "별빛컵은 두 박스예요.", "단위를 제대로 적어 주세요."
        joined = first + " " + second
        boundaries = [segment("A", "네."), segment("B", ""), segment("B", "   "),
                      segment("", "원문 경계"), segment("   ", "원문 경계"),
                      segment(None, "원문 경계")]
        for boundary in boundaries:
            with self.subTest(boundary=boundary):
                rows = [segment("B", first), boundary, segment("B", second)]
                result = self.project(*self.inputs(rows, [joined]))
                self.assert_requests(result, [])
                self.assertTrue(result["questions"])

    def test_joining_does_not_normalize_internal_source_whitespace(self):
        rows = [segment("B", "배송  시각을 알려"), segment("B", "주세요.")]
        exact = "배송  시각을 알려 주세요."
        self.assert_requests(self.project(*self.inputs(rows, [exact])), [exact])
        self.assert_requests(self.project(*self.inputs(rows, [INFO])), [])

    def test_same_block_offsets_and_exact_duplicates_determine_output_order(self):
        rows = [segment("B", INFO + " " + LABEL)]
        self.assert_requests(self.project(*self.inputs(rows, [LABEL, INFO, LABEL, INFO])),
                             [INFO, LABEL])

    def test_invalid_noncontiguous_quote_does_not_discard_valid_request(self):
        rows = [segment("B", INFO), segment("A", "네."), segment("B", LABEL)]
        valid_only = self.project(*self.inputs(rows, [INFO]))
        result = self.project(*self.inputs(rows, [INFO, INFO + " " + LABEL]))
        self.assert_requests(result, [INFO])
        self.assertGreater(len(result["questions"]), len(valid_only["questions"]))
        self.assertNotIn(LABEL.rstrip("."), result["replyDraft"])

    def test_own_cancellation_after_speaker_change_removes_only_its_request(self):
        rows = [segment("B", INFO), segment("A", "확인하겠습니다."),
                segment("B", RETURN), segment("A", "네."),
                segment("B", "반송 요청은 취소합니다.")]
        self.assert_requests(self.project(*self.inputs(rows, [RETURN, INFO])), [INFO])

    def test_other_speakers_cancellation_does_not_withdraw_callers_request(self):
        rows = [segment("B", INFO), segment("A", "배송 시각 요청은 취소합니다.")]
        self.assert_requests(self.project(*self.inputs(rows, [INFO])), [INFO])

    def test_pronoun_after_later_request_cancels_only_latest_request(self):
        rows = [segment("B", INFO), segment("A", "네."), segment("B", RETURN),
                segment("A", "확인하겠습니다."), segment("B", "그 요청은 취소합니다.")]
        self.assert_requests(self.project(*self.inputs(rows, [INFO, RETURN])), [INFO])

    def test_reported_example_and_negated_cancellations_are_not_actual_withdrawals(self):
        tails = [
            '상담원이 "배송 시각 요청은 취소합니다."라고 말했습니다.',
            '예시로 "배송 시각 요청은 취소합니다."라고 적었습니다.',
            '"배송 시각 요청은 취소합니다."라는 뜻은 아닙니다.',
        ]
        for tail in tails:
            with self.subTest(tail=tail):
                rows = [segment("B", INFO), segment("A", "네."), segment("B", tail)]
                self.assert_requests(self.project(*self.inputs(rows, [INFO])), [INFO])
        # New regression found in the first implementation: an opening quote in
        # the NEXT sentence must not turn a real cancellation into reported speech.
        independent_examples = [
            '배송 시각 요청은 취소합니다. "반송해 주세요"라는 문장은 예시입니다.',
            '배송 시각 요청은 취소합니다. "반송해 주세요"라고 요청한 적 없습니다.',
            '"배송 시각" 요청은 취소합니다. "반송해 주세요"라는 문장은 예시입니다.',
        ]
        for tail in independent_examples:
            with self.subTest(actual_cancellation_then_independent_example=tail):
                rows = [segment("B", INFO), segment("B", tail)]
                self.assert_requests(self.project(*self.inputs(rows, [INFO])), [])

    def test_ambiguous_repeated_quote_does_not_use_only_first_occurrence(self):
        rows = [segment("B", INFO),
                segment("A", '"배송 시각을 알려 주세요."라고 전달받았습니다.')]
        self.assert_requests(self.project(*self.inputs(rows, [INFO])), [])

    def test_legacy_single_null_missing_context_and_empty_list_are_read_only(self):
        contexts = [({"subjectQuote": INFO, "requestQuote": INFO}, [INFO]),
                    ({"subjectQuote": INFO, "requestQuote": None}, []),
                    ({"subjectQuote": INFO, "requestQuotes": []}, []),
                    (None, [])]
        for context, expected in contexts:
            with self.subTest(context=context):
                case, model, transcript = self.inputs([segment("B", INFO)], [])
                if context is None:
                    del model["draftContext"]  # Only absence enables this compatibility path.
                else:
                    model["draftContext"] = context
                self.assert_requests(self.project(case, model, transcript), expected)

    def test_mixed_keys_are_rejected_by_presence_even_when_empty(self):
        for old, new in ((None, []), (INFO, []), (None, [INFO])):
            with self.subTest(old=old, new=new):
                case, model, transcript = self.inputs([segment("B", INFO)], new)
                model["draftContext"]["requestQuote"] = old
                with self.assertRaises((ValidationError, DemoError)):
                    self.project(case, model, transcript)

    def test_wrong_types_missing_keys_and_explicit_null_context_are_rejected(self):
        contexts = [None, {}, {"subjectQuote": INFO},
                    {"subjectQuote": INFO, "requestQuotes": None},
                    {"subjectQuote": INFO, "requestQuotes": INFO},
                    {"subjectQuote": INFO, "requestQuotes": [None]},
                    {"subjectQuote": INFO, "requestQuotes": [1]},
                    {"subjectQuote": INFO, "requestQuote": []}]
        for context in contexts:
            with self.subTest(context=context):
                case, model, transcript = self.inputs([segment("B", INFO)], [])
                model["draftContext"] = context
                with self.assertRaises((ValidationError, DemoError)):
                    self.project(case, model, transcript)

    def test_eight_quotes_are_allowed_but_nine_duplicates_are_rejected_before_dedup(self):
        quotes = [f"대상{index}의 배송 시각을 알려 주세요." for index in range(1, 9)]
        rows = [segment("B", quote) for quote in quotes]
        self.assert_requests(self.project(*self.inputs(rows, list(reversed(quotes)))), quotes)
        case, model, transcript = self.inputs([segment("B", INFO)], [INFO] * 9)
        with self.assertRaises((ValidationError, DemoError)):
            self.project(case, model, transcript)

    def test_draft_subject_join_does_not_expand_claim_evidence_contract(self):
        quote = "별빛컵 두 박스를 받았습니다."
        rows = [segment("B", "별빛컵 두"), segment("B", "박스를 받았습니다."),
                segment("B", LABEL)]
        case, model, transcript = self.inputs(rows, [LABEL])
        model["draftContext"]["subjectQuote"] = quote
        model["receivedClaim"] = claim("별빛컵", 2, "BOX", quote)
        result = self.project(case, model, transcript)
        self.assertIn(quote.rstrip("."), result["replyDraft"])
        self.assertIsNone(result["fields"]["quantity"])
        self.assertIsNone(result["fields"]["unit"])

    def product_relation_inputs(self, title):
        ordered = "청록비누 4개를 주문했습니다."
        received = "별빛컵 2박스를 받았습니다."
        rows = [segment("B", ordered), segment("B", received), segment("B", LABEL)]
        case, model, transcript = self.inputs(rows, [LABEL])
        model["orderedClaim"] = claim("청록비누", 4, "EA", ordered)
        model["receivedClaim"] = claim("별빛컵", 2, "BOX", received)
        model["fields"]["subject"] = title
        model["draftContext"]["subjectQuote"] = ordered + " " + received
        return case, model, transcript

    def test_subject_meaning_survives_relation_prefix_without_unconditional_overwrite(self):
        full = "청록비누 주문 / 별빛컵 수령 건의 처리 방법 확인 요청"
        result = self.project(*self.product_relation_inputs(full))
        self.assertEqual(result["fields"]["subject"], full)
        short = "회송 가능 여부를 먼저 확인해 달라는 문의"
        result = self.project(*self.product_relation_inputs(short))
        self.assertIn(short, result["fields"]["subject"])
        self.assertIn("청록비누 주문", result["fields"]["subject"])
        self.assertIn("별빛컵 수령", result["fields"]["subject"])

    def test_explicit_reversed_product_relation_is_withheld_for_review(self):
        reversed_title = "별빛컵 주문 / 청록비누 수령 후 처리 확인 요청"
        result = self.project(*self.product_relation_inputs(reversed_title))
        self.assertIsNone(result["fields"]["subject"])
        self.assertTrue(any("원문" in value or "문의" in value
                            for value in result["questions"]))

    def test_partial_cancellation_composite_is_withheld_but_separate_live_quote_survives(self):
        composites = ["반송 요청은 취소합니다. " + INFO,
                      INFO + " 반송 요청은 취소합니다."]
        for composite in composites:
            with self.subTest(composite=composite):
                rows = [segment("B", composite)]
                result = self.project(*self.inputs(rows, [composite, INFO]))
                self.assert_requests(result, [INFO])
                self.assertNotIn("반송 요청은 취소합니다", result["fields"]["request"])

    def test_adjacent_continuation_can_negate_extracted_request_fragment(self):
        rows = [segment("B", '"배송 시각을 알려 주세요."'),
                segment("B", "라고 요청한 것은 아닙니다.")]
        self.assert_requests(self.project(*self.inputs(rows, [INFO])), [])


if __name__ == "__main__":
    unittest.main()
