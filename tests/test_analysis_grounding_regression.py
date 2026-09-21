"""Fresh synthetic counterexamples. No frozen evaluation inputs or network calls."""
import copy
import unittest
from unittest.mock import patch

from server.live import normalize_analysis
from tests.test_analysis_repair import case_and_model, claim, DEPARTMENTS


class GroundingRegressionTests(unittest.TestCase):
    def project(self, text, ordered=None, received=None, unknowns=None):
        case, model = case_and_model()
        case['text'] = '가상물결점입니다.\n' + text
        model['orderedClaim'] = ordered or claim()
        model['receivedClaim'] = received or claim()
        model['unknowns'] = unknowns or []
        before = copy.deepcopy((case, model))
        result = normalize_analysis(model, [{'speaker': '경영주', 'text': case['text']}], case, DEPARTMENTS)
        self.assertEqual((case, model), before)
        return result

    def test_positive_order_survives_unrelated_receipt_uncertainty(self):
        quote = '은빛차를 13개 주문했는데'
        result = self.project(quote + ' 아직 받은 수량을 세지 못했습니다.', ordered=claim('은빛차', 13, 'EA', quote))
        self.assertIn('주문 진술: 은빛차 13 EA', result['summary'])
        self.assertFalse(any('긍정 주문 진술' in x for x in result['questions']))

    def test_receipt_values_cannot_fill_unquantified_order(self):
        order = '은빛차 레몬맛을 주문했는데'
        receipt = '받은 것은 은빛차 복숭아맛 9개입니다.'
        result = self.project(order + ' ' + receipt, ordered=claim('은빛차 레몬맛', 9, 'EA', order), received=claim('은빛차 복숭아맛', 9, 'EA', receipt))
        self.assertIn('주문 진술: 은빛차 레몬맛 수량 미확인 단위 미확인', result['summary'])
        self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (9, 'EA'))

    def test_explicit_receipt_and_unknown_quantity_do_not_contradict(self):
        quote = '제가 주문하지 않은 바람봉투 7개를 받았습니다.'
        result = self.project(quote, received=claim('바람봉투', 7, 'EA', quote), unknowns=['바람봉투의 수령 수량 및 단위', '다른 점포의 물건인지 여부'])
        self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (7, 'EA'))
        self.assertNotIn('AI 검토 제안·미확인: 바람봉투의 수령 수량 및 단위', result['unknowns'])
        self.assertTrue(any('다른 점포' in x for x in result['unknowns']))
        self.assertTrue(any('진술' in x and '별도 확인' in x for x in result['unknowns']))

    def test_past_unit_cannot_fill_current_unit(self):
        current = '오늘 받은 은빛차 수량은 아직 세지 못했습니다.'
        result = self.project('지난달 은빛차 9박스를 받았지만 ' + current, received=claim('은빛차', None, 'BOX', current))
        self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (None, None))

    def test_same_number_in_other_role_does_not_support_unit(self):
        quote = '은빛차 7박스를 주문했지만 실제로 받은 은빛차는 7개입니다.'
        for quantity, unit in ((7, 'EA'), (7, 'BOX')):
            with self.subTest(unit=unit):
                result = self.project(quote, received=claim('은빛차', quantity, unit, quote))
                self.assertEqual(result['fields']['quantity'], 7)
                self.assertEqual(result['fields']['unit'], 'EA' if unit == 'EA' else None)

    def test_current_values_survive_past_contrast(self):
        quote = '지난달 은빛차 9박스를 받았지만 오늘 은빛차는 9개 받았습니다.'
        result = self.project(quote, received=claim('은빛차', 9, 'EA', quote))
        self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (9, 'EA'))
        wrong = self.project(quote, received=claim('은빛차', 9, 'BOX', quote))
        self.assertIsNone(wrong['fields']['unit'])

    def test_zero_and_partial_values_are_independent(self):
        for quote, quantity, unit in [('은빛차를 0개 받았습니다.', 0, 'EA'), ('은빛차는 박스로 받았지만 몇 박스인지는 모릅니다.', None, 'BOX'), ('은빛차는 7개 받았습니다.', 7, None), ('은빛차 수령 수량은 7입니다. 단위는 모릅니다.', 7, None), ('은빛차7개를 받았습니다.', 7, 'EA'), ('은빛차는 개 단위로 수령했지만 수량은 모릅니다.', None, 'EA')]:
            with self.subTest(quote=quote):
                result = self.project(quote, received=claim('은빛차', quantity, unit, quote))
                self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (quantity, unit))

    def test_other_unknowns_and_partial_unknown_are_preserved(self):
        quote = '은빛차는 박스로 받았지만 몇 박스인지는 모릅니다.'
        unknowns = ['은빛차 수령 수량', '푸른차 수령 수량 및 단위', '지난달 은빛차 수령 수량 및 단위', '은빛차 수령 수량 및 라벨 귀속']
        result = self.project(quote, received=claim('은빛차', None, 'BOX', quote), unknowns=unknowns)
        self.assertTrue(all('AI 검토 제안·미확인: ' + text in result['unknowns'] for text in unknowns))

    def test_full_quote_role_crossing_does_not_borrow_receipt_for_order(self):
        quote = '은빛차를 주문했는데 받은 은빛차는 7개입니다.'
        result = self.project(quote, ordered=claim('은빛차', 7, 'EA', quote), received=claim('은빛차', 7, 'EA', quote))
        self.assertIn('주문 진술: 은빛차 수량 미확인 단위 미확인', result['summary'])
        self.assertEqual(result['fields']['quantity'], 7)

    def test_pack_count_does_not_support_receipt_amount(self):
        quote = '은빛차 두 박스를 받았고 박스당 7개입니다.'
        result = self.project(quote, received=claim('은빛차', 14, 'EA', quote))
        self.assertIsNone(result['fields']['quantity'])
        self.assertIsNone(result['fields']['unit'])

    def test_neighbouring_product_same_number_different_units(self):
        quote = '은빛차 7박스와 달빛컵 7개를 주문했습니다.'
        valid = self.project(quote, ordered=claim('은빛차', 7, 'BOX', quote))
        self.assertIn('은빛차 7 BOX', valid['summary'])
        wrong = self.project(quote, ordered=claim('은빛차', 7, 'EA', quote))
        self.assertIn('은빛차 7 단위 미확인', wrong['summary'])

    def test_other_number_cannot_supply_quantity(self):
        quote = '은빛차는 7시에 받았습니다. 상품코드는 13입니다.'
        result = self.project(quote, received=claim('은빛차', 13, None, quote))
        self.assertIsNone(result['fields']['quantity'])

    def test_spoken_korean_numbers_are_not_false_omissions(self):
        for amount, quantity in [('열여덟', 18), ('스물세', 23), ('서른둘', 32), ('십팔', 18), ('백이십삼', 123), ('2.5', 2.5)]:
            with self.subTest(amount=amount):
                quote = f'은빛차 {amount}개를 받았습니다.'
                result = self.project(quote, received=claim('은빛차', quantity, 'EA', quote))
                self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (quantity, 'EA'))

    def test_past_only_quote_cannot_fill_explicit_today_inquiry(self):
        past = '지난달 은빛차 7박스를 받았습니다.'
        result = self.project(past + ' 오늘 은빛차는 받은 수량을 모릅니다.', received=claim('은빛차', 7, 'BOX', past))
        self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (None, None))

    def test_historical_inquiry_is_not_erased_by_unrelated_today_mention(self):
        past = '지난달 은빛차 7박스를 받았습니다.'
        result = self.project('오늘 전화드립니다. ' + past, received=claim('은빛차', 7, 'BOX', past))
        self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (7, 'BOX'))

    def test_independent_g1_negated_target_receipt(self):
        quote = '모래차 5개는 받지 않았고 별빛차 5개를 받았습니다.'
        result = self.project(quote, received=claim('모래차', 5, 'EA', quote))
        self.assertIsNone(result['fields']['quantity'])

    def test_independent_g2_future_is_not_current_receipt(self):
        text = '어제 모래차 4박스를 받았지만 내일 모래차 7개를 받을 예정입니다. 오늘 모래차 수령량은 모릅니다.'
        quote = '내일 모래차 7개를 받을 예정입니다.'
        result = self.project(text, received=claim('모래차', 7, 'EA', quote))
        self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (None, None))

    def test_independent_g3_attributive_order_and_receipt(self):
        quote = '주문한 모래차 7박스 중 실제로는 7개 받았습니다.'
        for unit, expected in [('EA', 'EA'), ('BOX', None)]:
            with self.subTest(unit=unit):
                result = self.project(quote, received=claim('모래차', 7, unit, quote))
                self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (7, expected))

    def test_independent_g4_neighbour_product_does_not_fill_target(self):
        quote = '모래차 수령량은 모르겠고 별빛차 3개를 받았습니다.'
        result = self.project(quote, received=claim('모래차', 3, 'EA', quote))
        self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (None, None))

    def test_independent_g5_unknown_scope_preservation(self):
        quote = '모래차 7개를 받았습니다.'
        unknowns = ['내일 모래차 수령 수량 및 단위', '모래차 수령 수량 및 라벨 귀속', '별빛차 수령 수량 및 단위', '모래차 수령 수량 및 단위']
        result = self.project(quote, received=claim('모래차', 7, 'EA', quote), unknowns=unknowns)
        self.assertTrue(all('AI 검토 제안·미확인: ' + text in result['unknowns'] for text in unknowns[:3]))
        self.assertNotIn('AI 검토 제안·미확인: ' + unknowns[3], result['unknowns'])
        self.assertTrue(any('진술은 원문에' in value and '별도 확인' in value for value in result['unknowns']))

    def test_new_forms_keep_actual_and_reject_other_scope(self):
        forms = [
            ('발주한 은빛차 8상자 가운데 실제 수령은 8개입니다.', '은빛차', 8, 'EA', 'BOX'),
            ('은빛차는 6개를 못 받았지만 별빛컵 6박스를 받았습니다.', '별빛컵', 6, 'BOX', 'EA'),
            ('은빛차 수령량은 아직 모르지만 별빛컵은 4개를 받았습니다.', '별빛컵', 4, 'EA', 'BOX'),
            ('은빛차는 내일 6개 받을 계획이며 오늘 별빛컵 6박스를 받았습니다.', '별빛컵', 6, 'BOX', 'EA'),
            ('주문한 은빛차 8박스이고 실제 수령은 8개입니다.', '은빛차', 8, 'EA', 'BOX'),
        ]
        for quote, product, quantity, unit, wrong_unit in forms:
            with self.subTest(quote=quote):
                good = self.project(quote, received=claim(product, quantity, unit, quote))
                self.assertEqual((good['fields']['quantity'], good['fields']['unit']), (quantity, unit))
                bad = self.project(quote, received=claim(product, quantity, wrong_unit, quote))
                self.assertIsNone(bad['fields']['unit'])

    def test_other_named_products_do_not_match_by_substring_or_contrast(self):
        for quote in ('모래차 말고 별빛차 3개를 받았습니다.', '검은모래차 3개를 받았습니다.', '모래차라떼 3개를 받았습니다.'):
            with self.subTest(quote=quote):
                result = self.project(quote, received=claim('모래차', 3, 'EA', quote))
                self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (None, None))

    def test_independent_nominal_polarity_and_future_pairs(self):
        pairs = [
            ('햇살차', 4, 'EA', '햇살차 4개를 받았습니다.', '햇살차 4개를 받은 것이 아닙니다.'),
            ('달샘물', 2, 'BOX', '달샘물 2박스를 수령했습니다.', '달샘물 2박스 수령 예정입니다.'),
        ]
        for product, quantity, unit, positive, negative in pairs:
            with self.subTest(product=product, polarity='positive'):
                result = self.project(positive, received=claim(product, quantity, unit, positive))
                self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (quantity, unit))
            with self.subTest(product=product, polarity='negative'):
                result = self.project(negative, received=claim(product, quantity, unit, negative))
                self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (None, None))

    def test_nominal_receipt_variants_and_completed_plan_positive(self):
        for text in ('은빛차 6개를 받은 건 아니에요.', '은빛차 6개를 수령한 사실이 없습니다.', '은빛차 6개 수령 계획입니다.', '은빛차 6개 수령 예정 수량입니다.'):
            with self.subTest(text=text):
                result = self.project(text, received=claim('은빛차', 6, 'EA', text))
                self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (None, None))
        for text in ('은빛차 6개를 수령한 것이 맞습니다.', '은빛차는 수령 예정대로 6개를 받았습니다.'):
            with self.subTest(text=text):
                result = self.project(text, received=claim('은빛차', 6, 'EA', text))
                self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (6, 'EA'))

    def test_order_assertion_withdrawal_stays_rejected(self):
        for tail in ('수령을 못했다고 적었지만 전체 문장은 사실이 아닙니다.', '수령을 못했습니다라는 문장은 예시입니다.'):
            with self.subTest(tail=tail):
                quote = '은빛차 13개를 주문했는데 ' + tail
                result = self.project(quote, ordered=claim('은빛차', 13, 'EA', quote))
                self.assertTrue(result['summary'].startswith('주문 진술: 미확인;'))

    def test_mutation_controls_detect_bypassed_or_overstrict_guards(self):
        checks = [
            ('server.live.supported_values', lambda c, *args: (c['quantity'], c['unit']), self.test_receipt_values_cannot_fill_unquantified_order),
            ('server.live.supported_values', lambda c, *args: (None, None), self.test_zero_and_partial_values_are_independent),
            ('server.live.order_assertion_scope', lambda text: text, self.test_positive_order_survives_unrelated_receipt_uncertainty),
            ('server.live.reconcile_unknown', lambda value, received: value, self.test_explicit_receipt_and_unknown_quantity_do_not_contradict),
        ]
        for target, mutant, check in checks:
            with self.subTest(target=target, mutant=mutant):
                # Invoke a fresh case so subTest does not absorb the assertion.
                fresh = GroundingRegressionTests(check.__name__)
                with patch(target, mutant), self.assertRaises(AssertionError):
                    getattr(fresh, check.__name__)()


if __name__ == '__main__':
    unittest.main()
