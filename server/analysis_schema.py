"""Strict structured output contract shared by validation and the model request."""
STRING = {"type": "string"}
NULLABLE = {"type": ["string", "null"]}


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


ANALYSIS_SCHEMA = obj({
    "summary": STRING,
    "fields": obj({"storeId": NULLABLE, "subject": NULLABLE,
                   "quantity": {"type": ["number", "null"], "description": (
                       "문의 대상 상품에 대해 경영주가 최종 진술·정정한 실제 수령 수량이다. "
                       "주문·발주·피킹·출고 수량이나 부족분이 아니다. 시스템이 검증한 사실을 뜻하지 않는다. "
                       "발화에서 수령 수량이 미확인이거나 여러 상품 중 대상이 불명확하면 null이다. "
                       "명시적으로 진술된 수령 0은 보존하며 전체 배송 미도착이나 기록 부재만으로 0을 추정하지 않는다.")},
                   "unit": {**NULLABLE, "description": (
                       "quantity와 동일한 수령 상품·발화에 대응하는 단위이다. "
                       "개·낱개는 EA, 박스·상자는 BOX로 표기만 정규화한다. 포장입수로 환산하지 않는다. "
                       "주문·피킹·출고 단위로 채우지 않으며 수령 단위를 모르거나 대상이 불명확하면 null이다.")},
                   "request": NULLABLE}),
    "issues": {"type": "array", "items": obj({"field": STRING, "message": STRING, "evidence": STRING})},
    "questions": {"type": "array", "items": STRING},
    "department": obj({"id": STRING, "name": STRING, "reason": STRING}),
    "facts": {"type": "array", "items": STRING},
    "unknowns": {"type": "array", "items": STRING},
    "replyDraft": STRING,
})


def claim_schema(basis):
    return {**obj({
        "product": {**NULLABLE, "description": "해당 진술의 상품. 문의 대상이 불명확하면 null."},
        "quantity": {"type": ["number", "null"], "description": f"현재 문의 대상의 {basis} 수량. 정정 전 수령량·지난 배송 수령량·다른 기준의 수량으로 보충하지 않는다."},
        "unit": {**NULLABLE, "description": f"같은 상품·같은 진술의 {basis} 단위. 개·낱개가 명시되면 EA, 박스·상자가 명시되면 BOX. 명시된 단위를 누락하거나 포장입수로 환산하지 않는다. 미확인만 null."},
        "evidenceQuote": {**NULLABLE, "description": "해당 주장을 뒷받침하는 STT 한 구간의 가장 짧은 자족적 원문 그대로. 부정·정정·인용 문맥을 잘라 반대 의미로 만들지 않는다. 화자·시각·설명을 덧붙이지 않는다. 근거가 없으면 null."},
    }), "description": (f"경영주의 현재 문의에 관한 최종 {basis} 진술. 시스템의 확인 사실이 아니며 불명확한 값은 null. "
                        + ("주문/발주를 실제로 했다는 명시적 긍정 발화만 해당한다. 수령 정정 전 값·과거 수령·주문 규격 확인 요청·주문 부정/불확실은 주문 진술이 아니다. 해당 발화가 없으면 네 값 모두 null."
                           if basis == "주문" else "현재 수령의 최종 정정을 우선한다. 과거 수령을 현재 값으로 쓰지 않으며 상담원 재오입력으로 덮어쓰지 않는다."))}


# Model-only extraction: receipt and order are separate. The HTTP analysis contract
# above is projected by live.normalize_analysis; the model cannot fill its quantity.
MODEL_ANALYSIS_SCHEMA = obj({
    **{key: value for key, value in ANALYSIS_SCHEMA["properties"].items()
       if key not in {"fields", "facts"}},
    "fields": obj({
        "subject": {**NULLABLE, "description": "제목만으로 문의 대상·문제·확인하려는 내용과 원문에 명시된 불확실성의 범위를 알 수 있게 새로 추출한다. 의미에 필요한 조건은 짧은 길이보다 우선하며 다른 필드에 있다는 이유로 생략하지 않는다. 확인 요청을 확인 중·완료로 바꾸지 않는다. 최초/재문의/처리 단계는 명시된 경우만 보존한다. 기존 문의의 후속 회신 문의를 새로운 최초 문의로 축약하지 않는다. 점포 귀속과 문의 점포의 식별은 구분한다. 상담 입력이나 임시 문구를 복사하지 않는다. 대상이 없거나 불명확하면 null과 확인 질문."},
        "request": {**NULLABLE, "description": "경영주가 발화에서 요청한 확인·안내 내용과 그 요청에 필요한 최종 정정·기한·조건·미해결 안내. 다른 필드로 대체하지 않고 실제 발화에서 새로 추출한다. 처리완료·귀책·센터 회신이나 원문에 없는 조건을 창작하지 않는다. 요청이 미확인이면 null."},
    }),
    "draftContext": obj({
        "subjectQuote": {**NULLABLE, "description": "문의 대상·문제·필수 조건을 뒷받침하는 원문을 그대로 인용한다. 같은 비어 있지 않은 화자의 인접 transcript 구간만 경계 한 공백으로 이을 수 있다. 다른 화자나 빈 구간을 건너뛰거나 내부 글자·공백을 바꾸지 않는다. 점포 소개만 선택하거나 fields.subject를 복사하거나 새로운 문장을 만들지 않는다. 짧게 만들기 위해 부정·정정·시점·귀속 불확실성을 자르지 않는다. 관련 원문이 없으면 null."},
        "requestQuotes": {"type": "array", "maxItems": 8, "items": STRING, "description": "현재 고객 요청을 각각 자족적인 원문 인용으로 추출한다. 최대8개, 없으면 빈 배열. 단위 정정·잘못 온 상품 처리·주문 상품 처리처럼 독립 요청을 빠뜨리지 않는다. 인용마다 같은 비어 있지 않은 화자의 인접 transcript 구간만 사용할 수 있고 구간 경계만 한 공백으로 잇는다. 다른 화자나 빈 구간을 건너뛰거나 내부 글자·공백을 바꾸지 않는다. 정정 대상·조건·기한을 자르지 않고 전사 순서로 중복 없이 반환한다. 욕설 순화는 서버가 담당한다."},
    }),
    "orderedClaim": claim_schema("주문"),
    "receivedClaim": claim_schema("실제 수령"),
    "storeClaim": obj({
        "name": {**NULLABLE, "description": "STT에서 들린 점포명 그대로. 마스터의 비슷한 이름으로 교정하지 않는다."},
        "evidenceQuote": {**NULLABLE, "description": "이 점포명이 등장한 STT 한 구간의 원문 그대로. 근거가 없으면 null."},
    }),
})
