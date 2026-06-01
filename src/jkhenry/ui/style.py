"""글로벌 CSS + HTML 컴포넌트. 라이트/다크 테마 지원.

전략:
- config.toml = dark  →  다크 모드는 Streamlit 네이티브 위젯이 그대로 잘 보임
- 라이트 모드 = CSS 오버라이드로 밝게 전환
- 헤더(사이드바 토글 포함)는 절대 숨기지 않음
"""

import streamlit as st

# ── CSS 변수 ──────────────────────────────────────────────────────────────────

_VARS = {
    "dark": """
:root {
    --bg:    #0F172A; --card: #1E293B; --card2: #263348;
    --border:rgba(148,163,184,0.12);
    --text:  #F1F5F9; --muted:#94A3B8;
    --ib:    #4F8EF7; --vr:   #A855F7;
    --buy:   #10B981; --sell: #F59E0B;
    --loss:  #EF4444; --info: #22D3EE;
    --p1:    #4F8EF7; --p2:   #A855F7;
    --shadow:0 4px 24px rgba(0,0,0,0.35);
}""",
    "light": """
:root {
    --bg:    #F8FAFC; --card: #FFFFFF; --card2: #F1F5F9;
    --border:rgba(15,23,42,0.09);
    --text:  #0F172A; --muted:#64748B;
    --ib:    #2563EB; --vr:   #7C3AED;
    --buy:   #059669; --sell: #D97706;
    --loss:  #DC2626; --info: #0284C7;
    --p1:    #2563EB; --p2:   #7C3AED;
    --shadow:0 2px 16px rgba(15,23,42,0.07);
}""",
}

# ── 라이트 모드: Streamlit 네이티브 위젯 색상 오버라이드 ───────────────────────
# config.toml이 dark이므로, 라이트 선택 시 밝게 강제 덮어씀

_LIGHT_OVERRIDES = """
/* 앱 배경 */
.stApp,
[data-testid="stAppViewContainer"] {
    background-color: #F8FAFC !important;
}
[data-testid="stHeader"] {
    background-color: #F8FAFC !important;
    border-bottom: 1px solid rgba(15,23,42,0.08) !important;
}
/* stDecoration(상단 컬러 바)는 숨겨도 사이드바 토글에 영향 없음 */
[data-testid="stDecoration"] { display:none !important; }
/* 상단 메뉴(MainMenu) 라이트 모드에서도 숨김 */
#MainMenu { visibility: hidden !important; }

/* 사이드바 */
section[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid rgba(15,23,42,0.08) !important;
}
[data-testid="stSidebarContent"] * { color: #0F172A !important; }
[data-testid="stSidebarCollapsedControl"] svg { color: #0F172A !important; }

/* 기본 텍스트 */
.stApp, .stMarkdown, p, span, label,
h1, h2, h3, h4, h5, h6 { color: #0F172A !important; }

/* 메트릭 */
[data-testid="stMetricValue"]  { color: #0F172A !important; }
[data-testid="stMetricLabel"]  { color: #64748B !important; }
[data-testid="stCaptionContainer"] { color: #64748B !important; }

/* 컨테이너·카드 */
[data-testid="stVerticalBlockBorderWrapper"] > div {
    background-color: #FFFFFF !important;
    border-color: rgba(15,23,42,0.09) !important;
}

/* Expander */
[data-testid="stExpander"] {
    background-color: #F1F5F9 !important;
    border-color: rgba(15,23,42,0.09) !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpanderDetails"] {
    background-color: #F1F5F9 !important;
    color: #0F172A !important;
}

/* 버튼 */
.stButton > button {
    background-color: #F1F5F9 !important;
    color: #0F172A !important;
    border: 1px solid rgba(15,23,42,0.15) !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid*="primary"] {
    background-color: #2563EB !important;
    color: #FFFFFF !important;
    border-color: #2563EB !important;
}
/* 전역 p/span 색상 오버라이드가 primary 버튼 텍스트를 검게 만드는 것을 방지 */
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
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    border-color: rgba(15,23,42,0.2) !important;
}

/* Selectbox */
.stSelectbox > div > div {
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    border-color: rgba(15,23,42,0.2) !important;
}

/* Radio */
.stRadio > div, .stRadio label { color: #0F172A !important; }

/* Form */
[data-testid="stForm"] {
    background-color: transparent !important;
    border-color: rgba(15,23,42,0.09) !important;
}

/* Alert 박스 */
[data-testid="stInfo"],
[data-testid="stSuccess"],
[data-testid="stWarning"],
[data-testid="stError"] {
    background-color: #F1F5F9 !important;
    color: #0F172A !important;
}

/* Dataframe */
[data-testid="stDataFrame"] iframe { background-color: #FFFFFF !important; }

/* Divider */
hr { border-color: rgba(15,23,42,0.09) !important; }

/* Page link */
[data-testid="stPageLink"] a { color: #2563EB !important; }

"""

# ── 공통 CSS (테마 무관) ───────────────────────────────────────────────────────

