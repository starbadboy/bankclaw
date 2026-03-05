import binascii
import json
import hashlib
import hmac
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections.abc import MutableMapping
from typing import Any

import streamlit as st

_AUTH_USER_KEY = "auth_user"
_AUTH_QUERY_TOKEN_KEY = "auth"
_PBKDF2_ALGO = "sha256"
_PBKDF2_ITERATIONS = 120_000
_SALT_SIZE = 16
_AUTH_TOKEN_TTL_SECONDS = 24 * 60 * 60


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _b64_encode(raw: bytes) -> str:
    return urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return urlsafe_b64decode((raw + padding).encode("utf-8"))


def _auth_secret() -> bytes:
    # Keep a deterministic default for local/dev usage when env var is absent.
    return os.getenv("AUTH_TOKEN_SECRET", "bankclaw-local-dev-secret").encode("utf-8")


def create_auth_token(email: str, now_ts: int | None = None) -> str:
    issued_at = int(now_ts if now_ts is not None else time.time())
    payload = {"email": normalize_email(email), "exp": issued_at + _AUTH_TOKEN_TTL_SECONDS}
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(_auth_secret(), payload_bytes, hashlib.sha256).hexdigest().encode("utf-8")
    return f"{_b64_encode(payload_bytes)}.{_b64_encode(signature)}"


def verify_auth_token(token: str, now_ts: int | None = None) -> str | None:
    try:
        payload_part, signature_part = token.split(".", maxsplit=1)
        payload_bytes = _b64_decode(payload_part)
        expected_sig = hmac.new(_auth_secret(), payload_bytes, hashlib.sha256).hexdigest()
        actual_sig = _b64_decode(signature_part).decode("utf-8")
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(payload_bytes.decode("utf-8"))
        email = normalize_email(payload["email"])
        exp_ts = int(payload["exp"])
        current_ts = int(now_ts if now_ts is not None else time.time())
        if current_ts > exp_ts:
            return None
        return email
    except (ValueError, KeyError, TypeError):
        return None


def restore_auth_from_query_token(
    session_state: MutableMapping[str, Any], query_params: MutableMapping[str, Any], now_ts: int | None = None
) -> bool:
    if session_state.get(_AUTH_USER_KEY):
        return True
    token = query_params.get(_AUTH_QUERY_TOKEN_KEY)
    if not token:
        return False
    email = verify_auth_token(str(token), now_ts=now_ts)
    if not email:
        clear_auth_query_token(query_params)
        return False
    session_state[_AUTH_USER_KEY] = {"email": email}
    return True


def clear_auth_query_token(query_params: MutableMapping[str, Any]) -> None:
    query_params.pop(_AUTH_QUERY_TOKEN_KEY, None)


def sync_auth_query_token(
    session_state: MutableMapping[str, Any], query_params: MutableMapping[str, Any], now_ts: int | None = None
) -> None:
    if query_params.get(_AUTH_QUERY_TOKEN_KEY):
        return
    user = session_state.get(_AUTH_USER_KEY)
    if not user:
        return
    email = user.get("email")
    if not email:
        return
    query_params[_AUTH_QUERY_TOKEN_KEY] = create_auth_token(email, now_ts=now_ts)


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
    except ValueError:
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
    restore_auth_from_query_token(st.session_state, st.query_params)
    sync_auth_query_token(st.session_state, st.query_params)
    email = get_current_user_email(st.session_state)
    if not email:
        st.warning("Please log in first to view your private dashboard.")
        st.stop()
    return email
