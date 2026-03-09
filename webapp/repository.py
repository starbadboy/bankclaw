from datetime import datetime, timezone
import re

import pandas as pd
from pymongo import ASCENDING, UpdateOne

from webapp.db import get_db

_COLLECTION = "transactions"
_CATEGORY_MEMORY_COLLECTION = "category_memory"

_EMPTY_COLUMNS = ["user_email", "date", "description", "amount", "bank", "category", "saved_at"]
_MEMORY_EMPTY_COLUMNS = [
    "user_email",
    "normalized_description",
    "last_raw_description",
    "category",
    "source",
    "updated_at",
]


def normalize_description(description: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]", " ", description.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def save_transactions(df: pd.DataFrame, user_email: str, batch_size: int = 200) -> int:
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
        update_doc = {
            "$set": {
                **filter_doc,
                "category": str(row.get("category", "Other")),
                "saved_at": datetime.now(tz=timezone.utc).isoformat(),
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


def get_transactions_by_date_range(start_date: str, end_date: str, user_email: str) -> pd.DataFrame:
    db = get_db()
    collection = db[_COLLECTION]

    cursor = collection.find(
        {"user_email": user_email, "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0},
        sort=[("date", ASCENDING)],
    )
    records = list(cursor)
    
    if not records:
        return pd.DataFrame(columns=_EMPTY_COLUMNS)

    return pd.DataFrame(records)


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
