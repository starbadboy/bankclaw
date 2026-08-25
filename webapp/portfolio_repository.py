"""Portfolio tracking — assets and liabilities per user.

Four collections, all scoped to ``user_email``:

* ``portfolio_assets`` — name, kind, sub, value, base, ticker, units
* ``portfolio_asset_types`` — user-defined asset class names and colors
* ``portfolio_debts``  — name, kind, sub, value, base, apr, monthly
* ``portfolio_valuations`` — dated values for each asset or debt
* ``portfolio_goals`` — net-worth milestone targets with optional dates

``value`` on an asset or debt is a denormalized copy of its latest dated
valuation. Historical charts read ``portfolio_valuations`` directly instead
of deriving synthetic data from the ``base → value`` pair.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime, timezone

from bson import ObjectId
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from webapp.db import get_db

_ASSETS_COLLECTION = "portfolio_assets"
_ASSET_TYPES_COLLECTION = "portfolio_asset_types"
_DEBTS_COLLECTION = "portfolio_debts"
_VALUATIONS_COLLECTION = "portfolio_valuations"
_GOALS_COLLECTION = "portfolio_goals"

_ASSET_KINDS = {"cash", "equities", "bonds", "retirement", "property", "crypto"}
_ASSET_KIND_NAMES = {"cash & savings", "equities", "bonds", "retirement", "property", "crypto"}
_DEBT_KINDS = {"mortgage", "credit", "loan"}
_CUSTOM_KIND_PREFIX = "custom_"
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _today_iso() -> str:
    return datetime.now(tz=timezone.utc).date().isoformat()


def _serialize(doc: dict) -> dict:
    out = dict(doc)
    out["id"] = str(out.pop("_id"))
    out.pop("user_email", None)
    return out


def _serialize_valuation(doc: dict) -> dict:
    out = dict(doc)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    out["item_id"] = str(out["item_id"])
    out.pop("user_email", None)
    return out


def _serialize_asset_type(doc: dict) -> dict:
    return {
        "id": f"{_CUSTOM_KIND_PREFIX}{doc['_id']}",
        "name": doc["name"],
        "color": doc["color"],
    }


def _ensure_indexes() -> None:
    db = get_db()
    for coll in (_ASSETS_COLLECTION, _DEBTS_COLLECTION):
        db[coll].create_index(
            [("user_email", ASCENDING), ("created_at", ASCENDING)],
            background=True,
        )
    db[_ASSET_TYPES_COLLECTION].create_index(
        [("user_email", ASCENDING), ("name_key", ASCENDING)],
        unique=True,
        background=True,
    )
    db[_VALUATIONS_COLLECTION].create_index(
        [
            ("user_email", ASCENDING),
            ("item_type", ASCENDING),
            ("item_id", ASCENDING),
            ("as_of_date", ASCENDING),
        ],
        unique=True,
        background=True,
    )
    db[_GOALS_COLLECTION].create_index(
        [("user_email", ASCENDING), ("target_amount", ASCENDING)],
        background=True,
    )


def _to_oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid id") from exc


def _coerce_value(raw: object, *, field: str) -> float:
    if raw is None:
        raise ValueError(f"{field} is required")
    try:
        v = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a number") from exc
    if not (v == v) or v in (float("inf"), float("-inf")):
        raise ValueError(f"{field} must be finite")
    return round(v, 2)


def _clean_str(raw: object, *, field: str, max_len: int = 200, required: bool = True) -> str:
    s = " ".join(str(raw or "").split())
    if required and not s:
        raise ValueError(f"{field} is required")
    return s[:max_len]


def _normalize_asset_type_name(raw: object) -> str:
    name = _clean_str(raw, field="name", max_len=40)
    if name.casefold() in _ASSET_KIND_NAMES:
        raise ValueError("A built-in asset type already uses this name")
    return name


def _normalize_asset_type_color(raw: object) -> str:
    color = _clean_str(raw or "#8B5CF6", field="color", max_len=7)
    if not _HEX_COLOR.fullmatch(color):
        raise ValueError("color must be a #RRGGBB hex value")
    return color.upper()


def _custom_asset_type_oid(type_id: str) -> ObjectId:
    value = _clean_str(type_id, field="asset type id", max_len=32)
    if not value.startswith(_CUSTOM_KIND_PREFIX):
        raise ValueError("Invalid custom asset type id")
    return _to_oid(value.removeprefix(_CUSTOM_KIND_PREFIX))


def _validate_asset_kind(user_email: str, kind: str) -> str:
    if kind in _ASSET_KINDS:
        return kind
    try:
        oid = _custom_asset_type_oid(kind)
    except ValueError as exc:
        raise ValueError(f"Unknown asset kind '{kind}'") from exc
    custom_type = get_db()[_ASSET_TYPES_COLLECTION].find_one({"_id": oid, "user_email": user_email})
    if not custom_type:
        raise ValueError(f"Unknown asset kind '{kind}'")
    return kind


_TICKER = re.compile(r"^[A-Z0-9.^=\-]{1,16}$")


def _clean_ticker(raw: object) -> str | None:
    ticker = (_clean_str(raw, field="ticker", max_len=32, required=False) or "").upper()
    if not ticker:
        return None
    if not _TICKER.match(ticker):
        raise ValueError("ticker may only contain letters, digits, . ^ = - (max 16)")
    return ticker


def _coerce_units(raw: object) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        units = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("units must be a number") from exc
    if not math.isfinite(units) or units < 0:
        raise ValueError("units must be zero or greater")
    return round(units, 6)  # fractional shares / coins


def _normalize_item_type(item_type: str) -> str:
    normalized = _clean_str(item_type, field="item_type", max_len=16)
    if normalized not in {"asset", "debt"}:
        raise ValueError("item_type must be 'asset' or 'debt'")
    return normalized


def _normalize_as_of_date(raw: object, *, field: str = "as_of_date") -> str:
    value = _clean_str(raw, field=field, max_len=10)
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid YYYY-MM-DD date") from exc


def _item_collection(item_type: str) -> str:
    return _ASSETS_COLLECTION if item_type == "asset" else _DEBTS_COLLECTION


def _valuation_filter(user_email: str, item_type: str, item_id: ObjectId) -> dict:
    return {
        "user_email": user_email,
        "item_type": item_type,
        "item_id": item_id,
    }


def _upsert_valuation(
    user_email: str,
    item_type: str,
    item_id: ObjectId,
    *,
    as_of_date: str,
    value: float,
) -> dict:
    now = _now_iso()
    query = {
        **_valuation_filter(user_email, item_type, item_id),
        "as_of_date": as_of_date,
    }
    collection = get_db()[_VALUATIONS_COLLECTION]
    collection.update_one(
        query,
        {
            "$set": {"value": value, "updated_at": now},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    return collection.find_one(query)


def _materialize_legacy_baseline(user_email: str, item_type: str, item: dict) -> None:
    item_id = item["_id"]
    valuations = get_db()[_VALUATIONS_COLLECTION]
    query = _valuation_filter(user_email, item_type, item_id)
    if valuations.count_documents(query, limit=1):
        return

    created_date = str(item.get("created_at") or "")[:10]
    try:
        created_date = date.fromisoformat(created_date).isoformat()
    except ValueError:
        created_date = _today_iso()
    _upsert_valuation(
        user_email,
        item_type,
        item_id,
        as_of_date=created_date,
        value=_coerce_value(item.get("value"), field="value"),
    )


def _sync_current_value(user_email: str, item_type: str, item_id: ObjectId) -> None:
    latest = get_db()[_VALUATIONS_COLLECTION].find_one(
        _valuation_filter(user_email, item_type, item_id),
        sort=[("as_of_date", -1)],
    )
    if not latest:
        return
    get_db()[_item_collection(item_type)].update_one(
        {"_id": item_id, "user_email": user_email},
        {"$set": {"value": latest["value"], "updated_at": _now_iso()}},
    )


def record_valuation(
    user_email: str,
    item_type: str,
    item_id: str,
    payload: dict,
    *,
    bootstrap_legacy: bool = True,
) -> dict:
    """Create or replace one dated valuation and sync the item's current value."""
    _ensure_indexes()
    normalized_type = _normalize_item_type(item_type)
    oid = _to_oid(item_id)
    item = get_db()[_item_collection(normalized_type)].find_one({"_id": oid, "user_email": user_email})
    if not item:
        raise ValueError(f"{normalized_type.title()} not found")
    if bootstrap_legacy:
        _materialize_legacy_baseline(user_email, normalized_type, item)

    as_of_date = _normalize_as_of_date(payload.get("as_of_date"))
    value = _coerce_value(payload.get("value"), field="value")
    if value < 0:
        raise ValueError("value must be zero or greater")
    saved = _upsert_valuation(
        user_email,
        normalized_type,
        oid,
        as_of_date=as_of_date,
        value=value,
    )
    _sync_current_value(user_email, normalized_type, oid)
    return _serialize_valuation(saved)


