"""IB (Infinite Buying) 전략 엔진 단위 테스트."""

from decimal import Decimal

import pytest

from jkhenry.domain.enums import IBPhase, OrderType
from jkhenry.domain.models import IBParams, IBState, MarketData
from jkhenry.strategies.infinite_buying import (
    compute_avg_price,
    compute_calendar_round,
    compute_effective_round,
    compute_round,
    compute_shares_held,
    compute_total_invested,
    compute_unit,
    determine_phase,
    generate_ib_guide,
)


# ── 기본 계산 함수 ────────────────────────────────────────────────────────────

def test_compute_unit():
    assert compute_unit(Decimal("4000"), 40) == Decimal("100.00")
    assert compute_unit(Decimal("10000"), 40) == Decimal("250.00")


def test_compute_unit_floor():
    result = compute_unit(Decimal("100"), 3)
    assert result == Decimal("33.33")


def test_determine_phase():
    params = IBParams()
    assert determine_phase(Decimal("1"),    params) == IBPhase.FIRST_HALF
    assert determine_phase(Decimal("20"),   params) == IBPhase.FIRST_HALF
    assert determine_phase(Decimal("20.5"), params) == IBPhase.SECOND_HALF
    assert determine_phase(Decimal("40"),   params) == IBPhase.SECOND_HALF
    assert determine_phase(Decimal("40.1"), params) == IBPhase.EXHAUSTED


# ── 더미 Trade 객체 ───────────────────────────────────────────────────────────

class _T:
    def __init__(self, side, shares, price, trade_date="2026-01-01"):
        self.side = side
        self.shares = shares
        self.price = price
        self.amount = Decimal(str(shares)) * Decimal(str(price))
        self.trade_date = trade_date


def test_compute_avg_price_no_trades():
    assert compute_avg_price([]) == Decimal("0")


def test_compute_avg_price():
    trades = [
        _T("BUY", "10", "50.00", "2026-01-01"),
        _T("BUY", "10", "60.00", "2026-01-02"),
    ]
    assert compute_avg_price(trades) == Decimal("55.0000")


def test_compute_shares_held():
    trades = [
        _T("BUY",  "10", "50.00"),
        _T("BUY",  "5",  "55.00"),
        _T("SELL", "8",  "60.00"),
    ]
    assert compute_shares_held(trades) == Decimal("7.00")


def test_compute_calendar_round():
    trades = [
        _T("BUY", "1", "50", "2026-01-01"),
        _T("BUY", "1", "51", "2026-01-01"),  # 같은 날 → 1일
        _T("BUY", "1", "52", "2026-01-02"),  # 다른 날 → 2일
        _T("SELL","1", "60", "2026-01-03"),
    ]
    assert compute_calendar_round(trades) == 2
    assert compute_round(trades) == 2        # alias 확인


def test_compute_effective_round_normal():
    """하루에 1 unit 정확히 매수 시 유효 회차 = 진행일."""
    unit = Decimal("250.00")
    trades = [
        _T("BUY", "2", "125.00", "2026-01-01"),  # $250 = 1 unit
        _T("BUY", "2", "125.00", "2026-01-02"),  # $250 = 1 unit
    ]
    result = compute_effective_round(trades, unit)
    assert result == Decimal("2.00")


def test_compute_effective_round_oversize():
    """하루에 2 unit 매수 시 유효 회차 = 2."""
    unit = Decimal("250.00")
    trades = [
        _T("BUY", "4", "125.00", "2026-01-01"),  # $500 = 2 unit
    ]
    result = compute_effective_round(trades, unit)
    assert result == Decimal("2.00")
    # 진행일은 1일이지만 유효 회차는 2
    assert compute_calendar_round(trades) == 1


def test_compute_effective_round_partial():
    """하루에 0.5 unit만 매수 시 유효 회차 = 0.5."""
    unit = Decimal("250.00")
    trades = [_T("BUY", "1", "125.00", "2026-01-01")]  # $125 = 0.5 unit
    result = compute_effective_round(trades, unit)
    assert result == Decimal("0.50")


# ── IBState 헬퍼 ──────────────────────────────────────────────────────────────

def _make_state(seed="4000", eff_rnd="5", cal_rnd=5, avg="62.10",
                held="10.00", invested=None, T=40):
    params = IBParams(T=T)
    unit = compute_unit(Decimal(seed), T)
    total = Decimal(invested) if invested else Decimal(eff_rnd) * unit
    return IBState(
        seed=Decimal(seed),
        params=params,
        calendar_round=cal_rnd,
        effective_round=Decimal(eff_rnd),
        total_invested=total,
        avg_price=Decimal(avg),
        shares_held=Decimal(held),
    )


# ── 전반전 가이드 ─────────────────────────────────────────────────────────────

def test_first_half_guide():
    state  = _make_state(eff_rnd="5")
    market = MarketData(ticker="TQQQ", prev_close=Decimal("61.20"), current_price=Decimal("64.00"))
    guide  = generate_ib_guide(state, market)

    assert guide.phase == IBPhase.FIRST_HALF
    assert len(guide.buy_orders) == 2

    small = guide.buy_orders[0]
    big   = guide.buy_orders[1]
    assert small.label == "작은수 LOC"
    assert small.price == Decimal("62.10")
    assert small.order_type == OrderType.LOC

    assert big.label == "큰수 LOC"
    assert big.price == (Decimal("61.20") * Decimal("1.15")).quantize(Decimal("0.01"))
    assert big.order_type == OrderType.LOC

    total = sum(o.amount for o in guide.buy_orders)
    assert total <= Decimal("100.00")  # ≤ 1 unit


