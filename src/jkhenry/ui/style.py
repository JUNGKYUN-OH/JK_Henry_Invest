# -*- coding: utf-8 -*-
"""글로벌 CSS + HTML 컴포넌트. Glassmorphism + Bento Grid 디자인."""

import streamlit as st

# ── CSS 변수 ──────────────────────────────────────────────────────────────────

_VARS = {
    "dark": """
:root {
    --bg:     #08101E;
    --card:   rgba(16,28,52,0.70);
    --card2:  rgba(24,38,68,0.55);
    --border: rgba(148,163,184,0.10);
    --text:   #F1F5F9; --muted: #94A3B8;
    --ib:     #4F8EF7; --vr:    #A855F7;
    --buy:    #10B981; --sell:  #F59E0B;
    --loss:   #EF4444; --info:  #22D3EE;
    --p1:     #4F8EF7; --p2:    #A855F7;
    --shadow:       0 8px 32px rgba(0,0,0,0.45);
    --glass-bg:     rgba(16,28,52,0.62);
    --glass-border: rgba(148,163,184,0.12);
    --glass-inset:  inset 0 1px 0 rgba(255,255,255,0.06);
    --blur:         blur(20px) saturate(180%);
}""",
    "light": """
:root {
    --bg:     #EEF2FB;
    --card:   rgba(255,255,255,0.74);
    --card2:  rgba(248,250,252,0.80);
    --border: rgba(15,23,42,0.09);
    --text:   #0F172A; --muted: #64748B;
    --ib:     #2563EB; --vr:    #7C3AED;
    --buy:    #059669; --sell:  #D97706;
    --loss:   #DC2626; --info:  #0284C7;
    --p1:     #2563EB; --p2:    #7C3AED;
    --shadow:       0 4px 24px rgba(15,23,42,0.10);
    --glass-bg:     rgba(255,255,255,0.74);
    --glass-border: rgba(255,255,255,0.85);
    --glass-inset:  inset 0 1px 0 rgba(255,255,255,0.95);
    --blur:         blur(20px) saturate(180%);
}""",
}

# ── 라이트 모드 오버라이드 ───────────────────────────────────────────────────

_LIGHT_OVERRIDES = """
[data-testid="stDecoration"] { display:none !important; }
#MainMenu { visibility: hidden !important; }

/* 그라디언트 메쉬 배경 */
.stApp, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse 80% 60% at 5% 10%, rgba(37,99,235,0.08) 0%, transparent 60%),
        radial-gradient(ellipse 70% 70% at 95% 90%, rgba(124,58,237,0.08) 0%, transparent 60%),
        #EEF2FB !important;
}
/* 라이트 모드 헤더 배경 (BASE_CSS의 var(--bg) 보강) */
[data-testid="stHeader"] { background-color: #EEF2FB !important; }

/* primary 버튼 텍스트 흰색 유지 */
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span,
.stButton > button[data-testid*="primary"] p,
.stButton > button[data-testid*="primary"] span {
    color: #FFFFFF !important;
}"""

# ── 다크 모드 오버라이드 ─────────────────────────────────────────────────────

