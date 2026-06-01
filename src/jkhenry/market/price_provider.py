"""yfinance 래퍼 + 세션 캐시.

동일 세션 내 같은 티커는 캐시에서 반환하여 중복 API 호출 방지.
네트워크 실패 시 예외를 발생시키지 않고 None을 반환 → 호출자가 처리.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import yfinance as yf

_cache: dict[str, dict] = {}  # {ticker: {"prev_close": Decimal, "current": Decimal}}
_friday_cache: dict[str, dict] = {}  # {ticker: {"date": date, "close": Decimal}}


def _fetch(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    hist = t.history(period="5d")
    if hist.empty:
        raise ValueError(f"{ticker}: yfinance 데이터 없음")
    prev_close = Decimal(str(round(float(hist["Close"].iloc[-2]), 4)))
    current = Decimal(str(round(float(hist["Close"].iloc[-1]), 4)))
    return {"prev_close": prev_close, "current": current}


def get_price_data(ticker: str, force_refresh: bool = False) -> Optional[dict]:
    """
    {"prev_close": Decimal, "current": Decimal} 반환.
    실패 시 None 반환.
    """
    key = ticker.upper()
    if not force_refresh and key in _cache:
        return _cache[key]
    try:
        data = _fetch(key)
        _cache[key] = data
        return data
    except Exception:
        return None


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


def get_friday_close(ticker: str, force_refresh: bool = False) -> Optional[dict]:
    """
    VR 기준가 — '직전 금요일 종가'를 {"date": date, "close": Decimal}로 반환.

    yfinance 최근 한 달 일봉에서 직전 금요일(공휴일 시 그 주 마지막 거래일) 종가를 고른다.
    실패 시 None.
    """
    key = ticker.upper()
    if not force_refresh and key in _friday_cache:
        return _friday_cache[key]
    try:
        t = yf.Ticker(key)
        hist = t.history(period="1mo")
        if hist.empty:
            return None
        bars = [
            (idx.date(), Decimal(str(round(float(close), 4))))
            for idx, close in hist["Close"].items()
        ]
        result = _pick_friday_close(bars, date.today())
        if result is not None:
            _friday_cache[key] = result
        return result
    except Exception:
        return None


def get_prev_close(ticker: str) -> Optional[Decimal]:
    data = get_price_data(ticker)
    return data["prev_close"] if data else None


def get_current_price(ticker: str) -> Optional[Decimal]:
    data = get_price_data(ticker)
    return data["current"] if data else None


def clear_cache() -> None:
    _cache.clear()
    _friday_cache.clear()


def ticker_exists(ticker: str) -> tuple[bool, Optional[dict]]:
    """티커가 yfinance에 존재하는지 확인. (exists, price_data) 반환."""
    data = get_price_data(ticker.upper(), force_refresh=True)
    return data is not None, data
