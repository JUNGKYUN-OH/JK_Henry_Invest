"""IB (Infinite Buying) 매매 가이드 페이지."""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st

from jkhenry.repository.db import init_db
from jkhenry.services.guide_service import GuideService
from jkhenry.ui.components import fmt_usd, order_table, show_price_alert, strategy_badge
from jkhenry.ui.style import gap, inject_css, page_header, render_sidebar, require_auth, section_label, status_banner

st.set_page_config(page_title="IB 가이드", page_icon="📈", layout="centered",
                   initial_sidebar_state="expanded")
inject_css()
render_sidebar()
require_auth()
init_db()

page_header("📈", "IB 가이드", "Infinite Buying 매매 가이드")

svc = GuideService()
portfolios = [p for p in svc.list_portfolios() if p.strategy == "IB"]

if not portfolios:
    st.info("IB 포트폴리오가 없습니다.")
    st.page_link("pages/1_포트폴리오_생성.py", label="포트폴리오 생성하기")
    st.stop()

selected = st.selectbox("포트폴리오 선택", portfolios, format_func=lambda p: f"{p.ticker} — {p.name}")

if not selected:
    st.stop()

snap    = svc.get_ib_snapshot(selected.id)
avg     = snap["avg_price"]
eff_rnd = snap["effective_round"]
cal_rnd = snap["calendar_round"]
params  = snap["params"]
shares  = snap["shares_held"]

# ── 시세 조회 ──────────────────────────────────────────────────────────────────
with st.container(border=True):
    section_label(f"{selected.ticker} 시세")
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        from jkhenry.market.price_provider import get_price_data
        price_data = get_price_data(selected.ticker)
        if price_data:
            prev_close_val = float(price_data["prev_close"])
            current_val = float(price_data["current"])
            st.metric("전일 종가 (C)", f"${prev_close_val:.2f}")
            st.metric("현재가", f"${current_val:.2f}")
            manual_override = False
        else:
            st.warning("시세 조회 실패 — 수동 입력 모드")
            manual_override = True

    with col2:
        if manual_override:
            prev_close_val = st.number_input("전일 종가 (C) 직접 입력", min_value=0.01, step=0.01)
            current_val = st.number_input("현재가 직접 입력", min_value=0.01, step=0.01)

    with col3:
        gap(28)
        if st.button("🔄 시세 새로고침", use_container_width=True):
            from jkhenry.market.price_provider import clear_cache
            clear_cache()
            st.rerun()

prev_close = Decimal(str(round(prev_close_val, 4)))
current_price = Decimal(str(round(current_val, 4)))

# 가이드 계산
guide = svc.generate_ib_daily_guide(selected.id, manual_prev_close=prev_close, manual_current=current_price)

# ── 현재 상태 배너 ─────────────────────────────────────────────────────────────
with st.container(border=True):
    section_label("현재 상태")
    phase_color = {"전반전": "🟢", "후반전": "🟡", "40회차소진": "🔴"}
    icon = phase_color.get(guide.phase.value, "⚪")
    max_rnd = params.half_round * 2

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("단계", f"{icon} {guide.phase.value}")
    m2.metric("유효 회차", f"{float(eff_rnd):.1f}/{max_rnd}")
    m3.metric("평단가", fmt_usd(avg))
    m4.metric("보유 수량", f"{float(shares):.2f}주")

    gap(4)
    progress = min(float(eff_rnd) / max_rnd, 1.0) if max_rnd > 0 else 0.0
    st.progress(progress, text=f"잔여 예산 {fmt_usd(guide.remaining_budget)}")

show_price_alert(guide.messages)

# ── 주문 가이드 ────────────────────────────────────────────────────────────────
section_label("오늘의 주문 가이드")
left, right = st.columns(2)

with left:
    with st.container(border=True):
        st.markdown("<div style='font-size:0.8rem;font-weight:700;color:var(--buy);margin-bottom:6px;'>📥 매수 주문</div>",
                    unsafe_allow_html=True)
        if guide.buy_orders:
            order_table(guide.buy_orders)
            total_buy = sum(o.amount for o in guide.buy_orders)
            st.caption(f"합계: {fmt_usd(total_buy)} (= 1 unit)")
        else:
            st.info("오늘은 매수 주문 없음")

with right:
    with st.container(border=True):
        st.markdown("<div style='font-size:0.8rem;font-weight:700;color:var(--sell);margin-bottom:6px;'>📤 매도 After 지정가 (매일 유지)</div>",
                    unsafe_allow_html=True)
        sell = guide.sell_order
        if float(sell.shares) > 0:
            order_table([sell])
            if current_price > 0 and sell.price > 0:
                gap_pct = (sell.price - current_price) / sell.price * 100
                st.caption(f"현재가 {fmt_usd(current_price)} → 목표가까지 {float(gap_pct):.1f}% 남음")
        else:
            st.info("보유 수량 없음 — 매수 먼저 진행하세요")

st.divider()
st.page_link("pages/3_체결_입력.py", label="체결 기록 입력하기 →")
