from datetime import datetime, timezone

import pandas as pd
from pymongo import ASCENDING, UpdateOne

from webapp.db import get_db

_COLLECTION = "transactions"

_EMPTY_COLUMNS = ["user_email", "date", "description", "amount", "bank", "category", "saved_at"]


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
