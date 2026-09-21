"""Bounded, source-preserving request selection; no API, I/O or numeric extraction.

Offsets use Python Unicode code points, not browser UTF-16 indices. Segment times
are retained verbatim; character times and speaker identities are never inferred.
"""
import re

from server.request_grounding import (
    CANCELLATION, NON_CURRENT, REQUEST, _current_cancellation_context, _meaningful_request, _same_target,
    current_request_quote,
)


MAX_REQUEST_QUOTES = 8


def _explicit_speaker(speaker):
    # A diarization label such as A is explicit even when its business role is
    # unknown. The STT fallback label '화자' does not identify the same speaker.
    return (isinstance(speaker, str) and bool(speaker.strip())
            and speaker.strip().casefold() not in {'화자', 'unknown', 'speaker', 'none'})


def source_occurrences(quote, transcript):
    """Find exact minimal spans; only adjacent, explicit equal speakers join."""
    if not isinstance(quote, str) or not quote.strip():
        return []
    found = []
    for first, row in enumerate(transcript):
        speaker = row.get('speaker', '')
        joined = ''
        positions = []
        for last in range(first, len(transcript)):
            part = transcript[last]
            if last > first and (not _explicit_speaker(speaker) or part.get('speaker') != speaker):
                break
            if last > first:
                joined += ' '
            positions.append((last, len(joined), len(joined) + len(part.get('text', ''))))
            joined += part.get('text', '')
            offset = joined.find(quote)
            while offset >= 0:
                end = offset + len(quote)
                touched = [(index, start, stop) for index, start, stop in positions
                           if offset < stop and end > start]
                if touched and touched[0][0] == first and touched[-1][0] == last:
                    spans = []
                    for index, start, stop in touched:
                        segment = transcript[index]
                        spans.append({
                            'segmentId': segment.get('id', f'segment-{index}'),
                            'segmentIndex': index,
                            'startChar': max(0, offset - start),
                            'endChar': min(stop - start, end - start),
                            'startSeconds': segment.get('startSeconds', segment.get('start')),
                            'endSeconds': segment.get('endSeconds', segment.get('end')),
                        })
                    found.append({'speaker': speaker, 'spans': spans})
                offset = joined.find(quote, offset + 1)
    return found


def _source_failure(quote, transcript):
    # Diagnose an illegal whole join without using it as evidence.
    joined = ' '.join(row.get('text', '') for row in transcript)
    if quote in joined and any(not _explicit_speaker(row.get('speaker')) for row in transcript):
        return 'EMPTY_SPEAKER_JOIN'
    parts = [part for part in re.split(r'(?<=[.!?])\s+', quote) if part]
    if len(parts) > 1 and all(source_occurrences(part, transcript) for part in parts):
        return 'NONCONTIGUOUS_QUOTE'
    return 'QUOTE_NOT_IN_SOURCE'


def _sentences(text):
    return list(re.finditer(r'[^.!?\n]+(?:[.!?]+|$)', text))


def _request_parts(quote):
    # This is deliberately not a general Korean task/coreference parser.
    return [part.group().strip() for part in _sentences(quote)
            if _meaningful_request(part.group()) and not NON_CURRENT.search(part.group())]


def _missing_correction_context(quote, occurrence, transcript):
    if not re.search(r'단위[^.!?\n]*(?:기록|적어)', quote):
        return False
    first = occurrence['spans'][0]
    index = first['segmentIndex']
    prefix = transcript[index].get('text', '')[:first['startChar']]
    if index and occurrence['speaker'] and transcript[index - 1].get('speaker') == occurrence['speaker']:
        prefix = transcript[index - 1].get('text', '') + ' ' + prefix
    return bool(re.search(r'아니라[^.!?\n]*(?:박스|상자|개|EA|BOX)', prefix))


def _cancellation(quote, occurrence, transcript, legacy=False):
    """Separate explicit withdrawal, ambiguous targets and another speaker."""
    last = occurrence['spans'][-1]
    speaker = occurrence['speaker']
    parts = _request_parts(quote)
    notices = []
    for index in range(last['segmentIndex'], len(transcript)):
        row = transcript[index]
        for sentence in _sentences(row.get('text', '')):
            cancellation = CANCELLATION.search(sentence.group())
            if not cancellation or not _current_cancellation_context(
                    row.get('text', ''), sentence.start() + cancellation.start(),
                    sentence.start() + cancellation.end()):
                continue
            cancel_position = sentence.start() + cancellation.start()
            if index == last['segmentIndex'] and cancel_position < last['endChar']:
                continue
            named_start = sentence.start()
            if index == last['segmentIndex']:
                named_start = max(named_start, last['endChar'])
            named = row.get('text', '')[named_start:cancel_position]
            pronoun = bool(re.match(r'\s*(?:그|이|해당|방금)\s*(?:요청|것)', named))
            matches = [_same_target(part, named) for part in parts]
            if not pronoun and not any(matches):
                continue
            if not _explicit_speaker(speaker) or row.get('speaker') != speaker:
                if 'OTHER_SPEAKER_CANCELLATION' not in notices:
                    notices.append('OTHER_SPEAKER_CANCELLATION')
                continue
            if pronoun:
                if legacy:
                    # Preserve the legacy single-quote nearest-request policy.
                    # The old current_check below evaluates the complete source
                    # context. New arrays use the adopted conservative policy.
                    continue
                prior = []
                for previous_index, previous in enumerate(transcript[:index + 1]):
                    if previous.get('speaker') != speaker:
                        continue
                    text = previous.get('text', '')
                    if previous_index == index:
                        text = text[:cancel_position]
                    for part in _request_parts(text):
                        prior.extend(match.group() for match in REQUEST.finditer(part))
                if len(prior) != 1:
                    return 'AMBIGUOUS_CANCELLATION', notices
                return 'WITHDRAWN', notices
            if len(parts) > 1 and not all(matches):
                return 'PARTIAL_WITHDRAWAL', notices
            return 'WITHDRAWN', notices
    return None, notices