def test_first_half_sell_order():
    state  = _make_state(eff_rnd="1", held="10.00")
    market = MarketData(ticker="TQQQ", prev_close=Decimal("61.20"), current_price=Decimal("64.00"))
    guide  = generate_ib_guide(state, market)

    sell = guide.sell_order
    assert sell.label == "매도 After 지정가"
    assert sell.price == (Decimal("62.10") * Decimal("1.10")).quantize(Decimal("0.01"))
    assert sell.shares == Decimal("10.00")
    assert sell.order_type == OrderType.AFTER_LIMIT


# ── 유효 회차 초과 매수 → 잔여 예산 자동 제한 ────────────────────────────────

def test_oversize_buy_caps_guide():
    """
    유효 회차 38 (잔여 2회차분 $200 남음) 시
    가이드 금액이 1 unit($100)이 아닌 잔여 예산 기준으로 제한되지 않음.
    (아직 잔여 > 1 unit이므로 정상 가이드)
    """
    unit = Decimal("100.00")
    remaining = Decimal("200.00")
    total = Decimal("4000") - remaining
    state = IBState(
        seed=Decimal("4000"),
        params=IBParams(T=40),
        calendar_round=15,
        effective_round=Decimal("38.00"),
        total_invested=total,
        avg_price=Decimal("50.00"),
        shares_held=Decimal("50.00"),
    )
    market = MarketData(ticker="TQQQ", prev_close=Decimal("48.00"), current_price=Decimal("49.00"))
    guide  = generate_ib_guide(state, market)
    # 후반전: 평단(50) > 종가(48) → 매수 있음
    assert guide.phase == IBPhase.SECOND_HALF
    assert len(guide.buy_orders) == 1
    assert guide.buy_orders[0].amount <= remaining


def test_remaining_budget_under_unit_shows_warning():
    """잔여 예산이 1 unit 미만이면 경고 메시지 포함."""
    unit  = Decimal("250.00")
    total = Decimal("9850.00")   # 시드 10000, 잔여 150 < 250
    state = IBState(
        seed=Decimal("10000"),
        params=IBParams(T=40),
        calendar_round=10,
        effective_round=Decimal("39.40"),
        total_invested=total,
        avg_price=Decimal("60.00"),
        shares_held=Decimal("30.00"),
    )
    market = MarketData(ticker="TQQQ", prev_close=Decimal("58.00"), current_price=Decimal("59.00"))
    guide  = generate_ib_guide(state, market)
    assert any("잔여 예산" in m for m in guide.messages)
    assert guide.remaining_budget == Decimal("150.00")


# ── 후반전 가이드 ─────────────────────────────────────────────────────────────

def test_second_half_condition_met():
    state  = _make_state(eff_rnd="25", avg="65.00", held="20.00")
    market = MarketData(ticker="TQQQ", prev_close=Decimal("63.00"), current_price=Decimal("63.50"))
    guide  = generate_ib_guide(state, market)

    assert guide.phase == IBPhase.SECOND_HALF
    assert len(guide.buy_orders) == 1
    assert guide.buy_orders[0].label == "후반전 LOC"


def test_second_half_always_loc():
    # A ≤ C 상황에서도 후반전 LOC 주문이 생성되어야 함
    state  = _make_state(eff_rnd="25", avg="60.00", held="20.00")
    market = MarketData(ticker="TQQQ", prev_close=Decimal("63.00"), current_price=Decimal("63.50"))
    guide  = generate_ib_guide(state, market)

    assert guide.phase == IBPhase.SECOND_HALF
    assert len(guide.buy_orders) == 1
    assert guide.buy_orders[0].label == "후반전 LOC"
    assert guide.buy_orders[0].price == Decimal("60.00")


# ── 40회차 소진 ───────────────────────────────────────────────────────────────

def test_exhausted_phase():
    state  = _make_state(eff_rnd="41", avg="50.00", held="50.00")
    market = MarketData(ticker="TQQQ", prev_close=Decimal("48.00"), current_price=Decimal("49.00"))
    guide  = generate_ib_guide(state, market)

    assert guide.phase == IBPhase.EXHAUSTED
    assert len(guide.buy_orders) == 0
    assert any("소진" in m for m in guide.messages)
    assert guide.sell_order.price == (Decimal("50.00") * Decimal("1.10")).quantize(Decimal("0.01"))


# ── 1회차 (평단가 없음) ───────────────────────────────────────────────────────

def test_first_round_no_avg():
    state = IBState(
        seed=Decimal("4000"), params=IBParams(T=40),
        calendar_round=0, effective_round=Decimal("0"),
        total_invested=Decimal("0"),
        avg_price=Decimal("0"), shares_held=Decimal("0"),
    )
    market = MarketData(ticker="TQQQ", prev_close=Decimal("61.20"), current_price=Decimal("61.00"))
    guide  = generate_ib_guide(state, market)

    assert guide.buy_orders[0].price == Decimal("61.20")  # 평단 없으면 전일종가 대체
