import pytest

from webapp.auth import (
    clear_auth_query_token,
    create_auth_token,
    hash_password,
    init_auth_state,
    is_authenticated,
    normalize_email,
    restore_auth_from_query_token,
    sync_auth_query_token,
    verify_auth_token,
    verify_password,
)


def test_normalize_email_trims_and_lowercases():
    assert normalize_email("  USER@Example.COM ") == "user@example.com"


def test_hash_and_verify_password_round_trip():
    stored = hash_password("Str0ngPass!")
    assert verify_password("Str0ngPass!", stored) is True
    assert verify_password("WrongPass!", stored) is False


def test_hash_password_rejects_empty():
    with pytest.raises(ValueError, match="Password cannot be empty"):
        hash_password("")


@pytest.mark.parametrize(
    "malformed_hash",
    [
        "",
        "pbkdf2_sha256$bad-iterations$0011$0022",
        "pbkdf2_sha256$120000$zzzz$ff",
        "pbkdf2_sha256$120000$aa",
    ],
)
def test_verify_password_returns_false_for_malformed_hash(malformed_hash):
    assert verify_password("password", malformed_hash) is False


def test_init_auth_state_defaults_to_logged_out():
    session_state = {}
    init_auth_state(session_state)
    assert is_authenticated(session_state) is False
    assert session_state["auth_user"] is None


def test_create_and_verify_auth_token_round_trip():
    token = create_auth_token("user@example.com", now_ts=1_700_000_000)
    email = verify_auth_token(token, now_ts=1_700_000_100)
    assert email == "user@example.com"


def test_verify_auth_token_rejects_expired():
    token = create_auth_token("user@example.com", now_ts=1_700_000_000)
    email = verify_auth_token(token, now_ts=1_700_086_500)
    assert email is None


def test_restore_auth_from_query_token_sets_user():
    session_state = {"auth_user": None}
    query_params = {"auth": "placeholder"}
    token = create_auth_token("user@example.com", now_ts=1_700_000_000)
    query_params["auth"] = token

    restored = restore_auth_from_query_token(session_state, query_params, now_ts=1_700_000_100)

    assert restored is True
    assert session_state["auth_user"]["email"] == "user@example.com"


def test_clear_auth_query_token_removes_auth_key():
    query_params = {"auth": "token", "other": "keep"}
    clear_auth_query_token(query_params)
    assert "auth" not in query_params
    assert query_params["other"] == "keep"


def test_sync_auth_query_token_writes_token_when_authenticated_and_missing():
    session_state = {"auth_user": {"email": "user@example.com"}}
    query_params = {"page": "history"}

    sync_auth_query_token(session_state, query_params, now_ts=1_700_000_000)

    assert "auth" in query_params
    assert verify_auth_token(query_params["auth"], now_ts=1_700_000_100) == "user@example.com"


def test_sync_auth_query_token_keeps_existing_token():
    session_state = {"auth_user": {"email": "user@example.com"}}
    existing = create_auth_token("user@example.com", now_ts=1_700_000_000)
    query_params = {"auth": existing}

    sync_auth_query_token(session_state, query_params, now_ts=1_700_000_100)

    assert query_params["auth"] == existing


def test_sync_auth_query_token_noop_when_not_authenticated():
    session_state = {"auth_user": None}
    query_params = {"page": "history"}

    sync_auth_query_token(session_state, query_params, now_ts=1_700_000_000)

    assert "auth" not in query_params
