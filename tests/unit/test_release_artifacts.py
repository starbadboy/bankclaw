import hashlib
import importlib.util
import io
import tarfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / ".github" / "scripts" / "check_release_artifacts.py"
SPEC = importlib.util.spec_from_file_location("check_release_artifacts", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


@pytest.mark.parametrize("problem", [None, "dependency", "source", "secret", "hash", "export"])
def test_release_artifacts_reject_stale_or_unsafe_packages(tmp_path, monkeypatch, problem):
    (tmp_path / "dist").mkdir()
    (tmp_path / "webapp").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\ndependencies = ["monopoly-core==0.23.1"]\n')
    (tmp_path / "README.md").write_text("Current documentation")
    (tmp_path / "webapp" / "app.py").write_text("CURRENT = True\n")
    files = {
        "PKG-INFO": b"Metadata-Version: 2.1\nVersion: 1.0.0\nRequires-Dist: monopoly-core==0.23.1\n\n",
        "README.md": b"Current documentation",
        "webapp/app.py": b"CURRENT = True\n",
    }
    if problem == "dependency":
        files["PKG-INFO"] = files["PKG-INFO"].replace(b"0.23.1", b"0.19.6")
    if problem == "source":
        files["webapp/app.py"] = b"CURRENT = False\n"
    if problem == "secret":
        files[".env"] = b"SYNTHETIC_KEY=test\n"
    archive = tmp_path / "dist" / "statement_sensei-1.0.0.tar.gz"
    with tarfile.open(archive, "w:gz") as package:
        for name, content in files.items():
            entry = tarfile.TarInfo(f"statement_sensei-1.0.0/{name}")
            entry.size = len(content)
            package.addfile(entry, io.BytesIO(content))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest() if problem != "hash" else "incorrect"
    export = "monopoly-core==0.23.1\n"
    (tmp_path / "requirements.txt").write_text(
        f"dist/{archive.name} --hash=sha256:{digest}\n# Export comments can vary\n{export}"
    )
    monkeypatch.setattr(
        checker.subprocess, "check_output", lambda *args, **kwargs: export if problem != "export" else ""
    )
    if problem:
        with pytest.raises(ValueError):
            checker.check_artifacts(tmp_path)
    else:
        checker.check_artifacts(tmp_path)
