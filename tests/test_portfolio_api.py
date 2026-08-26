import asyncio
import sys
from unittest.mock import patch
from unittest.mock import MagicMock

sys.modules.setdefault("pandas", MagicMock())
sys.modules.setdefault("streamlit", MagicMock())

import pytest
from fastapi import HTTPException

from webapp.api import (
    _DASHBOARD,
    add_portfolio_asset_type,
    add_portfolio_goal,
    add_portfolio_valuation,
    edit_portfolio_asset_type,
    edit_portfolio_goal,
    get_asset_market_history,
    get_goal_suggestions,
    get_portfolio_asset_types,
    get_portfolio_goals,
    get_portfolio_valuations,
    remove_portfolio_asset_type,
    remove_portfolio_goal,
    remove_portfolio_valuation,
    serve_root,
    serve_spa,
)
from webapp.dashboard_assets import asset_version
from webapp.goal_advisor import AdvisorBusy, AdvisorNotConfigured
from webapp.market_data import MarketDataError


class _JsonRequest:
    def __init__(self, body):
        self._body = body

    async def json(self):
        return self._body


def test_custom_asset_type_api_is_user_scoped():
    asset_types = [{"id": "custom_type-id", "name": "CPF", "color": "#8B5CF6"}]
    request = _JsonRequest({"name": "CPF", "color": "#8B5CF6"})

    with (
        patch("webapp.api.list_asset_types", return_value=asset_types) as mock_list,
        patch("webapp.api.create_asset_type", return_value=asset_types[0]) as mock_create,
    ):
        listed = asyncio.run(get_portfolio_asset_types(user="owner@example.com"))
        created = asyncio.run(add_portfolio_asset_type(request, user="owner@example.com"))

    assert listed == {"asset_types": asset_types}
    assert created == {"asset_type": asset_types[0]}
    mock_list.assert_called_once_with("owner@example.com")
    mock_create.assert_called_once_with("owner@example.com", {"name": "CPF", "color": "#8B5CF6"})


def test_custom_asset_type_api_updates_and_deletes_exact_type():
    updated_type = {"id": "custom_type-id", "name": "CPF OA", "color": "#0F766E"}
    request = _JsonRequest({"name": "CPF OA", "color": "#0F766E"})

    with (
        patch("webapp.api.update_asset_type", return_value=updated_type) as mock_update,
        patch("webapp.api.delete_asset_type", return_value={"deleted": 1}) as mock_delete,
    ):
        updated = asyncio.run(edit_portfolio_asset_type("custom_type-id", request, user="owner@example.com"))
        deleted = asyncio.run(remove_portfolio_asset_type("custom_type-id", user="owner@example.com"))

    assert updated == {"asset_type": updated_type}
    assert deleted == {"deleted": 1}
    mock_update.assert_called_once_with(
        "owner@example.com",
        "custom_type-id",
        {"name": "CPF OA", "color": "#0F766E"},
    )
    mock_delete.assert_called_once_with("owner@example.com", "custom_type-id")


def test_custom_asset_type_api_returns_repository_errors_as_bad_requests():
    request = _JsonRequest({"name": "Cash & savings", "color": "#8B5CF6"})

    with (
        patch("webapp.api.create_asset_type", side_effect=ValueError("built-in type exists")),
        pytest.raises(HTTPException) as exc_info,
    ):
        asyncio.run(add_portfolio_asset_type(request, user="owner@example.com"))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "built-in type exists"


def test_get_portfolio_valuations_uses_authenticated_user_scope():
    history = [{"as_of_date": "2026-04-30", "value": 1250.0}]

    with patch("webapp.api.list_valuations", return_value=history) as mock_list:
        result = asyncio.run(get_portfolio_valuations("asset", "asset-id", user="owner@example.com"))

    assert result == {"valuations": history}
    mock_list.assert_called_once_with("owner@example.com", "asset", "asset-id")


def test_post_portfolio_valuation_records_exact_date_and_value():
    saved = {"as_of_date": "2026-04-30", "value": 1250.0}
    request = _JsonRequest({"as_of_date": "2026-04-30", "value": 1250.0})

    with patch("webapp.api.record_valuation", return_value=saved) as mock_record:
        result = asyncio.run(add_portfolio_valuation("asset", "asset-id", request, user="owner@example.com"))

    assert result == {"valuation": saved}
    mock_record.assert_called_once_with(
        "owner@example.com",
        "asset",
        "asset-id",
        {"as_of_date": "2026-04-30", "value": 1250.0},
    )


def test_delete_portfolio_valuation_removes_exact_date():
    with patch("webapp.api.delete_valuation", return_value={"deleted": 1}) as mock_delete:
        result = asyncio.run(
            remove_portfolio_valuation(
                "debt",
                "debt-id",
                "2026-04-30",
                user="owner@example.com",
            )
        )

    assert result == {"deleted": 1}
    mock_delete.assert_called_once_with("owner@example.com", "debt", "debt-id", "2026-04-30")


