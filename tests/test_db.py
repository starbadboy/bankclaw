import importlib
from unittest.mock import MagicMock, patch


def test_get_db_raises_when_no_url(monkeypatch):
    monkeypatch.delenv("MONGODB_URL", raising=False)
    import webapp.db as db_module

    importlib.reload(db_module)
    import pytest

    with pytest.raises(ValueError, match="MONGODB_URL"):
        db_module.get_db()


def test_get_db_returns_database(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/testdb")
    with patch("webapp.db.MongoClient") as mock_client:
        mock_db = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        import webapp.db as db_module

        importlib.reload(db_module)
        db = db_module.get_db()
        assert db is not None
