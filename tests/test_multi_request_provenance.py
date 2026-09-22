"""Independent synthetic inputs for transcript quote projection, without API calls."""
import copy
import unittest
from unittest.mock import patch

from server.live import normalize_analysis
from tests.test_analysis_repair import case_and_model, claim, DEPARTMENTS


class MultiRequestProvenanceTests(unittest.TestCase):
    def project(self, segments, quotes, subject=None):
        case, model = case_and_model()
        model['receivedClaim'] = claim()
        model['draftContext'] = {'subjectQuote': subject, 'requestQuotes': quotes}
        before = copy.deepcopy((segments, model, case))
        result = normalize_analysis(model, segments, case, DEPARTMENTS)
        self.assertEqual((segments, model, case), before)
        return result

    def test_adjacent_correction_retains_context_and_separate_requests(self):
        correction = '봉투 한 개가 아니라 한 상자예요. 단위를 바로 적어 주세요.'
        disposition = '다르게 온 물건은 어떻게 하나요?'
        ordered = '주문한 상품 처리도 확인해 주세요.'
        segments = [
            {'speaker': 'B', 'text': ' 봉투 한 개가 아니라 한 상자예요. '},
            {'speaker': 'B', 'text': ' 단위를 바로 적어 주세요. '},
            {'speaker': 'A', 'text': '말씀하신 단위를 확인하겠습니다.'},
            {'speaker': 'B', 'text': disposition},
            {'speaker': 'A', 'text': '센터에 문의하겠습니다.'},
            {'speaker': 'B', 'text': ordered},
        ]
        result = self.project(segments, [ordered, correction, disposition, correction], correction)
        self.assertEqual(result['fields']['request'], '\n'.join([correction, disposition, ordered]))
        for quote in (correction, disposition, ordered):
            self.assertIn(quote.rstrip('.'), result['replyDraft'])
        self.assertEqual((result['fields']['quantity'], result['fields']['unit']), (None, None))

    def test_cross_speaker_splice_rejected_but_valid_request_kept(self):
        first, second = '배송 시각을 알려 주세요.', '상품 라벨을 확인해 주세요.'
        result = self.project([
            {'speaker': 'B', 'text': first}, {'speaker': 'A', 'text': '네.'},
            {'speaker': 'B', 'text': second},
        ], [first + ' ' + second, second])
        self.assertEqual(result['fields']['request'], second)
        self.assertTrue(any('요청' in q and '원문' in q for q in result['questions']))

    def test_offset_order_inside_one_block(self):
        first, second = '출고 시각을 알려 주세요.', '상품 라벨을 확인해 주세요.'
        result = self.project([{'speaker': 'B', 'text': first + ' ' + second}], [second, first])
        self.assertEqual(result['fields']['request'], first + '\n' + second)

    def test_internal_spaces_are_not_rewritten(self):
        original = '차량  위치를 알려 주세요.'
        result = self.project([{'speaker': 'B', 'text': original}], [original.replace('  ', ' ')])
        self.assertIsNone(result['fields']['request'])

    def test_empty_segments_and_unknown_speakers_remain_boundaries(self):
        first, second = '상자가 왔어요.', '단위를 확인해 주세요.'
        variants = [
            [{'speaker': 'B', 'text': first}, {'speaker': 'B', 'text': ' '}, {'speaker': 'B', 'text': second}],
            [{'speaker': '', 'text': first}, {'speaker': '', 'text': second}],
            [{'speaker': ' ', 'text': first}, {'speaker': ' ', 'text': second}],
            [{'text': first}, {'text': second}],
        ]
        for segments in variants:
            with self.subTest(segments=segments):
                self.assertIsNone(self.project(segments, [first + ' ' + second])['fields']['request'])

    def test_preserve_subject_condition_and_confirmation_purpose(self):
        case, model = case_and_model()
        order = '달모래잼 7개를 주문했습니다.'
        model['orderedClaim'] = claim('달모래잼', 7, 'EA', order)
        title = '오늘 마감 전 규격 차이와 주문 상품 처리 가능 여부 확인 요청'
        model['fields']['subject'] = title
        result = normalize_analysis(model, [{'speaker': 'B', 'text': order + '\n' + case['text']}], case, DEPARTMENTS)
        self.assertIn(title, result['fields']['subject'])
        self.assertIn('달모래잼 주문 / 구름바다칫솔 수령', result['fields']['subject'])

    def test_membership_null_and_source_order_mutations_are_detected(self):
        controls = [
            ('server.live.current_request_quote', lambda quote, blocks: None,
             'test_adjacent_correction_retains_context_and_separate_requests'),
            ('server.live.quote_position', lambda quote, blocks: None,
             'test_adjacent_correction_retains_context_and_separate_requests'),
            ('server.live.quote_position', lambda quote, blocks: (0, 0),
             'test_offset_order_inside_one_block'),
            ('server.live.speaker_blocks', lambda rows: rows,
             'test_adjacent_correction_retains_context_and_separate_requests'),
        ]
        for target, mutant, method in controls:
            with self.subTest(target=target), patch(target, mutant):
                result = unittest.TestResult()
                MultiRequestProvenanceTests(method).run(result)
                self.assertFalse(result.wasSuccessful(), 'behavioral control must detect mutant')


if __name__ == '__main__':
    unittest.main()
