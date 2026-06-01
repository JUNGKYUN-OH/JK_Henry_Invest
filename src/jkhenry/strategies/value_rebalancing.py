"""VR (Value Rebalancing) — 밸류 리밸런싱 계산 엔진.

순수 함수로만 구성. DB·네트워크 접근 없음.
"""

from decimal import ROUND_DOWN, Decimal

from jkhenry.domain.enums import OrderType
from jkhenry.domain.models import MarketData, OrderGuide, VRGuide, VRState


def compute_evaluation(shares: Decimal, current_price: Decimal) -> Decimal:
    """현재 평가금액 E = 보유수량 × 현재가."""
    return (shares * current_price).quantize(Decimal("0.01"))


def compute_v_next(v: Decimal, G: Decimal) -> Decimal:
    """다음 주기 목표값 V(다음) = V × (1 + G)."""
    return (v * (Decimal("1") + G)).quantize(Decimal("0.01"))


def determine_vr_action(
    e: Decimal, v: Decimal, band_upper: Decimal, band_lower: Decimal
) -> str:
    """밴드 이탈 여부로 BUY / SELL / HOLD 판정."""
    upper_threshold = (v * (Decimal("1") + band_upper)).quantize(Decimal("0.01"))
    lower_threshold = (v * (Decimal("1") - band_lower)).quantize(Decimal("0.01"))
    if e > upper_threshold:
        return "SELL"
    if e < lower_threshold:
        return "BUY"
    return "HOLD"


def generate_vr_guide(state: VRState, market: MarketData) -> VRGuide:
    """
    VR (Value Rebalancing) 리밸런싱 가이드를 계산한다.

    E 계산 → 밴드 판정 → 매수/매도 수량 계산 (현금 잔고 한도 적용) → v_next 계산
    """
    params = state.params
    e = compute_evaluation(state.shares_held, market.current_price)
    v = state.v_target
    current_price = market.current_price

    band_upper_val = (v * (Decimal("1") + params.band_upper)).quantize(Decimal("0.01"))
    band_lower_val = (v * (Decimal("1") - params.band_lower)).quantize(Decimal("0.01"))

    action = determine_vr_action(e, v, params.band_upper, params.band_lower)

    order = None
    messages: list[str] = []

    if action == "BUY":
        needed = (v - e).quantize(Decimal("0.01"))
        available = min(needed, state.cash_balance).quantize(Decimal("0.01"))
        if available <= Decimal("0"):
            messages.append("현금 잔고 부족 — 매수 불가. 현금을 충전해 주세요.")
        else:
            shares = (available / current_price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            order = OrderGuide(
                label="VR 매수",
                price=current_price.quantize(Decimal("0.01")),
                shares=shares,
                amount=(shares * current_price).quantize(Decimal("0.01")),
                order_type=OrderType.LIMIT,
            )
            if available < needed:
                messages.append(
                    f"현금 부족 — 필요 금액 ${needed:.2f} 중 잔고 ${available:.2f}만 매수 가능"
                )

    elif action == "SELL":
        sell_amount = (e - v).quantize(Decimal("0.01"))
        shares = (sell_amount / current_price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        order = OrderGuide(
            label="VR 매도",
            price=current_price.quantize(Decimal("0.01")),
            shares=shares,
            amount=(shares * current_price).quantize(Decimal("0.01")),
            order_type=OrderType.LIMIT,
        )

    v_next = compute_v_next(v, params.G)

    return VRGuide(
        v_target=v,
        cash_balance=state.cash_balance,
        e_value=e,
        band_upper=band_upper_val,
        band_lower=band_lower_val,
        action=action,
        order=order,
        messages=messages,
        v_next=v_next,
    )