_DARK_OVERRIDES = """
/* 그라디언트 메쉬 배경 */
.stApp, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse 80% 60% at 5% 10%, rgba(79,142,247,0.09) 0%, transparent 60%),
        radial-gradient(ellipse 70% 70% at 95% 90%, rgba(168,85,247,0.09) 0%, transparent 60%),
        #08101E !important;
}
/* 다크 모드 헤더 배경 (BASE_CSS의 var(--bg) 보강) */
[data-testid="stHeader"] { background-color: #08101E !important; }

[data-testid="stDecoration"] { display:none !important; }
#MainMenu { visibility: hidden !important; }

/* 사이드바 */
section[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {
    background: rgba(10,18,34,0.90) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-right: 1px solid rgba(148,163,184,0.08) !important;
}
[data-testid="stSidebarContent"] * { color: #F1F5F9 !important; }
[data-testid="stSidebarCollapsedControl"] svg { color: #F1F5F9 !important; }

/* 기본 텍스트 */
.stApp, .stMarkdown, p, span, label,
h1, h2, h3, h4, h5, h6 { color: #F1F5F9 !important; }

/* 메트릭 */
[data-testid="stMetricValue"]  { color: #F1F5F9 !important; }
[data-testid="stMetricLabel"]  { color: #94A3B8 !important; }
[data-testid="stCaptionContainer"] { color: #94A3B8 !important; }

/* 컨테이너·카드 */
[data-testid="stVerticalBlockBorderWrapper"] > div {
    background: rgba(16,28,52,0.62) !important;
    border-color: rgba(148,163,184,0.12) !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: rgba(24,38,68,0.55) !important;
    border-color: rgba(148,163,184,0.12) !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpanderDetails"] {
    background: transparent !important;
    color: #F1F5F9 !important;
}

/* 버튼 */
.stButton > button {
    background: rgba(16,28,52,0.80) !important;
    color: #F1F5F9 !important;
    border: 1px solid rgba(148,163,184,0.18) !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid*="primary"] {
    background: linear-gradient(135deg, #4F8EF7, #A855F7) !important;
    color: #FFFFFF !important;
    border: none !important;
}
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span,
.stButton > button[data-testid*="primary"] p,
.stButton > button[data-testid*="primary"] span {
    color: #FFFFFF !important;
}

/* 입력 필드 */
.stTextInput input,
.stNumberInput input,
.stDateInput input {
    background: rgba(16,28,52,0.80) !important;
    color: #F1F5F9 !important;
    border-color: rgba(148,163,184,0.20) !important;
}

/* Selectbox */
.stSelectbox > div > div {
    background: rgba(16,28,52,0.80) !important;
    color: #F1F5F9 !important;
    border-color: rgba(148,163,184,0.20) !important;
}

/* Radio */
.stRadio > div, .stRadio label { color: #F1F5F9 !important; }

/* Form */
[data-testid="stForm"] {
    background: transparent !important;
    border-color: rgba(148,163,184,0.12) !important;
}

/* Alert 박스 */
[data-testid="stInfo"],
[data-testid="stSuccess"],
[data-testid="stWarning"],
[data-testid="stError"] {
    background: rgba(24,38,68,0.55) !important;
    color: #F1F5F9 !important;
}

/* Dataframe */
[data-testid="stDataFrame"] iframe { background: rgba(16,28,52,0.80) !important; }

/* Divider */
hr { border-color: rgba(148,163,184,0.12) !important; }

/* Page link */
[data-testid="stPageLink"] a { color: #4F8EF7 !important; }"""

# ── 공통 CSS ──────────────────────────────────────────────────────────────────

_BASE_CSS = """
/* 네비게이션 숨김 */
[data-testid="stSidebarNav"] { display: none !important; }
footer { visibility: hidden !important; }

/* 헤더: 앱 배경색과 동일하게 설정 → 흰 공간 제거
   (transparent는 Streamlit 내부 CSS에 덮여 효과 없음) */
[data-testid="stHeader"] {
    background-color: var(--bg) !important;
    border-bottom: none !important;
    box-shadow: none !important;
}

/* 사이드바 토글 아이콘 — 배경이 바뀌어도 항상 가시화 */
[data-testid="stSidebarCollapsedControl"] button svg {
    color: var(--text) !important;
    fill: var(--text) !important;
}

/* 히어로 부제목 반응형 — 모바일은 짧은 버전 표시 */
.hero-sub-short { display: none; }
@media (max-width: 640px) {
    .hero-sub-full  { display: none !important; }
    .hero-sub-short { display: inline !important; }
}

/* 레이아웃 */
.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 920px !important;
    margin: 0 auto;
}

/* ── Glassmorphism: Streamlit 보더 컨테이너 ── */
[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius: 20px !important;
    background: var(--glass-bg) !important;
    border: 1px solid var(--glass-border) !important;
    box-shadow: var(--shadow), var(--glass-inset) !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease !important;
}
@supports (backdrop-filter: blur(1px)) {
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        backdrop-filter: var(--blur) !important;
        -webkit-backdrop-filter: var(--blur) !important;
    }
}

/* 진행률 바 */
[data-testid="stProgress"] > div { border-radius:999px; overflow:hidden; }
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, var(--p1), var(--p2)) !important;
    border-radius: 999px;
}

/* 메트릭 */
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important; font-weight: 600 !important;
    text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--muted) !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.1rem !important; font-weight: 700 !important;
    color: var(--text) !important;
}

/* ── 버튼 ── */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: opacity 0.15s, transform 0.12s, box-shadow 0.15s !important;
}
.stButton > button:hover {
    opacity: 0.88 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(0,0,0,0.18) !important;
}

/* Primary 버튼 그라디언트 */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--p1) 0%, var(--p2) 100%) !important;
    border: none !important;
    box-shadow: 0 2px 14px rgba(79,142,247,0.28) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 24px rgba(79,142,247,0.40) !important;
}

/* Expander */
[data-testid="stExpander"] {
    border-radius: 14px !important;
    border: 1px solid var(--border) !important;
    background: var(--card2) !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important; font-size: 0.88rem !important;
}

/* Form 테두리 제거 */
[data-testid="stForm"] {
    border: none !important; padding: 0 !important; background: transparent !important;
}

/* Divider */
hr { border-color: var(--border) !important; margin: 0.75rem 0 !important; }

/* Caption */
[data-testid="stCaptionContainer"] { color: var(--muted) !important; }

/* 모바일 */
@media (max-width: 640px) {
    .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 0 !important; }
    [data-testid="column"] { flex: 0 0 100% !important; min-width: 100% !important; }
    [data-testid="stMetricValue"] { font-size: 0.95rem !important; }
}

/* 태블릿 */
@media (min-width: 641px) and (max-width: 860px) {
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    [data-testid="column"] { flex: 0 0 50% !important; min-width: 50% !important; }
}
"""


