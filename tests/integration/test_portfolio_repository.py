from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId

from webapp.portfolio_repository import (
    create_asset,
    create_asset_type,
    delete_asset,
    delete_asset_type,
    delete_valuation,
    list_asset_types,
    list_valuations,
    record_valuation,
    update_asset_type,
)


def _portfolio_db():
    db = MagicMock()
    collections = {
        "portfolio_assets": MagicMock(),
        "portfolio_asset_types": MagicMock(),
        "portfolio_debts": MagicMock(),
        "portfolio_valuations": MagicMock(),
    }
    db.__getitem__.side_effect = collections.__getitem__
    return db, collections


def test_custom_asset_type_crud_is_user_scoped():
    db, collections = _portfolio_db()
    type_id = ObjectId()
    custom_types = collections["portfolio_asset_types"]
    custom_types.insert_one.return_value.inserted_id = type_id
    custom_types.find.return_value = [
        {
            "_id": type_id,
            "user_email": "owner@example.com",
            "name": "CPF",
            "name_key": "cpf",
            "color": "#8B5CF6",
        }
    ]
    custom_types.find_one_and_update.return_value = {
        "_id": type_id,
        "user_email": "owner@example.com",
        "name": "CPF Retirement",
        "name_key": "cpf retirement",
        "color": "#0F766E",
    }
    custom_types.find_one.return_value = {"_id": type_id, "user_email": "owner@example.com"}
    custom_types.delete_one.return_value.deleted_count = 1
    collections["portfolio_assets"].count_documents.return_value = 0

    with patch("webapp.portfolio_repository.get_db", return_value=db):
        created = create_asset_type("owner@example.com", {"name": "CPF", "color": "#8b5cf6"})
        listed = list_asset_types("owner@example.com")
        updated = update_asset_type(
            "owner@example.com",
            created["id"],
            {"name": "CPF Retirement", "color": "#0f766e"},
        )
        deleted = delete_asset_type("owner@example.com", created["id"])

    assert created == {"id": f"custom_{type_id}", "name": "CPF", "color": "#8B5CF6"}
    assert listed == [{"id": f"custom_{type_id}", "name": "CPF", "color": "#8B5CF6"}]
    assert updated == {"id": f"custom_{type_id}", "name": "CPF Retirement", "color": "#0F766E"}
    assert deleted == {"deleted": 1}
    assert custom_types.find.call_args.args[0] == {"user_email": "owner@example.com"}
    custom_types.delete_one.assert_called_once_with({"_id": type_id, "user_email": "owner@example.com"})


def test_create_asset_accepts_a_custom_type_owned_by_user():
    db, collections = _portfolio_db()
    asset_id = ObjectId()
    type_id = ObjectId()
    custom_kind = f"custom_{type_id}"
    collections["portfolio_assets"].insert_one.return_value.inserted_id = asset_id
    collections["portfolio_asset_types"].find_one.return_value = {
        "_id": type_id,
        "user_email": "owner@example.com",
    }

    with (
        patch("webapp.portfolio_repository.get_db", return_value=db),
        patch("webapp.portfolio_repository.record_valuation"),
    ):
        created = create_asset(
            "owner@example.com",
            {"name": "CPF OA", "kind": custom_kind, "value": 50000},
        )

    assert created["kind"] == custom_kind
    collections["portfolio_asset_types"].find_one.assert_called_with(
        {"_id": type_id, "user_email": "owner@example.com"}
    )


def test_delete_custom_asset_type_is_blocked_while_assets_use_it():
    db, collections = _portfolio_db()
    type_id = ObjectId()
    custom_kind = f"custom_{type_id}"
    collections["portfolio_asset_types"].find_one.return_value = {
        "_id": type_id,
        "user_email": "owner@example.com",
    }
    collections["portfolio_assets"].count_documents.return_value = 1

    with (
        patch("webapp.portfolio_repository.get_db", return_value=db),
        pytest.raises(ValueError, match="still uses this type"),
    ):
        delete_asset_type("owner@example.com", custom_kind)

    collections["portfolio_asset_types"].delete_one.assert_not_called()


def test_create_asset_records_initial_dated_valuation():
    db, collections = _portfolio_db()
    asset_id = ObjectId()
    collections["portfolio_assets"].insert_one.return_value.inserted_id = asset_id

    with (
        patch("webapp.portfolio_repository.get_db", return_value=db),
        patch("webapp.portfolio_repository.record_valuation") as mock_record,
    ):
        created = create_asset(
            "owner@example.com",
            {
                "name": "OCBC savings",
                "kind": "cash",
                "value": 28363.57,
                "as_of_date": "2026-04-30",
            },
        )

    assert created["id"] == str(asset_id)
    mock_record.assert_called_once_with(
        "owner@example.com",
        "asset",
        str(asset_id),
        {"as_of_date": "2026-04-30", "value": 28363.57},
        bootstrap_legacy=False,
    )


