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
        count = save_transactions(df)

    assert mock_collection.update_one.call_count == 2
    # Verify upsert=True was used
    call_kwargs = mock_collection.update_one.call_args_list[0][1]
    assert call_kwargs.get("upsert") is True
    assert count == 2


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
        result = get_transactions_by_date_range("2024-01-01", "2024-01-31")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]["category"] == "Transport"


def test_get_transactions_returns_empty_df_when_no_records():
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.find.return_value = []

    with patch("webapp.repository.get_db", return_value=mock_db):
        result = get_transactions_by_date_range("2024-01-01", "2024-01-31")

    assert isinstance(result, pd.DataFrame)
    assert result.empty
    assert "category" in result.columns
