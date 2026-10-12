import asyncio
import sys
from unittest.mock import MagicMock, patch

sys.modules.setdefault("pandas", MagicMock())
sys.modules.setdefault("streamlit", MagicMock())

import pytest
from fastapi import HTTPException

from webapp import auth
from webapp.api import check_auth_config, login, reset_password
from webapp.auth import hash_password, verify_auth_token

VICTIM = {"email": "victim@example.com", "password_hash": hash_password("correct-horse")}


class _JsonRequest:
    def __init__(self, body):
        self._body = body

    async def json(self):
        return self._body


def _login(body):
    return asyncio.run(login(_JsonRequest(body)))


@pytest.fixture
def accounts(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://accounts.example:27017")


def test_login_with_correct_password_issues_a_token(accounts):
    with patch("webapp.user_repository.authenticate_user", return_value=VICTIM):
        out = _login({"email": "Victim@Example.com", "password": "correct-horse"})
    assert verify_auth_token(out["token"]) == "victim@example.com"


@pytest.mark.parametrize("password", ["", None, "wrong", 123])
def test_login_without_the_right_password_is_rejected(accounts, password):
    body = {"email": "victim@example.com"} if password is None else {"email": "victim@example.com", "password": password}
    with patch("webapp.user_repository.authenticate_user", return_value=VICTIM), pytest.raises(HTTPException) as err:
        _login(body)
    assert err.value.status_code == 401


def test_login_for_unknown_or_google_only_account_is_rejected(accounts):
    for record in (None, {"email": "victim@example.com", "password_hash": "__google__"}):
        with patch("webapp.user_repository.authenticate_user", return_value=record), pytest.raises(HTTPException) as err:
            _login({"email": "victim@example.com", "password": "__google__"})
        assert err.value.status_code == 401


def test_login_fails_closed_when_the_user_store_errors(accounts):
    with (
        patch("webapp.user_repository.authenticate_user", side_effect=RuntimeError("mongo down")),
        pytest.raises(HTTPException) as err,
    ):
        _login({"email": "victim@example.com", "password": "anything"})
    assert err.value.status_code == 503


def test_login_demo_mode_only_without_a_configured_database(monkeypatch):
    monkeypatch.delenv("MONGODB_URL", raising=False)
    with patch("webapp.user_repository.authenticate_user") as store:
        out = _login({"email": "demo@example.com"})
    assert verify_auth_token(out["token"]) == "demo@example.com"
    store.assert_not_called()


def test_unauthenticated_password_reset_is_disabled():
    with patch("webapp.user_repository.update_password") as update, pytest.raises(HTTPException) as err:
        asyncio.run(reset_password(_JsonRequest({"email": "victim@example.com", "new_password": "attacker-pass"})))
    assert err.value.status_code == 410
    update.assert_not_called()


def test_default_signing_secret_is_refused_when_accounts_exist(monkeypatch, accounts):
    monkeypatch.delenv("AUTH_TOKEN_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="AUTH_TOKEN_SECRET"):
        auth.create_auth_token("victim@example.com")
    with pytest.raises(RuntimeError, match="AUTH_TOKEN_SECRET"):
        check_auth_config()


def test_dev_secret_still_works_without_a_database(monkeypatch):
    monkeypatch.delenv("AUTH_TOKEN_SECRET", raising=False)
    monkeypatch.delenv("MONGODB_URL", raising=False)
    assert verify_auth_token(auth.create_auth_token("dev@example.com")) == "dev@example.com"
    check_auth_config()


def test_unknown_email_costs_a_password_check_like_a_wrong_password(accounts):
    with (
        patch("webapp.user_repository.authenticate_user", return_value=None),
        patch("webapp.auth.verify_password", return_value=False) as verify,
        pytest.raises(HTTPException) as err,
    ):
        _login({"email": "nobody@example.com", "password": "guess"})
    assert err.value.status_code == 401
    verify.assert_called_once()  # same PBKDF2 cost as a wrong password: no account-enumeration timing gap


@pytest.mark.parametrize("body", [["victim@example.com"], "victim@example.com", None])
def test_login_rejects_a_non_object_body(accounts, body):
    with pytest.raises(HTTPException) as err:
        _login(body)
    assert err.value.status_code == 400


def test_google_only_account_also_pays_the_password_check(accounts):
    google_only = {"email": "g@example.com", "password_hash": "__google__"}
    with (
        patch("webapp.user_repository.authenticate_user", return_value=google_only),
        patch("webapp.auth.verify_password", return_value=True) as verify,
        pytest.raises(HTTPException) as err,
    ):
        _login({"email": "g@example.com", "password": "__google__"})
    assert err.value.status_code == 401  # even a verify "match" against the dummy hash is refused
    verify.assert_called_once()
