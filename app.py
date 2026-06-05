"""대시보드 — Bento Grid + Glassmorphism 디자인."""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st

from jkhenry.market.price_provider import get_friday_close, get_price_data, get_usd_krw_rate
from jkhenry.repository.db import init_db
from jkhenry.services.guide_service import GuideService
from jkhenry.ui.components import fmt_krw, fmt_pct, fmt_usd
from jkhenry.ui.style import (
    C, card_header, gap, inject_css, no_order_card,
    order_card, render_sidebar, require_auth, section_label, status_banner,
)

st.set_page_config(
    page_title="JK Henry Invest",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="expanded",
)
inject_css()
render_sidebar()
require_auth()
init_db()

# ── 히어로 헤더 ────────────────────────────────────────────────────────────────
# 새로고침 버튼은 사이드바로 이동 → 모바일/데스크탑 모두 CSS 없이 해결
st.markdown("""
<div style="padding:4px 0 0 0;">
    <div style="
        font-size:1.55rem;font-weight:800;letter-spacing:-0.02em;
        background:linear-gradient(135deg,var(--p1) 0%,var(--p2) 100%);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
        background-clip:text;display:inline-block;
    ">💼 JK Henry Invest</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="font-size:0.78rem;color:var(--muted);margin:-2px 0 4px 0;line-height:1.4;">
    <span class="hero-sub-full">IB (Infinite Buying) · VR (Value Rebalancing) 매매 가이드</span>
    <span class="hero-sub-short">IB · VR 매매 가이드</span>
</div>
""", unsafe_allow_html=True)

gap(16)

svc = GuideService()
portfolios = svc.list_portfolios()

