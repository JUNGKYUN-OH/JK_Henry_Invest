"""수익률 통계 페이지."""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import streamlit as st

from jkhenry.repository.db import init_db
from jkhenry.services.guide_service import GuideService
from jkhenry.ui.components import fmt_pct, fmt_usd
from jkhenry.ui.style import C, gap, inject_css, page_header, render_sidebar, require_auth, section_label, status_banner

st.set_page_config(page_title="수익률 통계", page_icon="📊", layout="centered",
                   initial_sidebar_state="expanded")
inject_css()
render_sidebar()
require_auth()
init_db()

page_header("📊", "수익률 통계", "IB 사이클별 손익 분석")

svc = GuideService()
ib_portfolios = [p for p in svc.list_portfolios() if p.strategy == "IB"]

if not ib_portfolios:
    st.info("IB (Infinite Buying) 포트폴리오가 없습니다.")
    st.stop()

selected = st.selectbox("포트폴리오", ib_portfolios,
                        format_func=lambda p: f"{p.ticker} — {p.name}")
if not selected:
    st.stop()

stats = svc.get_ib_statistics(selected.id)
gap(8)

# ── 요약 지표 ─────────────────────────────────────────────────────────────────
with st.container(border=True):
    section_label("요약")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("완료 사이클",  stats["total_cycles"])
    m2.metric("수익 사이클", f"{stats['win_cycles']}회")
    wr = stats["win_rate"]
    m3.metric("승률", f"{float(wr)*100:.1f}%")
    m4.metric("누적 손익",   fmt_usd(stats["total_profit"]))

gap(12)

cycles = stats["cycles"]
if not cycles:
    gap(20)
    st.markdown(
        f'<div style="text-align:center;background:var(--card);border:1px solid var(--glass-border);'
        f'border-radius:20px;padding:40px;backdrop-filter:var(--blur);">'
        f'<div style="font-size:2rem;margin-bottom:10px;">📭</div>'
        f'<div style="color:var(--muted);">완료된 사이클이 없습니다.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ── 사이클 상세 테이블 ─────────────────────────────────────────────────────────
with st.container(border=True):
    section_label("사이클 상세")
    rows = []
    for c in sorted(cycles, key=lambda x: x.cycle_num):
        profit = Decimal(str(c.realized_profit)) if c.realized_profit else Decimal("0")
        rate   = Decimal(str(c.profit_rate))     if c.profit_rate     else Decimal("0")
        status = "✅ 수익" if c.status == "completed" else "❌ 손절"
        rows.append({
            "사이클":    c.cycle_num,
            "시작일":    c.start_date,
            "종료일":    c.end_date or "—",
            "상태":      status,
            "손익(USD)": fmt_usd(profit),
            "수익률":    fmt_pct(rate),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
