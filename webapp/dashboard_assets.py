"""Dashboard asset versioning.

`index.html` references its scripts and stylesheet with `?v=__V__`; the server replaces the placeholder with a
version derived from the newest file among `index.html` and `app/*`, so any edit busts browser caches without
hand-bumped numbers.
"""

from contextlib import suppress
from pathlib import Path

_PLACEHOLDER = "__V__"


def asset_version(dashboard: Path) -> str:
    """Hex of the newest mtime (ns) among index.html and app/*; empty when the folder is missing."""
    # ponytail: one version for every asset, mtime-based (re-busts all on deploy) — per-file content hashes if the
    # re-download cost or replica disagreement ever matters
    files = [dashboard / "index.html", *(dashboard / "app").glob("*")] if dashboard.is_dir() else []
    mtimes = []
    for f in files:
        with suppress(OSError):  # editor temp files can vanish between glob and stat
            mtimes.append(f.stat().st_mtime_ns)
    return format(max(mtimes), "x") if mtimes else ""


def render_index(dashboard: Path) -> str | None:
    """index.html with every `__V__` replaced by the current asset version; None when there is no index.html."""
    idx = dashboard / "index.html"
    if not idx.is_file():
        return None
    return idx.read_text(encoding="utf-8").replace(_PLACEHOLDER, asset_version(dashboard))
