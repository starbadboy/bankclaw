"""Shared DeepSeek API configuration."""

from __future__ import annotations

import os

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-pro"


def get_deepseek_model() -> str:
    """Return the configured DeepSeek model, defaulting to the v4 Pro model."""
    return os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL).strip() or DEFAULT_DEEPSEEK_MODEL