def test_create_asset_validates_date_before_inserting_document():
    db, collections = _portfolio_db()

    with (
        patch("webapp.portfolio_repository.get_db", return_value=db),
        pytest.raises(ValueError, match="YYYY-MM-DD"),
    ):
        create_asset(
            "owner@example.com",
            {"name": "OCBC savings", "kind": "cash", "value": 1000, "as_of_date": "not-a-date"},
        )

    collections["portfolio_assets"].insert_one.assert_not_called()


def test_record_valuation_upserts_same_date_and_syncs_latest_value():
    db, collections = _portfolio_db()
    asset_id = ObjectId()
    assets = collections["portfolio_assets"]
    valuations = collections["portfolio_valuations"]
    assets.find_one.return_value = {
        "_id": asset_id,
        "user_email": "owner@example.com",
        "value": 1000.0,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    valuations.count_documents.return_value = 1
    valuations.find_one.side_effect = [
        {
            "_id": ObjectId(),
            "user_email": "owner@example.com",
            "item_type": "asset",
            "item_id": asset_id,
            "as_of_date": "2026-04-30",
            "value": 1250.0,
        },
        {"as_of_date": "2026-04-30", "value": 1250.0},
    ]

    with patch("webapp.portfolio_repository.get_db", return_value=db):
        saved = record_valuation(
            "owner@example.com",
            "asset",
            str(asset_id),
            {"as_of_date": "2026-04-30", "value": 1250.0},
        )

    valuation_filter = valuations.update_one.call_args.args[0]
    assert valuation_filter == {
        "user_email": "owner@example.com",
        "item_type": "asset",
        "item_id": asset_id,
        "as_of_date": "2026-04-30",
    }
    assert valuations.update_one.call_args.kwargs["upsert"] is True
    assert saved["as_of_date"] == "2026-04-30"
    assert saved["value"] == 1250.0
    assets.update_one.assert_called_once()
    assert assets.update_one.call_args.args[1]["$set"]["value"] == 1250.0


def test_list_valuations_is_user_scoped_and_sorted_by_date():
    db, collections = _portfolio_db()
    asset_id = ObjectId()
    valuations = collections["portfolio_valuations"]
    valuations.find.return_value = [
        {
            "_id": ObjectId(),
            "user_email": "owner@example.com",
            "item_type": "asset",
            "item_id": asset_id,
            "as_of_date": "2026-01-31",
            "value": 1000.0,
        },
        {
            "_id": ObjectId(),
            "user_email": "owner@example.com",
            "item_type": "asset",
            "item_id": asset_id,
            "as_of_date": "2026-04-30",
            "value": 1250.0,
        },
    ]

    with patch("webapp.portfolio_repository.get_db", return_value=db):
        history = list_valuations("owner@example.com", "asset", str(asset_id))

    assert [entry["as_of_date"] for entry in history] == ["2026-01-31", "2026-04-30"]
    assert valuations.find.call_args.args[0] == {
        "user_email": "owner@example.com",
        "item_type": "asset",
        "item_id": asset_id,
    }
    assert valuations.find.call_args.kwargs["sort"] == [("as_of_date", 1)]


def test_delete_asset_also_deletes_its_valuation_history():
    db, collections = _portfolio_db()
    asset_id = ObjectId()
    collections["portfolio_assets"].delete_one.return_value.deleted_count = 1

    with patch("webapp.portfolio_repository.get_db", return_value=db):
        result = delete_asset("owner@example.com", str(asset_id))

    assert result == {"deleted": 1}
    collections["portfolio_valuations"].delete_many.assert_called_once_with(
        {
            "user_email": "owner@example.com",
            "item_type": "asset",
            "item_id": asset_id,
        }
    )


def test_delete_valuation_syncs_item_to_latest_remaining_value():
    db, collections = _portfolio_db()
    asset_id = ObjectId()
    assets = collections["portfolio_assets"]
    valuations = collections["portfolio_valuations"]
    assets.find_one.return_value = {"_id": asset_id, "user_email": "owner@example.com"}
    valuations.count_documents.return_value = 2
    valuations.delete_one.return_value.deleted_count = 1
    valuations.find_one.return_value = {"as_of_date": "2026-01-31", "value": 1000.0}

    with patch("webapp.portfolio_repository.get_db", return_value=db):
        result = delete_valuation("owner@example.com", "asset", str(asset_id), "2026-04-30")

    assert result == {"deleted": 1}
    valuations.delete_one.assert_called_once_with(
        {
            "user_email": "owner@example.com",
            "item_type": "asset",
            "item_id": asset_id,
            "as_of_date": "2026-04-30",
        }
    )
    assert assets.update_one.call_args.args[1]["$set"]["value"] == 1000.0
