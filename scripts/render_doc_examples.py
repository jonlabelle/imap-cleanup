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
BINARY_COMMAND_PREFIX = ("imap-cleanup",)
SOURCE_COMMAND_PREFIX = ("uv", "run", "imap-cleanup")


class DocCommand:
    __slots__ = ("args",)

    args: tuple[str, ...]

    def __init__(self, args: tuple[str, ...]) -> None:
        self.args = args


COMMANDS: Mapping[str, DocCommand] = {
    "folders": DocCommand(("folders",)),
    "folders-json": DocCommand(("folders", "--format", "json")),
    "delete-dry-run": DocCommand(("delete", "--mailbox", "Archive", "--before", "2025-01-01")),
    "delete-sample-limit": DocCommand(
        (
            "delete",
            "--mailbox",
            "Archive",
            "--before",
            "2025-01-01",
            "--sample-limit",
            "50",
        )
    ),
    "delete-larger-than": DocCommand(("delete", "--mailbox", "Sent", "--larger-than", "25MiB")),
    "delete-smaller-than": DocCommand(
        ("delete", "--mailbox", "Archive", "--smaller-than", "100KiB")
    ),
    "delete-before-larger": DocCommand(
        (
            "delete",
            "--mailbox",
            "Archive",
            "--before",
            "2025-01-01",
            "--larger-than",
            "10MiB",
        )
    ),
    "delete-date-range": DocCommand(
        (
            "delete",
            "--mailbox",
            "Archive",
            "--since",
            "2020-01-01",
            "--before",
            "2023-01-01",
        )
    ),
    "delete-all-larger": DocCommand(
        ("delete", "--mailbox", "Trash", "--all", "--larger-than", "1MiB")
    ),
    "delete-limit": DocCommand(
        (
            "delete",
            "--mailbox",
            "Archive",
            "--before",
            "2025-01-01",
            "--limit",
            "100",
        )
    ),
    "delete-execute": DocCommand(
        ("delete", "--mailbox", "Archive", "--before", "2025-01-01", "--execute")
    ),
    "delete-expunge": DocCommand(
        (
            "delete",
            "--mailbox",
            "Archive",
            "--before",
            "2025-01-01",
            "--execute",
            "--expunge",
        )
    ),
    "delete-folder-expunge": DocCommand(
        (
            "delete",
            "--mailbox",
            "Archive",
            "--before",
            "2025-01-01",
            "--execute",
            "--expunge",
            "--allow-folder-expunge",
        )
    ),
    "delete-json": DocCommand(
        ("delete", "--mailbox", "Archive", "--before", "2025-01-01", "--format", "json")
    ),
    "delete-uid-dry-run": DocCommand(
        ("delete", "--mailbox", "Archive", "--uid", "12044", "--uid", "12087")
    ),
    "delete-uid-execute": DocCommand(
        (
            "delete",
            "--mailbox",
            "Archive",
            "--uid",
            "12044",
            "--uid",
            "12087",
            "--execute",
        )
    ),
    "delete-uid-expunge": DocCommand(
        (
            "delete",
            "--mailbox",
            "Archive",
            "--uid",
            "12044",
            "--uid",
            "12087",
            "--execute",
            "--expunge",
        )
    ),
    "delete-uid-json": DocCommand(
        (
            "delete",
            "--mailbox",
            "Archive",
            "--uid",
            "12044",
            "--uid",
            "12087",
            "--format",
            "json",
        )
    ),
    "delete-folder": DocCommand(("delete-folder", "--mailbox", "Old Projects")),
    "delete-folder-execute": DocCommand(
        ("delete-folder", "--mailbox", "Old Projects", "--execute")
    ),
    "delete-folder-recursive": DocCommand(
        (
            "delete-folder",
            "--mailbox",
            "Old Projects",
            "--recursive",
            "--sample-limit",
            "3",
        )
    ),
    "delete-folder-recursive-sample": DocCommand(
        (
            "delete-folder",
            "--mailbox",
            "Old Projects",
            "--recursive",
            "--sample-limit",
            "25",
        )
    ),
    "delete-folder-recursive-execute": DocCommand(
        ("delete-folder", "--mailbox", "Old Projects", "--recursive", "--execute")
    ),
    "delete-folder-json": DocCommand(
        ("delete-folder", "--mailbox", "Old Projects", "--format", "json")
    ),
}


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
    delete_uid_report = _delete_uid_report()
    delete_folder_report = _delete_folder_report()
    delete_folder_json_report = _delete_folder_json_report()

    return {
        "folders-command": _command_example(COMMANDS["folders"]),
        "folders-table": _console_example(
            COMMANDS["folders"],
            render_table(folders_report),
        ),
        "folders-json-command": _command_example(COMMANDS["folders-json"]),
        "folders-json": _fenced("json", render_json(folders_report)),
        "delete-sample-limit-command": _command_example(COMMANDS["delete-sample-limit"]),
        "delete-larger-than-command": _command_example(COMMANDS["delete-larger-than"]),
        "delete-smaller-than-command": _command_example(COMMANDS["delete-smaller-than"]),
        "delete-before-larger-command": _command_example(COMMANDS["delete-before-larger"]),
        "delete-date-range-command": _command_example(COMMANDS["delete-date-range"]),
        "delete-all-larger-command": _command_example(COMMANDS["delete-all-larger"]),
        "delete-limit-command": _command_example(COMMANDS["delete-limit"]),
        "delete-execute-command": _command_example(COMMANDS["delete-execute"]),
        "delete-expunge-command": _command_example(COMMANDS["delete-expunge"]),
        "delete-folder-expunge-command": _command_example(COMMANDS["delete-folder-expunge"]),
        "delete-dry-run": _console_example(
            COMMANDS["delete-dry-run"],
            render_deletion_table(delete_report),
        ),
        "delete-json-command": _command_example(COMMANDS["delete-json"]),
        "delete-json": _fenced("json", render_deletion_json(delete_json_report)),
        "delete-uid-execute-command": _command_example(COMMANDS["delete-uid-execute"]),
        "delete-uid-expunge-command": _command_example(COMMANDS["delete-uid-expunge"]),
        "delete-uid-dry-run": _console_example(
            COMMANDS["delete-uid-dry-run"],
            render_deletion_table(delete_uid_report),
        ),
        "delete-uid-json-command": _command_example(COMMANDS["delete-uid-json"]),
        "delete-uid-json": _fenced("json", render_deletion_json(delete_uid_report)),
        "delete-folder-command": _command_example(COMMANDS["delete-folder"]),
        "delete-folder-execute-command": _command_example(COMMANDS["delete-folder-execute"]),
        "delete-folder-recursive": _console_example(
            COMMANDS["delete-folder-recursive"],
            render_folder_deletion_table(delete_folder_report),
        ),
        "delete-folder-recursive-sample-command": _command_example(
            COMMANDS["delete-folder-recursive-sample"]
        ),
        "delete-folder-recursive-execute-command": _command_example(
            COMMANDS["delete-folder-recursive-execute"]
        ),
        "delete-folder-json-command": _command_example(COMMANDS["delete-folder-json"]),
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


def _delete_uid_report() -> DeletionReport:
    return DeletionReport(
        mailbox="Archive",
        mode="dry-run",
        search_criteria=["UID", "12044,12087"],
        selected_messages=1_250,
        searched_messages=2,
        matched_messages=2,
        affected_messages=2,
        affected_size_bytes=17_196_646,
        marked_deleted_messages=0,
        expunged_messages=0,
        expunge_method="none",
        uid_sample=[12_044, 12_087],
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


def _command_example(command: DocCommand) -> str:
    return _fenced("console", _command_lines(command, prompt=False))


def _console_example(command: DocCommand, output: str) -> str:
    return _fenced("console", f"{_command_lines(command, prompt=True)}\n\n# Output\n{output}")


def _command_lines(command: DocCommand, *, prompt: bool) -> str:
    prompt_prefix = "$ " if prompt else ""
    binary = _join_command((*BINARY_COMMAND_PREFIX, *command.args))
    source = _join_command((*SOURCE_COMMAND_PREFIX, *command.args))
    return (
        f"# Installed binary\n{prompt_prefix}{binary}\n\n# Source checkout\n{prompt_prefix}{source}"
    )


def _join_command(parts: Sequence[str]) -> str:
    return " ".join(_quote_command_part(part) for part in parts)


def _quote_command_part(part: str) -> str:
    if part and not any(character.isspace() for character in part):
        return part
    escaped = part.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


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
