from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from jkhenry.domain.enums import IBPhase, OrderType


class IBParams(BaseModel):
    T: int = 40
    half_round: int = 20
    buy_high_multiplier: Decimal = Decimal("1.15")
    sell_target_pct: Decimal = Decimal("0.10")

    model_config = {"arbitrary_types_allowed": True}


class VRParams(BaseModel):
    G: Decimal = Decimal("0.005")
    band_upper: Decimal = Decimal("0.20")
    band_lower: Decimal = Decimal("0.20")
    period_days: int = 7

    model_config = {"arbitrary_types_allowed": True}


class IBState(BaseModel):
    seed: Decimal
    params: IBParams
    calendar_round: int      # 진행 일수 (매수 체결이 있는 고유 날짜 수)
    effective_round: Decimal # 유효 회차 = 누적 매수금 / 1 unit (자금 소진 비례)
    total_invested: Decimal  # 실제 누적 매수금 (잔여 예산 계산용)
    avg_price: Decimal
    shares_held: Decimal

    model_config = {"arbitrary_types_allowed": True}


class VRState(BaseModel):
    params: VRParams
    v_target: Decimal
    cash_balance: Decimal
    shares_held: Decimal

    model_config = {"arbitrary_types_allowed": True}


class MarketData(BaseModel):
    ticker: str
    prev_close: Decimal
    current_price: Decimal

    model_config = {"arbitrary_types_allowed": True}


class OrderGuide(BaseModel):
    label: str
    price: Decimal
    shares: Decimal
    amount: Decimal
    order_type: OrderType

    model_config = {"arbitrary_types_allowed": True}


class IBDailyGuide(BaseModel):
    phase: IBPhase
    calendar_round: int      # 진행 일수
    effective_round: Decimal # 유효 회차 (자금 소진 기준)
    remaining_budget: Decimal  # 잔여 예산
    unit: Decimal
    buy_orders: list[OrderGuide]
    sell_order: OrderGuide
    messages: list[str]

    model_config = {"arbitrary_types_allowed": True}


class VRGuide(BaseModel):
    v_target: Decimal
    cash_balance: Decimal
    e_value: Decimal
    band_upper: Decimal
    band_lower: Decimal
    action: str  # "BUY" | "SELL" | "HOLD"
    order: Optional[OrderGuide]
    messages: list[str]
    v_next: Decimal

    model_config = {"arbitrary_types_allowed": True}
