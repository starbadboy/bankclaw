from unittest.mock import patch

import pytest

from webapp import market_data
from webapp.market_data import build_market_series, get_market_history


def test_build_series_converts_with_forward_filled_fx():
    closes = {"2026-08-03": 100.0, "2026-08-04": 110.0, "2026-08-05": 120.0}
    fx = {"2026-08-03": 1.30, "2026-08-05": 1.20}  # no FX on the 4th → carry the 3rd forward

    points = build_market_series(closes, fx, units=2)

    assert [p["date"] for p in points] == ["2026-08-03", "2026-08-04", "2026-08-05"]
    assert [p["price"] for p in points] == [130.0, 143.0, 144.0]
    assert [p["value"] for p in points] == [260.0, 286.0, 288.0]


def test_build_series_uses_first_fx_rate_before_first_fx_date():
    points = build_market_series({"2026-08-01": 10.0, "2026-08-02": 10.0}, {"2026-08-02": 1.5}, units=1)
    assert [p["price"] for p in points] == [15.0, 15.0]


def test_build_series_without_fx_keeps_native_prices_and_sorts_dates():
    points = build_market_series({"2026-08-02": 3.0, "2026-08-01": 2.0}, None, units=10)
    assert points == [
        {"date": "2026-08-01", "price": 2.0, "value": 20.0},
        {"date": "2026-08-02", "price": 3.0, "value": 30.0},
    ]


def test_build_series_rounds_price_to_4dp_and_value_to_2dp():
    points = build_market_series({"2026-08-01": 1.23456789}, {"2026-08-01": 1.0}, units=3)
    assert points == [{"date": "2026-08-01", "price": 1.2346, "value": 3.7}]


def _fake_fetch(ticker, range_key):
    if ticker == "ADSK":
        return "USD", {"2026-08-01": 100.0, "2026-08-02": 200.0}
    if ticker == "USDSGD=X":
        return "SGD", {"2026-08-01": 1.25}
    if ticker == "D05.SI":
        return "SGD", {"2026-08-01": 40.0}
    raise LookupError(ticker)


def test_get_market_history_converts_usd_and_skips_fx_for_sgd():
    market_data.clear_cache()
    with patch("webapp.market_data.fetch_history", side_effect=_fake_fetch) as fetch:
        usd = get_market_history("ADSK", 672, "1Y")
        sgd = get_market_history("D05.SI", 10, "1Y")

    assert usd["currency"] == "USD"
    assert usd["points"][-1] == {"date": "2026-08-02", "price": 250.0, "value": 168000.0}
    assert sgd["currency"] == "SGD"
    assert sgd["points"] == [{"date": "2026-08-01", "price": 40.0, "value": 400.0}]
    assert [c.args[0] for c in fetch.call_args_list] == ["ADSK", "USDSGD=X", "D05.SI"]


def test_get_market_history_caches_fetches_for_an_hour_independent_of_units():
    market_data.clear_cache()
    clock = [1000.0]
    with (
        patch("webapp.market_data.fetch_history", side_effect=_fake_fetch) as fetch,
        patch("webapp.market_data.time.monotonic", side_effect=lambda: clock[0]),
    ):
        first = get_market_history("ADSK", 1, "3M")
        second = get_market_history("ADSK", 2, "3M")
        assert fetch.call_count == 2  # ADSK + FX, once
        assert second["points"][0]["value"] == 2 * first["points"][0]["value"]

        clock[0] += 3601
        get_market_history("ADSK", 1, "3M")
        assert fetch.call_count == 4


def test_get_market_history_rejects_unknown_range():
    with pytest.raises(ValueError):
        get_market_history("ADSK", 1, "5Y")


def test_get_market_history_refuses_to_convert_without_fx_rates():
    market_data.clear_cache()

    def fetch(ticker, range_key):
        return ("USD", {"2026-08-01": 100.0}) if ticker == "ADSK" else ("SGD", {})

    with patch("webapp.market_data.fetch_history", side_effect=fetch):
        with pytest.raises(LookupError):
            get_market_history("ADSK", 1, "1Y")


def test_get_market_history_scales_minor_unit_currencies_and_pairs_the_major_unit():
    market_data.clear_cache()

    def fetch(ticker, range_key):
        if ticker == "SHEL.L":
            return "GBp", {"2026-08-01": 2500.0}  # pence
        if ticker == "GBPSGD=X":
            return "SGD", {"2026-08-01": 1.7}
        raise LookupError(ticker)

    with patch("webapp.market_data.fetch_history", side_effect=fetch) as mock_fetch:
        result = get_market_history("SHEL.L", 10, "1Y")

    assert result["currency"] == "GBP"
    assert result["points"] == [{"date": "2026-08-01", "price": 42.5, "value": 425.0}]
    assert [c.args[0] for c in mock_fetch.call_args_list] == ["SHEL.L", "GBPSGD=X"]


def test_get_market_history_rejects_unsafe_tickers_before_touching_the_feed():
    with patch("webapp.market_data.fetch_history") as fetch:
        for bad in ("../../v1/test", "AD SK", "a?b"):
            with pytest.raises(ValueError):
                get_market_history(bad, 1, "1Y")
    fetch.assert_not_called()
