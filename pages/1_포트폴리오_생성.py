"""포트폴리오 생성 페이지."""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st

from jkhenry.config import IB_DEFAULT, VR_DEFAULT
from jkhenry.market.price_provider import ticker_exists
from jkhenry.repository.db import get_engine, get_session, init_db
from jkhenry.repository.repositories import create_cycle, create_portfolio
from jkhenry.ui.components import fmt_usd, strategy_badge
from jkhenry.ui.style import gap, inject_css, render_sidebar, status_banner

st.set_page_config(page_title="포트폴리오 생성", page_icon="➕", layout="centered",
                   initial_sidebar_state="expanded")
inject_css()
render_sidebar()
init_db()

st.markdown("""
<div style="text-align:center;padding:8px 0 20px 0;">
    <div style="font-size:1.6rem;font-weight:800;">➕ 새 포트폴리오 생성</div>
</div>
""", unsafe_allow_html=True)

name = st.text_input("포트폴리오 이름", placeholder="예: TQQQ 무한매수 1호")

# ── 티커 입력 + 실시간 검증 ─────────────────────────────────────────────────────
tc1, tc2 = st.columns([3, 1])
ticker_raw = tc1.text_input("티커 심볼", placeholder="예: TQQQ").upper().strip()

# 티커가 바뀌면 이전 검증 결과 초기화
if st.session_state.get("_last_ticker") != ticker_raw:
    st.session_state["_ticker_ok"]      = False
    st.session_state["_ticker_price"]   = None
    st.session_state["_ticker_checked"] = False
    st.session_state["_last_ticker"]    = ticker_raw

with tc2:
    gap(28)
    check_clicked = st.button("🔍 확인", use_container_width=True,
                              disabled=not ticker_raw)

if check_clicked and ticker_raw:
    with st.spinner(f"{ticker_raw} 조회 중…"):
        ok, price_data = ticker_exists(ticker_raw)
    st.session_state["_ticker_ok"]      = ok
    st.session_state["_ticker_price"]   = price_data
    st.session_state["_ticker_checked"] = True

ticker_ok      = st.session_state.get("_ticker_ok", False)
ticker_price   = st.session_state.get("_ticker_price")
ticker_checked = st.session_state.get("_ticker_checked", False)
ticker         = ticker_raw

if ticker_raw and ticker_ok and ticker_price:
    st.success(
        f"✅ **{ticker_raw}** 확인 — "
        f"전일 종가 {fmt_usd(ticker_price['prev_close'])} / "
        f"현재가 {fmt_usd(ticker_price['current'])}"
    )
elif ticker_raw and ticker_checked and not ticker_ok:
    st.error(f"❌ **{ticker_raw}** 는 조회되지 않는 티커입니다. 심볼을 확인해 주세요.")
elif ticker_raw and not ticker_checked:
    st.caption("🔍 확인 버튼을 눌러 티커가 실제 존재하는지 검증해 주세요.")

strategy = st.radio("투자 기법", ["IB (Infinite Buying)", "VR (Value Rebalancing)"], horizontal=True)
strategy_code = "IB" if strategy.startswith("IB") else "VR"

st.divider()

with st.form("settings_form"):
    if strategy_code == "IB":
        st.markdown("#### IB (Infinite Buying) 설정")
        seed = st.number_input("총 시드 (USD)", min_value=100.0, value=10000.0, step=100.0)
        c1, c2 = st.columns(2)
        T          = c1.number_input("분할 횟수", min_value=10, max_value=100, value=IB_DEFAULT["T"])
        half_round = c2.number_input("전반전 경계 회차", min_value=5, max_value=50, value=IB_DEFAULT["half_round"])
        c3, c4 = st.columns(2)
        buy_high_mult = c3.number_input("큰수 배율 (전일종가 ×)", min_value=1.01, max_value=2.0,
                                        value=float(IB_DEFAULT["buy_high_multiplier"]), step=0.01)
        sell_pct      = c4.number_input("매도 목표 수익률 (%)", min_value=1.0, max_value=50.0,
                                        value=float(IB_DEFAULT["sell_target_pct"]) * 100, step=0.5)
        T_int = int(T)
        seed_decimal = Decimal(str(seed))
        unit = seed_decimal / T_int
        st.caption(f"1 unit = **${float(unit):.2f} USD**  ·  총 {T_int}회 분할")
        params = {
            "T": T_int, "half_round": int(half_round),
            "buy_high_multiplier": str(round(buy_high_mult, 4)),
            "sell_target_pct": str(round(sell_pct / 100, 4)),
        }

    else:
        st.markdown("#### VR (Value Rebalancing) 설정")
        seed = st.number_input(
            "V₀ — 처음 투자에 배정한 전체 금액 (현재 주식 평가금 + 현금 잔고) (USD)",
            min_value=100.0, value=10000.0, step=100.0,
        )
        cash = st.number_input("초기 현금 잔고 C (USD)", min_value=0.0, value=5000.0, step=100.0)
        c1, c2 = st.columns(2)
        G_pct      = c1.number_input("주기당 성장률 G (%)", min_value=0.1, max_value=10.0,
                                     value=float(VR_DEFAULT["G"]) * 100, step=0.1)
        band_upper = c2.number_input("상단 밴드 폭 (%)", min_value=1.0, max_value=50.0,
                                     value=float(VR_DEFAULT["band_upper"]) * 100, step=1.0)
        band_lower = st.number_input("하단 밴드 폭 (%)", min_value=1.0, max_value=50.0,
                                     value=float(VR_DEFAULT["band_lower"]) * 100, step=1.0)
        seed_decimal = Decimal(str(seed))
        st.caption(
            f"상단 **${seed*(1+band_upper/100):,.2f}**  ·  목표 V **${seed:,.2f}**  ·  하단 **${seed*(1-band_lower/100):,.2f}**"
        )
        params = {
            "v_initial": str(seed), "cash_balance": str(cash),
            "G": str(round(G_pct / 100, 4)),
            "band_upper": str(round(band_upper / 100, 4)),
            "band_lower": str(round(band_lower / 100, 4)),
            "period_days": 7,
        }

    gap(4)
    submitted = st.form_submit_button("✅ 포트폴리오 생성", type="primary", use_container_width=True)

if submitted:
    errors = []
    if not name:
        errors.append("포트폴리오 이름을 입력해 주세요.")
    if not ticker:
        errors.append("티커 심볼을 입력해 주세요.")
    elif not ticker_ok:
        errors.append(f"티커 '{ticker}'를 먼저 🔍 확인 버튼으로 검증해 주세요.")
    if errors:
        for e in errors:
            status_banner(f"⚠️ {e}", "warning")
    else:
        engine = get_engine()
        with get_session(engine) as s:
            pf = create_portfolio(s, name=name, ticker=ticker, strategy=strategy_code,
                                  seed_capital=seed_decimal, params=params)
            if strategy_code == "IB":
                create_cycle(s, portfolio_id=pf.id, cycle_num=1, start_date=date.today())
            s.commit()
        st.success(f"✅ '{name}' ({ticker} / {strategy_badge(strategy_code)}) 생성 완료!")
        gap(6)
        st.page_link("app.py", label="← 대시보드로 돌아가기")
