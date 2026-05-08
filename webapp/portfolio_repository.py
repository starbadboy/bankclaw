"""Portfolio tracking — assets and liabilities per user.

Two collections, both scoped to ``user_email``:

* ``portfolio_assets`` — name, kind, sub, value, base, ticker
* ``portfolio_debts``  — name, kind, sub, value, base, apr, monthly

``base`` is the opening / cost-basis snapshot used for delta and trend
calculation; ``value`` is the current valuation. The dashboard derives
12-month sparklines from the (base → value) pair.
"""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ASCENDING

from webapp.db import get_db

_ASSETS_COLLECTION = "portfolio_assets"
_DEBTS_COLLECTION = "portfolio_debts"

_ASSET_KINDS = {"cash", "equities", "bonds", "retirement", "property", "crypto"}
_DEBT_KINDS = {"mortgage", "credit", "loan"}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _serialize(doc: dict) -> dict:
    out = dict(doc)
    out["id"] = str(out.pop("_id"))
    out.pop("user_email", None)
    return out


def _ensure_indexes() -> None:
    db = get_db()
    for coll in (_ASSETS_COLLECTION, _DEBTS_COLLECTION):
        db[coll].create_index(
            [("user_email", ASCENDING), ("created_at", ASCENDING)],
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


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
def list_portfolio(user_email: str) -> dict:
    _ensure_indexes()
    db = get_db()
    assets = [
        _serialize(doc)
        for doc in db[_ASSETS_COLLECTION].find(
            {"user_email": user_email}, sort=[("created_at", ASCENDING)]
        )
    ]
    debts = [
        _serialize(doc)
        for doc in db[_DEBTS_COLLECTION].find(
            {"user_email": user_email}, sort=[("created_at", ASCENDING)]
        )
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
    return _serialize(doc)


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
    return _serialize(doc)


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
    return {"deleted": 1}
