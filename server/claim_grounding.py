"""Bounded surface grounding for quoted Korean quantity claims.

This is a necessary support check, not an entailment, speaker, or truth engine.
It only removes unsupported proposed values; it never fills or converts values.
"""
import re


ORDER = re.compile(r'(?:주문|발주)(?:을|를)?\s*(?:했|하였|해서|한\s)')
RECEIPT = re.compile(r'받|수령|왔|온\s|도착')
PAST = re.compile(r'지난\s*(?:주|달|번)|어제|이전\s*배송')
CURRENT = re.compile(r'오늘|이번')
CLAUSE_END = re.compile(r'((?:주문|발주)(?:을|를)?\s*(?:했|하였)(?:는데|지만|고)|(?:주문|발주)해서|받았(?:는데|지만|고)|받지\s*않았(?:는데|지만|고)|받지\s*못했(?:는데|지만|고)|모르(?:겠고|지만|는데)|(?:예정|계획)(?:이며|이고|이지만)|아니라|말고)')
RECEIPT_NEGATED = re.compile(
    r'받지\s*(?:않|못)|(?:못|안)\s*받|받은\s*적(?:이)?\s*없|수령하지\s*(?:않|못)|미수령'
    r'|(?:받은|수령한|도착한)\s*(?:것|거|건|사실|상태)(?:은|는|이|가)?\s*(?:아니|아닙|아닌|아님|없)')
RECEIPT_FUTURE = re.compile(
    r'받을|수령할|도착할|(?:내일|모레|다음\s*(?:주|달|배송)).*(?:받|수령|도착)'
    r'|(?:수령|도착)\s*(?:예정|계획)(?=$|[\s,.]|입니|이에|이며|이고|이지만|인|이다|임|수량)')
RECEIPT_UNCERTAIN = re.compile(r'받았는지|받은\s*건지|수령\s*여부|모르|모릅|불확실')
NATIVE = {'영': 0, '공': 0, '한': 1, '하나': 1, '두': 2, '둘': 2, '세': 3, '셋': 3,
          '네': 4, '넷': 4, '다섯': 5, '여섯': 6, '일곱': 7, '여덟': 8, '아홉': 9,
          '열': 10, '열한': 11, '열두': 12, '열세': 13, '열네': 14, '열다섯': 15,
          '스무': 20, '스물': 20}
for _prefix, _tens in [('열', 10), ('스물', 20), ('서른', 30), ('마흔', 40), ('쉰', 50), ('예순', 60), ('일흔', 70), ('여든', 80), ('아흔', 90)]:
    NATIVE[_prefix] = _tens
    for _ones_word, _ones in list(NATIVE.items()):
        if 0 < _ones < 10:
            NATIVE[_prefix + _ones_word] = _tens + _ones
NUMBER = r'(?:\d+(?:\.\d+)?|' + '|'.join(sorted(NATIVE, key=len, reverse=True)) + r'|[일이삼사오육칠팔구십백천]+)'
MEASURE = re.compile(r'(?<!\d)(?P<number>\d+(?:\.\d+)?|(?<![가-힣])' + NUMBER + r')\s*(?P<unit>낱개|개|박스|상자|EA\b|BOX\b)', re.I)
UNITS = {'낱개': 'EA', '개': 'EA', '박스': 'BOX', '상자': 'BOX'}


def _number(raw):
    if re.fullmatch(r'\d+(?:\.\d+)?', raw):
        return float(raw)
    if raw in NATIVE:
        return NATIVE[raw]
    if not re.fullmatch(r'(?:[일이삼사오육칠팔구]?천)?(?:[일이삼사오육칠팔구]?백)?(?:[일이삼사오육칠팔구]?십)?[일이삼사오육칠팔구]?', raw):
        return None
    digits = {word: value for value, word in enumerate('영일이삼사오육칠팔구')}
    total, pending = 0, 0
    for word in raw:
        if word in digits:
            pending = digits[word]
        else:
            total += (pending or 1) * {'십': 10, '백': 100, '천': 1000}[word]
            pending = 0
    return total + pending


def compact(value):
    return ''.join(value.split())


def order_assertion_scope(text):
    """A following receipt uncertainty is not a negation of an earlier order.

    Reported/withdrawn assertions remain whole, so the caller's existing rejection
    checks still see them. A mere sentence-wide '못' must not erase an order.
    """
    end = re.search(r'(?:주문|발주)(?:을|를)?\s*(?:했|하였)(?:는데|지만|고)|(?:주문|발주)해서', text)
    if end:
        tail = text[end.end():]
        if RECEIPT.search(tail) and not re.search(r'사실.{0,6}(?:아니|아닙)|거짓|잘못\s*입력|오입력|예시|예문|라고|라는|주문|발주', tail):
            return text[:end.end()]
    return text


def _clauses(quote):
    # Keep endings with their clause. Decimal punctuation is not a boundary.
    marked = CLAUSE_END.sub(r'\1\n', quote)
    # An attributive order amount is not the actual-receipt amount that follows.
    marked = re.sub(r'\s+(중(?:에|에서)?|가운데)\s+(?=실제|받은|수령)', r' \1\n', marked)
    parts = re.split(r'(?<!\d)[.!?。]|[.!?。](?!\d)|\n', marked)
    # An explicit current time starts a different attribution scope.
    output = []
    for part in parts:
        role_start = re.search(r'실제(?:로)?|수령(?:량)?(?:은|는)|받은\s*(?:것|수량)', part)
        if role_start and ORDER.search(part[:role_start.start()]) and MEASURE.search(part[:role_start.start()]):
            output.extend((part[:role_start.start()], part[role_start.start():]))
            continue
        current = CURRENT.search(part)
        if current and PAST.search(part[:current.start()]):
            output.extend((part[:current.start()], part[current.start():]))
        else:
            output.append(part)
    return [part.strip() for part in output if part.strip()]


