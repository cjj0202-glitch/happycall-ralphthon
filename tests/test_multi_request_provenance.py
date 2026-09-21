"""Independent PC2 oracle + fresh contract controls; no model/budget calls."""
import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from jsonschema import validate

from server.analysis_schema import ANALYSIS_SCHEMA, MODEL_ANALYSIS_SCHEMA
from server.live import normalize_analysis
from server.request_provenance import resolve_requests, source_occurrences
from tests.test_analysis_repair import DEPARTMENTS, case_and_model


ORACLE = json.loads((Path(__file__).parent / 'evaluation/multi-request-cases.json').read_text(encoding='utf-8'))
CASES = ORACLE['cases']
BY_ID = {case['id']: case for case in CASES}


def run_case(case):
    return resolve_requests(case['draftContext'], case['transcript'], case['speakerRoles'])


def minimal_provenance(active):
    return [{'quote': item['quote'], 'occurrences': [
        {'speaker': occurrence['speaker'], 'spans': [
            {key: span[key] for key in ('segmentId', 'startChar', 'endChar')}
            for span in occurrence['spans']]}
        for occurrence in item['occurrences']]} for item in active]


@pytest.mark.parametrize('case', CASES, ids=lambda case: case['id'])
def test_independent_pc2_contract(case):
    before = copy.deepcopy(case)
    result = run_case(case)
    assert [item['quote'] for item in result['active']] == case['expectedActiveQuotes']
    assert [{key: item[key] for key in ('proposalIndex', 'quote', 'reason')}
            for item in result['rejected']] == case['expectedRejectedDetails']
    assert result['reviewReasons'] == case['expectedReviewReasons']
    assert minimal_provenance(result['active']) == case['expectedProvenance']
    for item in result['active']:
        for occurrence in item['occurrences']:
            for span in occurrence['spans']:
                original = case['transcript'][span['segmentIndex']]
                assert span['startSeconds'] == original['startSeconds']
                assert span['endSeconds'] == original['endSeconds']
    assert case == before


def normalize_case(case):
    source, model = case_and_model()
    model['draftContext'] = {'subjectQuote': None, **copy.deepcopy(case['draftContext'])}
    before = copy.deepcopy((source, model, case['transcript']))
    with patch('server.live.OpenAI', side_effect=AssertionError('NO_API')), \
            patch('server.live.require_demo_api_key', side_effect=AssertionError('NO_KEY')), \
            patch('server.live.Budget', side_effect=AssertionError('NO_LEDGER')):
        result = normalize_analysis(model, case['transcript'], source, DEPARTMENTS)
    assert (source, model, case['transcript']) == before
    validate(result, ANALYSIS_SCHEMA)
    return result


@pytest.mark.parametrize('case', CASES, ids=lambda case: case['id'])
def test_http_projection_preserves_public_contract_and_inputs(case):
    result = normalize_case(case)
    active = case['expectedActiveQuotes']
    expected = None if not active else active[0] if len(active) == 1 else '\n'.join(
        f'{index + 1}. {quote}' for index, quote in enumerate(active))
    assert result['fields']['request'] == expected
    # Request provenance never creates receipt values or promotes a draft to a reply.
    assert result['fields']['quantity'] is None
    assert result['fields']['unit'] is None
    assert result['replyDraft'].startswith('담당자 검토용 초안:')
    for quote in active:
        assert quote.strip(' ,.!\t\r\n') in result['replyDraft']
    assert not any(issue['field'] == 'request' for issue in result['issues'])


@pytest.mark.parametrize('raw', [None, '', '배송 시각을 알려 주세요.', [None], [''], [' '], [3], [True], {}])
def test_malformed_new_collection_is_review_not_legacy_fallback(raw):
    quote = '배송 시각을 알려 주세요.'
    transcript = [{'speaker': '경영주', 'text': quote, 'start': 3.2, 'end': 5.8}]
    result = resolve_requests({'requestQuotes': raw}, transcript)
    assert not result['active']
    assert 'INVALID_QUOTES_TYPE' in result['reviewReasons']


