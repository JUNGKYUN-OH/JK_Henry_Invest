"""서비스 계층 — Repository, Strategy Engine, Market을 조율한다."""

import json
from datetime import date
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa

from jkhenry.domain.models import IBDailyGuide, IBParams, IBState, MarketData, VRGuide, VRParams, VRState
from jkhenry.market.price_provider import get_price_data
from jkhenry.repository.db import get_engine, get_session, init_db
from jkhenry.repository.repositories import (
    complete_cycle,
    create_cycle,
    create_trade,
    create_vr_period,
    get_active_cycle,
    get_all_cycles,
    get_all_portfolios,
    get_all_vr_periods,
    get_latest_vr_period,
    get_portfolio,
    get_trades_by_cycle,
    get_trades_by_portfolio,
    loss_cut_cycle,
)
from jkhenry.strategies.infinite_buying import (
    compute_avg_price,
    compute_calendar_round,
    compute_effective_round,
    compute_shares_held,
    compute_total_invested,
    compute_unit,
    generate_ib_guide,
)
from jkhenry.strategies.value_rebalancing import compute_evaluation, generate_vr_guide


class GuideService:

    def __init__(self, engine: Optional[sa.Engine] = None):
        self._engine = engine or init_db()

    # ── 공통 ──────────────────────────────────────────────────────────────────

    def list_portfolios(self, status: str = "active") -> list:
        with get_session(self._engine) as s:
            return get_all_portfolios(s, status=status)

    def get_portfolio(self, portfolio_id: int):
        with get_session(self._engine) as s:
            return get_portfolio(s, portfolio_id)

    # ── IB (Infinite Buying) ──────────────────────────────────────────────────

    def get_ib_snapshot(self, portfolio_id: int) -> dict:
        """IB 포트폴리오의 현재 상태(회차, 평단가, 보유수량 등)를 반환."""
        with get_session(self._engine) as s:
            portfolio = get_portfolio(s, portfolio_id)
            cycle = get_active_cycle(s, portfolio_id)
            trades = get_trades_by_cycle(s, cycle.id) if cycle else []

        params = IBParams(**{k: Decimal(str(v)) if isinstance(v, str) else v
                             for k, v in json.loads(portfolio.params).items()})
        seed   = Decimal(str(portfolio.seed_capital))
        unit   = compute_unit(seed, params.T)

        avg_price       = compute_avg_price(trades)
        shares_held     = compute_shares_held(trades)
        total_invested  = compute_total_invested(trades)
        calendar_round  = compute_calendar_round(trades)
        effective_round = compute_effective_round(trades, unit)

        return {
            "portfolio":       portfolio,
            "cycle":           cycle,
            "trades":          trades,
            "avg_price":       avg_price,
            "shares_held":     shares_held,
            "total_invested":  total_invested,
            "calendar_round":  calendar_round,
            "effective_round": effective_round,
            "unit":            unit,
            "params":          params,
        }

    def generate_ib_daily_guide(self, portfolio_id: int,
                                manual_prev_close: Optional[Decimal] = None,
                                manual_current: Optional[Decimal] = None) -> IBDailyGuide:
        snap = self.get_ib_snapshot(portfolio_id)
        portfolio = snap["portfolio"]
        params: IBParams = snap["params"]

        price_data = get_price_data(portfolio.ticker)
        prev_close = manual_prev_close or (Decimal(str(price_data["prev_close"])) if price_data else Decimal("0"))
        current_price = manual_current or (Decimal(str(price_data["current"])) if price_data else Decimal("0"))

        state = IBState(
            seed=Decimal(str(portfolio.seed_capital)),
            params=params,
            calendar_round=snap["calendar_round"],
            effective_round=snap["effective_round"],
            total_invested=snap["total_invested"],
            avg_price=snap["avg_price"],
            shares_held=snap["shares_held"],
        )
        market = MarketData(ticker=portfolio.ticker, prev_close=prev_close, current_price=current_price)
        return generate_ib_guide(state, market)

    def record_ib_trade(self, portfolio_id: int, *, trade_date: date, side: str,
                        order_type: str, shares: Decimal, price: Decimal,
                        note: str = "") -> None:
        with get_session(self._engine) as s:
            cycle = get_active_cycle(s, portfolio_id)
            if not cycle:
                cycle = create_cycle(s, portfolio_id=portfolio_id, cycle_num=1, start_date=trade_date)

            trade = create_trade(
                s,
                portfolio_id=portfolio_id,
                cycle_id=cycle.id,
                trade_date=trade_date,
                side=side,
                order_type=order_type,
                shares=shares,
                price=price,
                note=note,
            )

            # 매도 체결로 보유수량이 0이 되면 사이클 종료
            if side == "SELL":
                all_trades = get_trades_by_cycle(s, cycle.id)
                remaining = compute_shares_held(all_trades)
                if remaining <= Decimal("0"):
                    total_invested = sum((Decimal(str(t.amount)) for t in all_trades if t.side == "BUY"), Decimal("0"))
                    sell_amount = sum((Decimal(str(t.amount)) for t in all_trades if t.side == "SELL"), Decimal("0"))
                    profit = sell_amount - total_invested
                    rate = (profit / total_invested).quantize(Decimal("0.0001")) if total_invested > 0 else Decimal("0")
                    complete_cycle(s, cycle.id, realized_profit=profit, profit_rate=rate)
                    # 다음 사이클 자동 생성
                    all_c = get_all_cycles(s, portfolio_id)
                    create_cycle(s, portfolio_id=portfolio_id, cycle_num=len(all_c) + 1, start_date=date.today())
            s.commit()

    def manual_loss_cut(self, portfolio_id: int, *, trade_date: date,
                        shares: Decimal, price: Decimal) -> None:
        with get_session(self._engine) as s:
            cycle = get_active_cycle(s, portfolio_id)
            if not cycle:
                return
            create_trade(s, portfolio_id=portfolio_id, cycle_id=cycle.id,
                         trade_date=trade_date, side="SELL", order_type="MARKET",
                         shares=shares, price=price, note="손절")
            all_trades = get_trades_by_cycle(s, cycle.id)
            total_invested = sum((Decimal(str(t.amount)) for t in all_trades if t.side == "BUY"), Decimal("0"))
            sell_amount = sum((Decimal(str(t.amount)) for t in all_trades if t.side == "SELL"), Decimal("0"))
            profit = sell_amount - total_invested
            rate = (profit / total_invested).quantize(Decimal("0.0001")) if total_invested > 0 else Decimal("0")
            loss_cut_cycle(s, cycle.id, realized_profit=profit, profit_rate=rate)
            all_c = get_all_cycles(s, portfolio_id)
            create_cycle(s, portfolio_id=portfolio_id, cycle_num=len(all_c) + 1, start_date=date.today())
            s.commit()

    # ── VR (Value Rebalancing) ────────────────────────────────────────────────

    def get_vr_snapshot(self, portfolio_id: int) -> dict:
        """VR 포트폴리오의 현재 상태를 반환."""
        with get_session(self._engine) as s:
            portfolio = get_portfolio(s, portfolio_id)
            latest_period = get_latest_vr_period(s, portfolio_id)
            trades = get_trades_by_portfolio(s, portfolio_id)

        raw_params = json.loads(portfolio.params)
        params = VRParams(
            G=Decimal(str(raw_params.get("G", "0.005"))),
            band_upper=Decimal(str(raw_params.get("band_upper", "0.20"))),
            band_lower=Decimal(str(raw_params.get("band_lower", "0.20"))),
            period_days=int(raw_params.get("period_days", 7)),
        )
        v_target = (Decimal(str(latest_period.v_next))
                    if latest_period else Decimal(str(raw_params.get("v_initial", "0"))))
        cash_balance = Decimal(str(raw_params.get("cash_balance", "0")))
        shares_held = compute_shares_held(trades)

        return {
            "portfolio": portfolio,
            "latest_period": latest_period,
            "params": params,
            "v_target": v_target,
            "cash_balance": cash_balance,
            "shares_held": shares_held,
        }

    def generate_vr_guide(self, portfolio_id: int,
                          manual_current: Optional[Decimal] = None) -> VRGuide:
        snap = self.get_vr_snapshot(portfolio_id)
        portfolio = snap["portfolio"]

        price_data = get_price_data(portfolio.ticker)
        current_price = manual_current or (Decimal(str(price_data["current"])) if price_data else Decimal("0"))

        state = VRState(
            params=snap["params"],
            v_target=snap["v_target"],
            cash_balance=snap["cash_balance"],
            shares_held=snap["shares_held"],
        )
        market = MarketData(ticker=portfolio.ticker, prev_close=current_price, current_price=current_price)
        return generate_vr_guide(state, market)

    def record_vr_rebalance(self, portfolio_id: int, *, period_date: date,
                            action: str, shares: Decimal, price: Decimal,
                            e_value: Decimal, v_target: Decimal, v_next: Decimal,
                            cash_balance_after: Decimal) -> None:
        with get_session(self._engine) as s:
            portfolio = get_portfolio(s, portfolio_id)
            raw_params = json.loads(portfolio.params)

            if action in ("BUY", "SELL"):
                side = action
                create_trade(s, portfolio_id=portfolio_id, cycle_id=None,
                             trade_date=period_date, side=side, order_type="LIMIT",
                             shares=shares, price=price)

            all_p = get_all_vr_periods(s, portfolio_id)
            create_vr_period(
                s,
                portfolio_id=portfolio_id,
                period_num=len(all_p) + 1,
                period_date=period_date,
                v_target=v_target,
                cash_balance=cash_balance_after,
                e_value=e_value,
                action=action,
                v_next=v_next,
            )

            raw_params["cash_balance"] = str(cash_balance_after)
            portfolio.params = json.dumps(raw_params)
            s.commit()

    # ── 통계 ──────────────────────────────────────────────────────────────────

    def get_ib_statistics(self, portfolio_id: int) -> dict:
        with get_session(self._engine) as s:
            cycles = get_all_cycles(s, portfolio_id)

        finished = [c for c in cycles if c.status in ("completed", "loss_cut")]
        wins = [c for c in finished if c.status == "completed"]
        total_profit = sum((Decimal(str(c.realized_profit)) for c in finished if c.realized_profit), Decimal("0"))

        return {
            "total_cycles": len(finished),
            "win_cycles": len(wins),
            "win_rate": len(wins) / len(finished) if finished else Decimal("0"),
            "total_profit": total_profit,
            "cycles": finished,
        }

    def get_journal(self, portfolio_id: Optional[int] = None,
                    from_date: Optional[date] = None,
                    to_date: Optional[date] = None) -> list:
        with get_session(self._engine) as s:
            portfolios = get_all_portfolios(s, status="active") if portfolio_id is None else [get_portfolio(s, portfolio_id)]
            result = []
            for p in portfolios:
                result.extend(get_trades_by_portfolio(s, p.id, from_date=from_date, to_date=to_date))
        result.sort(key=lambda t: (t.trade_date, t.id), reverse=True)
        return result
