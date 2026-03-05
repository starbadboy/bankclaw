from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd

from webapp.repository import get_transactions_by_date_range, save_transactions
from webapp.user_repository import authenticate_user, create_user


def _sample_df():
    return pd.DataFrame([
        {
            "date": date(2024, 1, 10),
            "description": "Salary",
            "amount": 5000.0,
            "bank": "DBS",
            "category": "Income",
        }
    ])


def test_create_user_inserts_new_user_document():
    mock_users = MagicMock()
    mock_users.find_one.return_value = None
    mock_db = {"users": mock_users}

    with patch("webapp.user_repository.get_db", return_value=mock_db):
        created = create_user("user@example.com", "hashed-password")

    assert created is True
    args, _ = mock_users.insert_one.call_args
    assert args[0]["email"] == "user@example.com"
    assert args[0]["password_hash"] == "hashed-password"


def test_authenticate_user_returns_document_for_existing_user():
    mock_users = MagicMock()
    mock_users.find_one.return_value = {"email": "user@example.com", "password_hash": "stored_hash_value"}
    mock_db = {"users": mock_users}

    with patch("webapp.user_repository.get_db", return_value=mock_db):
        user = authenticate_user("user@example.com")

    assert user is not None
    assert user["email"] == "user@example.com"


def test_save_and_read_transactions_are_user_scoped():
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.find.return_value = [
        {
            "user_email": "u@example.com",
            "date": "2024-01-10",
            "description": "Salary",
            "amount": 5000.0,
            "bank": "DBS",
            "category": "Income",
            "saved_at": "2026-03-05T00:00:00Z",
        }
    ]

    with patch("webapp.repository.get_db", return_value=mock_db):
        saved_count = save_transactions(_sample_df(), user_email="u@example.com")
        loaded = get_transactions_by_date_range(
            "2024-01-01",
            "2024-01-31",
            user_email="u@example.com",
        )

    assert saved_count == 1
    upsert_filter = mock_collection.update_one.call_args_list[0][0][0]
    assert upsert_filter["user_email"] == "u@example.com"

    find_filter = mock_collection.find.call_args[0][0]
    assert find_filter["user_email"] == "u@example.com"
    assert not loaded.empty


def test_save_transactions_creates_unique_compound_index():
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("webapp.repository.get_db", return_value=mock_db):
        save_transactions(_sample_df(), user_email="u@example.com")

    index_spec = mock_collection.create_index.call_args[0][0]
    index_kwargs = mock_collection.create_index.call_args[1]
    assert ("user_email", 1) in index_spec
    assert ("description", 1) in index_spec
    assert ("amount", 1) in index_spec
    assert index_kwargs["unique"] is True
