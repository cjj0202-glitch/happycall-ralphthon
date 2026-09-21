"""Fresh authored surface-grounding cases; no live calls/evaluation oracle."""
import copy

import pytest

from server.claim_grounding import supported_values
from server.live import normalize_analysis
from tests.test_analysis_repair import case_and_model, claim, DEPARTMENTS


@pytest.mark.parametrize("text,quantity,unit,expected", [
    ("푸른달봉투 수령량은 4이고 별빛차는 2박스를 받았습니다.", 4, "BOX", (4, None)),
    ("푸른달봉투 수령량은 4이고 별빛차는 4박스를 받았습니다.", 4, "BOX", (4, None)),
    ("별빛차는 2박스를 받았고 푸른달봉투 수령량은 4입니다.", 4, "BOX", (4, None)),
    ("별빛차는 4박스이고 푸른달봉투 수령량은 4입니다.", 4, "BOX", (4, None)),
    ("푸른달봉투 수령량은 4입니다.", 4, "BOX", (4, None)),
    ("푸른달봉투 4개와 별빛차 4박스를 받았습니다.", 4, "BOX", (4, None)),
    ("별빛차 4박스와 푸른달봉투 4개를 받았습니다.", 4, "BOX", (4, None)),
    ("푸른달봉투와 별빛차 4박스를 받았습니다.", 4, "BOX", (None, None)),
    ("푸른달봉투는 박스로 받았고 별빛차는 4개를 받았습니다.", None, "EA", (None, None)),
    ("푸른달봉투는 박스로 받았고 별빛차는 4개를 받았습니다.", None, "BOX", (None, "BOX")),
    ("푸른달봉투 수령량은 모르겠고 별빛차 4박스를 받았습니다.", None, "BOX", (None, None)),
    ("푸른달봉투 수령량은 4이고 별빛차 수령량은 2입니다.", 2, None, (None, None)),
    ("푸른달봉투는 4개와 2박스를 받았습니다.", 4, "BOX", (4, None)),
    ("푸른달봉투는 4개와 2박스를 받았습니다.", 4, "EA", (4, "EA")),
    ("푸른달봉투 4개를 받았습니다. 푸른달봉투 2박스를 받았습니다.", 4, "BOX", (4, None)),
    ("푸른달봉투는 4박스를 주문했지만 4개를 받았습니다.", 4, "BOX", (4, None)),
    ("지난달 푸른달봉투 4박스를 받았지만 오늘 푸른달봉투 4개를 받았습니다.", 4, "BOX", (4, None)),
    ("푸른달봉투 4박스를 받지 않았고 별빛차 4개를 받았습니다.", 4, "BOX", (None, None)),
    ("푸른달봉투 4박스를 내일 받을 예정입니다.", 4, "BOX", (None, None)),
    ("푸른달봉투 4박스를 받았는지 모르겠습니다.", 4, "BOX", (None, None)),
])
def test_other_product_role_or_measure_cannot_supply_unit(text, quantity, unit, expected):
    proposed = claim("푸른달봉투", quantity, unit, text)
    before = copy.deepcopy(proposed)
    assert supported_values(proposed, "receivedClaim", [{"text": text}]) == expected
    assert proposed == before


