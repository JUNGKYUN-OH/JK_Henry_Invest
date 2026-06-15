"""IB (Infinite Buying) — 무한매수법 V2.2 계산 엔진.

순수 함수로만 구성. DB·네트워크 접근 없음.
같은 입력 → 항상 같은 출력 보장.

[방안 B] 유효 회차 = 누적 매수금 / 1 unit (자금 소진 비례)
전반전/후반전 판별과 남은 예산 제한에 유효 회차를 사용한다.
"""

from decimal import ROUND_DOWN, Decimal

from jkhenry.domain.enums import IBPhase, OrderType, Side
from jkhenry.domain.models import IBDailyGuide, IBParams, IBState, MarketData, OrderGuide


def compute_unit(seed: Decimal, T: int) -> Decimal:
    """1회 매수금 U = seed / T, 소수 둘째 자리 내림."""
    return (seed / Decimal(T)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def compute_avg_price(trades: list) -> Decimal:
    """평단가 A = Σ(매수 amount) / Σ(매수 shares). 매수 없으면 0."""
    buy_amount = sum((Decimal(str(t.amount)) for t in trades if t.side == Side.BUY), Decimal("0"))
    buy_shares = sum((Decimal(str(t.shares)) for t in trades if t.side == Side.BUY), Decimal("0"))
    if buy_shares == Decimal("0"):
        return Decimal("0")
    return (buy_amount / buy_shares).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)


def compute_shares_held(trades: list) -> Decimal:
    """보유 수량 = Σ매수 shares − Σ매도 shares."""
    bought = sum((Decimal(str(t.shares)) for t in trades if t.side == Side.BUY), Decimal("0"))
    sold   = sum((Decimal(str(t.shares)) for t in trades if t.side == Side.SELL), Decimal("0"))
    return (bought - sold).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def compute_calendar_round(trades: list) -> int:
    """진행 일수 = 매수 체결이 있는 고유 날짜 수."""
    buy_dates = {t.trade_date for t in trades if t.side == Side.BUY}
    return len(buy_dates)


# 하위 호환 alias
compute_round = compute_calendar_round


def compute_total_invested(trades: list) -> Decimal:
    """실제 누적 매수금 = 매수 체결 금액 합계."""
    return sum((Decimal(str(t.amount)) for t in trades if t.side == Side.BUY), Decimal("0"))


def compute_effective_round(trades: list, unit: Decimal) -> Decimal:
    """
    유효 회차 = 누적 매수금 / 1 unit (자금 소진 비례).

    하루에 2 unit을 샀으면 유효 회차 +2.
    하루에 0.5 unit을 샀으면 유효 회차 +0.5.
    """
    if unit <= Decimal("0"):
        return Decimal("0")
    total = compute_total_invested(trades)
    return (total / unit).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def determine_phase(effective_round: Decimal, params: IBParams) -> IBPhase:
    """전반전 / 후반전 / 40회차소진 판별 — 유효 회차(자금 기준) 사용."""
    half     = Decimal(str(params.half_round))
    max_rnd  = Decimal(str(params.half_round * 2))
    if effective_round > max_rnd:
        return IBPhase.EXHAUSTED
    if effective_round <= half:
        return IBPhase.FIRST_HALF
    return IBPhase.SECOND_HALF