def test_times_and_unicode_offsets_are_not_rewritten():
    transcript = [
        {'speaker': '경영주', 'text': '🧾 한 개가 아니라', 'start': 1.25, 'end': 2.5},
        {'speaker': '경영주', 'text': '한 박스입니다. 단위를 기록해 주세요.', 'start': 3.5, 'end': 8.75},
    ]
    quote = '한 개가 아니라 한 박스입니다. 단위를 기록해 주세요.'
    result = resolve_requests({'requestQuotes': [quote]}, transcript)
    spans = result['active'][0]['occurrences'][0]['spans']
    assert spans[0]['startChar'] == 2  # one Unicode scalar emoji + one space
    assert [(span['startSeconds'], span['endSeconds']) for span in spans] == [(1.25, 2.5), (3.5, 8.75)]
    assert ' '.join(transcript[s['segmentIndex']]['text'][s['startChar']:s['endChar']] for s in spans) == quote


def test_segment_text_cannot_be_corrected_or_middle_omitted():
    transcript = [{'speaker': '경영주', 'text': '한  박스로 받았습니다.'},
                  {'speaker': '경영주', 'text': '중간 확인 사항입니다.'},
                  {'speaker': '경영주', 'text': '단위를 기록해 주세요.'}]
    for quote in ('한 박스로 받았습니다. 중간 확인 사항입니다. 단위를 기록해 주세요.',
                  '한  박스로 받았습니다. 단위를 기록해 주세요.'):
        assert not resolve_requests({'requestQuotes': [quote]}, transcript)['active']


@pytest.mark.parametrize('speaker', ['', '화자', 'unknown', None])
def test_stt_default_label_is_not_evidence_of_same_adjacent_speaker(speaker):
    transcript = [{'speaker': speaker, 'text': '한 박스를 받았습니다.'},
                  {'speaker': speaker, 'text': '단위를 기록해 주세요.'}]
    result = resolve_requests({'requestQuotes': ['한 박스를 받았습니다. 단위를 기록해 주세요.']}, transcript)
    assert not result['active']
    assert result['reviewReasons'] == ['EMPTY_SPEAKER_JOIN', 'SPEAKER_ROLE_UNVERIFIED']


def test_schema_asks_model_for_bounded_array_only():
    properties = MODEL_ANALYSIS_SCHEMA['properties']['draftContext']['properties']
    assert 'requestQuote' not in properties
    assert properties['requestQuotes']['maxItems'] == 8
    assert ANALYSIS_SCHEMA['properties']['fields']['properties']['request']['type'] == ['string', 'null']


def test_mutation_controls_reject_drop_all_accept_all_and_ignore_withdrawal():
    # Execute deliberately broken decision paths against fixed independent cases.
    with patch('server.request_provenance.source_occurrences', return_value=[]):
        assert [item['quote'] for item in run_case(BY_ID['R04'])['active']] != BY_ID['R04']['expectedActiveQuotes']
    case = BY_ID['R08']
    accepted = resolve_requests(case['draftContext'], case['transcript'], case['speakerRoles'],
                                current_check=lambda quote, transcript: quote)
    assert [item['quote'] for item in accepted['active']] != case['expectedActiveQuotes']
    with patch('server.request_provenance._cancellation', return_value=(None, [])):
        assert [item['quote'] for item in run_case(BY_ID['R16'])['active']] != BY_ID['R16']['expectedActiveQuotes']


def test_no_request_context_stays_empty_without_fake_provenance():
    assert resolve_requests({}, [{'speaker': '경영주', 'text': '배송을 받았습니다.'}]) == {
        'active': [], 'rejected': [], 'reviewReasons': []}


def test_same_segment_unpunctuated_following_withdrawal_is_not_skipped():
    quote = '라벨을 확인해 주세요'
    transcript = [{'speaker': '경영주', 'text': quote + ' 그 요청은 취소합니다'}]
    result = resolve_requests({'requestQuotes': [quote]}, transcript)
    assert not result['active']
    assert result['reviewReasons'] == ['WITHDRAWN']


