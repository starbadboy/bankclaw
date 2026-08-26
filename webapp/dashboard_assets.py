"""Dashboard asset versioning.

`index.html` references its scripts and stylesheet with `?v=__V__`; the server replaces the placeholder with a
version derived from the newest file under `dashboard/`, so any edit busts browser caches without hand-bumped numbers.
"""

from pathlib import Path

_PLACEHOLDER = "__V__"


def asset_version(dashboard: Path) -> str:
    """Hex of the newest mtime under the dashboard folder (index.html + app/*); empty when the folder is missing."""
    files = [dashboard / "index.html", *(dashboard / "app").glob("*")] if dashboard.is_dir() else []
    mtimes = [int(f.stat().st_mtime) for f in files if f.is_file()]
    return format(max(mtimes), "x") if mtimes else ""


def render_index(dashboard: Path) -> str | None:
    """index.html with every `__V__` replaced by the current asset version; None when there is no index.html."""
    idx = dashboard / "index.html"
    if not idx.is_file():
        return None
    return idx.read_text(encoding="utf-8").replace(_PLACEHOLDER, asset_version(dashboard))
