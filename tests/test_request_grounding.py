"""Request provenance counterexamples; no model calls or frozen-input imports."""
import copy
import inspect
import unittest
from unittest.mock import patch

from server.live import normalize_analysis
from tests.test_analysis_repair import case_and_model, claim, DEPARTMENTS


class RequestGroundingTests(unittest.TestCase):
    def project(self, text, quote, proposal='상품 단위 확인과 당일 재배송 요청', received=None):
        case, model = case_and_model()
        case['text'] = '가상물결점입니다. ' + text
        model['fields']['request'] = proposal
        model['draftContext']['requestQuote'] = quote
        model['receivedClaim'] = received or claim()
        before = copy.deepcopy((case, model))
        with patch('server.live.OpenAI', side_effect=AssertionError('NO_API')), patch('server.live.require_demo_api_key', side_effect=AssertionError('NO_KEY')):
            result = normalize_analysis(model, [{'speaker': '경영주', 'text': case['text']}], case, DEPARTMENTS)
        self.assertEqual(before, (case, model))
        return result

    def test_real_customer_request_cannot_borrow_ai_followup_questions(self):
        quote = '출고 부서에서 주문 내역과 라벨을 확인해 주세요.'
        result = self.project(quote, quote)
        self.assertEqual(result['fields']['request'], quote)
        self.assertNotIn('단위', result['fields']['request'])
        self.assertNotIn('재배송', result['fields']['request'])

    def test_future_action_and_negative_instruction_are_current_requests(self):
        for quote in ('내일 오전까지 도착 시각을 알려 주세요.', '아직 재배송 완료로 확정하지 말아 주세요.', '접수 상태와 반송 가능한 절차를 문의합니다.', '라벨이 다르면 먼저 연락해 주시고 확인하고 싶습니다.'):
            with self.subTest(quote=quote):
                self.assertEqual(self.project(quote, quote)['fields']['request'], quote)

    def test_statement_denial_future_plan_and_completion_are_not_requests(self):
        for quote in ('출고 부서가 라벨을 확인했습니다.', '라벨 확인을 요청한 것이 아닙니다.', '내일 라벨 확인을 요청할 예정입니다.', '센터에서 재배송 처리를 완료했습니다.'):
            with self.subTest(quote=quote):
                result = self.project(quote, quote)
                self.assertIsNone(result['fields']['request'])
                self.assertTrue(any('요청' in q and '원문' in q for q in result['questions']))
                self.assertIn('참고 발화 원문', result['replyDraft'])
                self.assertNotIn('요청 원문의', result['replyDraft'])

    def test_valid_looking_fragment_cannot_be_cut_from_negated_or_example_context(self):
        quote = '라벨을 확인해 주세요'
        for text in (f'“{quote}”라고 부탁한 적은 없습니다.', f'예문은 “{quote}”입니다.', f'내일 “{quote}”라고 요청할 예정입니다.', f'“{quote}”라고 말한 것은 아닙니다.', f'지난달 “{quote}”라고 요청했습니다.'):
            with self.subTest(text=text):
                self.assertIsNone(self.project(text, quote)['fields']['request'])

    def test_missing_or_invented_quote_does_not_fall_back_to_proposal(self):
        for quote in (None, '', '없는 원문인데 라벨을 확인해 주세요.'):
            with self.subTest(quote=quote):
                self.assertIsNone(self.project('라벨이 다릅니다.', quote)['fields']['request'])

    def test_quoted_nominal_denial_past_report_and_hypothesis_are_not_requests(self):
        quote = '라벨을 확인해 주세요.'
        for text in (
            f'“{quote}”라는 문장은 요청이 아닙니다.',
            f'“{quote}”라는 말은 부탁이 아니에요.',
            f'“{quote}”라는 요청을 지난주에 전달받았습니다.',
            f'어제 “{quote}”라는 말을 들었습니다.',
            f'“{quote}”라고 말했다고 전해 들었습니다.',
            f'만약 고객이 “{quote}”라고 한다면 기록만 남깁니다.',
        ):
            with self.subTest(text=text):
                result = self.project(text, quote)
                self.assertIsNone(result['fields']['request'])
                self.assertIn('참고 발화 원문', result['replyDraft'])

    def test_actual_requests_keep_negative_and_conditional_content(self):
        for quote in (
            '박스 말고 개로 확인해 주세요.',
            '수령 확인이 아니라 라벨 확인을 부탁드립니다.',
            '어제 연락했지만 오늘 다시 라벨을 확인해 주세요.',
            '라벨이 다르다면 주문서를 확인해 주세요.',
        ):
            with self.subTest(quote=quote):
                self.assertEqual(self.project(quote, quote)['fields']['request'], quote)
        quote = '박스 말고 개로 확인해 주세요.'
        self.assertEqual(self.project(f'제 요청은 “{quote}”입니다.', quote)['fields']['request'], quote)

    def test_profanity_softening_preserves_complaint_and_urgency(self):
        quote = '씨발, 벌써 세 번째입니다. 오늘 안에 라벨을 확인하고 전화해 주세요.'
        result = self.project(quote, quote)
        self.assertNotIn('씨발', result['fields']['request'])
        for meaning in ('세 번째', '오늘 안에', '라벨을 확인하고 전화해 주세요', '불만'):
            self.assertIn(meaning, result['fields']['request'])

    def test_independent_future_intention_and_truncated_request(self):
        text = '다음 주에 라벨을 확인해 주세요라고 부탁하려고 합니다.'
        with self.subTest(kind='future_intention'):
            self.assertIsNone(self.project(text, '라벨을 확인해 주세요')['fields']['request'])
        for quote in ('주세요.', '해 주세요.'):
            with self.subTest(quote=quote):
                self.assertIsNone(self.project('라벨을 확인해 주세요.', quote)['fields']['request'])

    def test_nominal_requests_keep_explicit_action_and_target(self):
        for quote in ('반송 방법 안내 요청입니다.', '차량 도착 시각 확인 부탁입니다.'):
            with self.subTest(quote=quote):
                self.assertEqual(self.project(quote, quote)['fields']['request'], quote)

    def test_explicit_following_withdrawal_removes_only_its_request(self):
        quote = '라벨을 확인해 주세요.'
        for tail in ('그 요청은 취소합니다.', '라벨 확인 요청은 철회합니다.'):
            with self.subTest(tail=tail):
                self.assertIsNone(self.project(quote + ' ' + tail, quote)['fields']['request'])
        for tail in (
            '반송 요청은 취소합니다.',
            '반송 방법을 안내해 주세요. 그 요청은 취소합니다.',
            '그 요청은 취소하지 말아 주세요.',
        ):
            with self.subTest(tail=tail):
                self.assertEqual(self.project(quote + ' ' + tail, quote)['fields']['request'], quote)

    def test_following_withdrawal_obeys_speaker_boundary(self):
        from server.request_grounding import current_request_quote
        quote = '라벨을 확인해 주세요.'
        for speaker, expected in (('경영주', None), ('상담원', quote)):
            with self.subTest(speaker=speaker):
                transcript = [{'speaker': '경영주', 'text': quote},
                              {'speaker': speaker, 'text': '그 요청은 취소합니다.'}]
                self.assertEqual(current_request_quote(quote, transcript), expected)

    def test_named_cancellation_scope_keeps_distinct_requests(self):
        # Expectations fixed before changing cancellation matching. Shared
        # business words alone must not erase a separately stated inquiry.
        pairs = (
            ('배송 시각을 알려 주세요.', '배송 상품 반송 요청은 취소합니다.'),
            ('출고 시각을 알려 주세요.', '출고 상품 교환 요청은 취소합니다.'),
            ('상품 라벨을 확인해 주세요.', '상품 반송 요청은 취소합니다.'),
            ('주문 내역을 확인해 주세요.', '주문 상품 재배송 요청은 취소합니다.'),
        )
        for quote, tail in pairs:
            with self.subTest(quote=quote, tail=tail):
                self.assertEqual(self.project(quote + ' ' + tail, quote)['fields']['request'], quote)

    def test_named_cancellation_keeps_full_partial_and_related_target_controls(self):
        # A shorter name and a synonymous description must still withdraw an
        # actual request; requiring all words to match would reactivate these.
        pairs = (
            ('배송 시각을 알려 주세요.', '배송 시각 안내 요청은 취소합니다.'),
            ('배송 도착 예정 시각을 알려 주세요.', '시각 안내 요청은 철회합니다.'),
            ('배송 시각을 알려 주세요.', '배송 요청은 취소합니다.'),
            ('출고 상품 라벨을 확인해 주세요.', '라벨 확인 요청은 철회합니다.'),
            ('주문 상품 반송 방법을 안내해 주세요.', '주문 상품 반송 절차 문의는 취소합니다.'),
            ('배송 상품을 반송해 주세요.', '배송 상품 반송 요청은 취소합니다.'),
            ('배송 상품 반송 시각을 알려 주세요.', '배송 상품 반송 요청은 취소합니다.'),
            ('주문 내역과 라벨을 확인해 주세요.', '주문 내역 확인 요청은 취소합니다.'),
            ('배송 차량의 도착 시각을 알려 주세요.', '배송 차량 도착 시간 문의는 취소합니다.'),
            ('상품 반송 절차를 안내해 주세요.', '상품 반송 방법 문의는 취소합니다.'),
            ('상품 라벨을 다시 보내 주세요.', '상품 재배송 요청은 취소합니다.'),
            ('배송 시각을 알려 주세요. 배송 상품 반송해 주세요.', '배송 상품 반송 요청은 취소합니다.'),
            ('배송 시각을 알려 주세요.', '배송 상품 반송이 아니라 배송 요청은 취소합니다.'),
            ('배송 시각을 알려 주세요.', '배송 상품 반송 없이 배송 요청은 취소합니다.'),
        )
        for quote, tail in pairs:
            with self.subTest(quote=quote, tail=tail):
                self.assertIsNone(self.project(quote + ' ' + tail, quote)['fields']['request'])

    def test_nominal_information_request_survives_separate_operation_withdrawal(self):
        pairs = (
            ('배송 시각 안내 요청입니다.', '배송 상품 반송 요청은 취소합니다.'),
            ('출고 시간 확인 요청입니다.', '출고 상품 교환 요청은 취소합니다.'),
            ('배송 일정 확인 요청입니다.', '배송 상품 반품 요청은 취소합니다.'),
            ('상품 라벨 확인 요청입니다.', '상품 회송 요청은 취소합니다.'),
            ('주문 내역 확인 요청입니다.', '주문 상품 재배송 요청은 취소합니다.'),
        )
        for quote, tail in pairs:
            with self.subTest(quote=quote):
                self.assertEqual(self.project(quote + ' ' + tail, quote)['fields']['request'], quote)

    def test_two_nominal_requests_preserve_only_request_before_withdrawn_latest(self):
        first = '배송 시각 안내 요청입니다.'
        second = '배송 상품 반송 방법 안내 요청입니다.'
        for earlier, latest in ((first, second), (second, first)):
            text = earlier + ' ' + latest + ' 그 요청은 취소합니다.'
            with self.subTest(earlier=earlier, latest=latest):
                self.assertEqual(self.project(text, earlier)['fields']['request'], earlier)
                self.assertIsNone(self.project(text, latest)['fields']['request'])

    def test_information_with_particle_in_compound_cancellation_is_not_separate(self):
        # Same information target cannot disappear behind a Korean particle.
        for quote, information, operation in (
            ('배송 시각을 알려 주세요.', '배송 시각', '반송'),
            ('배송 시각 안내 요청입니다.', '배송 시각', '반송'),
            ('상품 라벨 확인 요청입니다.', '상품 라벨', '교환'),
            ('주문 내역 확인 요청입니다.', '주문 내역', '재배송'),
        ):
            for particle in ('과', '도', '을 포함한'):
                tail = f'{information}{particle} {operation} 요청은 취소합니다.'
                with self.subTest(quote=quote, tail=tail):
                    self.assertIsNone(self.project(quote + ' ' + tail, quote)['fields']['request'])
            latest = f'{information}과 {operation} 방법 안내 요청입니다.'
            with self.subTest(quote=quote, latest=latest):
                self.assertIsNone(self.project(quote + ' ' + latest + ' 그 요청은 취소합니다.', quote)['fields']['request'])

    def test_nominal_inquiry_keeps_related_and_noncurrent_guards(self):
        pairs = (
            ('배송 시각 안내 요청입니다.', '배송 시각 안내 요청은 취소합니다.'),
            ('배송 시각 안내 요청입니다.', '배송 요청은 취소합니다.'),
            ('배송 상품 반송 시간 안내 요청입니다.', '배송 상품 반송 요청은 취소합니다.'),
            ('배송 상품을 돌려보낼 시간 안내 요청입니다.', '배송 상품 반송 요청은 취소합니다.'),
            ('배송 시각 안내 요청입니다. 배송 상품 반송 요청입니다.', '배송 상품 반송 요청은 취소합니다.'),
        )
        for quote, tail in pairs:
            with self.subTest(quote=quote, tail=tail):
                self.assertIsNone(self.project(quote + ' ' + tail, quote)['fields']['request'])
        quote = '배송 시각 안내 요청입니다.'
        for text in (f'예문은 "{quote}"입니다.', f'"{quote}"라고 요청한 적은 없습니다.',
                     f'"{quote}"라고 내일 요청할 예정입니다.'):
            with self.subTest(text=text):
                self.assertIsNone(self.project(text, quote)['fields']['request'])

    def test_reported_nominal_operation_does_not_replace_nearest_current_request(self):
        quote = '배송 시각 안내 요청입니다.'
        past = '배송 상품 반송 방법 안내 요청입니다.'
        for context in (f'"{past}"라고 지난주에 요청했습니다.',
                        f'"{past}"라고 내일 요청할 예정입니다.',
                        f'"{past}"라고 요청한 적은 없습니다.',
                        f'예문은 "{past}"입니다.'):
            with self.subTest(context=context):
                text = quote + ' ' + context + ' 그 요청은 취소합니다.'
                self.assertIsNone(self.project(text, quote)['fields']['request'])

    def test_nominal_cancellation_boundary_mutations_are_detected(self):
        from server import request_grounding
        source = inspect.getsource(request_grounding._separate_inquiry)
        mutations = (
            ('not any(term in other for term in information)',
             'not information.intersection(_target_terms(other))',
             'test_information_with_particle_in_compound_cancellation_is_not_separate'),
            ('re.fullmatch(nominal_operation, other.strip())',
             're.search(nominal_operation, other.strip())',
             'test_nominal_operation_must_fill_clause'),
        )
        for before, after, test_name in mutations:
            with self.subTest(mutation=before):
                self.assertEqual(source.count(before), 1)
                namespace = dict(request_grounding.__dict__)
                exec(compile(source.replace(before, after), '<nominal-boundary-mutant>', 'exec'), namespace)
                fresh = RequestGroundingTests(test_name)
                with patch('server.request_grounding._separate_inquiry', namespace['_separate_inquiry']), self.assertRaises(AssertionError):
                    getattr(fresh, test_name)()

    def test_nominal_operation_must_fill_clause(self):
        from server.request_grounding import _separate_inquiry
        self.assertTrue(_separate_inquiry('배송 시각 안내 요청입니다.', '배송 상품 반송 방법 안내 요청입니다.'))
        self.assertFalse(_separate_inquiry('배송 시각 안내 요청입니다.', '점포 업무 외 배송 상품 반송 방법 안내 요청입니다.'))

    def test_shared_business_word_does_not_move_pronoun_to_earlier_request(self):
        first = '배송 시각을 알려 주세요.'
        second = '배송 상품 반송 방법을 안내해 주세요.'
        text = first + ' ' + second + ' 그 요청은 취소합니다.'
        self.assertEqual(self.project(text, first)['fields']['request'], first)
        self.assertIsNone(self.project(text, second)['fields']['request'])
        repeated = first + ' 배송 시각을 다시 알려 주세요. 그 요청은 취소합니다.'
        self.assertIsNone(self.project(repeated, first)['fields']['request'])
        reverse = second + ' ' + first + ' 그 요청은 취소합니다.'
        self.assertEqual(self.project(reverse, second)['fields']['request'], second)
        self.assertIsNone(self.project(reverse, first)['fields']['request'])

    def test_verbal_operation_modifiers_do_not_escape_named_cancellation(self):
        # A time/schedule noun does not make an action's dependent inquiry a
        # separate request. Fix these expectations before narrowing the guard.
        pairs = (
            ('배송 상품을 돌려보낼 시간을 알려 주세요.', '배송 상품 반송 요청은 취소합니다.'),
            ('배송 상품을 돌려 보낼 시간을 알려 주세요.', '배송 상품 반송 요청은 취소합니다.'),
            ('배송 상품을 다시 보낼 시간을 알려 주세요.', '배송 상품 재배송 요청은 취소합니다.'),
            ('배송 상품을 다시 보내 주실 시간을 알려 주세요.', '배송 상품 재배송 요청은 취소합니다.'),
            ('배송 상품을 바꿀 일정을 알려 주세요.', '배송 상품 교환 요청은 취소합니다.'),
            ('배송 상품을 바꿔 받을 일정을 알려 주세요.', '배송 상품 교환 요청은 취소합니다.'),
            ('배송 상품을 돌려보내는 시간을 알려 주세요.', '배송 상품 반송 요청은 취소합니다.'),
            ('배송 상품을 다시 보내려고 하는 시간을 알려 주세요.', '배송 상품 재배송 요청은 취소합니다.'),
            ('배송 상품을 돌려보내 주시고 처리 시간을 알려 주세요.', '배송 상품 반송 요청은 취소합니다.'),
            ('배송 상품을 다시 보내 주시고 배송 시간을 알려 주세요.', '배송 상품 재배송 요청은 취소합니다.'),
        )
        for quote, tail in pairs:
            with self.subTest(quote=quote, tail=tail):
                self.assertIsNone(self.project(quote + ' ' + tail, quote)['fields']['request'])

    def test_named_cancellation_scope_stops_at_adjacent_speaker_boundary(self):
        from server.request_grounding import current_request_quote
        quote = '배송 시각을 알려 주세요.'
        for speaker, expected in (('경영주', None), ('상담원', quote)):
            with self.subTest(speaker=speaker):
                transcript = [{'speaker': '경영주', 'text': quote},
                              {'speaker': speaker, 'text': '배송 시각 안내 요청은 취소합니다.'}]
                self.assertEqual(current_request_quote(quote, transcript), expected)
        for speaker in ('경영주', '상담원'):
            with self.subTest(distinct_speaker=speaker):
                transcript = [{'speaker': '경영주', 'text': quote},
                              {'speaker': speaker, 'text': '배송 상품 반송 요청은 취소합니다.'}]
                self.assertEqual(current_request_quote(quote, transcript), quote)

    def test_cancellation_scope_mutations_are_detected(self):
        checks = (
            (False, 'test_named_cancellation_scope_keeps_distinct_requests'),
            (False, 'test_shared_business_word_does_not_move_pronoun_to_earlier_request'),
            (True, 'test_named_cancellation_keeps_full_partial_and_related_target_controls'),
        )
        for forced_separation, test_name in checks:
            with self.subTest(forced_separation=forced_separation, test=test_name):
                fresh = RequestGroundingTests(test_name)
                with patch('server.request_grounding._separate_inquiry', return_value=forced_separation), self.assertRaises(AssertionError):
                    getattr(fresh, test_name)()

    def test_missing_receipt_unit_stays_question_not_customer_request(self):
        receipt = '반짝봉투 5개를 받았습니다.'
        quote = '주문과 라벨을 확인해 주세요.'
        result = self.project(receipt + ' ' + quote, quote, received=claim('반짝봉투', 5, None, receipt))
        self.assertIsNone(result['fields']['unit'])
        self.assertEqual(result['fields']['quantity'], 5)
        self.assertEqual(result['fields']['request'], quote)
        self.assertTrue(any('단위' in q for q in result['questions']))

    def test_unknown_target_receipt_amount_gets_unit_followup_without_inference(self):
        text = '지난달 바람차 2박스를 받았습니다. 오늘 받은 바람차 수량은 아직 모릅니다. 출고 내역을 확인해 주세요.'
        result = self.project(text, '출고 내역을 확인해 주세요.')
        self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (None, None))
        self.assertTrue(any('수량' in q and '단위' in q for q in result['questions']))
        self.assertEqual(result['fields']['request'], '출고 내역을 확인해 주세요.')

    def test_whole_delivery_inquiry_does_not_require_irrelevant_receipt_amount(self):
        quote = '차량 도착 시각을 알려 주세요.'
        for context in ('배송 차량이 오지 않았습니다. ', '배송 차량이 오지 않았고 무엇을 몇 개 받았는지는 아직 모릅니다. ', '받은 물건의 수량 이야기는 하지 않았습니다. '):
            with self.subTest(context=context):
                result = self.project(context + quote, quote)
                self.assertFalse(any('수량' in q or '단위' in q for q in result['questions']))

    def test_mutation_controls_reject_bypass_blanket_null_and_missing_followup(self):
        checks = [
            ('server.live.current_request_quote', lambda q, tr: q, 'test_statement_denial_future_plan_and_completion_are_not_requests'),
            ('server.live.current_request_quote', lambda q, tr: None, 'test_real_customer_request_cannot_borrow_ai_followup_questions'),
            ('server.live.receipt_followup', lambda *args: None, 'test_unknown_target_receipt_amount_gets_unit_followup_without_inference'),
        ]
        for target, mutant, test_name in checks:
            with self.subTest(target=target):
                fresh = RequestGroundingTests(test_name)
                with patch(target, mutant), self.assertRaises(AssertionError):
                    getattr(fresh, test_name)()


if __name__ == '__main__':
    unittest.main()
