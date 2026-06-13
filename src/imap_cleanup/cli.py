"""Command-line interface for imap-cleanup."""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Sequence
from datetime import date

from dotenv import find_dotenv, load_dotenv

from imap_cleanup.imap_client import (
    ConnectionConfig,
    DeletionOptions,
    FolderDeletionOptions,
    ImapCleanupError,
    build_account_report,
    build_deletion_report,
    build_folder_deletion_report,
)
from imap_cleanup.rendering import (
    render_deletion_json,
    render_deletion_table,
    render_folder_deletion_json,
    render_folder_deletion_table,
    render_json,
    render_table,
)

_SIZE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*([KMGT]?I?B?|B)?$", re.IGNORECASE)
_SIZE_UNITS = {
    "": 1,
    "B": 1,
    "K": 1024,
    "KB": 1024,
    "KIB": 1024,
    "M": 1024**2,
    "MB": 1024**2,
    "MIB": 1024**2,
    "G": 1024**3,
    "GB": 1024**3,
    "GIB": 1024**3,
    "T": 1024**4,
    "TB": 1024**4,
    "TIB": 1024**4,
}


def main(argv: Sequence[str] | None = None) -> int:
    load_environment()
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


def load_environment() -> None:
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path, override=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="imap-cleanup",
        description="IMAP mailbox reporting and cleanup tools.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    folders = subparsers.add_parser(
        "folders",
        help="Report message counts and storage size for each selectable mailbox.",
    )
    _add_connection_arguments(folders)
    _add_format_argument(folders)
    folders.set_defaults(func=_run_folders)

    delete = subparsers.add_parser(
        "delete",
        help="Dry-run or mark matching messages deleted from one mailbox.",
    )
    _add_connection_arguments(delete)
    _add_format_argument(delete)
    delete.add_argument("--mailbox", required=True, help="Mailbox/folder to clean up.")
    delete.add_argument(
        "--all",
        action="store_true",
        dest="all_messages",
        help="Match all messages before applying local size filters.",
    )
    delete.add_argument(
        "--before",
        type=_date_arg,
        help="Match messages received before this YYYY-MM-DD date.",
    )
    delete.add_argument(
        "--since",
        type=_date_arg,
        help="Match messages received since this YYYY-MM-DD date.",
    )
    delete.add_argument(
        "--larger-than",
        type=_size_arg,
        help="Keep only messages larger than this size, for example 25MiB.",
    )
    delete.add_argument(
        "--smaller-than",
        type=_size_arg,
        help="Keep only messages smaller than this size, for example 100MiB.",
    )
    delete.add_argument(
        "--limit",
        type=_positive_int,
        help="Limit how many matching messages are marked deleted.",
    )
    delete.add_argument(
        "--sample-limit",
        type=_positive_int,
        default=10,
        help="How many message summaries to show in dry-run output. Defaults to 10.",
    )
    delete.add_argument(
        "--execute",
        action="store_true",
        help="Actually mark matching messages \\Deleted. Without this, delete is a dry run.",
    )
    delete.add_argument(
        "--expunge",
        action="store_true",
        help="Permanently remove messages after marking them deleted.",
    )
    delete.add_argument(
        "--allow-folder-expunge",
        action="store_true",
        help="Allow folder-wide EXPUNGE when UID-scoped expunge is unavailable.",
    )
    delete.set_defaults(func=_run_delete)

    delete_folder = subparsers.add_parser(
        "delete-folder",
        aliases=["delete-mailbox"],
        help="Dry-run or delete an entire mailbox/folder and its messages.",
    )
    _add_connection_arguments(delete_folder)
    _add_format_argument(delete_folder)
    delete_folder.add_argument(
        "--mailbox",
        required=True,
        help="Mailbox/folder to delete.",
    )
    delete_folder.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete the mailbox/folder. Without this, delete-folder is a dry run.",
    )
    delete_folder.add_argument(
        "--recursive",
        action="store_true",
        help="Also delete selectable child mailboxes below --mailbox.",
    )
    delete_folder.add_argument(
        "--sample-limit",
        type=_positive_int,
        default=10,
        help="How many message summaries to show in dry-run output. Defaults to 10.",
    )
    delete_folder.set_defaults(func=_run_delete_folder)
    return parser


def _run_folders(args: argparse.Namespace) -> int:
    config = _connection_config_from_args(args)
    if config is None:
        return 2

    try:
        report = build_account_report(config)
    except ImapCleanupError as exc:
        print(f"imap-cleanup: {exc}", file=sys.stderr)
        return 1

    output = render_json(report) if args.format == "json" else render_table(report)
    print(output)
    return 0


