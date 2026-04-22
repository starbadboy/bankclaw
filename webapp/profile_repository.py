"""Family profiles — sub-accounts within one Bankclaw account.

Transactions are tagged with ``profile_id`` so the owner can view a single
profile (e.g. "Kids") or combine everything ("All"). Categories and category
memory remain shared across the account.
"""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ASCENDING

from webapp.db import get_db

_PROFILES_COLLECTION = "profiles"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _serialize(profile: dict) -> dict:
    out = dict(profile)
    out["id"] = str(out.pop("_id"))
    return out


def ensure_main_profile(user_email: str) -> dict:
    """Return the user's main profile, creating it on first access."""
    db = get_db()
    coll = db[_PROFILES_COLLECTION]
    coll.create_index([("user_email", ASCENDING), ("name", ASCENDING)], background=True)

    main = coll.find_one({"user_email": user_email, "is_main": True})
    if main:
        return _serialize(main)

    doc = {
        "user_email": user_email,
        "name": "Main",
        "color": "#1f2937",
        "is_main": True,
        "created_at": _now_iso(),
    }
    result = coll.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize(doc)


def list_profiles(user_email: str) -> list[dict]:
    ensure_main_profile(user_email)
    db = get_db()
    cursor = db[_PROFILES_COLLECTION].find(
        {"user_email": user_email},
        sort=[("is_main", -1), ("created_at", ASCENDING)],
    )
    return [_serialize(p) for p in cursor]


def create_profile(user_email: str, name: str, color: str | None = None) -> dict:
    cleaned = " ".join(str(name).split())
    if not cleaned:
        raise ValueError("Profile name cannot be blank")

    db = get_db()
    coll = db[_PROFILES_COLLECTION]
    existing = coll.find_one({"user_email": user_email, "name": cleaned})
    if existing:
        raise ValueError("A profile with that name already exists")

    doc = {
        "user_email": user_email,
        "name": cleaned,
        "color": (color or "").strip() or "#b8602e",
        "is_main": False,
        "created_at": _now_iso(),
    }
    result = coll.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize(doc)


def update_profile(
    user_email: str, profile_id: str, name: str | None = None, color: str | None = None
) -> dict:
    db = get_db()
    coll = db[_PROFILES_COLLECTION]
    try:
        oid = ObjectId(profile_id)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid profile id") from exc

    set_doc: dict = {}
    if name is not None:
        cleaned = " ".join(str(name).split())
        if not cleaned:
            raise ValueError("Profile name cannot be blank")
        clash = coll.find_one({"user_email": user_email, "name": cleaned, "_id": {"$ne": oid}})
        if clash:
            raise ValueError("A profile with that name already exists")
        set_doc["name"] = cleaned
    if color is not None:
        set_doc["color"] = str(color).strip() or "#b8602e"

    if not set_doc:
        raise ValueError("Nothing to update")

    result = coll.find_one_and_update(
        {"_id": oid, "user_email": user_email},
        {"$set": set_doc},
        return_document=True,
    )
    if not result:
        raise ValueError("Profile not found")
    return _serialize(result)


def delete_profile(user_email: str, profile_id: str) -> dict:
    """Delete a profile and re-assign its transactions to the main profile."""
    db = get_db()
    coll = db[_PROFILES_COLLECTION]
    try:
        oid = ObjectId(profile_id)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid profile id") from exc

    profile = coll.find_one({"_id": oid, "user_email": user_email})
    if not profile:
        raise ValueError("Profile not found")
    if profile.get("is_main"):
        raise ValueError("Cannot delete the main profile")

    main = ensure_main_profile(user_email)
    main_id_str = main["id"]

    reassigned = db["transactions"].update_many(
        {"user_email": user_email, "profile_id": profile_id},
        {"$set": {"profile_id": main_id_str}},
    ).modified_count

    coll.delete_one({"_id": oid, "user_email": user_email})
    return {"deleted": 1, "reassigned": reassigned, "moved_to_profile_id": main_id_str}
