import asyncio
import sys
from unittest.mock import patch
from unittest.mock import MagicMock

sys.modules.setdefault("pandas", MagicMock())
sys.modules.setdefault("streamlit", MagicMock())

import pytest
from fastapi import HTTPException

from webapp.api import (
    add_portfolio_valuation,
    get_portfolio_valuations,
    remove_portfolio_valuation,
)


class _JsonRequest:
    def __init__(self, body):
        self._body = body

    async def json(self):
        return self._body


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
