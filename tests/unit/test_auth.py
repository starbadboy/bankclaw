import pytest

from webapp.auth import (
    hash_password,
    init_auth_state,
    is_authenticated,
    normalize_email,
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
