import asyncio
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

from webapp.api import health


def test_health_exposes_installed_version_for_deployment_checks():
    with patch("webapp.api.version", return_value="0.10.4"), patch("webapp.api._MONGO", False):
        result = asyncio.run(health())
    assert result == {"status": "ok", "mongo": "disabled", "version": "0.10.4"}


def test_health_still_works_without_installed_package_metadata():
    with patch("webapp.api.version", side_effect=PackageNotFoundError):
        result = asyncio.run(health())
    assert result["status"] == "ok"
    assert result["version"] == "unknown"