def _floor_shares(amount: Decimal, price: Decimal) -> Decimal:
    """수량 = amount / price, 소수 둘째 자리 내림."""
    if price == Decimal("0"):
        return Decimal("0")
    return (amount / price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def generate_ib_guide(state: IBState, market: MarketData) -> IBDailyGuide:
    """
    오늘의 IB (Infinite Buying) 매수/매도 가이드를 계산한다.

    [핵심 변경 — 방안 B]
    - 전반전/후반전 판별: 유효 회차(자금 소진 기준) 사용
    - 오늘 매수 가능 금액: min(1 unit, 잔여 예산) 으로 자동 제한
      → 과거에 1 unit 초과 매수 시 다음 가이드 금액이 자동으로 줄어듦

    전반전: 작은수 LOC(평단가, 0.5U_today) + 큰수 LOC(종가×1.15, 0.5U_today)
    후반전: 평단가 > 전일종가 조건 충족 시 평단 LOC U_today 올인
    40회차소진: 매도 After 지정가 안내만
    항상: 매도 After 지정가 (평단×1.10, 보유 전량)
    """
    params = state.params
    U      = compute_unit(state.seed, params.T)
    phase  = determine_phase(state.effective_round, params)

    # 잔여 예산 계산 (초과 매수 시 자동 제한)
    remaining = (state.seed - state.total_invested).quantize(Decimal("0.01"))
    remaining = max(remaining, Decimal("0"))

    # 오늘 실제 사용 가능한 금액 (잔여 예산이 1 unit보다 적으면 잔여 예산으로 제한)
    U_today = min(U, remaining)

    C = market.prev_close
    A = state.avg_price if state.avg_price > Decimal("0") else C  # 1회차: 평단 = 전일 종가

    buy_orders: list[OrderGuide] = []
    messages: list[str] = []

    # 잔여 예산 부족 경고
    if Decimal("0") < remaining < U:
        messages.append(
            f"잔여 예산 ${remaining:.2f} — 1 unit(${U:.2f})보다 적습니다. "
            f"오늘 가이드는 잔여 예산 기준으로 계산됩니다."
        )

    if phase == IBPhase.FIRST_HALF:
        if U_today > Decimal("0"):
            half_U = (U_today * Decimal("0.5")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

            # 작은수 LOC: 평단가, 0.5U_today
            small_price  = A.quantize(Decimal("0.01"))
            small_shares = _floor_shares(half_U, small_price)
            buy_orders.append(OrderGuide(
                label="작은수 LOC",
                price=small_price,
                shares=small_shares,
                amount=(small_shares * small_price).quantize(Decimal("0.01")),
                order_type=OrderType.LOC,
            ))

            # 큰수 LOC: 전일종가 × 배율, 0.5U_today
            big_price  = (C * params.buy_high_multiplier).quantize(Decimal("0.01"))
            big_shares = _floor_shares(half_U, big_price)
            buy_orders.append(OrderGuide(
                label="큰수 LOC",
                price=big_price,
                shares=big_shares,
                amount=(big_shares * big_price).quantize(Decimal("0.01")),
                order_type=OrderType.LOC,
            ))

        if state.effective_round >= Decimal(str(params.half_round)):
            messages.append(f"유효 회차 {state.effective_round:.1f} — 곧 후반전 전환")

    elif phase == IBPhase.SECOND_HALF:
        if U_today > Decimal("0"):
            shares = _floor_shares(U_today, A)
            buy_orders.append(OrderGuide(
                label="후반전 LOC",
                price=A.quantize(Decimal("0.01")),
                shares=shares,
                amount=(shares * A).quantize(Decimal("0.01")),
                order_type=OrderType.LOC,
            ))

    elif phase == IBPhase.EXHAUSTED:
        messages.append("40회차 소진 — 매도 After 지정가를 체결될 때까지 매일 유지하세요 (영혼의 After 지정가).")

    # 매도 After 지정가: 항상 계산 (평단+목표수익률, 전량)
    sell_price  = (A * (Decimal("1") + params.sell_target_pct)).quantize(Decimal("0.01"))
    sell_shares = state.shares_held.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    sell_order  = OrderGuide(
        label="매도 After 지정가",
        price=sell_price,
        shares=sell_shares,
        amount=(sell_shares * sell_price).quantize(Decimal("0.01")),
        order_type=OrderType.AFTER_LIMIT,
    )

    # 목표가 근접 알림 (5% 이내)
    if market.current_price > Decimal("0") and sell_price > Decimal("0"):
        gap_pct = (sell_price - market.current_price) / sell_price * Decimal("100")
        if Decimal("0") <= gap_pct <= Decimal("5"):
            messages.append(f"목표가까지 {gap_pct:.1f}% 남음 — 매도 After 지정가를 꼭 유지하세요!")

    return IBDailyGuide(
        phase=phase,
        calendar_round=state.calendar_round,
        effective_round=state.effective_round,
        remaining_budget=remaining,
        unit=U,
        buy_orders=buy_orders,
        sell_order=sell_order,
        messages=messages,
    )
