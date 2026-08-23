from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId

from webapp.portfolio_repository import (
    create_asset,
    delete_asset,
    delete_valuation,
    list_valuations,
    record_valuation,
)


def _portfolio_db():
    db = MagicMock()
    collections = {
        "portfolio_assets": MagicMock(),
        "portfolio_debts": MagicMock(),
        "portfolio_valuations": MagicMock(),
    }
    db.__getitem__.side_effect = collections.__getitem__
    return db, collections


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
