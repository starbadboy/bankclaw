from datetime import datetime, timezone
import re

import pandas as pd
from pymongo import ASCENDING, UpdateOne

from webapp.db import get_db

_COLLECTION = "transactions"
_CATEGORY_MEMORY_COLLECTION = "category_memory"
_CUSTOM_CATEGORY_COLLECTION = "custom_categories"

_EMPTY_COLUMNS = ["user_email", "date", "description", "amount", "bank", "category", "saved_at", "profile_id"]
_MEMORY_EMPTY_COLUMNS = [
    "user_email",
    "normalized_description",
    "last_raw_description",
    "category",
    "source",
    "updated_at",
]
_CUSTOM_CATEGORY_EMPTY_COLUMNS = [
    "user_email",
    "name",
    "normalized_name",
    "is_active",
    "created_at",
    "updated_at",
]


def normalize_description(description: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]", " ", description.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _normalize_category_name(name: str) -> str:
    return " ".join(name.split()).casefold()


def save_transactions(
    df: pd.DataFrame,
    user_email: str,
    batch_size: int = 200,
    profile_id: str | None = None,
) -> int:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    db = get_db()
    collection = db[_COLLECTION]

    collection.create_index(
        [
            ("user_email", ASCENDING),
            ("date", ASCENDING),
            ("description", ASCENDING),
            ("amount", ASCENDING),
            ("bank", ASCENDING),
        ],
        unique=True,
        background=True,
    )

    saved_count = 0
    operations: list[UpdateOne] = []
    for _, row in df.iterrows():
        date_str = str(row["date"])
        filter_doc = {
            "user_email": user_email,
            "date": date_str,
            "description": str(row["description"]),
            "amount": float(row["amount"]),
            "bank": str(row["bank"]),
        }
        set_doc = {
            **filter_doc,
            "category": str(row.get("category", "Other")),
            "saved_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        if profile_id:
            set_doc["profile_id"] = profile_id
        update_doc = {"$set": set_doc}
        operations.append(UpdateOne(filter_doc, update_doc, upsert=True))

        if len(operations) >= batch_size:
            collection.bulk_write(operations, ordered=False)
            saved_count += len(operations)
            operations = []

    if operations:
        collection.bulk_write(operations, ordered=False)
        saved_count += len(operations)

    return saved_count


def save_category_memory(
    df: pd.DataFrame,
    user_email: str,
    source: str = "manual",
    batch_size: int = 200,
) -> int:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    db = get_db()
    collection = db[_CATEGORY_MEMORY_COLLECTION]

    collection.create_index(
        [
            ("user_email", ASCENDING),
            ("normalized_description", ASCENDING),
        ],
        unique=True,
        background=True,
    )
    collection.create_index(
        [
            ("user_email", ASCENDING),
            ("updated_at", ASCENDING),
        ],
        background=True,
    )

    normalized_rows: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        raw_description = str(row["description"])
        normalized_description = normalize_description(raw_description)
        if not normalized_description:
            continue
        normalized_rows[normalized_description] = {
            "last_raw_description": raw_description,
            "category": str(row["category"]),
        }

    saved_count = 0
    operations: list[UpdateOne] = []
    for normalized_description, row in normalized_rows.items():
        filter_doc = {
            "user_email": user_email,
            "normalized_description": normalized_description,
        }
        update_doc = {
            "$set": {
                **filter_doc,
                "last_raw_description": row["last_raw_description"],
                "category": row["category"],
                "source": source,
                "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        }
        operations.append(UpdateOne(filter_doc, update_doc, upsert=True))

        if len(operations) >= batch_size:
            collection.bulk_write(operations, ordered=False)
            saved_count += len(operations)
            operations = []

    if operations:
        collection.bulk_write(operations, ordered=False)
        saved_count += len(operations)

    return saved_count


def get_category_memory(user_email: str) -> pd.DataFrame:
    db = get_db()
    collection = db[_CATEGORY_MEMORY_COLLECTION]

    cursor = collection.find(
        {"user_email": user_email},
        {"_id": 0},
        sort=[("updated_at", ASCENDING)],
    )
    records = list(cursor)

    if not records:
        return pd.DataFrame(columns=_MEMORY_EMPTY_COLUMNS)

    return pd.DataFrame(records)


def save_custom_category(name: str, user_email: str, glyph: str | None = None) -> int:
    if not isinstance(name, str):
        raise ValueError("Category name must be a string")

    cleaned_name = " ".join(name.split())
    if not cleaned_name:
        raise ValueError("Category name cannot be blank")

    cleaned_glyph = (glyph or "").strip() or "•"

    normalized_name = _normalize_category_name(cleaned_name)
    now = datetime.now(tz=timezone.utc).isoformat()
    db = get_db()
    collection = db[_CUSTOM_CATEGORY_COLLECTION]

    collection.create_index(
        [
            ("user_email", ASCENDING),
            ("normalized_name", ASCENDING),
        ],
        unique=True,
        background=True,
    )
    collection.create_index(
        [
            ("user_email", ASCENDING),
            ("updated_at", ASCENDING),
        ],
        background=True,
    )

    filter_doc = {
        "user_email": user_email,
        "normalized_name": normalized_name,
    }
    update_doc = {
        "$set": {
            **filter_doc,
            "name": cleaned_name,
            "glyph": cleaned_glyph,
            "is_active": True,
            "updated_at": now,
        },
        "$setOnInsert": {
            "created_at": now,
        },
    }
    collection.bulk_write([UpdateOne(filter_doc, update_doc, upsert=True)], ordered=False)
    return 1


def get_custom_categories(user_email: str, include_inactive: bool = False) -> pd.DataFrame:
    db = get_db()
    collection = db[_CUSTOM_CATEGORY_COLLECTION]
    query = {"user_email": user_email}
    if not include_inactive:
        query["is_active"] = True

    cursor = collection.find(
        query,
        {"_id": 0},
        sort=[("updated_at", ASCENDING)],
    )
    records = list(cursor)
    if not records:
        return pd.DataFrame(columns=_CUSTOM_CATEGORY_EMPTY_COLUMNS)

    return pd.DataFrame(records)


def archive_custom_category(name: str, user_email: str) -> int:
    if not isinstance(name, str):
        raise ValueError("Category name must be a string")

    normalized_name = _normalize_category_name(" ".join(name.split()))
    if not normalized_name:
        raise ValueError("Category name cannot be blank")

    db = get_db()
    collection = db[_CUSTOM_CATEGORY_COLLECTION]
    result = collection.update_one(
        {
            "user_email": user_email,
            "normalized_name": normalized_name,
        },
        {
            "$set": {
                "is_active": False,
                "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        },
    )
    return result.modified_count


def get_transactions_by_date_range(
    start_date: str,
    end_date: str,
    user_email: str,
    profile_id: str | None = None,
    main_profile_id: str | None = None,
) -> pd.DataFrame:
    """Fetch transactions. When ``profile_id`` is provided, filter to that
    profile — for the main profile, also include rows missing ``profile_id``
    so pre-migration transactions show up."""
    db = get_db()
    collection = db[_COLLECTION]

    query: dict = {
        "user_email": user_email,
        "date": {"$gte": start_date, "$lte": end_date},
    }
    if profile_id:
        if main_profile_id and profile_id == main_profile_id:
            query["$or"] = [
                {"profile_id": profile_id},
                {"profile_id": {"$exists": False}},
                {"profile_id": None},
            ]
        else:
            query["profile_id"] = profile_id

    cursor = collection.find(query, {"_id": 0}, sort=[("date", ASCENDING)])
    records = list(cursor)

    if not records:
        return pd.DataFrame(columns=_EMPTY_COLUMNS)

    return pd.DataFrame(records)


def rename_custom_category(
    *, user_email: str, old_name: str, new_name: str | None = None, new_glyph: str | None = None
) -> dict:
    """Rename and/or re-glyph a custom category. Also re-tags matching transactions
    and category_memory rows so the rest of the app picks up the new name."""
    if not isinstance(old_name, str) or not old_name.strip():
        raise ValueError("Old category name required")

    old_clean = " ".join(old_name.split())
    old_norm = _normalize_category_name(old_clean)

    do_rename = bool(new_name) and _normalize_category_name(" ".join((new_name or "").split())) != old_norm
    new_clean = " ".join((new_name or "").split()) if do_rename else old_clean
    new_norm = _normalize_category_name(new_clean) if do_rename else old_norm

    if do_rename and not new_clean:
        raise ValueError("New category name cannot be blank")

    cleaned_glyph = (new_glyph or "").strip() or None
    now = datetime.now(tz=timezone.utc).isoformat()

    db = get_db()
    custom = db[_CUSTOM_CATEGORY_COLLECTION]

    if do_rename:
        # reject rename into a name that already exists (active or not)
        clash = custom.find_one({"user_email": user_email, "normalized_name": new_norm, "is_active": True})
        if clash:
            raise ValueError("A category with that name already exists")

    set_doc: dict = {"updated_at": now}
    if do_rename:
        set_doc["name"] = new_clean
        set_doc["normalized_name"] = new_norm
    if cleaned_glyph is not None:
        set_doc["glyph"] = cleaned_glyph

    result = custom.update_one(
        {"user_email": user_email, "normalized_name": old_norm},
        {"$set": set_doc},
    )

    tx_modified = 0
    mem_modified = 0
    if do_rename and result.matched_count:
        tx_res = db[_COLLECTION].update_many(
            {"user_email": user_email, "category": old_clean},
            {"$set": {"category": new_clean}},
        )
        tx_modified = tx_res.modified_count
        mem_res = db[_CATEGORY_MEMORY_COLLECTION].update_many(
            {"user_email": user_email, "category": old_clean},
            {"$set": {"category": new_clean}},
        )
        mem_modified = mem_res.modified_count

    return {
        "matched": result.matched_count,
        "modified": result.modified_count,
        "transactions_retagged": tx_modified,
        "memory_retagged": mem_modified,
        "name": new_clean,
    }


def update_transaction_category(
    *, user_email: str, date: str, description: str, amount: float, bank: str, category: str
) -> int:
    db = get_db()
    collection = db[_COLLECTION]
    result = collection.update_one(
        {
            "user_email": user_email,
            "date": str(date),
            "description": str(description),
            "amount": float(amount),
            "bank": str(bank),
        },
        {"$set": {"category": str(category)}},
    )
    return result.modified_count


def delete_transactions(df: pd.DataFrame, user_email: str) -> int:
    db = get_db()
    collection = db[_COLLECTION]

    deleted_count = 0
    for _, row in df.iterrows():
        result = collection.delete_one(
            {
                "user_email": user_email,
                "date": str(row["date"]),
                "description": str(row["description"]),
                "amount": float(row["amount"]),
                "bank": str(row["bank"]),
            }
        )
        deleted_count += result.deleted_count

    return deleted_count
