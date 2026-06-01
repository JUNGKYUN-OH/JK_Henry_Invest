"""VR (Value Rebalancing) 전략 엔진 단위 테스트."""

from decimal import Decimal

import pytest

from jkhenry.domain.models import MarketData, VRParams, VRState
from jkhenry.strategies.value_rebalancing import (
    compute_evaluation,
    compute_v_next,
    determine_vr_action,
    generate_vr_guide,
)


def test_compute_evaluation():
    assert compute_evaluation(Decimal("10"), Decimal("455.50")) == Decimal("4555.00")


def test_compute_v_next():
    v = Decimal("10000")
    g = Decimal("0.005")
    assert compute_v_next(v, g) == Decimal("10050.00")


def test_determine_action_hold():
    e = Decimal("10000")
    v = Decimal("10000")
    assert determine_vr_action(e, v, Decimal("0.20"), Decimal("0.20")) == "HOLD"


def test_determine_action_sell():
    e = Decimal("12500")  # V=10000, 상단=12000 초과
    v = Decimal("10000")
    assert determine_vr_action(e, v, Decimal("0.20"), Decimal("0.20")) == "SELL"


def test_determine_action_buy():
    e = Decimal("7500")   # V=10000, 하단=8000 미달
    v = Decimal("10000")
    assert determine_vr_action(e, v, Decimal("0.20"), Decimal("0.20")) == "BUY"


def test_band_boundary_upper():
    """상단 경계 정확히 = HOLD"""
    e = Decimal("12000")  # V × 1.20
    v = Decimal("10000")
    assert determine_vr_action(e, v, Decimal("0.20"), Decimal("0.20")) == "HOLD"


def test_band_boundary_lower():
    """하단 경계 정확히 = HOLD"""
    e = Decimal("8000")   # V × 0.80
    v = Decimal("10000")
    assert determine_vr_action(e, v, Decimal("0.20"), Decimal("0.20")) == "HOLD"


def test_generate_vr_guide_hold():
    state = VRState(
        params=VRParams(), v_target=Decimal("10000"),
        cash_balance=Decimal("5000"), shares_held=Decimal("22"),
    )
    market = MarketData(ticker="QQQ", prev_close=Decimal("455"), current_price=Decimal("455"))
    guide = generate_vr_guide(state, market)

    assert guide.action == "HOLD"
    assert guide.order is None
    assert guide.v_next == Decimal("10050.00")


def test_generate_vr_guide_buy():
    """하단 이탈 → BUY 가이드, 현금 한도 내"""
    state = VRState(
        params=VRParams(), v_target=Decimal("10000"),
        cash_balance=Decimal("500"),   # 현금 500만 있음
        shares_held=Decimal("15"),
    )
    # E = 15 × 455 = 6825 < 하단 8000 → BUY
    market = MarketData(ticker="QQQ", prev_close=Decimal("455"), current_price=Decimal("455"))
    guide = generate_vr_guide(state, market)

    assert guide.action == "BUY"
    assert guide.order is not None
    assert guide.order.label == "VR 매수"
    # 현금 한도 500 적용 → 주문 금액 ≤ 500
    assert guide.order.amount <= Decimal("500")
    assert any("현금 부족" in m for m in guide.messages)


def test_generate_vr_guide_sell():
    """상단 이탈 → SELL 가이드"""
    state = VRState(
        params=VRParams(), v_target=Decimal("10000"),
        cash_balance=Decimal("5000"), shares_held=Decimal("30"),
    )
    # E = 30 × 455 = 13650 > 상단 12000 → SELL
    market = MarketData(ticker="QQQ", prev_close=Decimal("455"), current_price=Decimal("455"))
    guide = generate_vr_guide(state, market)

    assert guide.action == "SELL"
    assert guide.order is not None
    assert guide.order.label == "VR 매도"
    # 매도 금액 ≈ 13650 - 10000 = 3650
    assert guide.order.amount > Decimal("0")
