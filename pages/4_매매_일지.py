"""매매 일지 — 조회 + 행별 인라인 수정/삭제."""

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st

from jkhenry.repository.db import get_engine, get_session, init_db
from jkhenry.repository.repositories import delete_trade, get_trade, update_trade
from jkhenry.services.guide_service import GuideService
from jkhenry.ui.components import fmt_usd, strategy_badge
from jkhenry.ui.style import C, gap, inject_css, render_sidebar, section_label, status_banner

st.set_page_config(page_title="매매 일지", page_icon="📋", layout="centered",
                   initial_sidebar_state="expanded")
inject_css()
render_sidebar()
init_db()

st.markdown("""
<div style="text-align:center;padding:8px 0 18px 0;">
    <div style="font-size:1.6rem;font-weight:800;">📋 매매 일지</div>
</div>
""", unsafe_allow_html=True)

svc = GuideService()
portfolios = svc.list_portfolios()
pf_map = {p.id: p for p in portfolios}
engine = get_engine()

# ── 필터 ───────────────────────────────────────────────────────────────────────
fc1, fc2, fc3 = st.columns(3)
with fc1:
    selected_pf = st.selectbox(
        "포트폴리오",
        [None] + portfolios,
        format_func=lambda p: "전체" if p is None else f"{p.ticker} — {p.name}",
    )
with fc2:
    from_date = st.date_input("시작일", value=date.today() - timedelta(days=90))
with fc3:
    to_date = st.date_input("종료일", value=date.today())

pid = selected_pf.id if selected_pf else None
trades = svc.get_journal(portfolio_id=pid, from_date=from_date, to_date=to_date)

if not trades:
    gap(20)
    st.markdown(f"""
    <div style="text-align:center;color:{C['muted']};padding:32px;">
        <div style="font-size:2rem;margin-bottom:8px;">📭</div>
        <div>해당 기간에 체결 기록이 없습니다.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# CSV 내보내기
import pandas as pd
rows_csv = []
for t in trades:
    pf = pf_map.get(t.portfolio_id)
    rows_csv.append({
        "ID": t.id, "날짜": t.trade_date, "종목": pf.ticker if pf else "—",
        "기법": strategy_badge(pf.strategy) if pf else "—",
        "구분": "매수" if t.side=="BUY" else "매도", "주문유형": t.order_type,
        "수량": float(t.shares), "단가": float(t.price), "금액": float(t.amount),
        "메모": t.note or "",
    })

col_cnt, col_csv = st.columns([3, 1])
col_cnt.caption(f"총 **{len(trades)}건**  ·  행을 펼치면 수정/삭제 가능")
if col_csv.button("📥 CSV", use_container_width=True):
    csv = pd.DataFrame(rows_csv).to_csv(index=False, encoding="utf-8-sig")
    st.download_button("다운로드", data=csv, file_name="trade_journal.csv", mime="text/csv")

gap(6)
st.divider()

# ── 행별 인라인 수정/삭제 ───────────────────────────────────────────────────────
for t in trades:
    pf = pf_map.get(t.portfolio_id)
    ticker   = pf.ticker if pf else "—"
    is_buy   = t.side == "BUY"
    side_ico = "📥" if is_buy else "📤"
    side_lbl = "매수" if is_buy else "매도"
    color    = C["buy"] if is_buy else C["sell"]

    # 아코디언 제목: 요약 정보가 한 줄에 보임
    label = (
        f"{side_ico} {t.trade_date}  ·  {ticker}  ·  {side_lbl}  ·  "
        f"${float(t.price):.4f} × {float(t.shares):.2f}주 = ${float(t.amount):.2f}"
        + (f"  ·  {t.note}" if t.note else "")
    )

    with st.expander(label):
        # 작은 배지 표시
        st.markdown(
            f'<span style="font-size:0.7rem;background:{color}22;color:{color};'
            f'padding:2px 8px;border-radius:20px;font-weight:700;">'
            f'ID #{t.id}  ·  {t.order_type}</span>',
            unsafe_allow_html=True,
        )
        gap(8)

        with st.form(f"ef_{t.id}"):
            ec1, ec2, ec3 = st.columns(3)
            new_date = ec1.date_input("체결일", value=date.fromisoformat(t.trade_date), key=f"d_{t.id}")
            new_side = ec2.radio("구분", ["매수","매도"],
                                 index=0 if t.side=="BUY" else 1,
                                 horizontal=True, key=f"s_{t.id}")
            new_ot   = ec3.selectbox("주문유형", ["LOC","LIMIT","MARKET"],
                                     index=["LOC","LIMIT","MARKET"].index(t.order_type),
                                     key=f"o_{t.id}")
            new_side_code = "BUY" if new_side == "매수" else "SELL"

            ef1, ef2, ef3 = st.columns(3)
            new_sh = ef1.number_input("수량(주)",  min_value=0.01, value=float(t.shares),
                                      step=0.01, format="%.2f",  key=f"sh_{t.id}")
            new_pr = ef2.number_input("단가(USD)", min_value=0.01, value=float(t.price),
                                      step=0.01, format="%.4f",  key=f"pr_{t.id}")
            new_nt = ef3.text_input("메모", value=t.note or "", key=f"n_{t.id}")

            new_amt = Decimal(str(new_sh)) * Decimal(str(new_pr))
            st.caption(f"수정 후 금액: **{fmt_usd(new_amt)}**")

            btn_s, btn_d = st.columns(2)
            save   = btn_s.form_submit_button("💾 저장", type="primary", use_container_width=True)
            delete = btn_d.form_submit_button("🗑️ 삭제", use_container_width=True)

        if save:
            with get_session(engine) as s:
                update_trade(s, t.id, trade_date=new_date, side=new_side_code,
                             order_type=new_ot, shares=Decimal(str(new_sh)),
                             price=Decimal(str(new_pr)), note=new_nt)
                s.commit()
            st.success(f"✅ #{t.id} 수정 완료")
            st.rerun()

        if delete:
            with get_session(engine) as s:
                delete_trade(s, t.id)
                s.commit()
            st.success(f"🗑️ #{t.id} 삭제 완료")
            st.rerun()
