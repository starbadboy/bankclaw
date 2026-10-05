import json
from types import SimpleNamespace
from unittest.mock import patch

import httpx2
import pandas as pd
import pytest
from typesafe_sdk import RetryPolicy, TypeSafeAPIError, TypeSafeClient

from webapp.categorizer import categorize_transactions


def transactions():
    return pd.DataFrame({"description": ["GRAB TAXI", "NTUC FAIRPRICE"]}, index=[5, 9])


def test_jev_sdk_serializes_choices_and_maps_reordered_answers(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    requests = []

    def respond(request):
        requests.append(request)
        return httpx2.Response(
            200,
            json={
                "model": "jev-latest",
                "answers": {
                    "transaction_1": {
                        "type": "choice",
                        "choice": "Food & Dining",
                        "probabilities": {"Transport": 0.1, "Food & Dining": 0.8, "Other": 0.1},
                        "confidence": 0.8,
                    },
                    "transaction_0": {
                        "type": "choice",
                        "choice": "Transport",
                        "probabilities": {"Transport": 0.8, "Food & Dining": 0.1, "Other": 0.1},
                        "confidence": 0.8,
                    },
                },
                "usage": {"input_tokens": 100, "output_tokens": 30},
            },
        )

    def client(**kwargs):
        return TypeSafeClient(**kwargs, transport=httpx2.MockTransport(respond))

    df = transactions()
    with patch("webapp.categorizer.TypeSafeClient", side_effect=client):
        result = categorize_transactions(df, allowed_categories=["Transport", "Food & Dining", "Other"])

    assert result.index.tolist() == [5, 9]
    assert result["category"].tolist() == ["Transport", "Food & Dining"]
    assert "category" not in df.columns
    assert requests[0].url.path == "/v1/systemone"
    assert requests[0].headers["Authorization"] == "Bearer test-key"
    body = json.loads(requests[0].content)
    assert body["state"]["transactions"] == {"transaction_0": "GRAB TAXI", "transaction_1": "NTUC FAIRPRICE"}
    for key, question in body["questions"].items():
        assert question["type"] == "choice"
        assert f"transactions.{key}" in question["instructions"]
        assert set(question["criteria"]) == {"Transport", "Food & Dining", "Other"}


@pytest.mark.parametrize("model,expected", [(None, "jev-latest"), (" ", "jev-latest"), (" jev-1.13.0 ", "jev-1.13.0")])
def test_jev_model_configuration(monkeypatch, model, expected):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    if model is None:
        monkeypatch.delenv("TYPESAFE_DEFAULT_MODEL", raising=False)
    else:
        monkeypatch.setenv("TYPESAFE_DEFAULT_MODEL", model)
    with patch("webapp.categorizer.TypeSafeClient") as client:
        client.return_value.__enter__.return_value.system_one.return_value = SimpleNamespace(choices={})
        categorize_transactions(transactions())
    client.assert_called_once_with(api_key="test-key", model=expected, timeout=30.0)
    client.return_value.__exit__.assert_called_once()


def test_deepseek_key_cannot_enable_jev(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "old-key")
    with pytest.raises(ValueError, match="TYPESAFE_API_KEY"):
        categorize_transactions(transactions())


def test_missing_jev_answer_does_not_shift_other_rows(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    with patch("webapp.categorizer.TypeSafeClient") as client:
        client.return_value.__enter__.return_value.system_one.return_value = SimpleNamespace(
            choices={
                "transaction_1": SimpleNamespace(choice="Food & Dining"),
            }
        )
        result = categorize_transactions(transactions())
    assert result["category"].tolist() == ["Other", "Food & Dining"]


def test_jev_api_failure_propagates_and_closes_client(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    clients = []

    def client(**kwargs):
        http_client = httpx2.Client(
            transport=httpx2.MockTransport(lambda request: httpx2.Response(401, json={"error": "Invalid API key"})),
        )
        clients.append(http_client)
        return TypeSafeClient(**kwargs, retry=RetryPolicy(max_retries=0), http_client=http_client)

    with patch("webapp.categorizer.TypeSafeClient", side_effect=client), pytest.raises(TypeSafeAPIError):
        categorize_transactions(transactions())
    assert clients[0].is_closed


def test_empty_transactions_do_not_require_jev(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with patch("webapp.categorizer.TypeSafeClient") as client:
        result = categorize_transactions(pd.DataFrame({"description": []}))
    assert result.empty and "category" in result.columns
    client.assert_not_called()


@pytest.mark.parametrize("batch_size", [0, -1])
def test_invalid_batch_size(batch_size):
    with pytest.raises(ValueError, match="batch_size"):
        categorize_transactions(transactions(), batch_size=batch_size)


def test_jev_choice_limit_is_checked_before_request():
    with pytest.raises(ValueError, match="255"):
        categorize_transactions(
            transactions(), allowed_categories=[*[f"Category {idx}" for idx in range(255)], "Other"]
        )