@pytest.mark.parametrize("text,quantity,unit,expected", [
    ("푸른달봉투 4개를 받았습니다.", 4, "EA", (4, "EA")),
    ("별빛차 2박스와 푸른달봉투 4개를 받았습니다.", 4, "EA", (4, "EA")),
    ("푸른달봉투 4개와 별빛차 2박스를 받았습니다.", 4, "EA", (4, "EA")),
    ("푸른달봉투 4개를 받았습니다. 푸른달봉투 2박스를 받았습니다.", 2, "BOX", (2, "BOX")),
    ("푸른달봉투 수령량은 4이고 별빛차는 2박스를 받았습니다.", 4, None, (4, None)),
    ("푸른달봉투를 0개 받았습니다.", 0, "EA", (0, "EA")),
    ("푸른달봉투는 4개 받았습니다.", 4, None, (4, None)),
    ("푸른달봉투는 4개 받았습니다.", None, "EA", (None, "EA")),
    ("푸른달봉투는 4개 받았습니다.", None, None, (None, None)),
    ("푸른달봉투는 박스로 받았지만 몇 박스인지는 모릅니다.", None, "BOX", (None, "BOX")),
    ("푸른달봉투는 개 단위로 수령했지만 수량은 모릅니다.", None, "EA", (None, "EA")),
    ("푸른달봉투는 수령 예정대로 4개를 받았습니다.", 4, "EA", (4, "EA")),
    ("푸른달봉투 네 개를 받았습니다.", 4, "EA", (4, "EA")),
    ("푸른달봉투 4박스를 주문했지만 실제 받은 푸른달봉투는 4개입니다.", 4, "EA", (4, "EA")),
    ("지난달 푸른달봉투 4박스를 받았습니다.", 4, "BOX", (4, "BOX")),
])
def test_supported_partial_zero_and_historical_values_survive(text, quantity, unit, expected):
    proposed = claim("푸른달봉투", quantity, unit, text)
    assert supported_values(proposed, "receivedClaim", [{"text": text}]) == expected


@pytest.mark.parametrize("product,quantity,unit,expected", [
    ("푸른달봉투", 4, "EA", (4, "EA")),
    ("푸른달봉투", 4, "BOX", (4, None)),
    ("별빛차", 2, "BOX", (2, "BOX")),
    ("별빛차", 2, "EA", (2, None)),
])
def test_order_values_also_stay_bound_to_named_product(product, quantity, unit, expected):
    text = "푸른달봉투 4개와 별빛차 2박스를 주문했습니다."
    assert supported_values(claim(product, quantity, unit, text), "orderedClaim", [{"text": text}]) == expected


def test_normalization_drops_borrowed_unit_with_question_and_keeps_original():
    text = "푸른달봉투 수령량은 4이고 별빛차는 2박스를 받았습니다."
    case, model = case_and_model()
    case["text"] = text
    model["orderedClaim"] = claim()
    model["receivedClaim"] = claim("푸른달봉투", 4, "BOX", text)
    before = copy.deepcopy((case, model))
    result = normalize_analysis(model, [{"speaker": "경영주", "text": text}], case, DEPARTMENTS)
    assert (result["fields"]["quantity"], result["fields"]["unit"]) == (4, None)
    assert any("같은 대상" in question and "원문" in question for question in result["questions"])
    assert (case, model) == before


@pytest.mark.parametrize("text", [
    "하늘솔티백도 이번에 다섯 개를 받았습니다.",
    "하늘솔티백은 오늘 오전에 다섯 개를 받았습니다.",
    "하늘솔티백은 정확히 다섯 개를 받았습니다.",
    "하늘솔티백은 오늘 오후 2시 30분에 다섯 개를 받았습니다.",
    "하늘솔티백은 7시에 다섯 개를 받았습니다.",
    "하늘솔티백은 방금 딱 다섯 개를 받았습니다.",
])
def test_independent_review_natural_time_and_emphasis_preserve_receipt(text):
    assert supported_values(claim("하늘솔티백", 5, "EA", text), "receivedClaim", [{"text": text}]) == (5, "EA")


@pytest.mark.parametrize("quantity,unit,expected", [
    (5, "BOX", (5, None)),
    (5, "EA", (5, "EA")),
    (None, "BOX", (None, "BOX")),
])
def test_independent_review_unit_only_statement_cannot_complete_other_pair(quantity, unit, expected):
    text = "하늘솔티백은 다섯 개를 받았습니다. 하늘솔티백은 박스로도 받았습니다."
    assert supported_values(claim("하늘솔티백", quantity, unit, text), "receivedClaim", [{"text": text}]) == expected


def test_time_words_do_not_turn_another_product_into_a_bridge():
    text = "하늘솔티백 수령량은 5이고 오늘 오전에 달빛차 다섯 박스를 받았습니다."
    assert supported_values(claim("하늘솔티백", 5, "BOX", text), "receivedClaim", [{"text": text}]) == (5, None)
