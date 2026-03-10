from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from webapp.repository import (
    archive_custom_category,
    delete_transactions,
    get_category_memory,
    get_custom_categories,
    get_transactions_by_date_range,
    save_category_memory,
    save_custom_category,
    save_transactions,
)
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
    upsert_filter = mock_collection.bulk_write.call_args_list[0].args[0][0]._filter
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


def test_delete_transactions_uses_user_scoped_filter():
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.delete_one.return_value.deleted_count = 1

    delete_df = pd.DataFrame([
        {
            "date": "2024-01-10",
            "description": "Salary",
            "amount": 5000.0,
            "bank": "DBS",
        }
    ])

    with patch("webapp.repository.get_db", return_value=mock_db):
        deleted_count = delete_transactions(delete_df, user_email="u@example.com")

    assert deleted_count == 1
    delete_filter = mock_collection.delete_one.call_args[0][0]
    assert delete_filter["user_email"] == "u@example.com"
    assert delete_filter["description"] == "Salary"


def test_save_category_memory_upserts_user_scoped_normalized_records():
    memory_df = pd.DataFrame([
        {
            "description": "GRAB TAXI",
            "category": "Transport",
        }
    ])
    mock_collection = MagicMock()
    mock_db = MagicMock()

    def _get_collection(name):  # noqa: ANN001
        return mock_collection

    mock_db.__getitem__.side_effect = _get_collection

    with patch("webapp.repository.get_db", return_value=mock_db):
        saved_count = save_category_memory(memory_df, user_email="u@example.com", source="manual")

    assert saved_count == 1
    index_spec = mock_collection.create_index.call_args_list[0][0][0]
    assert ("user_email", 1) in index_spec
    assert ("normalized_description", 1) in index_spec
    operation = mock_collection.bulk_write.call_args.args[0][0]
    assert operation._filter["user_email"] == "u@example.com"
    assert operation._filter["normalized_description"] == "grab taxi"
    assert operation._doc["$set"]["category"] == "Transport"
    assert operation._doc["$set"]["source"] == "manual"


def test_get_category_memory_returns_user_scoped_records():
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.find.return_value = [
        {
            "user_email": "u@example.com",
            "normalized_description": "grab taxi",
            "last_raw_description": "GRAB TAXI",
            "category": "Transport",
            "source": "manual",
            "updated_at": "2026-03-05T00:00:00Z",
        }
    ]

    with patch("webapp.repository.get_db", return_value=mock_db):
        result = get_category_memory(user_email="u@example.com")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]["category"] == "Transport"
    find_filter = mock_collection.find.call_args.args[0]
    assert find_filter["user_email"] == "u@example.com"


def test_save_category_memory_deduplicates_same_normalized_description():
    memory_df = pd.DataFrame([
        {
            "description": "GRAB-TAXI",
            "category": "Transport",
        },
        {
            "description": "GRAB TAXI",
            "category": "Other",
        },
    ])
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("webapp.repository.get_db", return_value=mock_db):
        saved_count = save_category_memory(memory_df, user_email="u@example.com", source="manual")

    assert saved_count == 1
    operations = mock_collection.bulk_write.call_args.args[0]
    assert len(operations) == 1
    assert operations[0]._filter["normalized_description"] == "grab taxi"
    assert operations[0]._doc["$set"]["category"] == "Other"


def test_save_custom_category_upserts_user_scoped_normalized_record():
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("webapp.repository.get_db", return_value=mock_db):
        saved_count = save_custom_category(" Pet Care ", user_email="u@example.com")

    assert saved_count == 1
    first_index = mock_collection.create_index.call_args_list[0]
    second_index = mock_collection.create_index.call_args_list[1]
    assert ("user_email", 1) in first_index.args[0]
    assert ("normalized_name", 1) in first_index.args[0]
    assert first_index.kwargs["unique"] is True
    assert ("updated_at", 1) in second_index.args[0]

    operation = mock_collection.bulk_write.call_args.args[0][0]
    assert operation._filter == {
        "user_email": "u@example.com",
        "normalized_name": "pet care",
    }
    assert operation._doc["$set"]["name"] == "Pet Care"
    assert operation._doc["$set"]["is_active"] is True
    assert "created_at" in operation._doc["$setOnInsert"]


def test_get_custom_categories_returns_user_scoped_records():
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.find.return_value = [
        {
            "user_email": "u@example.com",
            "name": "Pet Care",
            "normalized_name": "pet care",
            "is_active": True,
            "created_at": "2026-03-10T00:00:00Z",
            "updated_at": "2026-03-10T00:00:00Z",
        }
    ]

    with patch("webapp.repository.get_db", return_value=mock_db):
        result = get_custom_categories(user_email="u@example.com")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]["name"] == "Pet Care"
    find_filter = mock_collection.find.call_args.args[0]
    assert find_filter["user_email"] == "u@example.com"
    assert find_filter["is_active"] is True


def test_archive_custom_category_marks_matching_record_inactive():
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.update_one.return_value.modified_count = 1

    with patch("webapp.repository.get_db", return_value=mock_db):
        archived_count = archive_custom_category("Pet Care", user_email="u@example.com")

    assert archived_count == 1
    archive_filter = mock_collection.update_one.call_args.args[0]
    assert archive_filter == {
        "user_email": "u@example.com",
        "normalized_name": "pet care",
    }
    archive_update = mock_collection.update_one.call_args.args[1]
    assert archive_update["$set"]["is_active"] is False


def test_archived_custom_categories_are_excluded_from_default_reads():
    docs = []

    class FakeCollection:
        def create_index(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        def bulk_write(self, operations, ordered=False):  # noqa: ANN001, FBT002
            del ordered
            for operation in operations:
                document = {
                    **operation._filter,
                    **operation._doc["$setOnInsert"],
                    **operation._doc["$set"],
                }
                docs.append(document)

        def update_one(self, filter_doc, update_doc):  # noqa: ANN001
            modified_count = 0
            for document in docs:
                if all(document.get(key) == value for key, value in filter_doc.items()):
                    document.update(update_doc["$set"])
                    modified_count = 1
                    break

            result = MagicMock()
            result.modified_count = modified_count
            return result

        def find(self, filter_doc, projection, sort=None):  # noqa: ANN001
            del projection, sort
            return [
                dict(document)
                for document in docs
                if all(document.get(key) == value for key, value in filter_doc.items())
            ]

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = FakeCollection()

    with patch("webapp.repository.get_db", return_value=mock_db):
        save_custom_category("Pet Care", user_email="u@example.com")
        archive_custom_category("Pet Care", user_email="u@example.com")
        active_result = get_custom_categories(user_email="u@example.com")
        all_result = get_custom_categories(user_email="u@example.com", include_inactive=True)

    assert active_result.empty
    assert len(all_result) == 1
    assert not bool(all_result.iloc[0]["is_active"])


@pytest.mark.parametrize("name", [None, 123, "", "   "])
def test_save_custom_category_rejects_invalid_names(name):
    with pytest.raises(ValueError):
        save_custom_category(name, user_email="u@example.com")


@pytest.mark.parametrize("name", [None, 123, "", "   "])
def test_archive_custom_category_rejects_invalid_names(name):
    with pytest.raises(ValueError):
        archive_custom_category(name, user_email="u@example.com")