def test_normal_valid_requests_do_not_add_review_warnings():
    case, model = case_and_model()
    quote = model['draftContext'].pop('requestQuote')
    model['draftContext']['requestQuotes'] = [quote]
    transcript = [{'speaker': '경영주', 'text': case['text']}]
    result = normalize_analysis(model, transcript, case, DEPARTMENTS)
    assert not any('요청 인용' in question or '요청 원문' in question for question in result['questions'])
    assert [issue['field'] for issue in result['issues']] == ['unit']


@pytest.mark.parametrize('first,second,cancellation', [
    ('반송 방법을 알려 주세요.', '교환 방법을 알려 주세요.', '교환 방법 요청은 취소합니다.'),
    ('치약 반송 방법을 알려 주세요.', '컵 반송 방법을 알려 주세요.', '컵 반송 방법 요청은 취소합니다.'),
])
@pytest.mark.parametrize('particle', ['은', '만', '만을', '만은', '을만'])
def test_independent_review_named_withdrawal_keeps_distinct_operation_or_product(first, second, cancellation, particle):
    cancellation = cancellation.replace('요청은', '요청' + particle)
    transcript = [{'speaker': 'customer', 'text': first},
                  {'speaker': 'customer', 'text': second},
                  {'speaker': 'agent', 'text': '확인하겠습니다.'},
                  {'speaker': 'customer', 'text': cancellation}]
    case = {'draftContext': {'requestQuotes': [first, second]}, 'transcript': transcript}
    before = copy.deepcopy(case)
    result = resolve_requests(case['draftContext'], transcript)
    assert [item['quote'] for item in result['active']] == [first]
    assert [(item['quote'], item['reason']) for item in result['rejected']] == [(second, 'WITHDRAWN')]
    assert normalize_case(case)['fields']['request'] == first
    assert case == before


@pytest.mark.parametrize('interruption', [True, False])
@pytest.mark.parametrize('contract', ['requestQuote', 'requestQuotes'])
@pytest.mark.parametrize('punctuation', ['', '.', '!', '?', '?!', '!?', '...', '!!'])
def test_independent_review_denied_quoted_cancellation_keeps_original_request(interruption, contract, punctuation):
    quote = '반송 방법을 알려 주세요.'
    transcript = [{'speaker': 'customer', 'text': quote}]
    if interruption:
        transcript.append({'speaker': 'agent', 'text': '반송을 원하지 않으시나요?'})
    transcript.append({'speaker': 'customer', 'text': f'저는 "반송 방법 요청은 취소합니다{punctuation}"라고 말한 적이 없습니다.'})
    context = {contract: quote if contract == 'requestQuote' else [quote]}
    result = resolve_requests(context, transcript)
    assert [item['quote'] for item in result['active']] == [quote]
    assert result['reviewReasons'] == []
    assert normalize_case({'draftContext': context, 'transcript': transcript})['fields']['request'] == quote


@pytest.mark.parametrize('modifier', ['', '제대로 ', '정확히 '])
@pytest.mark.parametrize('adjacent', [False, True])
def test_independent_review_unit_correction_cannot_drop_context_without_adverb(modifier, adjacent):
    correction = '한 개가 아니라 한 박스예요.'
    quote = f'단위를 {modifier}기록해 주세요.'
    transcript = ([{'speaker': 'customer', 'text': correction}, {'speaker': 'customer', 'text': quote}]
                  if adjacent else [{'speaker': 'customer', 'text': correction + ' ' + quote}])
    result = resolve_requests({'requestQuotes': [quote]}, transcript)
    assert not result['active']
    assert result['reviewReasons'] == ['MISSING_CORRECTION_CONTEXT']
    assert normalize_case({'draftContext': {'requestQuotes': [quote]}, 'transcript': transcript})['fields']['request'] is None
    complete = correction + ' ' + quote
    assert [item['quote'] for item in resolve_requests({'requestQuotes': [complete]}, transcript)['active']] == [complete]


