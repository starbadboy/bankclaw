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


def test_categorize_reuses_exact_category_memory_without_ai(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB TAXI", "amount": -12.50, "bank": "DBS"},
    ])
    memory_df = pd.DataFrame([
        {
            "normalized_description": "grab taxi",
            "last_raw_description": "GRAB TAXI",
            "category": "Transport",
            "source": "manual",
            "updated_at": "2026-03-05T00:00:00Z",
        }
    ])

    with patch("webapp.categorizer.get_category_memory", return_value=memory_df), \
         patch("webapp.categorizer.OpenAI") as MockOpenAI:
        result = categorize_transactions(df, user_email="user@example.com")

    assert list(result["category"]) == ["Transport"]
    MockOpenAI.assert_not_called()


def test_categorize_reuses_similar_category_memory_above_threshold(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB TAXI SINGAPORE", "amount": -12.50, "bank": "DBS"},
    ])
    memory_df = pd.DataFrame([
        {
            "normalized_description": "grab taxi singapore pte ltd",
            "last_raw_description": "GRAB TAXI SINGAPORE PTE LTD",
            "category": "Transport",
            "source": "manual",
            "updated_at": "2026-03-05T00:00:00Z",
        }
    ])

    with patch("webapp.categorizer.get_category_memory", return_value=memory_df), \
         patch("webapp.categorizer.OpenAI") as MockOpenAI:
        result = categorize_transactions(df, user_email="user@example.com")

    assert list(result["category"]) == ["Transport"]
    MockOpenAI.assert_not_called()


def test_categorize_uses_ai_only_for_rows_without_memory_match(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB TAXI", "amount": -12.50, "bank": "DBS"},
        {"date": "2024-01-16", "description": "NTUC FAIRPRICE", "amount": -45.30, "bank": "DBS"},
    ])
    memory_df = pd.DataFrame([
        {
            "normalized_description": "grab taxi",
            "last_raw_description": "GRAB TAXI",
            "category": "Transport",
            "source": "manual",
            "updated_at": "2026-03-05T00:00:00Z",
        }
    ])

    mock_choice = MagicMock()
    mock_choice.message.content = "Food & Dining"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("webapp.categorizer.get_category_memory", return_value=memory_df), \
         patch("webapp.categorizer.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        MockOpenAI.return_value = mock_client

        result = categorize_transactions(df, user_email="user@example.com")

    assert list(result["category"]) == ["Transport", "Food & Dining"]
    assert mock_client.chat.completions.create.call_count == 1


def test_categorize_falls_back_to_ai_when_memory_lookup_fails(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB TAXI", "amount": -12.50, "bank": "DBS"},
    ])

    mock_choice = MagicMock()
    mock_choice.message.content = "Transport"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("webapp.categorizer.get_category_memory", side_effect=RuntimeError("db unavailable")), \
         patch("webapp.categorizer.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        MockOpenAI.return_value = mock_client

        result = categorize_transactions(df, user_email="user@example.com")

    assert list(result["category"]) == ["Transport"]
    mock_client.chat.completions.create.assert_called_once()


def test_categorize_does_not_reuse_memory_for_different_short_merchant_name(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB PAY", "amount": -12.50, "bank": "DBS"},
    ])
    memory_df = pd.DataFrame([
        {
            "normalized_description": "grab taxi",
            "last_raw_description": "GRAB TAXI",
            "category": "Transport",
            "source": "manual",
            "updated_at": "2026-03-05T00:00:00Z",
        }
    ])

    mock_choice = MagicMock()
    mock_choice.message.content = "Transfer"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("webapp.categorizer.get_category_memory", return_value=memory_df), \
         patch("webapp.categorizer.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        MockOpenAI.return_value = mock_client

        result = categorize_transactions(df, user_email="user@example.com")

    assert list(result["category"]) == ["Transfer"]
    mock_client.chat.completions.create.assert_called_once()


def test_categorize_does_not_reuse_memory_for_generic_payment_wording(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "FAST PAYMENT TO BOB", "amount": -12.50, "bank": "DBS"},
    ])
    memory_df = pd.DataFrame([
        {
            "normalized_description": "fast payment to alice",
            "last_raw_description": "FAST PAYMENT TO ALICE",
            "category": "Transfer",
            "source": "manual",
            "updated_at": "2026-03-05T00:00:00Z",
        }
    ])

    mock_choice = MagicMock()
    mock_choice.message.content = "Other"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("webapp.categorizer.get_category_memory", return_value=memory_df), \
         patch("webapp.categorizer.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        MockOpenAI.return_value = mock_client

        result = categorize_transactions(df, user_email="user@example.com")

    assert list(result["category"]) == ["Other"]
    mock_client.chat.completions.create.assert_called_once()


def test_categorize_uses_allowed_categories_for_prompt_and_output_validation(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "DOG GROOMER", "amount": -45.00, "bank": "DBS"},
    ])
    allowed_categories = ["Transport", "Pet Care", "Other"]

    mock_choice = MagicMock()
    mock_choice.message.content = "Pet Care"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("webapp.categorizer.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        MockOpenAI.return_value = mock_client

        result = categorize_transactions(df, allowed_categories=allowed_categories)

    assert list(result["category"]) == ["Pet Care"]
    system_prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "Pet Care" in system_prompt
    assert "Food & Dining" not in system_prompt


def test_categorize_ignores_memory_category_not_in_allowed_categories(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "DOG GROOMER", "amount": -45.00, "bank": "DBS"},
    ])
    memory_df = pd.DataFrame([
        {
            "normalized_description": "dog groomer",
            "last_raw_description": "DOG GROOMER",
            "category": "Archived Category",
            "source": "manual",
            "updated_at": "2026-03-05T00:00:00Z",
        }
    ])

    mock_choice = MagicMock()
    mock_choice.message.content = "Other"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("webapp.categorizer.get_category_memory", return_value=memory_df), \
         patch("webapp.categorizer.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        MockOpenAI.return_value = mock_client

        result = categorize_transactions(
            df,
            user_email="user@example.com",
            allowed_categories=["Transport", "Other"],
        )

    assert list(result["category"]) == ["Other"]
    mock_client.chat.completions.create.assert_called_once()


def test_categorize_requires_other_in_allowed_categories(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "DOG GROOMER", "amount": -45.00, "bank": "DBS"},
    ])

    with pytest.raises(ValueError, match="allowed_categories must include 'Other'"):
        categorize_transactions(df, allowed_categories=["Transport", "Pet Care"])
