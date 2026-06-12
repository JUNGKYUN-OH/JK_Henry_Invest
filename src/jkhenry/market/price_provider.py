"""yfinance 래퍼 + st.cache_data 캐시.

동일 요청은 캐시(TTL 300초)에서 반환하여 중복 API 호출 방지.
네트워크 실패 시 예외를 발생시키지 않고 None을 반환 → 호출자가 처리.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import streamlit as st
import yfinance as yf


def _fetch(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    hist = t.history(period="5d")
    if hist.empty:
        raise ValueError(f"{ticker}: yfinance 데이터 없음")
    # yfinance가 당일 미완성 봉에 NaN을 반환하는 경우 제거
    hist = hist.dropna(subset=["Close"])
    if len(hist) < 2:
        raise ValueError(f"{ticker}: 유효한 종가 데이터 부족 (NaN 제거 후 {len(hist)}행)")
    prev_close = Decimal(str(round(float(hist["Close"].iloc[-2]), 4)))
    current = Decimal(str(round(float(hist["Close"].iloc[-1]), 4)))
    return {"prev_close": prev_close, "current": current}


def _pick_friday_close(bars: list[tuple[date, Decimal]], today: date) -> Optional[dict]:
    """
    일봉 리스트에서 'today 기준 직전(완료된) 금요일' 종가를 고른다.

    - 금요일 봉이 공휴일 등으로 없으면 그 주의 마지막 거래일(목요일 등)로 자동 대체.
    - today가 금요일이면 그 주가 아직 마감 전이므로 직전 주 금요일을 사용.
    - 어느 요일에 호출해도 같은 주 안에서는 동일한 금요일을 가리켜 안정적이다.
    """
    if not bars:
        return None
    # weekday: Mon=0 … Fri=4. 금요일이면(offset 0) 직전 주 금요일(=7일 전)로.
    offset = (today.weekday() - 4) % 7 or 7
    candidate = today - timedelta(days=offset)
    eligible = [(d, c) for d, c in bars if d <= candidate]
    chosen = max(eligible, key=lambda x: x[0]) if eligible else max(bars, key=lambda x: x[0])
    return {"date": chosen[0], "close": chosen[1]}


# ── st.cache_data 래핑 함수들 ──────────────────────────────────────────────────
# today를 파라미터로 포함시켜 날짜가 바뀌면 캐시 키가 달라지도록 한다.

@st.cache_data(ttl=300)
def _cached_price_data(ticker: str) -> Optional[dict]:
    try:
        return _fetch(ticker)
    except Exception:
        return None


@st.cache_data(ttl=300)
def _cached_friday_data(ticker: str, today: date) -> Optional[dict]:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1mo")
        if hist.empty:
            return None
        hist = hist.dropna(subset=["Close"])
        bars = [
            (idx.date(), Decimal(str(round(float(close), 4))))
            for idx, close in hist["Close"].items()
        ]
        return _pick_friday_close(bars, today)
    except Exception:
        return None


@st.cache_data(ttl=300)
def _cached_krw_rate() -> Optional[Decimal]:
    try:
        t = yf.Ticker("KRW=X")
        hist = t.history(period="5d")
        if hist.empty:
            return None
        return Decimal(str(round(float(hist["Close"].iloc[-1]), 2)))
    except Exception:
        return None


# ── 공개 API ───────────────────────────────────────────────────────────────────

def get_price_data(ticker: str, force_refresh: bool = False) -> Optional[dict]:
    """
    {"prev_close": Decimal, "current": Decimal} 반환.
    실패 시 None 반환.
    """
    key = ticker.upper()
    if force_refresh:
        _cached_price_data.clear()
    return _cached_price_data(key)


def get_friday_close(ticker: str, force_refresh: bool = False) -> Optional[dict]:
    """
    VR 기준가 — '직전 금요일 종가'를 {"date": date, "close": Decimal}로 반환.

    yfinance 최근 한 달 일봉에서 직전 금요일(공휴일 시 그 주 마지막 거래일) 종가를 고른다.
    실패 시 None.
    """
    key = ticker.upper()
    if force_refresh:
        _cached_friday_data.clear()
    return _cached_friday_data(key, date.today())


def get_prev_close(ticker: str) -> Optional[Decimal]:
    data = get_price_data(ticker)
    return data["prev_close"] if data else None


def get_current_price(ticker: str) -> Optional[Decimal]:
    data = get_price_data(ticker)
    return data["current"] if data else None


def get_usd_krw_rate() -> Optional[Decimal]:
    """USD/KRW 실시간 환율. yfinance 'KRW=X' 티커 사용. st.cache_data 캐시."""
    return _cached_krw_rate()


def clear_cache() -> None:
    _cached_price_data.clear()
    _cached_friday_data.clear()
    _cached_krw_rate.clear()


def ticker_exists(ticker: str) -> tuple[bool, Optional[dict]]:
    """티커가 yfinance에 존재하는지 확인. (exists, price_data) 반환."""
    try:
        data = _fetch(ticker.upper())
        return True, data
    except Exception:
        return False, None
