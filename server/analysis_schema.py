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
        "quantity": {"type": ["number", "null"], "description": f"{basis} 수량. 다른 기준의 수량으로 보충하지 않는다."},
        "unit": {**NULLABLE, "description": f"같은 상품의 {basis} 단위. EA/BOX로 표기만 정규화하며 환산하지 않는다."},
        "evidenceQuote": {**NULLABLE, "description": "해당 진술을 뒷받침하는 STT 한 구간의 원문 그대로. 화자·시각·설명을 덧붙이지 않는다. 근거가 없으면 null."},
    }), "description": f"경영주의 최종 {basis} 진술. 시스템의 확인 사실이 아니며 불명확한 값은 null."}


# Model-only extraction: receipt and order are separate. The HTTP analysis contract
# above is projected by live.normalize_analysis; the model cannot fill its quantity.
MODEL_ANALYSIS_SCHEMA = obj({
    **{key: value for key, value in ANALYSIS_SCHEMA["properties"].items()
       if key not in {"fields", "facts"}},
    "fields": obj({"subject": NULLABLE, "request": NULLABLE}),
    "orderedClaim": claim_schema("주문"),
    "receivedClaim": claim_schema("실제 수령"),
    "storeClaim": obj({
        "name": {**NULLABLE, "description": "STT에서 들린 점포명 그대로. 마스터의 비슷한 이름으로 교정하지 않는다."},
        "evidenceQuote": {**NULLABLE, "description": "이 점포명이 등장한 STT 한 구간의 원문 그대로. 근거가 없으면 null."},
    }),
})
