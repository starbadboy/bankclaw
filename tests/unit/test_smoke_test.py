import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCRIPT = Path(__file__).parents[2] / ".github" / "scripts" / "smoke_test.py"
SPEC = importlib.util.spec_from_file_location("dashboard_smoke", SCRIPT)
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


@pytest.mark.parametrize(
    ("status", "health", "expected", "fails"),
    [
        (200, {"status": "ok", "version": "0.10.4"}, "v0.10.4", False),
        (503, {}, "", True),
        (200, {"status": "error"}, "", True),
        (200, {"status": "ok", "version": "0.10.3"}, "0.10.4", True),
    ],
)
def test_dashboard_check_detects_health_and_version_failures(status, health, expected, fails):
    page = MagicMock()
    page.request.get.return_value.status = status
    page.request.get.return_value.json.return_value = health
    if fails:
        with pytest.raises(ValueError):
            smoke.check_dashboard(page, "https://bankclaw.example/", expected)
        page.goto.assert_not_called()
    else:
        smoke.check_dashboard(page, "https://bankclaw.example/", expected)
        page.goto.assert_called_once()
        page.get_by_placeholder.assert_called_once_with("you@example.com")
