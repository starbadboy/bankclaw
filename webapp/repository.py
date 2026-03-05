from datetime import datetime, timezone

import pandas as pd
from pymongo import ASCENDING

from webapp.db import get_db

_COLLECTION = "transactions"

_EMPTY_COLUMNS = ["date", "description", "amount", "bank", "category", "saved_at"]


def save_transactions(df: pd.DataFrame) -> int:
    db = get_db()
    collection = db[_COLLECTION]

    collection.create_index([("date", ASCENDING)], background=True)

    saved_count = 0
    for _, row in df.iterrows():
        date_str = str(row["date"])
        filter_doc = {
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
        collection.update_one(filter_doc, update_doc, upsert=True)
        saved_count += 1

    return saved_count


def get_transactions_by_date_range(start_date: str, end_date: str) -> pd.DataFrame:
    db = get_db()
    collection = db[_COLLECTION]

    cursor = collection.find(
        {"date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0},
        sort=[("date", ASCENDING)],
    )
    records = list(cursor)
    if not records:
        return pd.DataFrame(columns=_EMPTY_COLUMNS)

    return pd.DataFrame(records)