def test_portfolio_valuation_errors_are_returned_as_bad_requests():
    request = _JsonRequest({"as_of_date": "bad-date", "value": 1250.0})

    with (
        patch("webapp.api.record_valuation", side_effect=ValueError("invalid valuation")),
        pytest.raises(HTTPException) as exc_info,
    ):
        asyncio.run(add_portfolio_valuation("asset", "asset-id", request, user="owner@example.com"))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "invalid valuation"


def test_goal_api_is_user_scoped():
    with (
        patch("webapp.api._MONGO", True),
        patch("webapp.api.list_goals", return_value=[{"id": "g1"}]) as mock_list,
        patch("webapp.api.create_goal", return_value={"id": "g1"}) as mock_create,
        patch("webapp.api.update_goal", return_value={"id": "g1"}) as mock_update,
        patch("webapp.api.delete_goal", return_value={"deleted": 1}) as mock_delete,
    ):
        listed = asyncio.run(get_portfolio_goals(user="owner@example.com"))
        created = asyncio.run(
            add_portfolio_goal(_JsonRequest({"name": "First 100k", "target_amount": 100000}), user="owner@example.com")
        )
        updated = asyncio.run(
            edit_portfolio_goal("g1", _JsonRequest({"target_amount": 120000}), user="owner@example.com")
        )
        deleted = asyncio.run(remove_portfolio_goal("g1", user="owner@example.com"))

    assert listed == {"goals": [{"id": "g1"}]}
    assert created == {"goal": {"id": "g1"}}
    assert updated == {"goal": {"id": "g1"}}
    assert deleted == {"deleted": 1}
    assert mock_list.call_args.args == ("owner@example.com",)
    assert mock_create.call_args.args[0] == "owner@example.com"
    assert mock_update.call_args.args[:2] == ("owner@example.com", "g1")
    assert mock_delete.call_args.args == ("owner@example.com", "g1")


def test_goal_api_returns_repository_errors_as_bad_requests():
    with (
        patch("webapp.api._MONGO", True),
        patch("webapp.api.create_goal", side_effect=ValueError("target_amount must be greater than zero")),
        patch("webapp.api.update_goal", side_effect=ValueError("Goal not found")),
        patch("webapp.api.delete_goal", side_effect=ValueError("Goal not found")),
    ):
        with pytest.raises(HTTPException) as create_err:
            asyncio.run(add_portfolio_goal(_JsonRequest({"name": "G", "target_amount": 0}), user="owner@example.com"))
        with pytest.raises(HTTPException) as update_err:
            asyncio.run(edit_portfolio_goal("bad", _JsonRequest({"name": "X"}), user="owner@example.com"))
        with pytest.raises(HTTPException) as delete_err:
            asyncio.run(remove_portfolio_goal("bad", user="owner@example.com"))

    assert create_err.value.status_code == 400
    assert create_err.value.detail == "target_amount must be greater than zero"
    assert update_err.value.status_code == 400
    assert delete_err.value.status_code == 400


def _portfolio_with(asset):
    return {"assets": [asset], "debts": []}


def test_market_history_requires_ticker_and_units_on_the_asset():
    bare = {"id": "a1", "name": "Cash", "ticker": None, "units": None}
    with patch("webapp.api.list_portfolio", return_value=_portfolio_with(bare)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_asset_market_history("a1", range="1Y", user="owner@example.com"))
    assert exc.value.status_code == 400


def test_market_history_returns_series_for_priced_asset():
    asset = {"id": "a1", "name": "ADSK", "ticker": "ADSK", "units": 672.0}
    series = {
        "ticker": "ADSK",
        "currency": "USD",
        "units": 672.0,
        "points": [{"date": "2026-08-01", "price": 1.0, "value": 672.0}],
    }
    with (
        patch("webapp.api.list_portfolio", return_value=_portfolio_with(asset)),
        patch("webapp.api.get_market_history", return_value=series) as mock_history,
    ):
        result = asyncio.run(get_asset_market_history("a1", range="3M", user="owner@example.com"))

    assert result == series
    mock_history.assert_called_once_with("ADSK", 672.0, "3M")


