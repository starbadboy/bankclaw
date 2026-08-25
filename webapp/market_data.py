"""Market prices for portfolio holdings — read-only, display-only.

Daily closes come from yfinance; non-SGD tickers are converted with the
``{CUR}SGD=X`` pair from the same feed. Nothing here writes to MongoDB.
"""

from __future__ import annotations

import time

BASE_CURRENCY = "SGD"
RANGES = {"1M": ("1mo", "1d"), "3M": ("3mo", "1d"), "1Y": ("1y", "1d"), "All": ("max", "1wk")}
_TTL_SECONDS = 3600
# ponytail: per-process dict cache; move to a Mongo collection if the app runs multi-worker.
_CACHE: dict[tuple[str, str], tuple[float, tuple[str, dict[str, float]]]] = {}


def fetch_history(ticker: str, range_key: str) -> tuple[str, dict[str, float]]:
    """Return ``(currency, {iso_date: close})`` for one ticker over one range.

    Raises ``LookupError`` when the feed has no data for the symbol.
    """
    import yfinance as yf  # lazy: keeps pandas-stubbing route tests importable

    period, interval = RANGES[range_key]
    symbol = yf.Ticker(ticker)
    frame = symbol.history(period=period, interval=interval, auto_adjust=False)
    if frame.empty or "Close" not in frame:
        raise LookupError(f"No price data for {ticker}")
    try:
        currency = symbol.fast_info["currency"]
    except (KeyError, AttributeError, TypeError) as exc:
        raise LookupError(f"No currency for {ticker}") from exc
    closes = frame["Close"].dropna()
    return currency, {ts.strftime("%Y-%m-%d"): float(v) for ts, v in closes.items()}


def _cached_fetch(ticker: str, range_key: str) -> tuple[str, dict[str, float]]:
    now = time.monotonic()
    hit = _CACHE.get((ticker, range_key))
    if hit and now - hit[0] < _TTL_SECONDS:
        return hit[1]
    result = fetch_history(ticker, range_key)
    _CACHE[(ticker, range_key)] = (now, result)
    return result


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
    currency, closes = _cached_fetch(ticker, range_key)
    fx = None if currency == BASE_CURRENCY else _cached_fetch(f"{currency}{BASE_CURRENCY}=X", range_key)[1]
    return {
        "ticker": ticker,
        "currency": currency,
        "units": units,
        "points": build_market_series(closes, fx, units),
    }
