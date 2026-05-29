"""Set the project version in release-managed metadata files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_NAME = "imap-cleanup"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: set_project_version.py <version>", file=sys.stderr)
        return 2

    version = args[0].strip()
    if not VERSION_RE.fullmatch(version):
        print(f"invalid semantic version: {version}", file=sys.stderr)
        return 2

    root = Path.cwd()
    update_pyproject(root / "pyproject.toml", version)
    update_uv_lock(root / "uv.lock", version)
    return 0


def update_pyproject(path: Path, version: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    in_project = False
    updated = False

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[project]":
            in_project = True
            continue
        if in_project and stripped.startswith("["):
            break
        if in_project and stripped.startswith("version = "):
            newline = "\n" if line.endswith("\n") else ""
            lines[index] = f'version = "{version}"{newline}'
            updated = True
            break

    if not updated:
        raise SystemExit(f"could not find [project] version in {path}")

    path.write_text("".join(lines), encoding="utf-8")


def update_uv_lock(path: Path, version: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    in_package = False
    saw_project_name = False
    updated = False

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[[package]]":
            in_package = True
            saw_project_name = False
            continue
        if in_package and stripped.startswith("[") and stripped != "[[package]]":
            in_package = False
            saw_project_name = False
            continue
        if in_package and stripped == f'name = "{PROJECT_NAME}"':
            saw_project_name = True
            continue
        if in_package and saw_project_name and stripped.startswith("version = "):
            newline = "\n" if line.endswith("\n") else ""
            lines[index] = f'version = "{version}"{newline}'
            updated = True
            break

    if not updated:
        raise SystemExit(f"could not find {PROJECT_NAME} package version in {path}")

    path.write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
