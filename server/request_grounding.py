"""Keep the customer's quoted request separate from generated follow-up advice.

This bounded speech-act check is not a Korean entailment or speaker classifier.
It never paraphrases a request and never promotes model prose to source evidence.
"""
import re


REQUEST = re.compile(
    r'주(?:세요|십시오|시고|실\s*수\s*있|시겠)|해\s*줘(?:요)?'
    r'|(?:부탁|요청|문의)(?:드립|드려|합니|해요|합니다|입니다)'
    r'|(?:확인|알|묻|문의|상담|안내)[^.!?\n]{0,18}싶(?:습니다|어요)'
    r'|(?:언제|어떻게|가능한가|가능할까|되나요|인가요)[^.!\n]*[?？]')
NON_CURRENT = re.compile(
    r'(?:요청|부탁|문의)(?:을|를)?\s*(?:할\s*(?:예정|계획)|하(?:려고|려는|고자)|(?:한|했던)\s*(?:것|건|적|사실)(?:이|은|는|가)?\s*(?:아니|아닙|없)|하지\s*않|안\s*했)'
    r'|(?:요청|부탁|문의)(?:이|가|은|는)\s*(?:아닙|아니에요|아니었|아니라고)'
    r'|(?:라고|라는)[^.!?\n]*(?:예정|계획|예시|예문|(?:부탁|요청|말)?한\s*(?:것|건|적|사실)(?:이|은|는|가)?\s*(?:아니|아닙|없)|(?:요청|부탁|문의|말|전달|입력)(?:했|하였|드렸))'
    r'|(?:라고|라는)[^.!?\n]*(?:(?:전달|전해)\s*(?:받았|들었)|들었|보냈|남겼|한다면|할\s*경우|가정)'
    r'|(?:예시|예문|연습용)')
CANCELLATION = re.compile(r'(?:취소|철회)(?:합니다|해요|하겠습니다|할게요|했습니다)')


def _meaningful_request(text):
    """Require content before an imperative/nominal ending, not just politeness."""
    for match in REQUEST.finditer(text):
        # Desire/question patterns carry their action or interrogative internally.
        if re.match(r'(?:확인|알|묻|문의|상담|안내).*싶|(?:언제|어떻게|가능한가|가능할까|되나요|인가요)', match.group()):
            return match
        left = max(text.rfind(mark, 0, match.start()) for mark in ('.', '!', '?', '\n')) + 1
        prefix = text[left:match.start()]
        prefix = re.sub(r'\b(?:좀|제발|부디|꼭|해)\b', '', prefix)
        if len(re.sub(r'[^가-힣A-Za-z0-9]', '', prefix)) >= 2:
            return match
    return None


def _target_terms(text):
    """Small lexical overlap for an explicitly named cancellation, not coreference."""
    terms = set()
    generic = {'요청', '부탁', '문의', '확인', '확인해', '안내', '안내해', '대조', '대조해',
               '알려', '연락', '전화', '해', '그', '이', '해당', '방금', '오늘', '내일'}
    for token in re.findall(r'[가-힣A-Za-z0-9]+', REQUEST.sub(' ', text)):
        token = re.sub(r'(?:에게|에서|으로|까지|부터|[을를은는이가로])$', '', token)
        if len(token) >= 2 and token not in generic:
            terms.add(token)
    return terms


