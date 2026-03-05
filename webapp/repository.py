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

    # Ensure dates are in YYYY-MM-DD format for string comparison
    # MongoDB string comparison works with ISO format (YYYY-MM-DD)
    query = {"date": {"$gte": start_date, "$lte": end_date}}
    
    # Debug logging
    print(f"[DEBUG] MongoDB Query: {query}")
    print(f"[DEBUG] Searching in collection: {_COLLECTION}")
    
    cursor = collection.find(
        query,
        {"_id": 0},
        sort=[("date", ASCENDING)],
    )
    records = list(cursor)
    
    print(f"[DEBUG] Found {len(records)} records")
    if records:
        print(f"[DEBUG] First date: {records[0].get('date')}, Last date: {records[-1].get('date')}")
        # Show a few sample dates to check format
        sample_dates = [r.get('date') for r in records[:5]]
        print(f"[DEBUG] Sample dates: {sample_dates}")
    
    if not records:
        return pd.DataFrame(columns=_EMPTY_COLUMNS)

    return pd.DataFrame(records)