_BASE_CSS = """
/* Streamlit 자동 생성 페이지 내비게이션 숨김 (커스텀 사이드바로 대체) */
[data-testid="stSidebarNav"] { display: none !important; }

/* footer 숨김 */
footer { visibility: hidden !important; }

/* 레이아웃 — 상단 패딩을 충분히 줘서 Streamlit 헤더바와 겹치지 않게 */
.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 860px !important;
    margin: 0 auto;
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

/* 버튼 공통 */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: opacity 0.15s, transform 0.1s !important;
}
.stButton > button:hover {
    opacity: 0.85 !important; transform: translateY(-1px) !important;
}

/* Expander */
[data-testid="stExpander"] {
    border-radius: 12px !important;
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

/* 카드 컨테이너 */
[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius: 16px !important;
    background-color: var(--card) !important;
    border-color: var(--border) !important;
    box-shadow: var(--shadow) !important;
}

/* Divider */
hr { border-color: var(--border) !important; margin: 0.75rem 0 !important; }

/* Caption */
[data-testid="stCaptionContainer"] { color: var(--muted) !important; }

/* 모바일 반응형 */
@media (max-width: 640px) {
    .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }
    /* 포트폴리오 그리드: 3열 → 1열 */
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 0 !important; }
    [data-testid="column"] { flex: 0 0 100% !important; min-width: 100% !important; }
    [data-testid="stMetricValue"] { font-size: 0.95rem !important; }
}

/* 태블릿: 3열 → 2열 */
@media (min-width: 641px) and (max-width: 860px) {
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    [data-testid="column"] { flex: 0 0 50% !important; min-width: 50% !important; }
}
"""


# ── 공개 API ──────────────────────────────────────────────────────────────────

def current_theme() -> str:
    return st.session_state.get("theme", "light")


def inject_css() -> None:
    """모든 페이지 최상단에서 호출. 현재 테마 CSS를 주입한다."""
    theme = current_theme()
    extra = _LIGHT_OVERRIDES if theme == "light" else ""
    st.markdown(
        f"<style>{_VARS[theme]}{_BASE_CSS}{extra}</style>",
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """사이드바 내비게이션 + 테마 토글."""
    theme = current_theme()
    with st.sidebar:
        st.markdown(
            "<div style='font-size:1.1rem;font-weight:800;padding:6px 0 2px 0;'>"
            "💼 JK Henry Invest</div>",
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
    color = "var(--ib)" if strategy == "IB" else "var(--vr)"
    full  = "IB · Infinite Buying" if strategy == "IB" else "VR · Value Rebalancing"
    sub   = (f'<span style="color:var(--muted);font-size:0.8rem;margin-left:6px;">{name}</span>'
             if name else "")
    st.markdown(f"""
    <div style="border-left:3px solid {color};padding-left:12px;margin-bottom:14px;">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <span style="font-size:1.5rem;font-weight:800;letter-spacing:-0.02em;
                         color:var(--text);">{ticker}</span>
            <span style="background:{color}22;color:{color};font-size:0.7rem;font-weight:700;
                         padding:3px 10px;border-radius:20px;letter-spacing:0.05em;">{full}</span>
            {sub}
        </div>
    </div>
    """, unsafe_allow_html=True)


def order_card(label: str, price, shares, amount, order_type: str, side: str = "BUY") -> None:
    color = "var(--buy)" if side == "BUY" else "var(--sell)"
    icon  = "📥" if side == "BUY" else "📤"
    st.markdown(f"""
    <div style="background:{color}11;border:1px solid {color}33;
                border-radius:12px;padding:12px 14px;margin:6px 0;">
        <div style="margin-bottom:8px;">
            <span style="font-weight:700;color:{color};font-size:0.82rem;">{icon} {label}</span>
        </div>
        <div style="display:flex;gap:20px;flex-wrap:wrap;">
            <div>
                <div style="font-size:0.65rem;color:var(--muted);text-transform:uppercase;
                             letter-spacing:0.05em;margin-bottom:2px;">주문가격</div>
                <div style="font-size:1.05rem;font-weight:700;color:var(--text);">${float(price):,.2f}</div>
            </div>
            <div>
                <div style="font-size:0.65rem;color:var(--muted);text-transform:uppercase;
                             letter-spacing:0.05em;margin-bottom:2px;">수량</div>
                <div style="font-size:1.05rem;font-weight:700;color:var(--text);">{float(shares):.2f}주</div>
            </div>
            <div>
                <div style="font-size:0.65rem;color:var(--muted);text-transform:uppercase;
                             letter-spacing:0.05em;margin-bottom:2px;">금액</div>
                <div style="font-size:1.05rem;font-weight:700;color:{color};">${float(amount):,.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def no_order_card(message: str) -> None:
    st.markdown(f"""
    <div style="background:var(--card2);border:1px solid var(--border);
                border-radius:12px;padding:14px;color:var(--muted);
                font-size:0.85rem;text-align:center;">{message}</div>
    """, unsafe_allow_html=True)


def status_banner(message: str, kind: str = "info") -> None:
    colors = {
        "success": "var(--buy)", "warning": "var(--sell)",
        "danger":  "var(--loss)", "info":    "var(--info)",
    }
    color = colors.get(kind, "var(--info)")
    st.markdown(f"""
    <div style="background:{color}14;border:1px solid {color}40;
                border-radius:10px;padding:10px 14px;
                font-size:0.85rem;font-weight:500;color:{color};margin:6px 0;">
        {message}
    </div>
    """, unsafe_allow_html=True)


def section_label(text: str) -> None:
    st.markdown(f"""
    <div style="font-size:0.72rem;font-weight:700;text-transform:uppercase;
                letter-spacing:0.08em;color:var(--muted);margin:14px 0 6px 0;">
        {text}
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
