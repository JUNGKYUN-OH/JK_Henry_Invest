"""CRUD 함수. 비즈니스 로직 없음, SQL 조작만."""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from jkhenry.repository.db import CycleModel, PortfolioModel, TradeModel, VrPeriodModel


# ── Portfolio ─────────────────────────────────────────────────────────────────

def create_portfolio(session: Session, *, name: str, ticker: str, strategy: str,
                     seed_capital: Decimal, params: dict, status: str = "active") -> PortfolioModel:
    row = PortfolioModel(
        name=name,
        ticker=ticker.upper(),
        strategy=strategy,
        seed_capital=seed_capital,
        params=json.dumps(params),
        status=status,
        created_at=datetime.now().isoformat(),
    )
    session.add(row)
    session.flush()
    return row


def get_all_portfolios(session: Session, status: str = "active") -> list[PortfolioModel]:
    return session.query(PortfolioModel).filter_by(status=status).order_by(PortfolioModel.id).all()


def get_portfolio(session: Session, portfolio_id: int) -> Optional[PortfolioModel]:
    return session.get(PortfolioModel, portfolio_id)


def update_portfolio_status(session: Session, portfolio_id: int, status: str) -> None:
    row = session.get(PortfolioModel, portfolio_id)
    if row:
        row.status = status
        session.flush()


def update_portfolio(session: Session, portfolio_id: int, *,
                     name: str, params: dict) -> None:
    row = session.get(PortfolioModel, portfolio_id)
    if row:
        row.name = name
        row.params = json.dumps(params)
        session.flush()


def update_portfolio_params(session: Session, portfolio_id: int, params: dict) -> None:
    row = session.get(PortfolioModel, portfolio_id)
    if row:
        row.params = json.dumps(params)
        session.flush()


def delete_portfolio(session: Session, portfolio_id: int) -> None:
    """포트폴리오와 연관된 모든 데이터(trade, cycle, vr_period)를 삭제한다."""
    from jkhenry.repository.db import CycleModel, TradeModel, VrPeriodModel
    session.query(TradeModel).filter_by(portfolio_id=portfolio_id).delete()
    session.query(CycleModel).filter_by(portfolio_id=portfolio_id).delete()
    session.query(VrPeriodModel).filter_by(portfolio_id=portfolio_id).delete()
    row = session.get(PortfolioModel, portfolio_id)
    if row:
        session.delete(row)
    session.flush()


# ── Cycle (IB 전용) ───────────────────────────────────────────────────────────

def create_cycle(session: Session, *, portfolio_id: int, cycle_num: int,
                 start_date: date) -> CycleModel:
    row = CycleModel(
        portfolio_id=portfolio_id,
        cycle_num=cycle_num,
        start_date=start_date.isoformat(),
        status="active",
        created_at=datetime.now().isoformat(),
    )
    session.add(row)
    session.flush()
    return row


def get_active_cycle(session: Session, portfolio_id: int) -> Optional[CycleModel]:
    return (session.query(CycleModel)
            .filter_by(portfolio_id=portfolio_id, status="active")
            .first())


def get_all_cycles(session: Session, portfolio_id: int) -> list[CycleModel]:
    return (session.query(CycleModel)
            .filter_by(portfolio_id=portfolio_id)
            .order_by(CycleModel.cycle_num)
            .all())


def complete_cycle(session: Session, cycle_id: int,
                   realized_profit: Decimal, profit_rate: Decimal) -> None:
    row = session.get(CycleModel, cycle_id)
    if row:
        row.status = "completed"
        row.end_date = date.today().isoformat()
        row.realized_profit = realized_profit
        row.profit_rate = profit_rate
        session.flush()


def loss_cut_cycle(session: Session, cycle_id: int,
                   realized_profit: Decimal, profit_rate: Decimal) -> None:
    row = session.get(CycleModel, cycle_id)
    if row:
        row.status = "loss_cut"
        row.end_date = date.today().isoformat()
        row.realized_profit = realized_profit
        row.profit_rate = profit_rate
        session.flush()


