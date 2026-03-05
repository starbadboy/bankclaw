from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from webapp.categorizer import VALID_CATEGORIES, categorize_transactions


def make_df():
    return pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB TAXI", "amount": -12.50, "bank": "DBS"},
        {"date": "2024-01-16", "description": "NTUC FAIRPRICE", "amount": -45.30, "bank": "DBS"},
    ])


def test_categorize_raises_when_no_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    df = make_df()
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        categorize_transactions(df)


def test_categorize_returns_df_with_category_column(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    df = make_df()

    mock_response_text = "Transport\nFood & Dining"
    mock_choice = MagicMock()
    mock_choice.message.content = mock_response_text
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("webapp.categorizer.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        MockOpenAI.return_value = mock_client

        result = categorize_transactions(df)

    assert "category" in result.columns
    assert list(result["category"]) == ["Transport", "Food & Dining"]


def test_invalid_category_falls_back_to_other(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    df = make_df()

    mock_response_text = "INVALID_CATEGORY\nFood & Dining"
    mock_choice = MagicMock()
    mock_choice.message.content = mock_response_text
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("webapp.categorizer.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        MockOpenAI.return_value = mock_client

        result = categorize_transactions(df)

    assert result.iloc[0]["category"] == "Other"


def test_valid_categories_list():
    assert "Food & Dining" in VALID_CATEGORIES
    assert "Transport" in VALID_CATEGORIES
    assert "Other" in VALID_CATEGORIES
    assert len(VALID_CATEGORIES) == 10


def test_categorize_processes_in_batches_and_preserves_order(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB TAXI", "amount": -12.50, "bank": "DBS"},
        {"date": "2024-01-16", "description": "NTUC FAIRPRICE", "amount": -45.30, "bank": "DBS"},
        {"date": "2024-01-17", "description": "SP GROUP", "amount": -90.00, "bank": "DBS"},
    ])

    first_choice = MagicMock()
    first_choice.message.content = "Transport\nFood & Dining"
    second_choice = MagicMock()
    second_choice.message.content = "Utilities"

    first_completion = MagicMock()
    first_completion.choices = [first_choice]
    second_completion = MagicMock()
    second_completion.choices = [second_choice]

    with patch("webapp.categorizer.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [first_completion, second_completion]
        MockOpenAI.return_value = mock_client

        result = categorize_transactions(df, batch_size=2)

    assert list(result["category"]) == ["Transport", "Food & Dining", "Utilities"]
    assert mock_client.chat.completions.create.call_count == 2