def resolve_requests(draft_context, transcript, speaker_roles=None, current_check=current_request_quote):
    """Return selected quotes, rejections, review reasons and immutable provenance.

    speaker_roles is optional trusted caller metadata, never model output. Its
    absence does not establish anybody's role; only explicit unknown roles or
    anonymous speaker labels add a targeted review reason. Provenance labels
    themselves remain labels, not identity verification.
    """
    result = {'active': [], 'rejected': [], 'reviewReasons': []}

    def review(reason):
        if reason not in result['reviewReasons']:
            result['reviewReasons'].append(reason)

    def reject(index, quote, reason, occurrences=None):
        item = {'proposalIndex': index, 'quote': quote, 'reason': reason}
        if occurrences:
            item['occurrences'] = occurrences
        result['rejected'].append(item)
        if reason != 'DUPLICATE_QUOTE':
            review(reason)

    context = draft_context if isinstance(draft_context, dict) else {}
    legacy = 'requestQuote' in context and 'requestQuotes' not in context
    mixed = 'requestQuote' in context and 'requestQuotes' in context
    raw = context.get('requestQuotes', context.get('requestQuote'))
    if mixed:
        candidates = raw if isinstance(raw, list) else [raw]
        if not candidates:
            candidates = [context['requestQuote']]
        for index, quote in enumerate(candidates):
            reject(index, quote, 'MIXED_CONTRACT_KEYS')
        return result
    if 'requestQuotes' not in context:
        raw = [] if raw is None or raw == '' else [raw]
    reason = None
    if not isinstance(raw, list):
        reason = 'INVALID_QUOTES_TYPE'
        candidates = [raw]
    elif len(raw) > MAX_REQUEST_QUOTES:
        reason = 'TOO_MANY_QUOTES'
        candidates = raw
    elif any(not isinstance(quote, str) or not quote.strip() for quote in raw):
        reason = 'INVALID_QUOTES_TYPE'
        candidates = raw
    else:
        candidates = raw
    if reason:
        for index, quote in enumerate(candidates):
            reject(index, quote, reason)
        if not candidates:
            review(reason)
        return result

    seen = set()
    for index, raw_quote in enumerate(candidates):
        quote = raw_quote.strip()
        occurrences = source_occurrences(quote, transcript)
        if quote in seen:
            reject(index, quote, 'DUPLICATE_QUOTE', occurrences)
            continue
        seen.add(quote)
        if not occurrences:
            failure = _source_failure(quote, transcript)
            reject(index, quote, failure)
            if failure == 'EMPTY_SPEAKER_JOIN':
                review('SPEAKER_ROLE_UNVERIFIED')
            continue
        if len(occurrences) != 1:
            reject(index, quote, 'AMBIGUOUS_OCCURRENCE', occurrences)
            continue
        occurrence = occurrences[0]
        speaker = occurrence['speaker']
        if ((speaker_roles is not None and speaker_roles.get(speaker, 'unverified') == 'unverified')
                or not _explicit_speaker(speaker)
                or re.fullmatch(r'[A-Z]|speaker[_ -]?\d+', str(speaker), re.I)):
            review('SPEAKER_ROLE_UNVERIFIED')
        failure, notices = _cancellation(quote, occurrence, transcript, legacy=legacy)
        for notice in notices:
            review(notice)
        if failure:
            reject(index, quote, failure, occurrences)
            continue
        if _missing_correction_context(quote, occurrence, transcript):
            reject(index, quote, 'MISSING_CORRECTION_CONTEXT', occurrences)
            continue
        first, last = occurrence['spans'][0], occurrence['spans'][-1]
        # Include surrounding source context, but never another speaker or a
        # skipped segment. This temporary view does not replace the transcript.
        source = ' '.join(row.get('text', '') for row in
                          transcript[first['segmentIndex']:last['segmentIndex'] + 1])
        semantic_transcript = [{'speaker': speaker, 'text': source}]
        if legacy:
            semantic_transcript = (transcript[:first['segmentIndex']] + semantic_transcript
                                   + transcript[last['segmentIndex'] + 1:])
        if not current_check(quote, semantic_transcript):
            reject(index, quote, 'NON_CURRENT_CONTEXT', occurrences)
            continue
        result['active'].append({'proposalIndex': index, 'quote': quote, 'occurrences': occurrences})
    result['active'].sort(key=lambda item: (
        item['occurrences'][0]['spans'][0]['segmentIndex'],
        item['occurrences'][0]['spans'][0]['startChar']))
    return result