if not portfolios:
    st.markdown("""
    <div style="
        text-align:center;padding:56px 24px;
        background:var(--card);border:1px solid var(--glass-border);
        border-radius:24px;backdrop-filter:var(--blur);
        -webkit-backdrop-filter:var(--blur);
        box-shadow:var(--shadow),var(--glass-inset);
    ">
        <div style="font-size:2.8rem;margin-bottom:14px;">📭</div>
        <div style="font-size:1.1rem;font-weight:700;color:var(--text);margin-bottom:6px;">포트폴리오가 없습니다</div>
        <div style="font-size:0.85rem;color:var(--muted);">사이드바 ➕ 새 포트폴리오를 눌러 시작하세요.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# 첫 진입 시 첫 번째 포트폴리오 자동 선택
if "selected_pid" not in st.session_state:
    st.session_state["selected_pid"] = portfolios[0].id

# ── 전략 필터 ─────────────────────────────────────────────────────────────────
_ib_cnt = sum(1 for p in portfolios if p.strategy == "IB")
_vr_cnt = sum(1 for p in portfolios if p.strategy == "VR")
_has_both = _ib_cnt > 0 and _vr_cnt > 0

if _has_both:
    # st.radio(horizontal=True) — 모바일/데스크탑 모두 한 줄 보장
    # st.columns 기반 버튼은 Streamlit CSS 클래스 구조상 모바일 CSS 타겟 불가
    _filter = st.radio(
        "전략 필터",
        options=["전체", "IB", "VR"],
        format_func=lambda x: {
            "전체": f"전체 ({len(portfolios)})",
            "IB":   f"📈 IB ({_ib_cnt})",
            "VR":   f"⚖️ VR ({_vr_cnt})",
        }[x],
        horizontal=True,
        key="dash_filter",
        label_visibility="collapsed",
    )
    # 필터 변경 시 현재 선택 포트폴리오가 목록에 없으면 첫 번째 항목으로 자동 전환
    _candidates = (
        [p for p in portfolios if p.strategy == _filter]
        if _filter in ("IB", "VR") else portfolios
    )
    if _candidates and st.session_state.get("selected_pid") not in {p.id for p in _candidates}:
        st.session_state["selected_pid"] = _candidates[0].id
    gap(8)
else:
    _filter = "전체"


# ── 컴팩트 요약 카드 데이터 수집 ───────────────────────────────────────────────
def _get_card_data(p):
    price_data = get_price_data(p.ticker)
    current    = Decimal(str(price_data["current"])) if price_data else None
    rate       = get_usd_krw_rate()

    if p.strategy == "IB":
        snap    = svc.get_ib_snapshot(p.id)
        avg     = snap["avg_price"]
        eff_rnd = snap["effective_round"]
        params  = snap["params"]
        max_rnd = params.half_round * 2

        if current and avg and avg > 0:
            pnl_pct = (current - avg) / avg * 100
            pnl_str = f"{'+' if pnl_pct >= 0 else ''}{float(pnl_pct):.1f}%"
            pnl_color = "var(--buy)" if pnl_pct >= 0 else "var(--loss)"
        else:
            pnl_str, pnl_color = "—", "var(--muted)"

        if eff_rnd > max_rnd:
            status_icon, status_color = "🔴", "var(--loss)"
        elif eff_rnd > params.half_round:
            status_icon, status_color = "🟡", "var(--sell)"
        else:
            status_icon, status_color = "🟢", "var(--buy)"

        invested  = snap["total_invested"]
        eval_amt  = snap["shares_held"] * current if current else None

        def _combined(usd):
            return f"{fmt_usd(usd, 0)} · {fmt_krw(usd, rate)}" if usd else "—"

        metrics = [
            ("유효 회차", f"{float(eff_rnd):.1f} / {max_rnd}"),
            ("평단가",    fmt_usd(avg) if avg > 0 else "—"),
            ("현재가",    fmt_usd(current) if current else "—"),
            ("손익",      pnl_str),
            ("매입금액",  _combined(invested)),
            ("평가금액",  _combined(eval_amt)),
        ]
        return dict(metrics=metrics, status_icon=status_icon,
                    status_color=status_color, pnl_color=pnl_color,
                    price_data=price_data)

    else:  # VR
        friday_data  = get_friday_close(p.ticker)
        friday_price = Decimal(str(friday_data["close"])) if friday_data else current

        snap  = svc.get_vr_snapshot(p.id)
        guide = svc.generate_vr_guide(p.id, manual_current=friday_price)

        action_icon = {"HOLD": "✅", "BUY": "⬇️", "SELL": "⬆️"}.get(guide.action, "—")
        action_color = {
            "HOLD": "var(--buy)", "BUY": "var(--info)", "SELL": "var(--sell)"
        }.get(guide.action, "var(--muted)")

        fri_label = (f"{friday_data['date'].month}/{friday_data['date'].day} 금"
                     if friday_data else "금 종가")
        invested = snap["total_invested"]
        metrics = [
            ("목표값 V",  fmt_usd(guide.v_target)),
            ("평가금액 E", fmt_usd(guide.e_value)),
            (fri_label,   fmt_usd(friday_price) if friday_price else "—"),
            ("현금 C",    fmt_usd(guide.cash_balance)),
            ("매입금액",  f"{fmt_usd(invested, 0)} · {fmt_krw(invested, rate)}"),
        ]
        return dict(metrics=metrics, status_icon=action_icon,
                    status_color=action_color, pnl_color=action_color,
                    price_data=price_data)


# ── Bento 카드 렌더 함수 ───────────────────────────────────────────────────────
def _render_compact_card(p, card_data):
    is_sel  = st.session_state["selected_pid"] == p.id
    color   = "var(--ib)" if p.strategy == "IB" else "var(--vr)"
    strat   = "IB" if p.strategy == "IB" else "VR"
    metrics = card_data["metrics"]

    # 선택 상태별 스타일
    border  = f"2px solid {color}" if is_sel else "1px solid var(--glass-border)"
    bg      = f"linear-gradient(135deg,{color}18,{color}06)" if is_sel else "var(--card)"
    glow    = f"0 0 24px {color}35, var(--shadow), var(--glass-inset)" if is_sel else "var(--shadow), var(--glass-inset)"

    # 상단 accent bar (선택 시)
    accent_bar = (
        f'<div style="position:absolute;top:0;left:0;right:0;height:3px;'
        f'border-radius:18px 18px 0 0;'
        f'background:linear-gradient(90deg,{color},{color}55);"></div>'
        if is_sel else ""
    )

    rows_html = "".join(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:4px 0;border-bottom:1px solid var(--border);">'
        f'<span style="color:var(--muted);font-size:0.69rem;">{lbl}</span>'
        f'<span style="font-weight:700;font-size:0.78rem;color:var(--text);">{val}</span>'
        f'</div>'
        for lbl, val in metrics
    )

    # 빈 accent_bar로 공백 줄이 생기면 CommonMark가 HTML 블록을 종료시키므로
    # 단일 문자열로 조립해 줄 바꿈을 제거한다.
    badge = (
        f'<span style="font-size:0.60rem;color:{color};font-weight:700;'
        f'background:{color}1A;padding:2px 8px;border-radius:20px;'
        f'border:1px solid {color}28;letter-spacing:0.04em;">{strat}</span>'
    )
    header = (
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
        f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">'
        f'<span style="font-size:1.12rem;font-weight:800;color:var(--text);">{p.ticker}</span>'
        f'{badge}</div>'
        f'<span style="font-size:1.15rem;">{card_data["status_icon"]}</span>'
        f'</div>'
    )
    card_html = (
        f'<div style="position:relative;overflow:hidden;background:{bg};border:{border};'
        f'border-radius:18px;padding:15px 14px 12px;box-shadow:{glow};'
        f'backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);'
        f'transition:transform 0.18s ease,box-shadow 0.18s ease;">'
        f'{accent_bar}{header}{rows_html}</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    gap(4)
    label = "✅ 선택됨" if is_sel else "📊 상세보기"
    if st.button(label, key=f"sel_{p.id}", use_container_width=True,
                 type="primary" if is_sel else "secondary"):
        st.session_state["selected_pid"] = p.id
        st.rerun()


# ── Bento 포트폴리오 그리드 ────────────────────────────────────────────────────
if _filter == "IB":
    display_portfolios = [p for p in portfolios if p.strategy == "IB"]
elif _filter == "VR":
    display_portfolios = [p for p in portfolios if p.strategy == "VR"]
else:
    display_portfolios = portfolios

# 섹션 레이블
st.markdown("""
<div style="display:flex;align-items:center;gap:8px;margin:4px 0 10px 0;">
    <div style="width:3px;height:16px;border-radius:2px;flex-shrink:0;
                background:linear-gradient(180deg,var(--p1),var(--p2));"></div>
    <span style="font-size:0.72rem;font-weight:700;text-transform:uppercase;
                 letter-spacing:0.08em;color:var(--muted);">포트폴리오</span>
</div>
""", unsafe_allow_html=True)

if not display_portfolios:
    st.info("해당 전략 포트폴리오가 없습니다.")
else:
    n = len(display_portfolios)
    cols = st.columns(min(n, 3))
    for idx, p in enumerate(display_portfolios):
        with cols[idx % 3]:
            data = _get_card_data(p)
            _render_compact_card(p, data)

gap(8)

# 얇은 그라디언트 구분선
st.markdown("""
<div style="
    height:1px;margin:12px 0 18px 0;
    background:linear-gradient(90deg,transparent,var(--p1)40,var(--p2)40,transparent);
"></div>
""", unsafe_allow_html=True)

# ── 선택된 포트폴리오 상세 ────────────────────────────────────────────────────
selected_pid = st.session_state.get("selected_pid")
sel_p = next((x for x in portfolios if x.id == selected_pid), None)

if not sel_p:
    st.stop()

# 상세 섹션 레이블
st.markdown("""
<div style="display:flex;align-items:center;gap:8px;margin:0 0 14px 0;">
    <div style="width:3px;height:16px;border-radius:2px;flex-shrink:0;
                background:linear-gradient(180deg,var(--p1),var(--p2));"></div>
    <span style="font-size:0.72rem;font-weight:700;text-transform:uppercase;
                 letter-spacing:0.08em;color:var(--muted);">상세 분석</span>
</div>
""", unsafe_allow_html=True)

price_data    = get_price_data(sel_p.ticker)
prev_close    = Decimal(str(price_data["prev_close"])) if price_data else None
current_price = Decimal(str(price_data["current"]))    if price_data else None

friday_data  = get_friday_close(sel_p.ticker) if sel_p.strategy == "VR" else None
friday_price = Decimal(str(friday_data["close"])) if friday_data else current_price

# ── IB 상세 ───────────────────────────────────────────────────────────────────
if sel_p.strategy == "IB":
    snap           = svc.get_ib_snapshot(sel_p.id)
    avg            = snap["avg_price"]
    eff_rnd        = snap["effective_round"]
    cal_rnd        = snap["calendar_round"]
    total_invested = snap["total_invested"]
    held           = snap["shares_held"]
    params         = snap["params"]
    guide = svc.generate_ib_daily_guide(
        sel_p.id,
        manual_prev_close=prev_close,
        manual_current=current_price,
    )

    card_header(sel_p.ticker, "IB", sel_p.name)

    if not price_data:
        status_banner("⚠️ 시세 조회 실패 — 새로고침을 눌러 주세요.", "warning")

    m1, m2, m3, m4 = st.columns(4)
    max_rnd = params.half_round * 2
    m1.metric("유효 회차", f"{float(eff_rnd):.1f} / {max_rnd}",
              help=f"자금 소진 기준 | 진행일: {cal_rnd}일")
    m2.metric("단계", guide.phase.value)
    m3.metric("평단가", fmt_usd(avg) if avg > 0 else "—")
    if current_price and avg and avg > 0:
        m4.metric("현재가", fmt_usd(current_price),
                  fmt_pct((current_price - avg) / avg))
    else:
        m4.metric("현재가", fmt_usd(current_price) if current_price else "—")

    gap(4)
    progress = min(float(eff_rnd) / max_rnd, 1.0) if max_rnd > 0 else 0.0
    phase_emoji = "🟢" if eff_rnd <= params.half_round else ("🟡" if eff_rnd <= max_rnd else "🔴")
    st.progress(
        progress,
        text=f"{phase_emoji} **{guide.phase.value}** | "
             f"유효 {float(eff_rnd):.1f}/{max_rnd}회차 | "
             f"잔여 {fmt_usd(guide.remaining_budget)}"
    )
    gap(10)

    for msg in guide.messages:
        kind = "warning" if ("없음" in msg or "소진" in msg or "잔여" in msg) else "info"
        status_banner(f"ℹ️ {msg}", kind)

    section_label("오늘의 주문 가이드")
    buy_col, sell_col = st.columns(2)

    with buy_col:
        st.markdown("<div style='font-size:0.8rem;font-weight:700;"
                    "color:var(--buy);margin-bottom:4px;'>📥 매수 주문</div>",
                    unsafe_allow_html=True)
        if guide.buy_orders:
            for o in guide.buy_orders:
                order_card(o.label, o.price, o.shares, o.amount, o.order_type, "BUY")
            total = sum((o.amount for o in guide.buy_orders), Decimal("0"))
            st.caption(f"합계 **{fmt_usd(total)}** (1 unit = {fmt_usd(guide.unit)})")
        else:
            no_order_card("오늘 매수 없음")

    with sell_col:
        st.markdown("<div style='font-size:0.8rem;font-weight:700;"
                    "color:var(--sell);margin-bottom:4px;'>📤 매도 After 지정가 (상시 유지)</div>",
                    unsafe_allow_html=True)
        sell = guide.sell_order
        if float(sell.shares) > 0:
            order_card(sell.label, sell.price, sell.shares, sell.amount, sell.order_type, "SELL")
            if current_price and sell.price > 0:
                gap_pct = (sell.price - current_price) / sell.price * 100
                icon = "🟢" if float(gap_pct) > 5 else ("🟡" if float(gap_pct) > 0 else "🔴")
                st.caption(f"{icon} 목표가까지 **{float(gap_pct):.1f}%** 남음")
        else:
            no_order_card("보유 수량 없음")

    gap(6)
    _last = st.session_state.pop("_dash_last_trade", None)
    if _last:
        st.success("✅ 체결 기록이 저장되었습니다.")
        with st.container(border=True):
            section_label("저장된 체결")
            order_card(
                label=f"{_last['ticker']} · {_last['date']}",
                price=_last["price"],
                shares=_last["shares"],
                amount=_last["amount"],
                order_type=_last["order_type"],
                side=_last["side"],
            )
            if _last.get("note"):
                st.caption(f"💬 {_last['note']}")
        gap(4)

    with st.expander("✏️ 체결 기록 입력"):
        with st.form(f"tf_{sel_p.id}"):
            r1c1, r1c2, r1c3 = st.columns(3)
            td   = r1c1.date_input("체결일", value=date.today(), key=f"d_{sel_p.id}")
            side = r1c2.radio("구분", ["매수", "매도"], horizontal=True, key=f"sd_{sel_p.id}")
            ot   = r1c3.selectbox("주문유형", ["LOC", "AFTER_LIMIT", "LIMIT", "MARKET"],
                                  key=f"ot_{sel_p.id}")
            side_code = "BUY" if side == "매수" else "SELL"

            def_price  = float(guide.buy_orders[0].price)  if guide.buy_orders else 0.01
            def_shares = float(guide.buy_orders[0].shares) if guide.buy_orders else 0.01

            r2c1, r2c2, r2c3 = st.columns(3)
            t_sh = r2c1.number_input("수량(주)", min_value=0.01,
                                      value=max(def_shares, 0.01),
                                      step=0.01, format="%.2f", key=f"sh_{sel_p.id}")
            t_pr = r2c2.number_input("단가(USD)", min_value=0.01,
                                      value=max(def_price, 0.01),
                                      step=0.01, format="%.4f", key=f"pr_{sel_p.id}")
            t_nt = r2c3.text_input("메모", key=f"nt_{sel_p.id}")
            amt  = Decimal(str(t_sh)) * Decimal(str(t_pr))
            st.caption(f"금액: **{fmt_usd(amt)}**")

            if st.form_submit_button("💾 저장", type="primary", use_container_width=True):
                try:
                    svc.record_ib_trade(
                        sel_p.id, trade_date=td, side=side_code, order_type=ot,
                        shares=Decimal(str(t_sh)), price=Decimal(str(t_pr)), note=t_nt,
                    )
                    st.session_state["_dash_last_trade"] = {
                        "ticker": sel_p.ticker,
                        "date": str(td),
                        "side": side_code,
                        "order_type": ot,
                        "shares": t_sh,
                        "price": t_pr,
                        "amount": float(amt),
                        "note": t_nt,
                    }
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")

# ── VR 상세 ───────────────────────────────────────────────────────────────────
else:
    snap  = svc.get_vr_snapshot(sel_p.id)
    guide = svc.generate_vr_guide(sel_p.id, manual_current=friday_price)

    card_header(sel_p.ticker, "VR", sel_p.name)

    if not friday_data:
        status_banner("⚠️ 시세 조회 실패 — 새로고침을 눌러 주세요.", "warning")
    else:
        st.caption(
            f"📅 기준: {friday_data['date'].strftime('%Y-%m-%d')} "
            f"({'금' if friday_data['date'].weekday() == 4 else '대체 거래일'}) "
            f"종가 {fmt_usd(friday_price)}"
        )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("목표값 V", fmt_usd(guide.v_target))
    m2.metric("평가금액 E", fmt_usd(guide.e_value))
    if guide.v_target > 0:
        m3.metric("V 대비", fmt_pct((guide.e_value - guide.v_target) / guide.v_target))
    else:
        m3.metric("V 대비", "—")
    m4.metric("현금 C", fmt_usd(guide.cash_balance))

    gap(10)
    action_cfg = {
        "HOLD": ("✅  밴드 내 유지 — 이번 주는 주문 없음", "success"),
        "BUY":  ("⬇️  하단 이탈 — 매수 필요",             "info"),
        "SELL": ("⬆️  상단 이탈 — 매도 필요",             "warning"),
    }
    msg_vr, kind_vr = action_cfg.get(guide.action, ("—", "info"))
    status_banner(msg_vr, kind_vr)

    for msg in guide.messages:
        status_banner(f"ℹ️ {msg}", "warning")

    if guide.order:
        section_label("리밸런싱 주문")
        o = guide.order
        side_vr = "BUY" if guide.action == "BUY" else "SELL"
        order_card(o.label, o.price, o.shares, o.amount, o.order_type, side_vr)

    st.caption(
        f"다음 주기 V: {fmt_usd(guide.v_next)}  ·  "
        f"상단 {fmt_usd(guide.band_upper)}  ·  하단 {fmt_usd(guide.band_lower)}"
    )
    gap(4)
    st.page_link("pages/3_VR_가이드.py", label="⚖️ VR 상세 가이드 →")