def _run_delete(args: argparse.Namespace) -> int:
    config = _connection_config_from_args(args)
    if config is None:
        return 2

    validation_error = _validate_delete_args(args)
    if validation_error is not None:
        print(f"imap-cleanup: {validation_error}", file=sys.stderr)
        return 2

    options = DeletionOptions(
        mailbox=str(args.mailbox),
        all_messages=bool(args.all_messages),
        before=args.before,
        since=args.since,
        larger_than=args.larger_than,
        smaller_than=args.smaller_than,
        limit=args.limit,
        sample_limit=args.sample_limit,
        execute=bool(args.execute),
        expunge=bool(args.expunge),
        allow_folder_expunge=bool(args.allow_folder_expunge),
    )

    try:
        report = build_deletion_report(config, options)
    except ImapCleanupError as exc:
        print(f"imap-cleanup: {exc}", file=sys.stderr)
        return 1

    output = (
        render_deletion_json(report) if args.format == "json" else render_deletion_table(report)
    )
    print(output)
    return 0


def _run_delete_folder(args: argparse.Namespace) -> int:
    config = _connection_config_from_args(args)
    if config is None:
        return 2

    options = FolderDeletionOptions(
        mailbox=str(args.mailbox),
        execute=bool(args.execute),
        recursive=bool(args.recursive),
        sample_limit=args.sample_limit,
    )

    try:
        report = build_folder_deletion_report(config, options)
    except ImapCleanupError as exc:
        print(f"imap-cleanup: {exc}", file=sys.stderr)
        return 1

    output = (
        render_folder_deletion_json(report)
        if args.format == "json"
        else render_folder_deletion_table(report)
    )
    print(output)
    return 0


def _connection_config_from_args(args: argparse.Namespace) -> ConnectionConfig | None:
    missing = _missing_connection_values(args)
    if missing:
        values = ", ".join(missing)
        print(f"imap-cleanup: missing required connection value(s): {values}", file=sys.stderr)
        return None

    return ConnectionConfig(
        host=str(args.host),
        port=int(args.port),
        username=str(args.username),
        password=str(args.password),
        use_ssl=bool(args.ssl),
    )


def _missing_connection_values(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    if not args.host:
        missing.append("host")
    if not args.username:
        missing.append("username")
    if not args.password:
        missing.append("password")
    return missing


def _add_connection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default=os.getenv("IMAP_CLEANUP_HOST"))
    parser.add_argument(
        "--port",
        type=int,
        default=_env_int("IMAP_CLEANUP_PORT", default=993),
    )
    parser.add_argument("--username", default=os.getenv("IMAP_CLEANUP_USERNAME"))
    parser.add_argument("--password", default=os.getenv("IMAP_CLEANUP_PASSWORD"))
    parser.add_argument(
        "--ssl",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use IMAP over TLS. Enabled by default.",
    )


def _add_format_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format. Defaults to table.",
    )


def _validate_delete_args(args: argparse.Namespace) -> str | None:
    has_selector = any(
        (
            args.all_messages,
            args.before is not None,
            args.since is not None,
            args.larger_than is not None,
            args.smaller_than is not None,
        )
    )
    if not has_selector:
        return "delete requires at least one selector: --all, --before, --since, or a size filter"
    if args.all_messages and (args.before is not None or args.since is not None):
        return "--all cannot be combined with --before or --since"
    if args.since is not None and args.before is not None and args.since >= args.before:
        return "--since must be earlier than --before"
    if (
        args.larger_than is not None
        and args.smaller_than is not None
        and args.larger_than >= args.smaller_than
    ):
        return "--larger-than must be smaller than --smaller-than"
    if args.allow_folder_expunge and not args.expunge:
        return "--allow-folder-expunge requires --expunge"
    if args.expunge and not args.execute:
        return "--expunge requires --execute"
    return None


def _date_arg(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from None


def _size_arg(value: str) -> int:
    match = _SIZE_RE.match(value.strip())
    if match is None:
        raise argparse.ArgumentTypeError("expected bytes or a size like 25MiB")
    amount = float(match.group(1))
    unit = (match.group(2) or "").upper()
    multiplier = _SIZE_UNITS.get(unit)
    if multiplier is None:
        raise argparse.ArgumentTypeError("expected B, KiB, MiB, GiB, or TiB")
    return int(amount * multiplier)


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("expected a positive integer") from None
    if parsed <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def _env_int(name: str, *, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise SystemExit(f"imap-cleanup: {name} must be an integer") from None
