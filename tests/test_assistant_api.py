import asyncio
import sys
from unittest.mock import MagicMock, patch

sys.modules.setdefault("pandas", MagicMock())
sys.modules.setdefault("streamlit", MagicMock())

import pytest
from fastapi import HTTPException
from pymongo.errors import ServerSelectionTimeoutError

from webapp.api import assistant_message
from webapp.assistant import AssistantInputError, AssistantNotConfigured, ThreadNotFound

USER = "owner@example.com"


class _JsonRequest:
    def __init__(self, body):
        self._body = body

    async def json(self):
        return self._body


def _send(body, **send_kwargs):
    with patch("webapp.assistant.send_message", **send_kwargs) as send:
        out = asyncio.run(assistant_message(_JsonRequest(body), user=USER))
    return out, send


def test_message_route_passes_user_thread_profile_and_message_through():
    result = {"thread": {"id": "t1", "title": "Q", "updated_at": "now"}, "reply": "A"}
    out, send = _send({"thread_id": "t1", "profile_id": "p1", "message": "Q"}, return_value=result)
    assert out == result
    user, profile_id, thread_id, message = send.call_args.args[:4]
    assert (user, profile_id, thread_id, message) == (USER, "p1", "t1", "Q")


def test_message_route_record_loader_applies_the_profile_rule():
    _, send = _send({"message": "Q"}, return_value={"thread": {}, "reply": ""})
    load_records = send.call_args.args[4]
    df = MagicMock(empty=False)
    df.to_dict.return_value = [{"amount": -1.0}]
    with (
        patch("webapp.api.ensure_main_profile", return_value={"id": "main"}),
        patch("webapp.api.get_transactions_by_date_range", return_value=df) as query,
    ):
        assert load_records("2026-09-01", "2026-09-30", "all") == [{"amount": -1.0}]
        load_records("2026-09-01", "2026-09-30", "p2")
    assert query.call_args_list[0].args == ("2026-09-01", "2026-09-30", USER)
    assert query.call_args_list[0].kwargs == {"profile_id": None, "main_profile_id": "main"}
    assert query.call_args_list[1].kwargs["profile_id"] == "p2"


def test_message_route_rejects_non_string_ids():
    for body in ({"message": "Q", "thread_id": {"$ne": None}}, {"message": "Q", "profile_id": "x" * 65}):
        with pytest.raises(HTTPException) as err:
            _send(body)
        assert err.value.status_code == 400


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (AssistantInputError("Message must be 1–2000 characters"), 400),
        (ThreadNotFound("Thread not found"), 404),
        (AssistantNotConfigured("AI assistant not configured"), 503),
        (ServerSelectionTimeoutError("mongo down"), 503),
        (RuntimeError("secret internal detail"), 502),
    ],
)
def test_message_route_maps_errors(error, status):
    with pytest.raises(HTTPException) as err:
        _send({"message": "Q"}, side_effect=error)
    assert err.value.status_code == status
    assert "secret internal detail" not in str(err.value.detail)


def test_message_route_without_mongo_is_503(monkeypatch):
    monkeypatch.setattr("webapp.api._MONGO", False)
    with pytest.raises(HTTPException) as err:
        _send({"message": "Q"})
    assert err.value.status_code == 503
