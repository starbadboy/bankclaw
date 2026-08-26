"""Dashboard asset versioning: one version derived from the newest file under dashboard/, injected into index.html."""

import os
import time
from pathlib import Path

from webapp.dashboard_assets import asset_version, render_index


def _make_dashboard(root: Path) -> Path:
    app = root / "dashboard" / "app"
    app.mkdir(parents=True)
    (root / "dashboard" / "index.html").write_text('<script src="app/data.js?v=__V__"></script><link href="app/styles.css?v=__V__">')
    (app / "data.js").write_text("// v1")
    return root / "dashboard"


def test_asset_version_changes_when_any_dashboard_file_changes(tmp_path: Path) -> None:
    dashboard = _make_dashboard(tmp_path)
    before = asset_version(dashboard)
    assert before and before == asset_version(dashboard)  # stable while nothing changes
    newer = time.time() + 120
    os.utime(dashboard / "app" / "data.js", (newer, newer))
    assert asset_version(dashboard) != before


def test_asset_version_distinguishes_edits_within_the_same_second(tmp_path: Path) -> None:
    dashboard = _make_dashboard(tmp_path)
    before = asset_version(dashboard)
    st = (dashboard / "app" / "data.js").stat()
    os.utime(dashboard / "app" / "data.js", ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000))  # +5 ms
    assert asset_version(dashboard) != before


def test_render_index_replaces_every_placeholder_with_the_version(tmp_path: Path) -> None:
    dashboard = _make_dashboard(tmp_path)
    html = render_index(dashboard)
    version = asset_version(dashboard)
    assert "__V__" not in html
    assert html.count(f"?v={version}") == 2


def test_render_index_missing_returns_none(tmp_path: Path) -> None:
    assert render_index(tmp_path / "nowhere") is None
