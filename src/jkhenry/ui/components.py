"""공통 UI 컴포넌트."""

from decimal import Decimal

import streamlit as st

STRATEGY_LABEL = {
    "IB": "IB (Infinite Buying)",
    "VR": "VR (Value Rebalancing)",
}


def strategy_badge(strategy: str) -> str:
    return STRATEGY_LABEL.get(strategy, strategy)


def fmt_usd(value: Decimal | float | None, decimals: int = 2) -> str:
    if value is None:
        return "—"
    return f"${float(value):,.{decimals}f}"


def fmt_krw(usd_value: Decimal | float | None, rate: Decimal | float | None) -> str:
    """USD 금액을 원화 만원 단위로 변환. 예: ₩621만, ₩1.2억"""
    if usd_value is None or rate is None:
        return "—"
    krw = float(usd_value) * float(rate)
    man = krw / 10_000
    if man >= 10_000:
        return f"₩{man / 10_000:.1f}억"
    elif man >= 1:
        return f"₩{man:,.0f}만"
    else:
        return f"₩{krw:,.0f}"


def fmt_pct(value: Decimal | float | None, decimals: int = 2) -> str:
    if value is None:
        return "—"
    sign = "+" if float(value) >= 0 else ""
    return f"{sign}{float(value) * 100:.{decimals}f}%"


def price_status_color(current: Decimal, avg: Decimal) -> str:
    if current >= avg:
        return "normal"
    return "inverse"


def show_price_alert(messages: list[str]) -> None:
    for msg in messages:
        if "목표가까지" in msg or "전환" in msg:
            st.info(msg)
        elif "없음" in msg or "부족" in msg or "소진" in msg:
            st.warning(msg)
        else:
            st.info(msg)


def order_table(orders: list, title: str = "") -> None:
    if title:
        st.markdown(f"**{title}**")
    if not orders:
        st.caption("주문 없음")
        return
    import pandas as pd
    rows = [
        {
            "구분": o.label,
            "주문가격 (USD)": fmt_usd(o.price),
            "수량 (주)": f"{float(o.shares):.2f}",
            "금액 (USD)": fmt_usd(o.amount),
            "주문유형": o.order_type,
        }
        for o in orders
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