@pytest.mark.parametrize('speaker', ['화자', 'unknown', 'speaker', 'none'])
@pytest.mark.parametrize('contract', ['requestQuote', 'requestQuotes'])
def test_independent_review_fallback_label_cannot_confirm_same_person_withdrawal(speaker, contract):
    quote = '반송 방법을 알려 주세요.'
    transcript = [{'speaker': speaker, 'text': quote},
                  {'speaker': speaker, 'text': '반송 방법 요청은 취소합니다.'}]
    context = {contract: quote if contract == 'requestQuote' else [quote]}
    result = resolve_requests(context, transcript)
    assert [item['quote'] for item in result['active']] == [quote]
    assert result['reviewReasons'] == ['SPEAKER_ROLE_UNVERIFIED', 'OTHER_SPEAKER_CANCELLATION']


def pc2_r2_cases():
    """Fixed D01-D20 expectations from PC2 commit 4c200dec, not code output."""
    q, paste, cup = '반송 방법을 알려 주세요.', '치약 반송 방법을 알려 주세요.', '컵 반송 방법을 알려 주세요.'
    exchange, unit = '교환 방법을 알려 주세요.', '단위를 기록해 주세요.'

    def rows(parts):
        return [{'id': f't{i+1}', 'speaker': speaker, 'text': text,
                 'startSeconds': i * 4.0, 'endSeconds': i * 4.0 + 3.5}
                for i, (speaker, text) in enumerate(parts)]

    def one(quote, tail, speaker='customer', legacy=False, interruption=False):
        parts = [(speaker, quote)] + ([('agent', '확인하겠습니다.')] if interruption else []) + [(speaker, tail)]
        return ({'requestQuote': quote} if legacy else {'requestQuotes': [quote]}, rows(parts))

    def two(first, second, tail):
        return ({'requestQuotes': [first, second]}, rows([
            ('customer', first), ('customer', second), ('agent', '확인하겠습니다.'), ('customer', tail)]))

    result = []

    def add(id, inputs, active, rejected=(), review=()):
        context, transcript = inputs
        result.append({'id': id, 'draftContext': context, 'transcript': transcript,
                       'active': active, 'rejected': list(rejected), 'review': list(review)})

    add('D01', one('치약을 반송해 주세요.', '치약 반송 요청은 취소합니다.'), [],
        [(0, '치약을 반송해 주세요.', 'WITHDRAWN')], ['WITHDRAWN'])
    add('D02', one(paste, '치약 반송 요청은 취소합니다.'), [], [(0, paste, 'WITHDRAWN')], ['WITHDRAWN'])
    add('D03', one('치약을 반송해 주세요.', '컵 반송 요청은 취소합니다.'), ['치약을 반송해 주세요.'])
    add('D04', two(paste, cup, '컵 반송 방법 요청만 취소합니다.'), [paste], [(1, cup, 'WITHDRAWN')], ['WITHDRAWN'])
    add('D05', two(paste, cup, '컵 반송 방법 요청은 취소합니다.'), [paste], [(1, cup, 'WITHDRAWN')], ['WITHDRAWN'])
    add('D06', two(q, exchange, '교환 방법 요청만 취소합니다.'), [q], [(1, exchange, 'WITHDRAWN')], ['WITHDRAWN'])
    add('D07', two(q, exchange, '교환 방법 요청은 취소합니다.'), [q], [(1, exchange, 'WITHDRAWN')], ['WITHDRAWN'])
    denial = '저는 "반송 방법 요청은 취소합니다?!"라고 말한 적이 없습니다.'
    add('D08', one(q, denial, interruption=True), [q])
    add('D09', one(q, denial, legacy=True, interruption=True), [q])
    add('D10', one(q, '저는 "반송 방법 요청은 취소합니다."라고 말한 적이 없습니다.', interruption=True), [q])
    add('D11', one(q, '반송 방법 요청은 취소합니다?!'), [], [(0, q, 'WITHDRAWN')], ['WITHDRAWN'])
    for id, speaker, legacy in [('D12', 'unknown', True), ('D13', 'unknown', False),
                                ('D14', None, True), ('D15', '화자', True)]:
        add(id, one(q, '반송 방법 요청은 취소합니다.', speaker=speaker, legacy=legacy), [q],
            review=['SPEAKER_ROLE_UNVERIFIED', 'OTHER_SPEAKER_CANCELLATION'])
    add('D16', one(q, '반송 방법 요청은 취소합니다.', legacy=True), [], [(0, q, 'WITHDRAWN')], ['WITHDRAWN'])
    correction = '한 개가 아닌 한 박스예요. '
    add('D17', ({'requestQuotes': [unit]}, rows([('customer', correction + unit)])), [],
        [(0, unit, 'MISSING_CORRECTION_CONTEXT')], ['MISSING_CORRECTION_CONTEXT'])
    add('D18', ({'requestQuotes': [correction + unit]}, rows([('customer', correction + unit)])), [correction + unit])
    add('D19', ({'requestQuotes': [unit]}, rows([('customer', '한 개가 아니라 한 박스예요. ' + unit)])), [],
        [(0, unit, 'MISSING_CORRECTION_CONTEXT')], ['MISSING_CORRECTION_CONTEXT'])
    add('D20', ({'requestQuotes': [q]}, rows([('customer', q), ('agent', '확인하겠습니다.'), ('customer', q)])), [],
        [(0, q, 'AMBIGUOUS_OCCURRENCE')], ['AMBIGUOUS_OCCURRENCE'])
    return result


