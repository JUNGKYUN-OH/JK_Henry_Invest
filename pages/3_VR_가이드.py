"""VR (Value Rebalancing) 리밸런싱 가이드 페이지."""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st

from jkhenry.repository.db import init_db
from jkhenry.services.guide_service import GuideService
from jkhenry.ui.components import fmt_usd, order_table, show_price_alert
from jkhenry.ui.style import inject_css, render_sidebar

st.set_page_config(page_title="VR 가이드", page_icon="⚖️", layout="centered",
                   initial_sidebar_state="expanded")
inject_css()
render_sidebar()
init_db()

st.title("⚖️ VR (Value Rebalancing) 가이드")

svc = GuideService()
portfolios = [p for p in svc.list_portfolios() if p.strategy == "VR"]

if not portfolios:
    st.info("VR 포트폴리오가 없습니다.")
    st.page_link("pages/1_포트폴리오_생성.py", label="포트폴리오 생성하기")
    st.stop()

selected = st.selectbox("포트폴리오 선택", portfolios, format_func=lambda p: f"{p.ticker} — {p.name}")

if not selected:
    st.stop()

snap = svc.get_vr_snapshot(selected.id)

# 시세 조회
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    from jkhenry.market.price_provider import get_price_data
    price_data = get_price_data(selected.ticker)
    if price_data:
        current_val = float(price_data["current"])
        st.metric("현재가", f"${current_val:.2f}")
        manual_override = False
    else:
        st.warning("시세 조회 실패")
        manual_override = True

with col2:
    if manual_override:
        current_val = st.number_input("현재가 직접 입력", min_value=0.01, step=0.01)

with col3:
    if st.button("시세 새로고침"):
        from jkhenry.market.price_provider import clear_cache
        clear_cache()
        st.rerun()

current_price = Decimal(str(round(current_val, 4)))
guide = svc.generate_vr_guide(selected.id, manual_current=current_price)

# 핵심 지표 표시
st.subheader("📊 이번 주기 현황")
m1, m2, m3, m4 = st.columns(4)
m1.metric("목표값 V", fmt_usd(guide.v_target))
m2.metric("현금 잔고 C", fmt_usd(guide.cash_balance))
m3.metric("평가금액 E", fmt_usd(guide.e_value))
e_vs_v = (guide.e_value - guide.v_target) / guide.v_target * 100 if guide.v_target > 0 else Decimal("0")
sign = "+" if float(e_vs_v) >= 0 else ""
m4.metric("V 대비", f"{sign}{float(e_vs_v):.1f}%")

# 밴드 시각화
st.subheader("📉 밴드 상태")
lower_f = float(guide.band_lower)
v_f = float(guide.v_target)
upper_f = float(guide.band_upper)
e_f = float(guide.e_value)

import pandas as pd
band_df = pd.DataFrame({
    "구분": ["하단 밴드", "목표값 V", "상단 밴드", "현재 E"],
    "금액 (USD)": [lower_f, v_f, upper_f, e_f],
})
st.dataframe(band_df, use_container_width=True, hide_index=True)

# 판정 결과
action_map = {
    "HOLD": ("✅ 밴드 내 — 이번 주는 매수/매도 없음", "success"),
    "BUY": ("⬇️ 하단 이탈 — 매수 가이드", "warning"),
    "SELL": ("⬆️ 상단 이탈 — 매도 가이드", "warning"),
}
msg, kind = action_map.get(guide.action, ("알 수 없음", "info"))
if kind == "success":
    st.success(msg)
else:
    st.warning(msg)

show_price_alert(guide.messages)

if guide.order:
    st.subheader("💡 리밸런싱 주문")
    order_table([guide.order])

st.caption(f"다음 주기 목표값 V: {fmt_usd(guide.v_next)} (현재 V × {1 + float(snap['params'].G):.3f})")

# 주기 완료 처리
st.divider()
st.subheader("주기 완료 처리")
with st.expander("체결 후 주기 완료 처리 (V 갱신)"):
    col_a, col_b = st.columns(2)
    with col_a:
        p_date = st.date_input("기준일 (토요일)", value=date.today())
        action_input = st.selectbox("실행한 액션", ["HOLD", "BUY", "SELL"])
    with col_b:
        if action_input in ("BUY", "SELL"):
            exec_shares = st.number_input("체결 수량 (주)", min_value=0.01, step=0.01)
            exec_price = st.number_input("체결 단가 (USD)", min_value=0.01, step=0.01)
        else:
            exec_shares, exec_price = 0.0, 0.0
        cash_after = st.number_input("처리 후 현금 잔고 C", min_value=0.0,
                                     value=float(guide.cash_balance), step=10.0)

    if st.button("주기 완료 처리", type="primary"):
        svc.record_vr_rebalance(
            selected.id,
            period_date=p_date,
            action=action_input,
            shares=Decimal(str(exec_shares)),
            price=Decimal(str(exec_price)),
            e_value=guide.e_value,
            v_target=guide.v_target,
            v_next=guide.v_next,
            cash_balance_after=Decimal(str(cash_after)),
        )
        st.success(f"✅ 주기 완료 처리. 다음 V = {fmt_usd(guide.v_next)}")
        st.rerun()
