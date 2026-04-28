from unittest.mock import MagicMock, patch

import pandas as pd

from webapp.ai_coach import _call_llm
from webapp.categorizer import categorize_transactions
from webapp.deepseek_config import DEFAULT_DEEPSEEK_MODEL, get_deepseek_model


def test_deepseek_model_defaults_to_v4_pro(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)

    assert DEFAULT_DEEPSEEK_MODEL == "deepseek-v4-pro"
    assert get_deepseek_model() == "deepseek-v4-pro"


def test_deepseek_model_can_be_overridden(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

    assert get_deepseek_model() == "deepseek-v4-flash"


def test_categorizer_uses_configured_v4_model(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    df = pd.DataFrame(
        [
            {"date": "2024-01-15", "description": "GRAB TAXI", "amount": -12.50, "bank": "DBS"},
        ]
    )

    mock_choice = MagicMock()
    mock_choice.message.content = "Transport"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("webapp.categorizer.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client

        categorize_transactions(df)

    assert mock_client.chat.completions.create.call_args.kwargs["model"] == "deepseek-v4-pro"


def test_ai_coach_uses_deepseek_model_override(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

    mock_choice = MagicMock()
    mock_choice.message.content = (
        '{"summary":"ok","strengths":[],"opportunities":[],"subscriptions_review":[],"watchouts":[]}'
    )
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("webapp.ai_coach.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client

        _call_llm({"transaction_count": 1})

    assert mock_client.chat.completions.create.call_args.kwargs["model"] == "deepseek-v4-flash"
