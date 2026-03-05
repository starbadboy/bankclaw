from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd

from webapp.repository import get_transactions_by_date_range, save_transactions


def make_categorized_df():
    return pd.DataFrame([
        {
            "date": date(2024, 1, 15),
            "description": "GRAB TAXI",
            "amount": -12.50,
            "bank": "DBS",
            "category": "Transport",
        },
        {
            "date": date(2024, 1, 16),
            "description": "NTUC FAIRPRICE",
            "amount": -45.30,
            "bank": "DBS",
            "category": "Food & Dining",
        },
    ])


def test_save_transactions_upserts_records():
    df = make_categorized_df()
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("webapp.repository.get_db", return_value=mock_db):
        count = save_transactions(df, user_email="user@example.com")

    assert mock_collection.bulk_write.call_count == 1
    first_call = mock_collection.bulk_write.call_args_list[0]
    operations = first_call.args[0]
    assert len(operations) == 2
    assert first_call.kwargs.get("ordered") is False
    assert count == 2


def test_save_transactions_writes_in_batches():
    df = pd.DataFrame([
        {
            "date": date(2024, 1, 15),
            "description": "GRAB TAXI",
            "amount": -12.50,
            "bank": "DBS",
            "category": "Transport",
        },
        {
            "date": date(2024, 1, 16),
            "description": "NTUC FAIRPRICE",
            "amount": -45.30,
            "bank": "DBS",
            "category": "Food & Dining",
        },
        {
            "date": date(2024, 1, 17),
            "description": "SP GROUP",
            "amount": -90.00,
            "bank": "DBS",
            "category": "Utilities",
        },
    ])
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("webapp.repository.get_db", return_value=mock_db):
        count = save_transactions(df, user_email="user@example.com", batch_size=2)

    assert mock_collection.bulk_write.call_count == 2
    first_ops = mock_collection.bulk_write.call_args_list[0].args[0]
    second_ops = mock_collection.bulk_write.call_args_list[1].args[0]
    assert len(first_ops) == 2
    assert len(second_ops) == 1
    assert count == 3


def test_get_transactions_by_date_range_returns_df():
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.find.return_value = [
        {
            "date": "2024-01-15",
            "description": "GRAB TAXI",
            "amount": -12.50,
            "bank": "DBS",
            "category": "Transport",
            "saved_at": "2024-01-20",
        }
    ]

    with patch("webapp.repository.get_db", return_value=mock_db):
        result = get_transactions_by_date_range("2024-01-01", "2024-01-31", user_email="user@example.com")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]["category"] == "Transport"


def test_get_transactions_returns_empty_df_when_no_records():
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.find.return_value = []

    with patch("webapp.repository.get_db", return_value=mock_db):
        result = get_transactions_by_date_range("2024-01-01", "2024-01-31", user_email="user@example.com")

    assert isinstance(result, pd.DataFrame)
    assert result.empty
    assert "category" in result.columns
