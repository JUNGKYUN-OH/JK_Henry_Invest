"""체결 기록 입력 페이지."""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import streamlit as st

from jkhenry.repository.db import init_db
from jkhenry.services.guide_service import GuideService
from jkhenry.ui.components import fmt_usd, strategy_badge
from jkhenry.ui.style import gap, inject_css, order_card, page_header, render_sidebar, require_auth, section_label

st.set_page_config(page_title="체결 입력", page_icon="✏️", layout="centered",
                   initial_sidebar_state="expanded")
inject_css()
render_sidebar()
require_auth()
init_db()

page_header("✏️", "체결 기록 입력", "미체결 건은 입력하지 않습니다 — 해당 날짜 회차가 유지됩니다.")

svc = GuideService()
portfolios = svc.list_portfolios()

if not portfolios:
    st.info("포트폴리오가 없습니다.")
    st.stop()

selected = st.selectbox(
    "포트폴리오",
    portfolios,
    format_func=lambda p: f"{p.ticker} [{strategy_badge(p.strategy)}] — {p.name}",
)

if not selected:
    st.stop()

# ── 현재 상태 표시 ─────────────────────────────────────────────────────────────
if selected.strategy == "IB":
    with st.container(border=True):
        section_label("현재 상태")
        snap = svc.get_ib_snapshot(selected.id)
        c1, c2, c3 = st.columns(3)
        c1.metric("유효 회차", f"{float(snap['effective_round']):.1f} / {snap['params'].half_round * 2}",
                  help="자금 소진 기준 (진행일: " + str(snap['calendar_round']) + "일)")
        c2.metric("평단가", fmt_usd(snap["avg_price"]))
        c3.metric("보유 수량", f"{float(snap['shares_held']):.2f}주")

# ── 오늘 가이드 기반 기본값 산출 ──────────────────────────────────────────────
def_price = 0.01
def_shares = 0.01

if selected.strategy == "IB":
    try:
        _guide = svc.generate_ib_daily_guide(selected.id)
        if _guide.buy_orders:
            def_price  = max(float(_guide.buy_orders[0].price),  0.01)
            def_shares = max(float(_guide.buy_orders[0].shares), 0.01)
    except Exception:
        pass

st.divider()

# ── 체결 입력 폼 ───────────────────────────────────────────────────────────────
with st.container(border=True):
    section_label("체결 내역 입력")
    with st.form("trade_form"):
        col1, col2 = st.columns(2)
        with col1:
            trade_date = st.date_input("체결일", value=date.today())
            side = st.radio("구분", ["BUY (매수)", "SELL (매도)"])
            side_code = "BUY" if side.startswith("BUY") else "SELL"
        with col2:
            order_type = st.selectbox("주문 유형", ["LOC", "LIMIT", "MARKET"])
            shares = st.number_input("체결 수량 (주)", min_value=0.01, value=def_shares, step=0.01, format="%.2f")
            price = st.number_input("체결 단가 (USD)", min_value=0.01, value=def_price, step=0.01, format="%.4f")
            note = st.text_input("메모 (선택)")

        amount = Decimal(str(shares)) * Decimal(str(price))
        st.caption(f"체결 금액 (자동): {fmt_usd(amount)}")

        submitted = st.form_submit_button("저장", type="primary", use_container_width=True)

if submitted:
    if shares <= 0 or price <= 0:
        st.error("수량과 단가를 입력해 주세요.")
    else:
        try:
            svc.record_ib_trade(
                selected.id,
                trade_date=trade_date,
                side=side_code,
                order_type=order_type,
                shares=Decimal(str(shares)),
                price=Decimal(str(price)),
                note=note,
            )
            st.success("✅ 체결 기록이 저장되었습니다.")

            # ── 1. 저장된 체결 요약 카드 ───────────────────────────────────────
            with st.container(border=True):
                section_label("저장된 체결")
                order_card(
                    label=f"{selected.ticker} · {trade_date}",
                    price=price,
                    shares=shares,
                    amount=amount,
                    order_type=order_type,
                    side=side_code,
                )
                if note:
                    st.caption(f"💬 {note}")

            # ── 2. IB 갱신 상태 ────────────────────────────────────────────────
            if selected.strategy == "IB":
                snap = svc.get_ib_snapshot(selected.id)
                with st.container(border=True):
                    section_label("저장 후 상태")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("갱신 유효 회차", f"{float(snap['effective_round']):.1f}")
                    c2.metric("갱신 평단가", fmt_usd(snap["avg_price"]))
                    c3.metric("갱신 보유수량", f"{float(snap['shares_held']):.2f}주")

            # ── 3. 최근 체결 내역 ──────────────────────────────────────────────
            recent = svc.get_journal(portfolio_id=selected.id)[:5]
            if recent:
                with st.container(border=True):
                    section_label(f"최근 체결 내역 — {selected.ticker}")
                    rows = [
                        {
                            "날짜": str(t.trade_date),
                            "구분": "📥 매수" if t.side == "BUY" else "📤 매도",
                            "유형": t.order_type,
                            "수량(주)": f"{float(t.shares):.2f}",
                            "단가(USD)": f"${float(t.price):.4f}",
                            "금액(USD)": f"${float(t.amount):.2f}",
                            "메모": t.note or "",
                        }
                        for t in recent
                    ]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"저장 실패: {e}")