def list_valuations(user_email: str, item_type: str, item_id: str) -> list[dict]:
    """Return one item's real valuation history in chronological order."""
    _ensure_indexes()
    normalized_type = _normalize_item_type(item_type)
    oid = _to_oid(item_id)
    item = get_db()[_item_collection(normalized_type)].find_one({"_id": oid, "user_email": user_email})
    if not item:
        raise ValueError(f"{normalized_type.title()} not found")
    _materialize_legacy_baseline(user_email, normalized_type, item)
    docs = get_db()[_VALUATIONS_COLLECTION].find(
        _valuation_filter(user_email, normalized_type, oid),
        sort=[("as_of_date", ASCENDING)],
    )
    return [_serialize_valuation(doc) for doc in docs]


def delete_valuation(user_email: str, item_type: str, item_id: str, as_of_date: str) -> dict:
    """Delete one dated value while keeping at least one valuation per item."""
    _ensure_indexes()
    normalized_type = _normalize_item_type(item_type)
    normalized_date = _normalize_as_of_date(as_of_date)
    oid = _to_oid(item_id)
    item = get_db()[_item_collection(normalized_type)].find_one({"_id": oid, "user_email": user_email})
    if not item:
        raise ValueError(f"{normalized_type.title()} not found")
    _materialize_legacy_baseline(user_email, normalized_type, item)

    collection = get_db()[_VALUATIONS_COLLECTION]
    item_filter = _valuation_filter(user_email, normalized_type, oid)
    if collection.count_documents(item_filter, limit=2) <= 1:
        raise ValueError("At least one valuation is required")
    result = collection.delete_one({**item_filter, "as_of_date": normalized_date})
    if result.deleted_count == 0:
        raise ValueError("Valuation not found")
    _sync_current_value(user_email, normalized_type, oid)
    return {"deleted": 1}


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
def list_portfolio(user_email: str) -> dict:
    _ensure_indexes()
    db = get_db()
    assets = [
        _serialize(doc)
        for doc in db[_ASSETS_COLLECTION].find({"user_email": user_email}, sort=[("created_at", ASCENDING)])
    ]
    debts = [
        _serialize(doc)
        for doc in db[_DEBTS_COLLECTION].find({"user_email": user_email}, sort=[("created_at", ASCENDING)])
    ]
    return {"assets": assets, "debts": debts}


