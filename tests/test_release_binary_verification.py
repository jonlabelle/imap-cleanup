import hashlib
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from scripts.verify_release_binaries import (
    EXPECTED_BINARY_NAMES,
    VerificationError,
    verify_built_binary,
    verify_release_bundle,
)


def test_verify_built_binary_runs_binary() -> None:
    verify_built_binary(Path(sys.executable), ("--version",))


def test_verify_release_bundle_accepts_expected_binaries_and_checksums(tmp_path: Path) -> None:
    bundle = _write_release_bundle(tmp_path, EXPECTED_BINARY_NAMES)

    verify_release_bundle(bundle, run_current_platform=False)


def test_verify_release_bundle_rejects_missing_binary(tmp_path: Path) -> None:
    bundle = _write_release_bundle(
        tmp_path,
        tuple(name for name in EXPECTED_BINARY_NAMES if name != "imap-cleanup-macos-arm64"),
    )

    with pytest.raises(VerificationError, match="expected exactly one imap-cleanup-macos-arm64"):
        verify_release_bundle(bundle, run_current_platform=False)


def test_verify_release_bundle_rejects_checksum_mismatch(tmp_path: Path) -> None:
    bundle = _write_release_bundle(tmp_path, EXPECTED_BINARY_NAMES)
    binary = next(bundle.rglob("imap-cleanup-linux-x86_64"))
    binary.write_bytes(b"changed after checksum generation")

    with pytest.raises(VerificationError, match="imap-cleanup-linux-x86_64 checksum mismatch"):
        verify_release_bundle(bundle, run_current_platform=False)


def _write_release_bundle(root: Path, names: Sequence[str]) -> Path:
    bundle = root / "release-binaries"
    checksum_lines = []
    for index, name in enumerate(names):
        contents = f"{name}\n".encode("ascii")
        binary = bundle / f"artifact-{index}" / name
        binary.parent.mkdir(parents=True)
        binary.write_bytes(contents)
        checksum_lines.append(f"{hashlib.sha256(contents).hexdigest()}  {name}\n")

    bundle.joinpath("SHA256SUMS.txt").write_text("".join(checksum_lines), encoding="ascii")
    return bundle
