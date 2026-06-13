"""Render fixture-backed README and command documentation examples.

The generated blocks exercise the production CLI renderers without needing a live
IMAP account. The script rewrites marked Markdown regions only when the example
content changes, so running it after Prettier remains idempotent.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from imap_cleanup.models import (
    AccountReport,
    DeletionReport,
    FolderDeletionItem,
    FolderDeletionReport,
    FolderReport,
    MessageSummary,
    QuotaReport,
    QuotaResource,
)
from imap_cleanup.rendering import (
    render_deletion_json,
    render_deletion_table,
    render_folder_deletion_json,
    render_folder_deletion_table,
    render_json,
    render_table,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATHS = (
    Path("README.md"),
    Path("docs/folders.md"),
    Path("docs/delete.md"),
    Path("docs/delete-folder.md"),
)
START_RE = re.compile(r"<!-- doc-example:start ([a-z0-9-]+) -->")
END_RE = re.compile(r"<!-- doc-example:end ([a-z0-9-]+) -->")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify generated examples are current")
    mode.add_argument("--write", action="store_true", help="rewrite generated examples in-place")
    args = parser.parse_args(argv)

    examples = _generated_examples()
    changed: list[tuple[Path, str, str]] = []
    used_examples: set[str] = set()

    for relative_path in DOC_PATHS:
        path = ROOT / relative_path
        original = path.read_text(encoding="utf-8")
        updated, used = _replace_examples(original, examples, path=relative_path)
        used_examples.update(used)
        if updated == original:
            continue
        changed.append((relative_path, original, updated))
        if args.write:
            path.write_text(updated, encoding="utf-8")

    unused_examples = sorted(set(examples) - used_examples)
    if unused_examples:
        names = ", ".join(unused_examples)
        print(f"Unused generated doc example(s): {names}", file=sys.stderr)
        return 1

    if args.check and changed:
        print("Generated doc examples are out of date. Run:", file=sys.stderr)
        print("  uv run python scripts/render_doc_examples.py --write", file=sys.stderr)
        for relative_path, original, updated in changed:
            sys.stderr.write(_unified_diff(relative_path, original, updated))
        return 1

    if args.write:
        if changed:
            paths = ", ".join(str(path) for path, _, _ in changed)
            print(f"Updated generated doc examples in {paths}.")
        else:
            print("Generated doc examples are already current.")
    else:
        print("Generated doc examples are current.")
    return 0


def _replace_examples(
    content: str,
    examples: Mapping[str, str],
    *,
    path: Path,
) -> tuple[str, set[str]]:
    parts: list[str] = []
    used: set[str] = set()
    index = 0

    while True:
        start_match = START_RE.search(content, index)
        if start_match is None:
            parts.append(content[index:])
            break

        key = start_match.group(1)
        if key not in examples:
            raise ValueError(f"{path}: unknown generated example marker {key!r}")

        end_match = END_RE.search(content, start_match.end())
        if end_match is None:
            raise ValueError(f"{path}: generated example {key!r} has no end marker")

        end_key = end_match.group(1)
        if end_key != key:
            raise ValueError(f"{path}: generated example {key!r} closes with {end_key!r}")

        current_region = content[start_match.end() : end_match.start()]
        if _regions_equivalent(current_region, examples[key]):
            parts.append(content[index : end_match.end()])
        else:
            parts.append(content[index : start_match.end()])
            parts.append("\n")
            parts.append(examples[key])
            parts.append("\n")
            parts.append(end_match.group(0))
        used.add(key)
        index = end_match.end()

    return "".join(parts), used


def _regions_equivalent(current_region: str, generated: str) -> bool:
    current = _strip_wrapper_blank_lines(current_region)
    expected = _strip_wrapper_blank_lines(generated)
    if current == expected:
        return True

    current_fence = _parse_fenced_block(current)
    expected_fence = _parse_fenced_block(expected)
    if current_fence is None or expected_fence is None:
        return False

    current_language, current_body = current_fence
    expected_language, expected_body = expected_fence
    if current_language != expected_language:
        return False

    if current_language == "json":
        return _json_equivalent(current_body, expected_body)

    return current_body == expected_body


def _strip_wrapper_blank_lines(value: str) -> str:
    lines = [line.rstrip() for line in value.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _parse_fenced_block(value: str) -> tuple[str, str] | None:
    lines = value.splitlines()
    if len(lines) < 2:
        return None
    opening = lines[0]
    if not opening.startswith("```"):
        return None
    if lines[-1] != "```":
        return None
    return opening.removeprefix("```"), "\n".join(lines[1:-1])


def _json_equivalent(current_body: str, expected_body: str) -> bool:
    try:
        current = json.loads(current_body)
        expected = json.loads(expected_body)
    except json.JSONDecodeError:
        return False
    return bool(_json_sortable(current) == _json_sortable(expected))


def _json_sortable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_sortable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_json_sortable(item) for item in value]
    return value


def _generated_examples() -> dict[str, str]:
    folders_report = _folders_report()
    delete_report = _delete_report()
    delete_json_report = _delete_json_report()
    delete_folder_report = _delete_folder_report()
    delete_folder_json_report = _delete_folder_json_report()

    return {
        "folders-table": _console_example(
            "uv run imap-cleanup folders",
            render_table(folders_report),
        ),
        "folders-json": _fenced("json", render_json(folders_report)),
        "delete-dry-run": _console_example(
            "uv run imap-cleanup delete --mailbox Archive --before 2025-01-01",
            render_deletion_table(delete_report),
        ),
        "delete-json": _fenced("json", render_deletion_json(delete_json_report)),
        "delete-folder-recursive": _console_example(
            'uv run imap-cleanup delete-folder --mailbox "Old Projects" '
            "--recursive --sample-limit 3",
            render_folder_deletion_table(delete_folder_report),
        ),
        "delete-folder-json": _fenced(
            "json",
            render_folder_deletion_json(delete_folder_json_report),
        ),
    }


def _folders_report() -> AccountReport:
    return AccountReport(
        folders=[
            FolderReport("Archive", 1_250, 3 * 1024**3, "status-size"),
            FolderReport("Sent", 420, 750 * 1024**2, "status-size"),
            FolderReport("INBOX", 80, 90 * 1024**2, "status-size"),
        ],
        quota=QuotaReport(
            root="",
            resources=[
                QuotaResource(
                    name="STORAGE",
                    usage=4_823_449,
                    limit=15 * 1024**2,
                )
            ],
        ),
        capabilities=["IMAP4REV1", "QUOTA", "STATUS=SIZE"],
        errors=[],
    )


def _delete_report() -> DeletionReport:
    return DeletionReport(
        mailbox="Archive",
        mode="dry-run",
        search_criteria=["BEFORE", "01-Jan-2025"],
        selected_messages=1_250,
        searched_messages=390,
        matched_messages=390,
        affected_messages=390,
        affected_size_bytes=3_006_477_107,
        marked_deleted_messages=0,
        expunged_messages=0,
        expunge_method="none",
        uid_sample=[12_044, 12_045, 12_046, 12_047, 12_048],
        warnings=[],
        sample_messages=[
            MessageSummary(
                uid=12_044,
                date="Mon, 18 Mar 2024 14:22:10 +0000",
                from_header="Statements <statements@example.com>",
                subject="Quarterly statement",
                size_bytes=9 * 1024**2,
            ),
            MessageSummary(
                uid=12_087,
                date="Thu, 05 Dec 2024 09:08:33 +0000",
                from_header="Receipts <receipts@example.com>",
                subject="Travel receipt",
                size_bytes=7_759_462,
            ),
        ],
    )


def _delete_json_report() -> DeletionReport:
    return DeletionReport(
        mailbox="Archive",
        mode="dry-run",
        search_criteria=["BEFORE", "01-Jan-2025"],
        selected_messages=1_250,
        searched_messages=390,
        matched_messages=390,
        affected_messages=390,
        affected_size_bytes=3_006_477_107,
        marked_deleted_messages=0,
        expunged_messages=0,
        expunge_method="none",
        uid_sample=[12_044, 12_045, 12_046, 12_047, 12_048],
        warnings=[],
    )


def _delete_folder_report() -> FolderDeletionReport:
    return FolderDeletionReport(
        mailbox="Old Projects",
        mode="dry-run",
        messages=340,
        size_bytes=1_677_721_600,
        size_method="status-size",
        deleted=False,
        recursive=True,
        warnings=[
            "Deleting a mailbox removes messages stored in that mailbox.",
            "Recursive delete enabled; child mailboxes are deleted before parents.",
            "Showing first 3 of 340 affected messages.",
        ],
        mailboxes=[
            FolderDeletionItem(
                mailbox="Old Projects",
                messages=120,
                size_bytes=600 * 1024**2,
                size_method="status-size",
                deleted=False,
                sample_messages=[
                    MessageSummary(
                        uid=12_044,
                        date="Mon, 18 Mar 2024 14:22:10 +0000",
                        from_header="Statements <statements@example.com>",
                        subject="Quarterly statement",
                        size_bytes=9 * 1024**2,
                    ),
                    MessageSummary(
                        uid=12_087,
                        date="Thu, 05 Dec 2024 09:08:33 +0000",
                        from_header="Receipts <receipts@example.com>",
                        subject="Travel receipt",
                        size_bytes=7_759_462,
                    ),
                ],
            ),
            FolderDeletionItem(
                mailbox="Old Projects/2022",
                messages=220,
                size_bytes=1_000 * 1024**2,
                size_method="status-size",
                deleted=False,
                sample_messages=[
                    MessageSummary(
                        uid=22_410,
                        date="Tue, 09 Aug 2022 16:45:00 +0000",
                        from_header="Build System <builds@example.com>",
                        subject="Project export archive",
                        size_bytes=13 * 1024**2,
                    )
                ],
            ),
        ],
    )


def _delete_folder_json_report() -> FolderDeletionReport:
    return FolderDeletionReport(
        mailbox="Old Projects",
        mode="dry-run",
        messages=120,
        size_bytes=600 * 1024**2,
        size_method="status-size",
        deleted=False,
        recursive=False,
        warnings=[
            "Deleting a mailbox removes messages stored in that mailbox.",
            "Child mailboxes are not deleted recursively unless --recursive is set.",
        ],
        mailboxes=[
            FolderDeletionItem(
                mailbox="Old Projects",
                messages=120,
                size_bytes=600 * 1024**2,
                size_method="status-size",
                deleted=False,
            )
        ],
    )


def _console_example(command: str, output: str) -> str:
    return _fenced("console", f"$ {command}\n\n{output}")


def _fenced(language: str, body: str) -> str:
    normalized = "\n".join(line.rstrip() for line in body.rstrip().splitlines())
    return f"```{language}\n{normalized}\n```"


def _unified_diff(relative_path: Path, original: str, updated: str) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"{relative_path} (current)",
            tofile=f"{relative_path} (generated)",
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