# ---------------------------------------------------------------------------
# Custom asset types
# ---------------------------------------------------------------------------
def list_asset_types(user_email: str) -> list[dict]:
    _ensure_indexes()
    docs = get_db()[_ASSET_TYPES_COLLECTION].find(
        {"user_email": user_email},
        sort=[("name_key", ASCENDING)],
    )
    return [_serialize_asset_type(doc) for doc in docs]


def create_asset_type(user_email: str, payload: dict) -> dict:
    _ensure_indexes()
    name = _normalize_asset_type_name(payload.get("name"))
    now = _now_iso()
    doc = {
        "user_email": user_email,
        "name": name,
        "name_key": name.casefold(),
        "color": _normalize_asset_type_color(payload.get("color")),
        "created_at": now,
        "updated_at": now,
    }
    try:
        result = get_db()[_ASSET_TYPES_COLLECTION].insert_one(doc)
    except DuplicateKeyError as exc:
        raise ValueError("An asset type with this name already exists") from exc
    doc["_id"] = result.inserted_id
    return _serialize_asset_type(doc)


def update_asset_type(user_email: str, type_id: str, payload: dict) -> dict:
    _ensure_indexes()
    oid = _custom_asset_type_oid(type_id)
    set_doc: dict = {}
    if "name" in payload:
        name = _normalize_asset_type_name(payload["name"])
        set_doc.update({"name": name, "name_key": name.casefold()})
    if "color" in payload:
        set_doc["color"] = _normalize_asset_type_color(payload["color"])
    if not set_doc:
        raise ValueError("Nothing to update")
    set_doc["updated_at"] = _now_iso()
    try:
        result = get_db()[_ASSET_TYPES_COLLECTION].find_one_and_update(
            {"_id": oid, "user_email": user_email},
            {"$set": set_doc},
            return_document=True,
        )
    except DuplicateKeyError as exc:
        raise ValueError("An asset type with this name already exists") from exc
    if not result:
        raise ValueError("Asset type not found")
    return _serialize_asset_type(result)


