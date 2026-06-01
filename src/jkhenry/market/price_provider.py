"""yfinance 래퍼 + 세션 캐시.

동일 세션 내 같은 티커는 캐시에서 반환하여 중복 API 호출 방지.
네트워크 실패 시 예외를 발생시키지 않고 None을 반환 → 호출자가 처리.
"""

from decimal import Decimal
from typing import Optional

import yfinance as yf

_cache: dict[str, dict] = {}  # {ticker: {"prev_close": Decimal, "current": Decimal}}


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


def get_prev_close(ticker: str) -> Optional[Decimal]:
    data = get_price_data(ticker)
    return data["prev_close"] if data else None


def get_current_price(ticker: str) -> Optional[Decimal]:
    data = get_price_data(ticker)
    return data["current"] if data else None


def clear_cache() -> None:
    _cache.clear()


def ticker_exists(ticker: str) -> tuple[bool, Optional[dict]]:
    """티커가 yfinance에 존재하는지 확인. (exists, price_data) 반환."""
    data = get_price_data(ticker.upper(), force_refresh=True)
    return data is not None, data
