"""포트폴리오 관리 — 수정 / 비활성화 / 삭제."""

import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st

from jkhenry.config import IB_DEFAULT, VR_DEFAULT
from jkhenry.repository.db import get_engine, get_session, init_db
from jkhenry.repository.repositories import (
    delete_portfolio,
    get_all_portfolios,
    update_portfolio,
    update_portfolio_status,
)
from jkhenry.ui.components import strategy_badge
from jkhenry.ui.style import C, gap, inject_css, page_header, render_sidebar, require_auth, section_label, status_banner

st.set_page_config(page_title="포트폴리오 관리", page_icon="⚙️", layout="centered",
                   initial_sidebar_state="expanded")
inject_css()
render_sidebar()
require_auth()
init_db()

page_header("⚙️", "포트폴리오 관리", "수정 · 비활성화 · 삭제")

engine = get_engine()

with get_session(engine) as s:
    active   = get_all_portfolios(s, status="active")
    inactive = get_all_portfolios(s, status="inactive")
all_portfolios = active + inactive

if not all_portfolios:
    st.info("생성된 포트폴리오가 없습니다.")
    st.page_link("pages/1_포트폴리오_생성.py", label="➕ 새 포트폴리오 생성")
    st.stop()

# ── 포트폴리오별 카드 ──────────────────────────────────────────────────────────
for p in all_portfolios:
    is_active = p.status == "active"
    color = C["ib"] if p.strategy == "IB" else C["vr"]
    status_icon = "🟢" if is_active else "⚫"

    with st.expander(f"{status_icon}  **{p.ticker}**  ·  {p.name}  ·  {strategy_badge(p.strategy)}"):

        params = json.loads(p.params)

        # ── 파라미터 수정 폼 ────────────────────────────────────────────────────
        section_label("파라미터 수정")
        with st.form(f"edit_{p.id}"):
            new_name = st.text_input("포트폴리오 이름", value=p.name, key=f"nm_{p.id}")

            if p.strategy == "IB":
                c1, c2 = st.columns(2)
                new_T    = c1.number_input("분할 횟수 (T)", min_value=10, max_value=100,
                                           value=int(params.get("T", IB_DEFAULT["T"])), key=f"T_{p.id}")
                new_half = c2.number_input("전반전 경계 회차", min_value=5, max_value=50,
                                           value=int(params.get("half_round", IB_DEFAULT["half_round"])),
                                           key=f"hr_{p.id}")
                c3, c4 = st.columns(2)
                new_mult = c3.number_input("큰수 배율 (전일종가 ×)", min_value=1.01, max_value=2.0,
                                           value=float(params.get("buy_high_multiplier",
                                                                   IB_DEFAULT["buy_high_multiplier"])),
                                           step=0.01, key=f"bh_{p.id}")
                new_sell = c4.number_input("매도 목표 수익률 (%)", min_value=1.0, max_value=50.0,
                                           value=float(params.get("sell_target_pct",
                                                                   IB_DEFAULT["sell_target_pct"])) * 100,
                                           step=0.5, key=f"sp_{p.id}")
                seed_val = float(p.seed_capital)
                unit_val = seed_val / int(new_T)
                st.caption(f"총 시드 **${seed_val:,.2f}**  ·  1 unit = **${unit_val:.2f}**")

                new_params = {
                    "T": int(new_T), "half_round": int(new_half),
                    "buy_high_multiplier": str(round(new_mult, 4)),
                    "sell_target_pct": str(round(new_sell / 100, 4)),
                }

            else:  # VR
                c1, c2 = st.columns(2)
                new_G    = c1.number_input("주간 성장률 G (%/주)", min_value=0.1, max_value=10.0,
                                           value=float(params.get("G", VR_DEFAULT["G"])) * 100,
                                           step=0.1, key=f"G_{p.id}")
                new_cash = c2.number_input("현금 잔고 C (USD)", min_value=0.0,
                                           value=float(params.get("cash_balance", 0)),
                                           step=100.0, key=f"cb_{p.id}")
                c3, c4 = st.columns(2)
                new_bu = c3.number_input("상단 밴드 폭 (%)", min_value=1.0, max_value=50.0,
                                         value=float(params.get("band_upper",
                                                                 VR_DEFAULT["band_upper"])) * 100,
                                         step=1.0, key=f"bu_{p.id}")
                new_bl = c4.number_input("하단 밴드 폭 (%)", min_value=1.0, max_value=50.0,
                                         value=float(params.get("band_lower",
                                                                 VR_DEFAULT["band_lower"])) * 100,
                                         step=1.0, key=f"bl_{p.id}")
                new_params = {
                    **params,
                    "G": str(round(new_G / 100, 4)),
                    "cash_balance": str(new_cash),
                    "band_upper": str(round(new_bu / 100, 4)),
                    "band_lower": str(round(new_bl / 100, 4)),
                }

            if st.form_submit_button("💾 수정 저장", type="primary", use_container_width=True):
                with get_session(engine) as s:
                    update_portfolio(s, p.id, name=new_name, params=new_params)
                    s.commit()
                st.success("✅ 수정 완료")
                st.rerun()

        gap(10)
        st.divider()

        # ── 비활성화 / 재활성화 ─────────────────────────────────────────────────
        section_label("운용 상태")
        if is_active:
            st.caption("비활성화하면 대시보드에서 숨겨집니다. 데이터는 보존됩니다.")
            if st.button("⏸ 비활성화 (숨김)", key=f"deact_{p.id}", use_container_width=True):
                with get_session(engine) as s:
                    update_portfolio_status(s, p.id, "inactive")
                    s.commit()
                st.success("비활성화 완료")
                st.rerun()
        else:
            status_banner("⚫ 현재 비활성화 상태입니다.", "info")
            if st.button("▶️ 다시 활성화", key=f"act_{p.id}", use_container_width=True):
                with get_session(engine) as s:
                    update_portfolio_status(s, p.id, "active")
                    s.commit()
                st.success("활성화 완료")
                st.rerun()

        gap(10)
        st.divider()

        # ── 완전 삭제 (2단계 확인) ───────────────────────────────────────────────
        section_label("⚠️ 위험 구역")
        st.caption("삭제하면 체결 기록, 사이클, VR 주기 데이터가 **모두 영구 삭제**됩니다.")

        confirm_key = f"confirm_del_{p.id}"
        if confirm_key not in st.session_state:
            st.session_state[confirm_key] = False

        if not st.session_state[confirm_key]:
            if st.button("🗑️ 포트폴리오 삭제", key=f"del_btn_{p.id}",
                         use_container_width=True):
                st.session_state[confirm_key] = True
                st.rerun()
        else:
            status_banner(f"⚠️ <b>{p.ticker} — {p.name}</b>의 모든 데이터가 삭제됩니다. 정말 삭제할까요?", "danger")
            col_yes, col_no = st.columns(2)
            if col_yes.button("✅ 예, 삭제합니다", key=f"yes_{p.id}",
                              type="primary", use_container_width=True):
                with get_session(engine) as s:
                    delete_portfolio(s, p.id)
                    s.commit()
                st.session_state[confirm_key] = False
                st.success("🗑️ 삭제 완료")
                st.rerun()
            if col_no.button("❌ 취소", key=f"no_{p.id}", use_container_width=True):
                st.session_state[confirm_key] = False
                st.rerun()
