import binascii
import hashlib
import hmac
import os
from collections.abc import MutableMapping
from typing import Any

import streamlit as st

_AUTH_USER_KEY = "auth_user"
_PBKDF2_ALGO = "sha256"
_PBKDF2_ITERATIONS = 120_000
_SALT_SIZE = 16


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    salt = os.urandom(_SALT_SIZE)
    digest = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${binascii.hexlify(salt).decode()}${binascii.hexlify(digest).decode()}"


def verify_password(password: str, stored_password_hash: str) -> bool:
    try:
        _, iterations, salt_hex, hash_hex = stored_password_hash.split("$")
        salt = binascii.unhexlify(salt_hex.encode("utf-8"))
        expected_hash = binascii.unhexlify(hash_hex.encode("utf-8"))
        computed_hash = hashlib.pbkdf2_hmac(
            _PBKDF2_ALGO,
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
    except (ValueError, binascii.Error):
        return False
    return hmac.compare_digest(computed_hash, expected_hash)


def init_auth_state(session_state: MutableMapping[str, Any]) -> None:
    session_state.setdefault(_AUTH_USER_KEY, None)


def is_authenticated(session_state: MutableMapping[str, Any]) -> bool:
    return bool(session_state.get(_AUTH_USER_KEY))


def get_current_user_email(session_state: MutableMapping[str, Any]) -> str | None:
    user = session_state.get(_AUTH_USER_KEY)
    if not user:
        return None
    return user.get("email")


def require_authentication() -> str:
    init_auth_state(st.session_state)
    email = get_current_user_email(st.session_state)
    if not email:
        st.warning("Please log in first to view your private dashboard.")
        st.stop()
    return email
