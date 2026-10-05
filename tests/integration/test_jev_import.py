import json
from pathlib import Path
from unittest.mock import patch

import httpx2
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from typesafe_sdk import RetryPolicy, TypeSafeClient

from webapp.api import _current_user, app


@pytest.mark.parametrize("mode", ["success", "invalid_key", "missing_key"])
def test_pdf_import_uses_jev_and_preserves_failure_fallback(monkeypatch, mode):
    if mode == "missing_key":
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    else:
        monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.delenv("TYPESAFE_DEFAULT_MODEL", raising=False)
    requests = []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        if mode == "invalid_key":
            return httpx2.Response(401, json={"error": "Invalid API key"})
        return httpx2.Response(
            200,
            json={
                "model": "jev-latest",
                "answers": {
                    key: {
                        "type": "choice",
                        "choice": "Transport",
                        "probabilities": {
                            category: float(category == "Transport") for category in question["criteria"]
                        },
                        "confidence": 1.0,
                    }
                    for key, question in body["questions"].items()
                },
                "usage": {"input_tokens": 100, "output_tokens": 30},
            },
        )

    def client(**kwargs):
        return TypeSafeClient(**kwargs, retry=RetryPolicy(max_retries=0), transport=httpx2.MockTransport(respond))

    fixture = Path(__file__).parents[1] / "fixtures" / "example_statement.pdf"
    with (
        patch.dict(app.dependency_overrides, {_current_user: lambda: "smoke@example.com"}),
        patch("webapp.api._MONGO", False),
        patch("webapp.categorizer.get_category_memory", return_value=pd.DataFrame()),
        patch("webapp.categorizer.TypeSafeClient", side_effect=client),
        TestClient(app) as browser_api,
    ):
        response = browser_api.post(
            "/api/import",
            files={"files": (fixture.name, fixture.read_bytes(), "application/pdf")},
            data={"categorize": "true"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["status"] == "ok"
    assert payload["transactions"]
    assert payload["saved"] == 0
    expected_category = "Transport" if mode == "success" else "Other"
    assert {row["category"] for row in payload["transactions"]} == {expected_category}
    if mode == "missing_key":
        assert requests == []
    else:
        descriptions = [value for request in requests for value in request["state"]["transactions"].values()]
        assert descriptions == [row["description"] for row in payload["transactions"]]
        assert all(request["model"] == "jev-latest" for request in requests)
