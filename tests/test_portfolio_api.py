import asyncio
import sys
from unittest.mock import patch
from unittest.mock import MagicMock

sys.modules.setdefault("pandas", MagicMock())
sys.modules.setdefault("streamlit", MagicMock())

import pytest
from fastapi import HTTPException

from webapp.api import (
    add_portfolio_asset_type,
    add_portfolio_goal,
    add_portfolio_valuation,
    edit_portfolio_asset_type,
    edit_portfolio_goal,
    get_portfolio_asset_types,
    get_portfolio_goals,
    get_portfolio_valuations,
    remove_portfolio_asset_type,
    remove_portfolio_goal,
    remove_portfolio_valuation,
)


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