def delete_asset_type(user_email: str, type_id: str) -> dict:
    _ensure_indexes()
    oid = _custom_asset_type_oid(type_id)
    collection = get_db()[_ASSET_TYPES_COLLECTION]
    if not collection.find_one({"_id": oid, "user_email": user_email}):
        raise ValueError("Asset type not found")
    if get_db()[_ASSETS_COLLECTION].count_documents({"user_email": user_email, "kind": type_id}, limit=1):
        raise ValueError("An asset still uses this type")
    result = collection.delete_one({"_id": oid, "user_email": user_email})
    if result.deleted_count == 0:
        raise ValueError("Asset type not found")
    return {"deleted": 1}


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------


def _serialize_goal(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "target_amount": doc["target_amount"],
        "target_date": doc.get("target_date"),
    }


def _normalize_goal_target(raw: object) -> float:
    value = _coerce_value(raw, field="target_amount")
    if value <= 0:
        raise ValueError("target_amount must be greater than zero")
    return value


def _normalize_goal_date(raw: object) -> str | None:
    if raw in (None, ""):
        return None
    return _normalize_as_of_date(raw, field="target_date")


def list_goals(user_email: str) -> list[dict]:
    _ensure_indexes()
    docs = get_db()[_GOALS_COLLECTION].find(
        {"user_email": user_email},
        sort=[("target_amount", ASCENDING)],
    )
    return [_serialize_goal(doc) for doc in docs]


