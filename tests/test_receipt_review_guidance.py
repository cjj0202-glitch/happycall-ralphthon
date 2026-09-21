"""Review guidance must preserve unknown values and exact source attribution."""
import copy

import pytest

from server.live import normalize_analysis
from tests.test_analysis_repair import case_and_model, claim, DEPARTMENTS


UNIT_GUIDANCE = (
    "AI가 수령 단위를 자동 확인하지 못했습니다. 인용문을 원문과 대조해 주세요. "
    "원문에서도 불명확하면 경영주에게 추가 확인해 주세요."
)
RECEIPT_PREFIX = "AI 추가 확인: 실제 수령 "


def project(quote, quantity, unit, *, ordered=None, fabricated_quote=None):
    case, model = case_and_model()
    request = "출고 기록과 문의 내용을 대조해 주세요."
    text = "가상물결점입니다. " + quote + " " + request
    case["text"] = text
    case["intake"].update(subject="하늘솔티백 수령", quantity=None, unit=None)
    model["fields"] = {"subject": "하늘솔티백 수령 확인", "request": request}
    model["draftContext"] = {"subjectQuote": quote, "requestQuote": request}
    model["orderedClaim"] = ordered or claim()
    model["receivedClaim"] = claim("하늘솔티백", quantity, unit, fabricated_quote or quote)
    model["questions"] = ["모델 제안 질문을 유지합니다."]
    model["unknowns"] = ["다른 상품의 포장 귀속은 아직 불명확합니다."]
    model["issues"] = [{"field": "label", "message": "포장 라벨 대조를 제안합니다.", "evidence": quote}]
    transcript = [{"speaker": "경영주", "text": text}]
    before = copy.deepcopy((case, model, transcript))
    result = normalize_analysis(model, transcript, case, DEPARTMENTS)
    assert (case, model, transcript) == before
    assert result["fields"]["request"] == request
    assert "모델 제안 질문을 유지합니다." in result["questions"]
    assert "AI 검토 제안·미확인: 다른 상품의 포장 귀속은 아직 불명확합니다." in result["unknowns"]
    assert any(issue["field"] == "label" and issue["message"].startswith("AI 검토 제안:")
               for issue in result["issues"])
    return result


@pytest.mark.parametrize("quote", [
    "하늘솔티백 4개를 받았습니다.",
    "하늘솔티백 수령량은 4입니다.",
])
def test_missing_unit_keeps_null_and_exact_quote_with_one_review_first_question(quote):
    result = project(quote, 4, None)
    assert (result["fields"]["quantity"], result["fields"]["unit"]) == (4, None)
    assert "수령 진술: 하늘솔티백 4 단위 미확인" in result["summary"]
    assert [issue for issue in result["issues"] if issue["field"] == "unit"] == [
        {"field": "unit", "message": UNIT_GUIDANCE, "evidence": quote}]
    fixed = [question for question in result["questions"] if question.startswith(RECEIPT_PREFIX)]
    assert fixed == [RECEIPT_PREFIX + "단위를 원문과 대조해 주세요. 원문에서도 불명확한 항목만 경영주에게 추가 확인해 주세요."]
    assert not any("수령 수량 또는 단위가 미확인입니다. 경영주에게 확인" in question for question in result["questions"])


@pytest.mark.parametrize("quote,unit", [("하늘솔티백 4개를 받았습니다.", "EA"), ("하늘솔티백 4박스를 받았습니다.", "BOX")])
def test_supported_unit_has_no_missing_unit_issue_or_fixed_followup(quote, unit):
    result = project(quote, 4, unit)
    assert (result["fields"]["quantity"], result["fields"]["unit"]) == (4, unit)
    assert not any(issue["message"] == UNIT_GUIDANCE for issue in result["issues"])
    assert not any(question.startswith(RECEIPT_PREFIX) for question in result["questions"])


def test_quantity_and_unit_both_unknown_are_not_filled_or_asked_twice():
    quote = "하늘솔티백을 받았지만 수량과 단위는 모릅니다."
    result = project(quote, None, None)
    assert (result["fields"]["quantity"], result["fields"]["unit"]) == (None, None)
    fixed = [question for question in result["questions"] if question.startswith(RECEIPT_PREFIX)]
    assert fixed == [RECEIPT_PREFIX + "수량·단위를 원문과 대조해 주세요. 원문에서도 불명확한 항목만 경영주에게 추가 확인해 주세요."]
    assert len([issue for issue in result["issues"] if issue["message"] == UNIT_GUIDANCE]) == 1
    assert not any("수령 수량 또는 단위가 미확인입니다. 경영주에게 확인" in question for question in result["questions"])


@pytest.mark.parametrize("ordered_quantity,ordered_unit,quote,missing", [
    (4, None, "하늘솔티백 4개를 주문했습니다.", "단위"),
    (None, None, "하늘솔티백을 주문했습니다.", "수량·단위"),
])
def test_order_omissions_point_to_order_source_first(ordered_quantity, ordered_unit, quote, missing):
    received = "하늘솔티백 4개를 받았습니다."
    result = project(quote + " " + received, 4, "EA", ordered=claim("하늘솔티백", ordered_quantity, ordered_unit, quote))
    fixed = [question for question in result["questions"] if question.startswith("AI 추가 확인: 주문 ")]
    assert fixed == [f"AI 추가 확인: 주문 {missing}를 원문과 대조해 주세요. 원문에서도 불명확한 항목만 경영주에게 추가 확인해 주세요."]
    assert not any("주문 수량 또는 단위가 미확인입니다. 경영주에게 확인" in question for question in result["questions"])


def test_rejected_quote_never_appears_as_missing_unit_evidence():
    actual = "하늘솔티백 수령 수량은 4입니다."
    invented = "하늘솔티백 4개를 확실히 받았습니다."
    result = project(actual, 4, None, fabricated_quote=invented)
    assert (result["fields"]["quantity"], result["fields"]["unit"]) == (None, None)
    assert not any(issue["message"] == UNIT_GUIDANCE for issue in result["issues"])
    assert not any(issue["evidence"] == invented for issue in result["issues"])
    assert any("인용 근거를 확인하지 못했습니다" in question for question in result["questions"])