def _separate_inquiry(inquiry, other):
    """Recognize only a narrow information/physical-operation distinction.

    Only allow the simple noun phrases below, not an arbitrary modifier before
    an information noun: "돌려보낼 시간" still depends on the cancelled action.
    Everything else keeps the conservative overlap rule. This is not a general
    intent classifier or a list of all possible operation synonyms.
    """
    information = {'시각', '시간', '일정', '라벨', '내역'}
    operation = r'(?:반송|반품|회송|교환|재배송)'
    named_operation = (
        operation + r'(?:\s*(?:방법|절차)(?:을|를)?)?\s*'
        r'(?:(?:요청|부탁|문의)(?:[은는을를])?|(?:안내해|확인해|해)?\s*'
        r'(?:주세요|주십시오))[.!?]?\s*$'
    )
    simple_inquiry = (
        r'(?:(?:배송|출고)\s+(?:시각|시간|일정)|상품\s+라벨|주문\s+내역)'
        r'(?:을|를)?\s*(?:알려|안내해|확인해)\s*(?:주세요|주십시오)[.!?]?'
    )
    return (
        bool(re.fullmatch(simple_inquiry, inquiry.strip()))
        and bool(re.search(named_operation, other))
        and not information.intersection(_target_terms(other))
        and not re.search(r'아니|말고|제외|빼고|않|못|대신', other)
    )


def _same_target(reference, other):
    if not _target_terms(reference).intersection(_target_terms(other)):
        return False
    return not (_separate_inquiry(reference, other) or _separate_inquiry(other, reference))


def _withdrawn(reference, following):
    nearest = True
    for sentence in re.split(r'[.!?\n]+', following):
        cancellation = CANCELLATION.search(sentence)
        if cancellation:
            named = sentence[:cancellation.start()]
            pronoun = re.match(r'\s*(?:그|이|해당|방금)\s*요청', named)
            if (pronoun and nearest) or _same_target(reference, named):
                return True
        elif _meaningful_request(sentence) and not NON_CURRENT.search(sentence):
            # A pronoun after another distinct request belongs to that request.
            nearest = _same_target(reference, sentence)
    return False


def current_request_quote(quote, transcript):
    """Return the verbatim quote only if it supports a current request.

    A request about tomorrow or to refrain from an action is still a request.
    Reported/negated/example context around an extracted fragment is not one.
    Every occurrence must be compatible; ambiguous repetition needs review.
    """
    if not isinstance(quote, str) or not quote.strip():
        return None
    quote = quote.strip()
    request = _meaningful_request(quote)
    if not request or NON_CURRENT.search(quote):
        return None
    contexts = []
    for index, segment in enumerate(transcript):
        text = segment.get('text', '')
        start = text.find(quote)
        while start >= 0:
            end = start + len(quote)
            left = max(text.rfind(mark, 0, start) for mark in ('.', '!', '?', '\n')) + 1
            right = end
            tail = text[end:].lstrip()
            if not quote.endswith(('.', '!', '?')) or tail.startswith(('"', "'", '”', '’', '」', '』', '라고', '라는')):
                boundaries = [text.find(mark, end) for mark in ('.', '!', '?', '\n')]
                right = min((position + 1 for position in boundaries if position >= 0), default=len(text))
            contexts.append(text[left:right])
            following = text[start + request.end():]
            for later in transcript[index + 1:]:
                if not segment.get('speaker') or later.get('speaker') != segment['speaker']:
                    break
                following += '\n' + later.get('text', '')
            if _withdrawn(quote, following):
                return None
            start = text.find(quote, end)
    if not contexts or any(NON_CURRENT.search(context) for context in contexts):
        return None
    return quote


def receipt_followup(fields, transcript, received_product):
    """Field omissions are AI follow-up questions, never customer requests."""
    source = '\n'.join(segment.get('text', '') for segment in transcript)
    amount_inquiry = received_product or re.search(
        r'수령\s*수량|수령량|(?:오늘|이번)[^.!?\n]{0,25}받은[^.!?\n]{0,25}수량', source)
    if not amount_inquiry:
        return None
    missing = [label for key, label in (('quantity', '수량'), ('unit', '단위')) if fields[key] is None]
    if not missing:
        return None
    return ('AI 추가 확인: 실제 수령 ' + '·'.join(missing)
            + ('을' if missing == ['수량'] else '를')
            + ' 원문과 대조해 주세요. 원문에서도 불명확한 항목만 경영주에게 추가 확인해 주세요.')