def create_goal(user_email: str, payload: dict) -> dict:
    _ensure_indexes()
    now = _now_iso()
    doc = {
        "user_email": user_email,
        "name": _clean_str(payload.get("name"), field="name", max_len=80),
        "target_amount": _normalize_goal_target(payload.get("target_amount")),
        "target_date": _normalize_goal_date(payload.get("target_date")),
        "created_at": now,
        "updated_at": now,
    }
    result = get_db()[_GOALS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize_goal(doc)


def update_goal(user_email: str, goal_id: str, payload: dict) -> dict:
    _ensure_indexes()
    set_doc: dict = {}
    if "name" in payload:
        set_doc["name"] = _clean_str(payload["name"], field="name", max_len=80)
    if "target_amount" in payload:
        set_doc["target_amount"] = _normalize_goal_target(payload["target_amount"])
    if "target_date" in payload:
        set_doc["target_date"] = _normalize_goal_date(payload["target_date"])
    if not set_doc:
        raise ValueError("Nothing to update")
    set_doc["updated_at"] = _now_iso()
    result = get_db()[_GOALS_COLLECTION].find_one_and_update(
        {"_id": _to_oid(goal_id), "user_email": user_email},
        {"$set": set_doc},
        return_document=True,
    )
    if not result:
        raise ValueError("Goal not found")
    return _serialize_goal(result)


def delete_goal(user_email: str, goal_id: str) -> dict:
    _ensure_indexes()
    result = get_db()[_GOALS_COLLECTION].delete_one(
        {"_id": _to_oid(goal_id), "user_email": user_email}
    )
    if result.deleted_count == 0:
        raise ValueError("Goal not found")
    return {"deleted": 1}


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
def create_asset(user_email: str, payload: dict) -> dict:
    _ensure_indexes()
    name = _clean_str(payload.get("name"), field="name")
    kind = _clean_str(payload.get("kind"), field="kind", max_len=32)
    _validate_asset_kind(user_email, kind)
    value = _coerce_value(payload.get("value"), field="value")
    if value < 0:
        raise ValueError("value must be zero or greater")
    as_of_date = _normalize_as_of_date(payload.get("as_of_date") or _today_iso())
    base = _coerce_value(payload.get("base", value), field="base")
    sub = _clean_str(payload.get("sub"), field="sub", required=False) or "Manual entry"
    ticker = _clean_ticker(payload.get("ticker"))
    units = _coerce_units(payload.get("units"))

    doc = {
        "user_email": user_email,
        "name": name,
        "kind": kind,
        "sub": sub,
        "value": value,
        "base": base,
        "ticker": ticker,
        "units": units,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    result = get_db()[_ASSETS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    serialized = _serialize(doc)
    record_valuation(
        user_email,
        "asset",
        serialized["id"],
        {"as_of_date": as_of_date, "value": value},
        bootstrap_legacy=False,
    )
    return serialized


def update_asset(user_email: str, asset_id: str, payload: dict) -> dict:
    oid = _to_oid(asset_id)
    set_doc: dict = {}
    if "name" in payload:
        set_doc["name"] = _clean_str(payload["name"], field="name")
    if "kind" in payload:
        kind = _clean_str(payload["kind"], field="kind", max_len=32)
        _validate_asset_kind(user_email, kind)
        set_doc["kind"] = kind
    if "sub" in payload:
        set_doc["sub"] = _clean_str(payload["sub"], field="sub", required=False) or "Manual entry"
    if "value" in payload:
        set_doc["value"] = _coerce_value(payload["value"], field="value")
    if "base" in payload:
        set_doc["base"] = _coerce_value(payload["base"], field="base")
    if "ticker" in payload:
        set_doc["ticker"] = _clean_ticker(payload["ticker"])
    if "units" in payload:
        set_doc["units"] = _coerce_units(payload["units"])
    if not set_doc:
        raise ValueError("Nothing to update")
    set_doc["updated_at"] = _now_iso()

    result = get_db()[_ASSETS_COLLECTION].find_one_and_update(
        {"_id": oid, "user_email": user_email},
        {"$set": set_doc},
        return_document=True,
    )
    if not result:
        raise ValueError("Asset not found")
    return _serialize(result)


def delete_asset(user_email: str, asset_id: str) -> dict:
    oid = _to_oid(asset_id)
    res = get_db()[_ASSETS_COLLECTION].delete_one({"_id": oid, "user_email": user_email})
    if res.deleted_count == 0:
        raise ValueError("Asset not found")
    get_db()[_VALUATIONS_COLLECTION].delete_many(_valuation_filter(user_email, "asset", oid))
    return {"deleted": 1}


# ---------------------------------------------------------------------------
# Debts
# ---------------------------------------------------------------------------
def create_debt(user_email: str, payload: dict) -> dict:
    _ensure_indexes()
    name = _clean_str(payload.get("name"), field="name")
    kind = _clean_str(payload.get("kind"), field="kind", max_len=32)
    if kind not in _DEBT_KINDS:
        raise ValueError(f"Unknown debt kind '{kind}'")
    value = _coerce_value(payload.get("value"), field="value")
    if value < 0:
        raise ValueError("value must be zero or greater")
    as_of_date = _normalize_as_of_date(payload.get("as_of_date") or _today_iso())
    base = _coerce_value(payload.get("base", value), field="base")
    sub = _clean_str(payload.get("sub"), field="sub", required=False) or "Manual entry"
    apr = float(payload.get("apr") or 0.0)
    monthly = float(payload.get("monthly") or 0.0)

    doc = {
        "user_email": user_email,
        "name": name,
        "kind": kind,
        "sub": sub,
        "value": value,
        "base": base,
        "apr": round(apr, 4),
        "monthly": round(monthly, 2),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    result = get_db()[_DEBTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    serialized = _serialize(doc)
    record_valuation(
        user_email,
        "debt",
        serialized["id"],
        {"as_of_date": as_of_date, "value": value},
        bootstrap_legacy=False,
    )
    return serialized


def update_debt(user_email: str, debt_id: str, payload: dict) -> dict:
    oid = _to_oid(debt_id)
    set_doc: dict = {}
    if "name" in payload:
        set_doc["name"] = _clean_str(payload["name"], field="name")
    if "kind" in payload:
        kind = _clean_str(payload["kind"], field="kind", max_len=32)
        if kind not in _DEBT_KINDS:
            raise ValueError(f"Unknown debt kind '{kind}'")
        set_doc["kind"] = kind
    if "sub" in payload:
        set_doc["sub"] = _clean_str(payload["sub"], field="sub", required=False) or "Manual entry"
    if "value" in payload:
        set_doc["value"] = _coerce_value(payload["value"], field="value")
    if "base" in payload:
        set_doc["base"] = _coerce_value(payload["base"], field="base")
    if "apr" in payload:
        set_doc["apr"] = round(float(payload["apr"] or 0.0), 4)
    if "monthly" in payload:
        set_doc["monthly"] = round(float(payload["monthly"] or 0.0), 2)
    if not set_doc:
        raise ValueError("Nothing to update")
    set_doc["updated_at"] = _now_iso()

    result = get_db()[_DEBTS_COLLECTION].find_one_and_update(
        {"_id": oid, "user_email": user_email},
        {"$set": set_doc},
        return_document=True,
    )
    if not result:
        raise ValueError("Debt not found")
    return _serialize(result)


def delete_debt(user_email: str, debt_id: str) -> dict:
    oid = _to_oid(debt_id)
    res = get_db()[_DEBTS_COLLECTION].delete_one({"_id": oid, "user_email": user_email})
    if res.deleted_count == 0:
        raise ValueError("Debt not found")
    get_db()[_VALUATIONS_COLLECTION].delete_many(_valuation_filter(user_email, "debt", oid))
    return {"deleted": 1}
