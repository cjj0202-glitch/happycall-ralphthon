"""Draft quote lookup over adjacent STT segments; never rewrites the source.

Only known, identical speakers can share a block. Empty text/speaker boundaries
are retained. Claims still use their separate, single-segment evidence contract.
"""


def speaker_blocks(transcript):
    blocks = []
    for index, segment in enumerate(transcript):
        raw_speaker = segment.get('speaker')
        speaker = raw_speaker if isinstance(raw_speaker, str) and raw_speaker.strip() else None
        raw_text = segment.get('text')
        text = raw_text.strip() if isinstance(raw_text, str) else ''
        if (blocks and speaker and text and blocks[-1]['speaker'] == speaker
                and blocks[-1]['text']):
            blocks[-1]['text'] += ' ' + text
            blocks[-1]['endIndex'] = index
        else:
            blocks.append({'speaker': speaker, 'text': text, 'startIndex': index, 'endIndex': index})
    return blocks


def quote_position(quote, blocks):
    """Position of the first literal occurrence; None is never a valid quote.

    This proves membership only. Callers must separately check every occurrence
    for current intent, negation, reported speech and later withdrawal.
    """
    if not isinstance(quote, str) or not quote.strip():
        return None
    quote = quote.strip()
    for index, block in enumerate(blocks):
        offset = block['text'].find(quote)
        if offset >= 0:
            return index, offset
    return None