# ── 공개 API ──────────────────────────────────────────────────────────────────

def current_theme() -> str:
    return st.session_state.get("theme", "light")


def inject_css() -> None:
    """모든 페이지 최상단에서 호출."""
    theme = current_theme()
    extra = _DARK_OVERRIDES if theme == "dark" else _LIGHT_OVERRIDES
    st.markdown(
        f"<style>{_VARS[theme]}{_BASE_CSS}{extra}</style>",
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """사이드바 내비게이션 + 테마 토글."""
    theme = current_theme()
    with st.sidebar:
        # 다크 모드에서 [stSidebarContent] * { color !important } 가 그라디언트 텍스트와
        # 충돌해 텍스트가 투명해지는 문제를 방지하기 위해 color !important 인라인 스타일 사용.
        # 인라인 !important 는 외부 CSS !important 보다 명시도(1-0-0-0)가 높아 항상 우선.
        brand_color = "#4F8EF7" if theme == "dark" else "#2563EB"
        st.markdown(
            f"<div style='"
            f"font-size:1.1rem;font-weight:800;padding:8px 0 4px 0;"
            f"color:{brand_color} !important;"
            f"'>💼 JK Henry Invest</div>",
            unsafe_allow_html=True,
        )
        st.divider()
        st.page_link("app.py",                        label="🏠  대시보드")
        st.page_link("pages/1_포트폴리오_생성.py",    label="➕  새 포트폴리오")
        st.page_link("pages/2_IB_가이드.py",          label="📈  IB 가이드")
        st.page_link("pages/3_VR_가이드.py",          label="⚖️  VR 가이드")
        st.page_link("pages/3_체결_입력.py",          label="✏️  체결 입력")
        st.page_link("pages/4_매매_일지.py",          label="📋  매매 일지")
        st.page_link("pages/5_통계.py",               label="📊  통계")
        st.page_link("pages/6_포트폴리오_관리.py",    label="⚙️  포트폴리오 관리")
        st.divider()

        label = "☀️  라이트 모드" if theme == "dark" else "🌙  다크 모드"
        if st.button(label, use_container_width=True, key="__theme_toggle__"):
            st.session_state["theme"] = "light" if theme == "dark" else "dark"
            st.rerun()
        st.caption(f"현재: {'🌙 다크' if theme == 'dark' else '☀️ 라이트'}")


# ── HTML 컴포넌트 ─────────────────────────────────────────────────────────────

def card_header(ticker: str, strategy: str, name: str = "") -> None:
    color  = "var(--ib)" if strategy == "IB" else "var(--vr)"
    color2 = "var(--p1)" if strategy == "IB" else "var(--p2)"
    full   = "IB · Infinite Buying" if strategy == "IB" else "VR · Value Rebalancing"
    sub    = (f'<span style="color:var(--muted);font-size:0.78rem;margin-left:8px;">{name}</span>'
              if name else "")
    st.markdown(f"""
    <div style="
        position:relative;
        background:linear-gradient(135deg,{color}18,{color}06);
        border:1px solid {color}30;
        border-left:4px solid {color};
        border-radius:16px;
        padding:14px 18px;
        margin-bottom:18px;
        backdrop-filter:blur(8px);
        -webkit-backdrop-filter:blur(8px);
        overflow:hidden;
    ">
        <div style="position:absolute;top:0;right:0;width:120px;height:120px;
                    background:radial-gradient(circle,{color}14 0%,transparent 70%);
                    pointer-events:none;"></div>
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <span style="font-size:1.6rem;font-weight:800;letter-spacing:-0.02em;
                         color:var(--text);">{ticker}</span>
            <span style="background:{color}20;color:{color};font-size:0.70rem;font-weight:700;
                         padding:4px 12px;border-radius:20px;letter-spacing:0.05em;
                         border:1px solid {color}30;">{full}</span>
            {sub}
        </div>
    </div>
    """, unsafe_allow_html=True)


def order_card(label: str, price, shares, amount, order_type: str, side: str = "BUY") -> None:
    color = "var(--buy)" if side == "BUY" else "var(--sell)"
    icon  = "📥" if side == "BUY" else "📤"
    st.markdown(f"""
    <div style="
        background:linear-gradient(135deg,{color}12,{color}05);
        border:1px solid {color}28;
        border-left:3px solid {color};
        border-radius:14px;
        padding:14px 16px;
        margin:6px 0;
        backdrop-filter:blur(8px);
        -webkit-backdrop-filter:blur(8px);
    ">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
            <span style="font-weight:700;color:{color};font-size:0.84rem;">{icon} {label}</span>
            <span style="font-size:0.66rem;color:var(--muted);
                         background:var(--card2);border:1px solid var(--border);
                         padding:2px 9px;border-radius:20px;">{order_type}</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
            <div>
                <div style="font-size:0.60rem;color:var(--muted);text-transform:uppercase;
                             letter-spacing:0.07em;margin-bottom:3px;">주문가격</div>
                <div style="font-size:1.0rem;font-weight:700;color:var(--text);">${float(price):,.2f}</div>
            </div>
            <div>
                <div style="font-size:0.60rem;color:var(--muted);text-transform:uppercase;
                             letter-spacing:0.07em;margin-bottom:3px;">수량</div>
                <div style="font-size:1.0rem;font-weight:700;color:var(--text);">{float(shares):.2f}주</div>
            </div>
            <div>
                <div style="font-size:0.60rem;color:var(--muted);text-transform:uppercase;
                             letter-spacing:0.07em;margin-bottom:3px;">금액</div>
                <div style="font-size:1.0rem;font-weight:700;color:{color};">${float(amount):,.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def no_order_card(message: str) -> None:
    st.markdown(f"""
    <div style="
        background:var(--card2);
        border:1px dashed var(--border);
        border-radius:14px;
        padding:18px;
        color:var(--muted);
        font-size:0.85rem;
        text-align:center;
        backdrop-filter:blur(8px);
        -webkit-backdrop-filter:blur(8px);
    ">{message}</div>
    """, unsafe_allow_html=True)


def status_banner(message: str, kind: str = "info") -> None:
    colors = {
        "success": "var(--buy)", "warning": "var(--sell)",
        "danger":  "var(--loss)", "info":    "var(--info)",
    }
    color = colors.get(kind, "var(--info)")
    st.markdown(f"""
    <div style="
        background:{color}10;
        border:1px solid {color}28;
        border-left:3px solid {color};
        border-radius:10px;
        padding:10px 14px;
        font-size:0.85rem;font-weight:500;
        color:{color};margin:6px 0;
        backdrop-filter:blur(8px);
        -webkit-backdrop-filter:blur(8px);
    ">{message}</div>
    """, unsafe_allow_html=True)


def section_label(text: str) -> None:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:8px;margin:18px 0 8px 0;">
        <div style="
            width:3px;height:16px;border-radius:2px;flex-shrink:0;
            background:linear-gradient(180deg,var(--p1),var(--p2));
        "></div>
        <span style="font-size:0.72rem;font-weight:700;text-transform:uppercase;
                     letter-spacing:0.08em;color:var(--muted);">{text}</span>
    </div>
    """, unsafe_allow_html=True)


def gap(px: int = 8) -> None:
    st.markdown(f'<div style="height:{px}px"></div>', unsafe_allow_html=True)


# 하위 호환
C = {
    "bg": "var(--bg)", "card": "var(--card)", "card2": "var(--card2)",
    "border": "var(--border)", "text": "var(--text)", "muted": "var(--muted)",
    "ib": "var(--ib)", "vr": "var(--vr)",
    "buy": "var(--buy)", "sell": "var(--sell)", "loss": "var(--loss)", "hold": "var(--info)",
}
