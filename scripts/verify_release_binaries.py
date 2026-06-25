"""Verify release binary artifacts before publication."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import stat
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

EXPECTED_BINARY_NAMES = (
    "imap-cleanup-linux-x86_64",
    "imap-cleanup-macos-arm64",
    "imap-cleanup-windows-x86_64.exe",
)
CURRENT_PLATFORM_BINARY = {
    "Linux": "imap-cleanup-linux-x86_64",
    "Darwin": "imap-cleanup-macos-arm64",
    "Windows": "imap-cleanup-windows-x86_64.exe",
}
CHECKSUM_FILE_NAME = "SHA256SUMS.txt"


class VerificationError(Exception):
    """Raised when a release artifact check fails."""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    built_binary = subparsers.add_parser(
        "built-binary",
        help="Verify one freshly built binary exists and runs.",
    )
    built_binary.add_argument("path", type=Path)

    release_bundle = subparsers.add_parser(
        "release-bundle",
        help="Verify downloaded release binaries and checksums.",
    )
    release_bundle.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path("release-binaries"),
    )

    args = parser.parse_args(argv)

    try:
        if args.command == "built-binary":
            verify_built_binary(args.path)
        else:
            verify_release_bundle(args.path)
    except VerificationError as exc:
        print(f"release binary verification failed: {exc}", file=sys.stderr)
        return 1

    return 0


def verify_built_binary(path: Path, run_args: Sequence[str] = ("--help",)) -> None:
    resolved_path = path.resolve()
    _verify_regular_file(resolved_path)

    if platform.system() != "Windows" and not os.access(resolved_path, os.X_OK):
        raise VerificationError(f"{resolved_path} is not executable")

    _run_binary(resolved_path, run_args)


def verify_release_bundle(
    root: Path,
    *,
    run_current_platform: bool = True,
) -> None:
    if not root.is_dir():
        raise VerificationError(f"{root} is not a directory")

    binaries = {name: _find_one_file(root, name) for name in EXPECTED_BINARY_NAMES}
    _verify_checksums(root / CHECKSUM_FILE_NAME, binaries)

    if run_current_platform:
        current_binary_name = CURRENT_PLATFORM_BINARY.get(platform.system())
        if current_binary_name is not None:
            current_binary = binaries[current_binary_name]
            _ensure_executable(current_binary)
            _run_binary(current_binary, ("--help",))


def _verify_regular_file(path: Path) -> None:
    if not path.is_file():
        raise VerificationError(f"{path} is missing")
    if path.stat().st_size == 0:
        raise VerificationError(f"{path} is empty")


def _find_one_file(root: Path, name: str) -> Path:
    matches = sorted(path for path in root.rglob(name) if path.is_file())
    if len(matches) != 1:
        match_list = ", ".join(str(path) for path in matches) or "none"
        raise VerificationError(f"expected exactly one {name}, found {len(matches)}: {match_list}")

    path = matches[0]
    _verify_regular_file(path)
    return path


def _verify_checksums(checksum_path: Path, binaries: dict[str, Path]) -> None:
    _verify_regular_file(checksum_path)

    expected_names = set(binaries)
    seen_names: set[str] = set()
    for line_number, line in enumerate(checksum_path.read_text(encoding="ascii").splitlines(), 1):
        if not line:
            continue

        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise VerificationError(f"{checksum_path}:{line_number} is not a valid checksum line")

        expected_digest, name = parts
        has_invalid_digest = len(expected_digest) != 64 or any(
            char not in "0123456789abcdef" for char in expected_digest
        )
        if has_invalid_digest:
            raise VerificationError(f"{checksum_path}:{line_number} has an invalid SHA-256 digest")
        if name not in expected_names:
            raise VerificationError(
                f"{checksum_path}:{line_number} references unexpected file {name}"
            )
        if name in seen_names:
            raise VerificationError(f"{checksum_path}:{line_number} repeats checksum for {name}")

        actual_digest = _sha256(binaries[name])
        if actual_digest != expected_digest:
            raise VerificationError(f"{name} checksum mismatch")

        seen_names.add(name)

    missing_names = sorted(expected_names - seen_names)
    if missing_names:
        raise VerificationError(
            f"{checksum_path} is missing checksums for {', '.join(missing_names)}"
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_executable(path: Path) -> None:
    if platform.system() == "Windows" or os.access(path, os.X_OK):
        return

    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_binary(path: Path, run_args: Sequence[str]) -> None:
    result = subprocess.run(
        [str(path), *run_args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise VerificationError(
            f"{path} {' '.join(run_args)} exited with {result.returncode}: {result.stderr.strip()}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