def test_market_history_maps_feed_failures_to_502_and_bad_range_to_400():
    asset = {"id": "a1", "name": "ADSK", "ticker": "NOPE", "units": 1.0}
    with (
        patch("webapp.api.list_portfolio", return_value=_portfolio_with(asset)),
        patch("webapp.api.get_market_history", side_effect=MarketDataError("No price data for NOPE")),
    ):
        with pytest.raises(HTTPException) as feed_exc:
            asyncio.run(get_asset_market_history("a1", range="1Y", user="owner@example.com"))
    assert feed_exc.value.status_code == 502

    with (
        patch("webapp.api.list_portfolio", return_value=_portfolio_with(asset)),
        patch("webapp.api.get_market_history", side_effect=ValueError("pandas: unsupported period")) as feed,
    ):
        with pytest.raises(HTTPException) as value_exc:
            asyncio.run(get_asset_market_history("a1", range="1Y", user="owner@example.com"))
        with pytest.raises(HTTPException) as range_exc:
            asyncio.run(get_asset_market_history("a1", range="5Y", user="owner@example.com"))
    assert value_exc.value.status_code == 502  # library ValueErrors are feed failures, not client errors
    assert range_exc.value.status_code == 400
    assert feed.call_count == 1  # bad range is rejected before the feed is called


def test_market_history_unknown_asset_is_400():
    with patch("webapp.api.list_portfolio", return_value={"assets": [], "debts": []}):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_asset_market_history("missing", range="1Y", user="owner@example.com"))
    assert exc.value.status_code == 400


def test_market_history_hides_internal_errors_but_keeps_feed_messages():
    asset = {"id": "a1", "name": "ADSK", "ticker": "ADSK", "units": 1.0}
    with (
        patch("webapp.api.list_portfolio", return_value=_portfolio_with(asset)),
        patch("webapp.api.get_market_history", side_effect=KeyError("Close")),
    ):
        with pytest.raises(HTTPException) as internal:
            asyncio.run(get_asset_market_history("a1", range="1Y", user="owner@example.com"))
    assert internal.value.status_code == 502
    assert "Close" not in internal.value.detail

    with (
        patch("webapp.api.list_portfolio", return_value=_portfolio_with(asset)),
        patch("webapp.api.get_market_history", side_effect=ValueError("could not convert string to float: 'n/a'")),
    ):
        with pytest.raises(HTTPException) as library:
            asyncio.run(get_asset_market_history("a1", range="1Y", user="owner@example.com"))
    assert library.value.detail == "Market data unavailable"  # library ValueErrors are internal too

    legacy_bad = {"id": "a1", "name": "X", "ticker": "../../v1/test", "units": 1.0}
    with (
        patch("webapp.api.list_portfolio", return_value=_portfolio_with(legacy_bad)),
        patch("webapp.api.get_market_history") as never,
    ):
        with pytest.raises(HTTPException) as unsafe:
            asyncio.run(get_asset_market_history("a1", range="1Y", user="owner@example.com"))
        never.assert_not_called()
    assert unsafe.value.status_code == 400

    with (
        patch("webapp.api.list_portfolio", return_value=_portfolio_with(asset)),
        patch("webapp.api.get_market_history", side_effect=MarketDataError("No price data for ADSK")),
    ):
        with pytest.raises(HTTPException) as feed:
            asyncio.run(get_asset_market_history("a1", range="1Y", user="owner@example.com"))
    assert feed.value.detail == "Market data unavailable: No price data for ADSK"


def _suggestion_portfolio_patches():
    return (
        patch(
            "webapp.api.list_portfolio",
            return_value={
                "assets": [{"id": "a1", "name": "X", "kind": "cash", "value": 5.0}],
                "debts": [{"id": "d1", "name": "L", "kind": "loan", "value": 2.0}],
            },
        ),
        patch(
            "webapp.api.list_valuations",
            side_effect=lambda user, item_type, item_id: [{"as_of_date": "2026-08-01", "value": 1.0}],
        ),
        patch("webapp.api.list_goals", return_value=[]),
        patch("webapp.api.list_asset_types", return_value=[{"id": "custom_1", "name": "CPF", "color": "#000000"}]),
    )


def test_goal_suggestions_route_builds_the_snapshot_server_side_and_passes_flags():
    result = {"suggestions": [], "snapshot": {"net": 3.0, "goal_count": 0}, "generated_at": "now", "from_cache": False}
    p1, p2, p3, p4 = _suggestion_portfolio_patches()
    with p1, p2, p3, p4, patch("webapp.goal_advisor.get_suggestions", return_value=result) as advisor:
        out = asyncio.run(
            get_goal_suggestions(_JsonRequest({"force_refresh": True, "dismiss": "abc"}), user="owner@example.com")
        )
        portfolio = advisor.call_args.args[1]()  # lazy builder: only called when generating (inside the patches)

    assert out == result
    kwargs = advisor.call_args.kwargs
    assert advisor.call_args.args[0] == "owner@example.com"
    assert set(portfolio["histories"]) == {"asset:a1", "debt:d1"}
    assert portfolio["asset_kind_names"] == {"custom_1": "CPF"}  # built-in names live in the advisor
    assert kwargs == {"force_refresh": True, "dismiss": "abc"}


