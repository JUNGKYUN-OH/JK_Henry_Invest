"""체결 기록 입력 페이지."""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st

from jkhenry.repository.db import init_db
from jkhenry.services.guide_service import GuideService
from jkhenry.ui.components import fmt_usd, strategy_badge
from jkhenry.ui.style import inject_css, render_sidebar

st.set_page_config(page_title="체결 입력", page_icon="✏️", layout="centered",
                   initial_sidebar_state="expanded")
inject_css()
render_sidebar()
init_db()

st.title("✏️ 체결 기록 입력")
st.caption("미체결 건은 입력하지 않습니다 — 해당 날짜 회차가 유지됩니다.")

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

# 현재 상태 표시
if selected.strategy == "IB":
    snap = svc.get_ib_snapshot(selected.id)
    c1, c2, c3 = st.columns(3)
    c1.metric("유효 회차", f"{float(snap['effective_round']):.1f} / {snap['params'].half_round * 2}",
              help="자금 소진 기준 (진행일: " + str(snap['calendar_round']) + "일)")
    c2.metric("평단가", fmt_usd(snap["avg_price"]))
    c3.metric("보유 수량", f"{float(snap['shares_held']):.2f}주")

st.divider()

with st.form("trade_form"):
    col1, col2 = st.columns(2)
    with col1:
        trade_date = st.date_input("체결일", value=date.today())
        side = st.radio("구분", ["BUY (매수)", "SELL (매도)"])
        side_code = "BUY" if side.startswith("BUY") else "SELL"
    with col2:
        order_type = st.selectbox("주문 유형", ["LOC", "LIMIT", "MARKET"])
        shares = st.number_input("체결 수량 (주)", min_value=0.01, step=0.01, format="%.2f")
        price = st.number_input("체결 단가 (USD)", min_value=0.01, step=0.01, format="%.4f")
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

            if selected.strategy == "IB":
                snap = svc.get_ib_snapshot(selected.id)
                c1, c2, c3 = st.columns(3)
                c1.metric("갱신 유효 회차", f"{float(snap['effective_round']):.1f}")
                c2.metric("갱신 평단가", fmt_usd(snap["avg_price"]))
                c3.metric("갱신 보유수량", f"{float(snap['shares_held']):.2f}주")
        except Exception as e:
            st.error(f"저장 실패: {e}")
