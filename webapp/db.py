import os

from pymongo import MongoClient
from pymongo.database import Database

_client: MongoClient | None = None


def get_db() -> Database:
    url = os.getenv("MONGODB_URL")
    if not url:
        raise ValueError("MONGODB_URL environment variable is not set")

    global _client  # noqa: PLW0603
    if _client is None:
        _client = MongoClient(url)

    db_name = os.getenv("MONGODB_DB_NAME", "bankclaw")
    return _client[db_name]