def _scopes(claim, kind, transcript):
    quote = claim['evidenceQuote']
    parts = _clauses(quote)
    product_pattern = _product_pattern(claim['product'])
    scopes = []
    previous_target = False
    for part in parts:
        named_target = bool(product_pattern.search(part))
        # Only explicit ellipsis of one preceding named target may omit its name.
        # '별빛차 3개...' is not ellipsis of the preceding '모래차'.
        linked_target = named_target or (previous_target and _receipt_ellipsis(part))
        pattern = ORDER if kind == 'orderedClaim' else RECEIPT
        if linked_target and pattern.search(part):
            scopes.append(part)
        if named_target:
            previous_target = len(list(MEASURE.finditer(part))) <= 1
        elif not _receipt_ellipsis(part):
            previous_target = False
    if kind == 'receivedClaim':
        # '주문한 적 없는 ... 받음' is a valid receipt, not an order assertion.
        scopes = [part for part in scopes if not RECEIPT_NEGATED.search(part)
                  and not RECEIPT_FUTURE.search(part)]
        # Uncounted receipts may still explicitly state their unit. Keep those
        # scopes for unit-only proposals, but never certify a proposed quantity.
        if claim['quantity'] is not None:
            scopes = [part for part in scopes if not RECEIPT_UNCERTAIN.search(part)]
        current_exists = any(CURRENT.search(part) for part in scopes)
        product = compact(claim['product'])
        # Also reject a past-only excerpt when the surrounding input explicitly
        # distinguishes today's same product. No broad all-past rejection.
        current_in_source = any(CURRENT.search(part) and not PAST.search(part) and product in compact(part)
                                for s in transcript for part in _clauses(s.get('text', '')))
        if current_exists or current_in_source:
            scopes = [part for part in scopes if not PAST.search(part) or CURRENT.search(part)]
    # Discard the superseded half of an explicit correction, not its final value.
    return [part for part in scopes if not part.endswith(('아니라', '말고'))]


def _product_pattern(product):
    # Permit ordinary particles in a multiword product, e.g. '차는 레몬맛'.
    words = product.split()
    name = r'(?:은|는|이|가|의)?\s*'.join(re.escape(word) for word in words)
    suffix = r'(?=$|[\s\d.,!?]|(?:은|는|이|가|의|을|를|와|과|도|만|에서|로|부터|까지)(?=$|\s|\d))'
    return re.compile(r'(?<![가-힣A-Za-z0-9])' + name + suffix)


def _receipt_ellipsis(part):
    prefix = r'(?:(?:오늘|이번|현재|최종|실제(?:로)?(?:는)?|그중)\s*)*'
    nominal = r'(?:(?:받은\s*(?:것|수량)|수령(?:량)?)(?:은|는|이|가)?\s*)?'
    return bool(re.match(r'^' + prefix + nominal + r'(?:' + NUMBER + r'\s*(?:개|박스|상자|EA|BOX)|박스|상자|낱개)', part))


def supported_values(claim, kind, transcript):
    """Return independently supported proposed quantity/unit, never a new value."""
    scopes = _scopes(claim, kind, transcript)
    quantities, units = set(), set()
    for scope in scopes:
        matches = list(MEASURE.finditer(scope))
        # If multiple products/amounts share an order clause, support only the
        # first amount after the explicitly named target, not a neighbour's.
        product_match = _product_pattern(claim['product']).search(scope)
        if len(matches) > 1 and product_match:
            following = [match for match in matches if match.start() >= product_match.end()]
            matches = following[:1]
        for match in matches:
            raw = match['number']
            number = _number(raw)
            if number is not None:
                quantities.add(number)
            units.add(UNITS.get(match['unit'], match['unit'].upper()))
        # Explicit quantity without a unit does not become a clock, SKU or other
        # arbitrary numeral merely because it appears somewhere in the quote.
        for match in re.finditer(r'(?:수량|수령량|주문량)(?:은|는|이|가|:)?\s*(\d+(?:\.\d+)?)(?=\s*(?:입니다|이고|이며|이지만|$))', scope):
            quantities.add(float(match[1]))
        # A known unit without a number is allowed only in a receipt/order scope.
        if not matches:
            for match in re.finditer(r'박스|상자|낱개|(?<![가-힣])개(?=\s*(?:단위|로|를|는|$))|\bEA\b|\bBOX\b', scope, re.I):
                units.add(UNITS.get(match[0], match[0].upper()))
    quantity, unit = claim['quantity'], claim['unit']
    return (quantity if quantity is None or quantity in quantities else None,
            unit if unit is None or unit in units else None)


def reconcile_unknown(value, received):
    """Replace only a simple current same-product quantity/unit missing claim.

    Do not erase compound uncertainty, physical verification, other products,
    other dates, or a genuinely absent field. Free prose is not treated as truth.
    """
    if not received['product'] or received['quantity'] is None or received['unit'] is None:
        return value
    product = re.escape(compact(received['product']))
    text = compact(value)
    missing = r'(?:수령수량|수령량)(?:(?:및|과|와|·|/)단위)?|수령단위'
    if re.fullmatch(product + r'(?:의)?(?:실제|최종)?(?:' + missing + r')(?:미확인|불명확|확인필요)?[.]?', text):
        return (f"{received['product']} 수령 {received['quantity']} {received['unit']}라는 진술은 원문에 있습니다. "
                "실제 인도 및 시스템 기록과의 일치는 별도 확인이 필요합니다.")
    return value