def test_goal_suggestions_route_rejects_non_string_dismiss_and_ignores_empty():
    result = {"suggestions": [], "snapshot": {}, "generated_at": "now", "from_cache": True}
    p1, p2, p3, p4 = _suggestion_portfolio_patches()
    with p1, p2, p3, p4, patch("webapp.goal_advisor.get_suggestions", return_value=result) as advisor:
        with pytest.raises(HTTPException) as bad:
            asyncio.run(get_goal_suggestions(_JsonRequest({"dismiss": {"$each": ["a"]}}), user="owner@example.com"))
        with pytest.raises(HTTPException) as too_long:
            asyncio.run(get_goal_suggestions(_JsonRequest({"dismiss": "x" * 65}), user="owner@example.com"))
        asyncio.run(get_goal_suggestions(_JsonRequest({"dismiss": ""}), user="owner@example.com"))
    assert bad.value.status_code == 400 and too_long.value.status_code == 400
    assert advisor.call_args.kwargs["dismiss"] is None


def test_goal_suggestions_route_maps_missing_key_to_503_and_failures_to_502():
    p1, p2, p3, p4 = _suggestion_portfolio_patches()
    with (
        p1,
        p2,
        p3,
        p4,
        patch("webapp.goal_advisor.get_suggestions", side_effect=AdvisorNotConfigured("DEEPSEEK_API_KEY not set")),
    ):
        with pytest.raises(HTTPException) as no_key:
            asyncio.run(get_goal_suggestions(_JsonRequest({}), user="owner@example.com"))
    assert no_key.value.status_code == 503 and "DEEPSEEK_API_KEY" in no_key.value.detail
    p1, p2, p3, p4 = _suggestion_portfolio_patches()
    with (
        p1,
        p2,
        p3,
        p4,
        patch("webapp.goal_advisor.get_suggestions", side_effect=ValueError("Expecting value: line 1")),
    ):
        with pytest.raises(HTTPException) as bad_json:
            asyncio.run(get_goal_suggestions(_JsonRequest({}), user="owner@example.com"))
    assert bad_json.value.status_code == 502  # a ValueError from the model/JSON path is not "not configured"
    p1, p2, p3, p4 = _suggestion_portfolio_patches()
    with p1, p2, p3, p4, patch("webapp.goal_advisor.get_suggestions", side_effect=RuntimeError("boom")):
        with pytest.raises(HTTPException) as failed:
            asyncio.run(get_goal_suggestions(_JsonRequest({}), user="owner@example.com"))
    assert failed.value.status_code == 502
    assert "boom" not in failed.value.detail


def test_goal_route_returns_400_for_invalid_kind_payloads():
    with patch("webapp.api.create_goal", side_effect=ValueError("Unknown goal kind 'lottery'")):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                add_portfolio_goal(
                    _JsonRequest({"kind": "lottery", "name": "x", "target_amount": 1}), user="owner@example.com"
                )
            )
    assert exc.value.status_code == 400 and "lottery" in exc.value.detail


def test_goal_suggestions_route_reports_busy_as_429():
    p1, p2, p3, p4 = _suggestion_portfolio_patches()
    with p1, p2, p3, p4, patch("webapp.goal_advisor.get_suggestions", side_effect=AdvisorBusy("busy")):
        with pytest.raises(HTTPException) as busy:
            asyncio.run(get_goal_suggestions(_JsonRequest({}), user="owner@example.com"))
    assert busy.value.status_code == 429


# --- dashboard shell: versioned index.html, no path traversal --------------------------------------------------


def test_root_serves_index_with_the_asset_version_substituted():
    resp = asyncio.run(serve_root())
    body = resp.body.decode()
    assert "__V__" not in body
    assert f"?v={asset_version(_DASHBOARD)}" in body
    assert resp.headers["cache-control"] == "no-cache"


_HOSTILE_PATHS = [
    "../.env",
    "../webapp/api.py",
    "app/../../.env",
    "app/" + "../" * 12 + "etc/passwd",
    "a\x00b.js",  # NUL byte → ValueError from resolve()
    "..\x00/.env",
    "x" * 300 + ".js",  # over NAME_MAX → OSError from is_file()
    "app/" + "x" * 300 + ".js",
]


@pytest.mark.parametrize("path", _HOSTILE_PATHS)
def test_spa_fallback_never_serves_files_outside_the_dashboard(path):
    resp = asyncio.run(serve_spa(path))
    # anything that is not a dashboard asset falls back to the versioned index.html — never the escaped file
    assert resp.headers["content-type"].startswith("text/html")
    assert b"MONGODB_URL" not in resp.body and b"FastAPI" not in resp.body


def test_spa_serves_a_real_dashboard_asset():
    resp = asyncio.run(serve_spa("app/data.js"))
    assert resp.path.endswith("dashboard/app/data.js")