@pytest.mark.parametrize('case', pc2_r2_cases(), ids=lambda case: 'PC2-R2-' + case['id'])
def test_pc2_r2_fixed_resolver_and_public_projection(case):
    before = copy.deepcopy(case)
    result = resolve_requests(case['draftContext'], case['transcript'])
    assert [item['quote'] for item in result['active']] == case['active']
    assert [(item['proposalIndex'], item['quote'], item['reason']) for item in result['rejected']] == case['rejected']
    assert result['reviewReasons'] == case['review']
    active = case['active']
    expected = None if not active else active[0] if len(active) == 1 else '\n'.join(
        f'{index + 1}. {quote}' for index, quote in enumerate(active))
    projection = normalize_case(case)
    assert projection['fields']['request'] == expected
    assert projection['fields']['quantity'] is None and projection['fields']['unit'] is None
    for item in result['active']:
        for occurrence in item['occurrences']:
            slices = []
            for span in occurrence['spans']:
                row = case['transcript'][span['segmentIndex']]
                slices.append(row['text'][span['startChar']:span['endChar']])
                assert (span['startSeconds'], span['endSeconds']) == (row['startSeconds'], row['endSeconds'])
                assert occurrence['speaker'] == row['speaker']
            assert ' '.join(slices) == item['quote']
    assert case == before


@pytest.mark.parametrize('product,particle', [('치약', '을'), ('컵', '을'), ('오이', '를'), ('파이', '를')])
def test_particle_comparison_keeps_surface_nouns_and_one_character_products(product, particle):
    quote = f'{product}{particle} 반송해 주세요.'
    transcript = [{'speaker': 'customer', 'text': quote},
                  {'speaker': 'customer', 'text': f'{product} 반송 요청만은 취소합니다.'}]
    result = resolve_requests({'requestQuotes': [quote]}, transcript)
    assert not result['active']
    assert result['reviewReasons'] == ['WITHDRAWN']


def test_independent_review_subject_particle_syllable_does_not_merge_distinct_product_names():
    quote = '파이 반송 방법을 알려 주세요.'
    transcript = [{'speaker': 'customer', 'text': quote},
                  {'speaker': 'customer', 'text': '파 반송 요청만 취소합니다.'}]
    context = {'requestQuotes': [quote]}
    result = resolve_requests(context, transcript)
    assert [item['quote'] for item in result['active']] == [quote]
    assert result['reviewReasons'] == []
    assert normalize_case({'draftContext': context, 'transcript': transcript})['fields']['request'] == quote
