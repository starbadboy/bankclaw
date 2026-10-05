from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from webapp.categorizer import VALID_CATEGORIES, categorize_transactions


def make_response(*categories, start=0):
    return SimpleNamespace(choices={
        f"transaction_{start + idx}": SimpleNamespace(choice=category)
        for idx, category in enumerate(categories)
    })


def make_df():
    return pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB TAXI", "amount": -12.50, "bank": "DBS"},
        {"date": "2024-01-16", "description": "NTUC FAIRPRICE", "amount": -45.30, "bank": "DBS"},
    ])


def test_categorize_raises_when_no_api_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    df = make_df()
    with pytest.raises(ValueError, match="TYPESAFE_API_KEY"):
        categorize_transactions(df)


def test_categorize_returns_df_with_category_column(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    df = make_df()

    mock_completion = make_response('Transport', 'Food & Dining')

    with patch("webapp.categorizer.TypeSafeClient") as MockTypeSafeClient:
        mock_client = MagicMock()
        mock_client.system_one.return_value = mock_completion
        MockTypeSafeClient.return_value.__enter__.return_value = mock_client

        result = categorize_transactions(df)

    assert "category" in result.columns
    assert list(result["category"]) == ["Transport", "Food & Dining"]


def test_invalid_category_falls_back_to_other(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    df = make_df()

    mock_completion = make_response('INVALID_CATEGORY', 'Food & Dining')

    with patch("webapp.categorizer.TypeSafeClient") as MockTypeSafeClient:
        mock_client = MagicMock()
        mock_client.system_one.return_value = mock_completion
        MockTypeSafeClient.return_value.__enter__.return_value = mock_client

        result = categorize_transactions(df)

    assert result.iloc[0]["category"] == "Other"


def test_valid_categories_list():
    assert "Food & Dining" in VALID_CATEGORIES
    assert "Transport" in VALID_CATEGORIES
    assert "Other" in VALID_CATEGORIES
    assert len(VALID_CATEGORIES) == 10


def test_categorize_processes_in_batches_and_preserves_order(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB TAXI", "amount": -12.50, "bank": "DBS"},
        {"date": "2024-01-16", "description": "NTUC FAIRPRICE", "amount": -45.30, "bank": "DBS"},
        {"date": "2024-01-17", "description": "SP GROUP", "amount": -90.00, "bank": "DBS"},
    ])

    first_completion = make_response("Transport", "Food & Dining")
    second_completion = make_response("Utilities", start=2)

    with patch("webapp.categorizer.TypeSafeClient") as MockTypeSafeClient:
        mock_client = MagicMock()
        mock_client.system_one.side_effect = [first_completion, second_completion]
        MockTypeSafeClient.return_value.__enter__.return_value = mock_client

        result = categorize_transactions(df, batch_size=2)

    assert list(result["category"]) == ["Transport", "Food & Dining", "Utilities"]
    assert mock_client.system_one.call_count == 2


def test_categorize_reuses_exact_category_memory_without_ai(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
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
         patch("webapp.categorizer.TypeSafeClient") as MockTypeSafeClient:
        result = categorize_transactions(df, user_email="user@example.com")

    assert list(result["category"]) == ["Transport"]
    MockTypeSafeClient.assert_not_called()


def test_categorize_reuses_similar_category_memory_above_threshold(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
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
         patch("webapp.categorizer.TypeSafeClient") as MockTypeSafeClient:
        result = categorize_transactions(df, user_email="user@example.com")

    assert list(result["category"]) == ["Transport"]
    MockTypeSafeClient.assert_not_called()


def test_categorize_uses_ai_only_for_rows_without_memory_match(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
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

    mock_completion = make_response('Food & Dining', start=1)

    with patch("webapp.categorizer.get_category_memory", return_value=memory_df), \
         patch("webapp.categorizer.TypeSafeClient") as MockTypeSafeClient:
        mock_client = MagicMock()
        mock_client.system_one.return_value = mock_completion
        MockTypeSafeClient.return_value.__enter__.return_value = mock_client

        result = categorize_transactions(df, user_email="user@example.com")

    assert list(result["category"]) == ["Transport", "Food & Dining"]
    assert mock_client.system_one.call_count == 1


def test_categorize_falls_back_to_ai_when_memory_lookup_fails(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB TAXI", "amount": -12.50, "bank": "DBS"},
    ])

    mock_completion = make_response('Transport')

    with patch("webapp.categorizer.get_category_memory", side_effect=RuntimeError("db unavailable")), \
         patch("webapp.categorizer.TypeSafeClient") as MockTypeSafeClient:
        mock_client = MagicMock()
        mock_client.system_one.return_value = mock_completion
        MockTypeSafeClient.return_value.__enter__.return_value = mock_client

        result = categorize_transactions(df, user_email="user@example.com")

    assert list(result["category"]) == ["Transport"]
    mock_client.system_one.assert_called_once()


def test_categorize_does_not_reuse_memory_for_different_short_merchant_name(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
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

    mock_completion = make_response('Transfer')

    with patch("webapp.categorizer.get_category_memory", return_value=memory_df), \
         patch("webapp.categorizer.TypeSafeClient") as MockTypeSafeClient:
        mock_client = MagicMock()
        mock_client.system_one.return_value = mock_completion
        MockTypeSafeClient.return_value.__enter__.return_value = mock_client

        result = categorize_transactions(df, user_email="user@example.com")

    assert list(result["category"]) == ["Transfer"]
    mock_client.system_one.assert_called_once()


def test_categorize_does_not_reuse_memory_for_generic_payment_wording(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
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

    mock_completion = make_response('Other')

    with patch("webapp.categorizer.get_category_memory", return_value=memory_df), \
         patch("webapp.categorizer.TypeSafeClient") as MockTypeSafeClient:
        mock_client = MagicMock()
        mock_client.system_one.return_value = mock_completion
        MockTypeSafeClient.return_value.__enter__.return_value = mock_client

        result = categorize_transactions(df, user_email="user@example.com")

    assert list(result["category"]) == ["Other"]
    mock_client.system_one.assert_called_once()


def test_categorize_uses_allowed_categories_for_choices_and_output_validation(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "DOG GROOMER", "amount": -45.00, "bank": "DBS"},
    ])
    allowed_categories = ["Transport", "Pet Care", "Other"]

    mock_completion = make_response('Pet Care')

    with patch("webapp.categorizer.TypeSafeClient") as MockTypeSafeClient:
        mock_client = MagicMock()
        mock_client.system_one.return_value = mock_completion
        MockTypeSafeClient.return_value.__enter__.return_value = mock_client

        result = categorize_transactions(df, allowed_categories=allowed_categories)

    assert list(result["category"]) == ["Pet Care"]
    question = mock_client.system_one.call_args.kwargs["questions"]["transaction_0"]
    assert set(question.criteria) == set(allowed_categories)


def test_categorize_ignores_memory_category_not_in_allowed_categories(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
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

    mock_completion = make_response('Other')

    with patch("webapp.categorizer.get_category_memory", return_value=memory_df), \
         patch("webapp.categorizer.TypeSafeClient") as MockTypeSafeClient:
        mock_client = MagicMock()
        mock_client.system_one.return_value = mock_completion
        MockTypeSafeClient.return_value.__enter__.return_value = mock_client

        result = categorize_transactions(
            df,
            user_email="user@example.com",
            allowed_categories=["Transport", "Other"],
        )

    assert list(result["category"]) == ["Other"]
    mock_client.system_one.assert_called_once()


def test_categorize_requires_other_in_allowed_categories(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    df = pd.DataFrame([
        {"date": "2024-01-15", "description": "DOG GROOMER", "amount": -45.00, "bank": "DBS"},
    ])

    with pytest.raises(ValueError, match="allowed_categories must include 'Other'"):
        categorize_transactions(df, allowed_categories=["Transport", "Pet Care"])