# ── Trade ─────────────────────────────────────────────────────────────────────

def create_trade(session: Session, *, portfolio_id: int, cycle_id: Optional[int],
                 trade_date: date, side: str, order_type: str,
                 shares: Decimal, price: Decimal, note: str = "") -> TradeModel:
    amount = (shares * price).quantize(Decimal("0.01"))
    row = TradeModel(
        portfolio_id=portfolio_id,
        cycle_id=cycle_id,
        trade_date=trade_date.isoformat(),
        side=side,
        order_type=order_type,
        shares=shares,
        price=price,
        amount=amount,
        note=note or None,
        created_at=datetime.now().isoformat(),
    )
    session.add(row)
    session.flush()
    return row


def get_trades_by_cycle(session: Session, cycle_id: int) -> list[TradeModel]:
    return (session.query(TradeModel)
            .filter_by(cycle_id=cycle_id)
            .order_by(TradeModel.trade_date, TradeModel.id)
            .all())


def get_trades_by_portfolio(session: Session, portfolio_id: int,
                            from_date: Optional[date] = None,
                            to_date: Optional[date] = None) -> list[TradeModel]:
    q = session.query(TradeModel).filter_by(portfolio_id=portfolio_id)
    if from_date:
        q = q.filter(TradeModel.trade_date >= from_date.isoformat())
    if to_date:
        q = q.filter(TradeModel.trade_date <= to_date.isoformat())
    return q.order_by(TradeModel.trade_date.desc(), TradeModel.id.desc()).all()


def get_trade(session: Session, trade_id: int) -> Optional[TradeModel]:
    return session.get(TradeModel, trade_id)


def update_trade(session: Session, trade_id: int, *,
                 trade_date: date, side: str, order_type: str,
                 shares: Decimal, price: Decimal, note: str = "") -> None:
    row = session.get(TradeModel, trade_id)
    if row:
        row.trade_date = trade_date.isoformat()
        row.side = side
        row.order_type = order_type
        row.shares = shares
        row.price = price
        row.amount = (shares * price).quantize(Decimal("0.01"))
        row.note = note or None
        session.flush()


def delete_trade(session: Session, trade_id: int) -> None:
    row = session.get(TradeModel, trade_id)
    if row:
        session.delete(row)
        session.flush()


# ── VrPeriod ──────────────────────────────────────────────────────────────────

def create_vr_period(session: Session, *, portfolio_id: int, period_num: int,
                     period_date: date, v_target: Decimal, cash_balance: Decimal,
                     v_next: Decimal, e_value: Optional[Decimal] = None,
                     action: Optional[str] = None) -> VrPeriodModel:
    row = VrPeriodModel(
        portfolio_id=portfolio_id,
        period_num=period_num,
        period_date=period_date.isoformat(),
        v_target=v_target,
        cash_balance=cash_balance,
        e_value=e_value,
        action=action,
        v_next=v_next,
        created_at=datetime.now().isoformat(),
    )
    session.add(row)
    session.flush()
    return row


def get_latest_vr_period(session: Session, portfolio_id: int) -> Optional[VrPeriodModel]:
    return (session.query(VrPeriodModel)
            .filter_by(portfolio_id=portfolio_id)
            .order_by(VrPeriodModel.period_num.desc())
            .first())


def get_all_vr_periods(session: Session, portfolio_id: int) -> list[VrPeriodModel]:
    return (session.query(VrPeriodModel)
            .filter_by(portfolio_id=portfolio_id)
            .order_by(VrPeriodModel.period_num)
            .all())


def update_vr_period_cash(session: Session, portfolio_id: int, delta: Decimal) -> None:
    """현금 잔고를 delta만큼 조정 (매수: 음수, 매도: 양수, 수동 조정: 임의)."""
    portfolio = session.get(PortfolioModel, portfolio_id)
    if not portfolio:
        return
    params = json.loads(portfolio.params)
    current_cash = Decimal(str(params.get("cash_balance", "0")))
    params["cash_balance"] = str(current_cash + delta)
    portfolio.params = json.dumps(params)
    session.flush()
