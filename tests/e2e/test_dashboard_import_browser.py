"""Opt-in browser check with real authentication/PDF parsing and isolated services."""

import json
import os
import re
import socket
import threading
import time
from pathlib import Path

import httpx
import httpx2
import pandas as pd
import pytest
import uvicorn
from typesafe_sdk import RetryPolicy, TypeSafeClient

from webapp import api, categorizer, db, user_repository
from webapp.auth import hash_password

pytestmark = pytest.mark.skipif(
    os.getenv("BANKCLAW_RUN_BROWSER_TESTS") != "1", reason="Set BANKCLAW_RUN_BROWSER_TESTS=1 to run browser checks"
)


@pytest.fixture
def isolated_dashboard(monkeypatch):
    monkeypatch.setattr(api, "_MONGO", False)
    monkeypatch.setenv("TYPESAFE_API_KEY", "browser-test-key")
    monkeypatch.setenv("TYPESAFE_DEFAULT_MODEL", "jev-latest")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    record = {"password_hash": hash_password("browser-test-password")}
    monkeypatch.setattr(user_repository, "authenticate_user", lambda email: record)

    def reject_database():
        raise RuntimeError("Database access is disabled in browser checks")

    monkeypatch.setattr(db, "get_db", reject_database)
    monkeypatch.setattr(user_repository, "get_db", reject_database)
    monkeypatch.setattr(categorizer, "get_category_memory", lambda **kwargs: pd.DataFrame())
    requests = []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
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

    monkeypatch.setattr(categorizer, "TypeSafeClient", client)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    address = f"http://127.0.0.1:{listener.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(api.app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started, "Isolated dashboard failed to start"
        assert httpx.get(f"{address}/api/health").json()["status"] == "ok"
        yield address, requests
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()


def test_sign_in_pdf_import_and_ledger(isolated_dashboard, tmp_path):
    playwright_api = pytest.importorskip("playwright.sync_api")
    address, requests = isolated_dashboard
    fixture = Path(__file__).parents[1] / "fixtures" / "example_statement.pdf"
    expected = pd.read_csv(fixture.with_suffix(".csv"))
    errors = []
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(address)
            page.get_by_role("button", name="Sign in", exact=True).first.click(timeout=60_000)
            page.get_by_placeholder("you@example.com").fill("browser@example.com")
            page.locator('input[type="password"]').fill("browser-test-password")
            page.get_by_role("button", name="Sign in", exact=True).click()
            page.locator(".sidebar").get_by_text("Import", exact=True).click(timeout=30_000)
            with page.expect_response(
                lambda response: response.url.endswith("/api/import") and response.request.method == "POST"
            ) as imported:
                page.locator('input[type="file"]').set_input_files(str(fixture))
            response = imported.value
            assert response.status == 200
            payload = response.json()
            assert payload["results"][0]["status"] == "ok"
            assert payload["saved"] == 0
            assert len(payload["transactions"]) == len(expected)
            assert [row["description"] for row in payload["transactions"]] == expected["description"].tolist()
            assert [row["amount"] for row in payload["transactions"]] == expected["amount"].tolist()
            assert {row["category"] for row in payload["transactions"]} == {"Transport"}
            assert requests
            assert all(request["model"] == "jev-latest" for request in requests)
            page.get_by_text(f"{len(expected)} transactions imported", exact=True).wait_for(state="visible")
            page.get_by_role("button", name=re.compile("View in ledger")).click()
            assert page.locator(".sidebar .nav-item.active").inner_text().strip() == "Transactions"
            page.reload()
            page.locator(".sidebar").wait_for(state="visible")
            assert page.locator(".sidebar .nav-item.active").inner_text().strip() == "Transactions"
            page.screenshot(path=str(tmp_path / "dashboard-import.png"))
            assert not errors, errors
        finally:
            browser.close()
