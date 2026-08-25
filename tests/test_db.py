from unittest.mock import MagicMock, patch

import pytest

import webapp.db as db_module


def test_get_db_raises_when_no_url(monkeypatch):
    monkeypatch.delenv("MONGODB_URL", raising=False)
    monkeypatch.setattr(db_module, "_client", None)

    with pytest.raises(ValueError, match="MONGODB_URL"):
        db_module.get_db()


def test_get_db_returns_database(monkeypatch):
    # No importlib.reload here: reloading re-binds MongoClient to the real class behind the patch,
    # creates a real localhost client and leaves it in the singleton for every later test.
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/testdb")
    monkeypatch.setattr(db_module, "_client", None)  # restored after the test
    with patch("webapp.db.MongoClient") as mock_client:
        mock_db = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db

        db = db_module.get_db()

    assert db is mock_db
    mock_client.assert_called_once_with("mongodb://localhost:27017/testdb")
