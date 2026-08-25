"""Market prices for portfolio holdings — read-only, display-only.

Daily closes come from yfinance; non-SGD tickers are converted with the
``{CUR}SGD=X`` pair from the same feed. Nothing here writes to MongoDB.
"""

from __future__ import annotations

import re
import time
from functools import lru_cache

BASE_CURRENCY = "SGD"
# Yahoo symbol shapes: BRK-B, ^GSPC, USDSGD=X, D05.SI, BTC-USD. Also the write-side rule in portfolio_repository.
TICKER_PATTERN = re.compile(r"^[A-Z0-9.^=\-]{1,16}$")
RANGES = {"1M": ("1mo", "1d"), "3M": ("3mo", "1d"), "1Y": ("1y", "1d"), "All": ("max", "1wk")}
_TTL_SECONDS = 3600


class MarketDataError(LookupError):
    """Feed-level failure whose message is safe to show to the user (unknown symbol, no FX rates)."""


# Feeds that quote in minor units (pence, cents): major-unit code and the scale to apply to closes.
_MINOR_UNITS = {"GBp": ("GBP", 0.01), "ZAc": ("ZAR", 0.01), "ILA": ("ILS", 0.01)}


def fetch_history(ticker: str, range_key: str) -> tuple[str, dict[str, float]]:
    """Return ``(currency, {iso_date: close})`` for one ticker over one range.

    Raises ``MarketDataError`` when the feed has no data for the symbol.
    """
    import yfinance as yf  # lazy: keeps pandas-stubbing route tests importable

    period, interval = RANGES[range_key]
    symbol = yf.Ticker(ticker)
    frame = symbol.history(period=period, interval=interval, auto_adjust=False)
    if frame.empty or "Close" not in frame:
        raise MarketDataError(f"No price data for {ticker}")
    try:
        currency = symbol.fast_info["currency"]
    except (KeyError, AttributeError, TypeError) as exc:
        raise MarketDataError(f"No currency for {ticker}") from exc
    closes = frame["Close"].dropna()
    return currency, {ts.strftime("%Y-%m-%d"): float(v) for ts, v in closes.items()}


# ponytail: per-process LRU keyed by a 1h time bucket; move to a Mongo collection if the app runs multi-worker.
@lru_cache(maxsize=256)
def _fetch_bucketed(ticker: str, range_key: str, _bucket: int) -> tuple[str, dict[str, float]]:
    return fetch_history(ticker, range_key)


def _cached_fetch(ticker: str, range_key: str) -> tuple[str, dict[str, float]]:
    return _fetch_bucketed(ticker, range_key, int(time.monotonic() // _TTL_SECONDS))


def clear_cache() -> None:
    _fetch_bucketed.cache_clear()


def build_market_series(closes: dict[str, float], fx: dict[str, float] | None, units: float) -> list[dict]:
    """Convert dated closes into ``[{date, price, value}]`` in base currency.

    FX is forward-filled onto the close dates; dates before the first FX point use that first rate.
    """
    fx_dates = sorted(fx) if fx else []
    rate = fx[fx_dates[0]] if fx_dates else 1.0
    fx_index = 0
    points = []
    for day in sorted(closes):
        while fx_index < len(fx_dates) and fx_dates[fx_index] <= day:
            rate = fx[fx_dates[fx_index]]
            fx_index += 1
        price = closes[day] * rate
        points.append({"date": day, "price": round(price, 4), "value": round(price * units, 2)})
    return points


def get_market_history(ticker: str, units: float, range_key: str) -> dict:
    """Price and market-value history for a holding, in base currency."""
    if range_key not in RANGES:
        raise ValueError(f"range must be one of {', '.join(RANGES)}")
    ticker = str(ticker).upper()  # rows saved before the write-side rule existed may be lowercase
    if not TICKER_PATTERN.match(ticker):
        raise ValueError(f"unsupported ticker {ticker!r}")
    currency, closes = _cached_fetch(ticker, range_key)
    if currency in _MINOR_UNITS:
        currency, scale = _MINOR_UNITS[currency]
        closes = {day: close * scale for day, close in closes.items()}
    fx = None
    if currency != BASE_CURRENCY:
        fx = _cached_fetch(f"{currency}{BASE_CURRENCY}=X", range_key)[1]
        if not fx:
            raise MarketDataError(f"No {currency}{BASE_CURRENCY} rates to convert with")
    return {
        "ticker": ticker,
        "currency": currency,
        "units": units,
        "points": build_market_series(closes, fx, units),
    }
