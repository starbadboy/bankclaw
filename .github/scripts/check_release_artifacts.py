"""Verify the committed source package and exported dependencies match the app."""
# ruff: noqa: INP001, T201

import hashlib
import shutil
import subprocess
import tarfile
import tomllib
from email.parser import BytesParser
from pathlib import Path

from packaging.requirements import Requirement


def check_artifacts(root: Path) -> None:
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    archive = root / "dist" / f"statement_sensei-{project['version']}.tar.gz"
    requirements = (root / "requirements.txt").read_text().splitlines()
    expected = f"{archive.relative_to(root)} --hash=sha256:{hashlib.sha256(archive.read_bytes()).hexdigest()}"
    if requirements[0] != expected:
        message = "requirements.txt must pin the current source package and its SHA256"
        raise ValueError(message)

    with tarfile.open(archive) as package:
        files = {member.name.split("/", 1)[1]: member for member in package.getmembers() if member.isfile()}
        metadata = BytesParser().parsebytes(package.extractfile(files["PKG-INFO"]).read())
        if metadata["Version"] != project["version"]:
            message = "Source package version differs from pyproject.toml"
            raise ValueError(message)
        dependencies = {str(Requirement(value)) for value in metadata.get_all("Requires-Dist", [])}
        for dependency in project["dependencies"]:
            if str(Requirement(dependency)) not in dependencies:
                message = f"Source package has a stale dependency: {dependency}"
                raise ValueError(message)
        if any(Path(name).name == ".env" for name in files):
            message = "Source package must not contain .env"
            raise ValueError(message)
        sources = [root / "README.md", *(root / "webapp").rglob("*.py")]
        for source in sources:
            path = source.relative_to(root).as_posix()
            if path not in files or package.extractfile(files[path]).read() != source.read_bytes():
                message = f"Source package has stale or missing source: {path}"
                raise ValueError(message)

    exported = subprocess.check_output(  # noqa: S603 — fixed command, no shell
        [shutil.which("uv") or "uv", "export", "--frozen", "--all-extras", "--no-emit-project"], cwd=root, text=True
    )

    def dependency_lines(lines):
        return [line for line in lines if line.strip() and not line.lstrip().startswith("#")]

    if dependency_lines(requirements[1:]) != dependency_lines(exported.splitlines()):
        message = "requirements.txt dependencies differ from the frozen lockfile export"
        raise ValueError(message)


if __name__ == "__main__":
    check_artifacts(Path(__file__).resolve().parents[2])
    print("Source package, requirements, and lockfile are consistent.")
