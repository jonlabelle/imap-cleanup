"""Command-line interface for imap-cleanup."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from dotenv import find_dotenv, load_dotenv

from imap_cleanup.imap_client import ConnectionConfig, ImapCleanupError, build_account_report
from imap_cleanup.rendering import render_json, render_table


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
        description="IMAP mailbox size reports.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    folders = subparsers.add_parser(
        "folders",
        help="Report message counts and storage size for each selectable mailbox.",
    )
    folders.add_argument("--host", default=os.getenv("IMAP_CLEANUP_HOST"))
    folders.add_argument(
        "--port",
        type=int,
        default=_env_int("IMAP_CLEANUP_PORT", default=993),
    )
    folders.add_argument("--username", default=os.getenv("IMAP_CLEANUP_USERNAME"))
    folders.add_argument("--password", default=os.getenv("IMAP_CLEANUP_PASSWORD"))
    folders.add_argument(
        "--ssl",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use IMAP over TLS. Enabled by default.",
    )
    folders.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format. Defaults to table.",
    )
    folders.set_defaults(func=_run_folders)
    return parser


def _run_folders(args: argparse.Namespace) -> int:
    missing = [
        name
        for name, value in (
            ("host", args.host),
            ("username", args.username),
            ("password", args.password),
        )
        if not value
    ]
    if missing:
        values = ", ".join(missing)
        print(f"imap-cleanup: missing required connection value(s): {values}", file=sys.stderr)
        return 2

    config = ConnectionConfig(
        host=str(args.host),
        port=int(args.port),
        username=str(args.username),
        password=str(args.password),
        use_ssl=bool(args.ssl),
    )

    try:
        report = build_account_report(config)
    except ImapCleanupError as exc:
        print(f"imap-cleanup: {exc}", file=sys.stderr)
        return 1

    output = render_json(report) if args.format == "json" else render_table(report)
    print(output)
    return 0


def _env_int(name: str, *, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise SystemExit(f"imap-cleanup: {name} must be an integer") from None
