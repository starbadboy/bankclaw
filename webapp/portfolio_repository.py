"""Portfolio tracking — assets and liabilities per user.

Three collections, all scoped to ``user_email``:

* ``portfolio_assets`` — name, kind, sub, value, base, ticker
* ``portfolio_debts``  — name, kind, sub, value, base, apr, monthly
* ``portfolio_valuations`` — dated values for each asset or debt

``value`` on an asset or debt is a denormalized copy of its latest dated
valuation. Historical charts read ``portfolio_valuations`` directly instead
of deriving synthetic data from the ``base → value`` pair.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from bson import ObjectId
from pymongo import ASCENDING

from webapp.db import get_db

_ASSETS_COLLECTION = "portfolio_assets"
_DEBTS_COLLECTION = "portfolio_debts"
_VALUATIONS_COLLECTION = "portfolio_valuations"

_ASSET_KINDS = {"cash", "equities", "bonds", "retirement", "property", "crypto"}
_DEBT_KINDS = {"mortgage", "credit", "loan"}


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


def _ensure_indexes() -> None:
    db = get_db()
    for coll in (_ASSETS_COLLECTION, _DEBTS_COLLECTION):
        db[coll].create_index(
            [("user_email", ASCENDING), ("created_at", ASCENDING)],
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


def _normalize_item_type(item_type: str) -> str:
    normalized = _clean_str(item_type, field="item_type", max_len=16)
    if normalized not in {"asset", "debt"}:
        raise ValueError("item_type must be 'asset' or 'debt'")
    return normalized


def _normalize_as_of_date(raw: object) -> str:
    value = _clean_str(raw, field="as_of_date", max_len=10)
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError("as_of_date must be a valid YYYY-MM-DD date") from exc


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
# Assets
# ---------------------------------------------------------------------------
def create_asset(user_email: str, payload: dict) -> dict:
    _ensure_indexes()
    name = _clean_str(payload.get("name"), field="name")
    kind = _clean_str(payload.get("kind"), field="kind", max_len=32)
    if kind not in _ASSET_KINDS:
        raise ValueError(f"Unknown asset kind '{kind}'")
    value = _coerce_value(payload.get("value"), field="value")
    if value < 0:
        raise ValueError("value must be zero or greater")
    as_of_date = _normalize_as_of_date(payload.get("as_of_date") or _today_iso())
    base = _coerce_value(payload.get("base", value), field="base")
    sub = _clean_str(payload.get("sub"), field="sub", required=False) or "Manual entry"
    ticker = _clean_str(payload.get("ticker"), field="ticker", max_len=16, required=False) or None

    doc = {
        "user_email": user_email,
        "name": name,
        "kind": kind,
        "sub": sub,
        "value": value,
        "base": base,
        "ticker": ticker,
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
        if kind not in _ASSET_KINDS:
            raise ValueError(f"Unknown asset kind '{kind}'")
        set_doc["kind"] = kind
    if "sub" in payload:
        set_doc["sub"] = _clean_str(payload["sub"], field="sub", required=False) or "Manual entry"
    if "value" in payload:
        set_doc["value"] = _coerce_value(payload["value"], field="value")
    if "base" in payload:
        set_doc["base"] = _coerce_value(payload["base"], field="base")
    if "ticker" in payload:
        set_doc["ticker"] = _clean_str(payload["ticker"], field="ticker", max_len=16, required=False) or None
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
