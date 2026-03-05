from datetime import datetime, timezone

from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from webapp.db import get_db

_COLLECTION = "users"


def create_user(email: str, password_hash: str) -> bool:
    db = get_db()
    collection = db[_COLLECTION]
    collection.create_index([("email", ASCENDING)], unique=True, background=True)

    existing = collection.find_one({"email": email}, {"_id": 1})
    if existing:
        return False

    try:
        collection.insert_one(
            {
                "email": email,
                "password_hash": password_hash,
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
    except DuplicateKeyError:
        return False
    return True


def authenticate_user(email: str) -> dict | None:
    db = get_db()
    collection = db[_COLLECTION]
    return collection.find_one({"email": email}, {"_id": 0})
