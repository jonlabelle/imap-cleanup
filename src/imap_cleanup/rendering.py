"""Output renderers for account reports."""

from __future__ import annotations

import json
from typing import Any

from imap_cleanup.models import AccountReport, FolderReport, QuotaReport, QuotaResource


def render_table(report: AccountReport) -> str:
    lines: list[str] = []
    if report.quota is not None:
        lines.append(_render_quota(report.quota))
        lines.append("")

    if report.folders:
        lines.extend(_render_folder_table(report.folders))
    else:
        lines.append("No selectable mailboxes found.")

    if report.errors:
        lines.append("")
        lines.append("Errors:")
        for error in report.errors:
            mailbox = error.mailbox or "account"
            lines.append(f"- {mailbox} [{error.stage}]: {error.message}")

    return "\n".join(lines)


def render_json(report: AccountReport) -> str:
    return json.dumps(_account_report_to_dict(report), indent=2, sort_keys=True)


def format_bytes(size_bytes: int) -> str:
    value = float(size_bytes)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"


def _render_folder_table(folders: list[FolderReport]) -> list[str]:
    rows = [
        (
            folder.mailbox,
            f"{folder.messages:,}",
            f"{folder.size_bytes:,}",
            format_bytes(folder.size_bytes),
            folder.method,
        )
        for folder in folders
    ]
    headers = ("Mailbox", "Messages", "Size bytes", "Size", "Method")
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]

    lines = [_format_row(headers, widths)]
    lines.append(_format_row(tuple("-" * width for width in widths), widths))
    lines.extend(_format_row(row, widths) for row in rows)
    return lines


def _format_row(row: tuple[str, ...], widths: list[int]) -> str:
    return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))


def _render_quota(quota: QuotaReport) -> str:
    resources = ", ".join(_render_quota_resource(resource) for resource in quota.resources)
    root = quota.root or '""'
    return f"Quota root {root}: {resources}"


def _render_quota_resource(resource: QuotaResource) -> str:
    if resource.name.upper() == "STORAGE":
        usage = format_bytes(resource.usage * 1024)
        limit = format_bytes(resource.limit * 1024)
        return f"STORAGE {usage} / {limit}"
    return f"{resource.name} {resource.usage:,} / {resource.limit:,} {resource.unit}"


def _account_report_to_dict(report: AccountReport) -> dict[str, Any]:
    return {
        "capabilities": report.capabilities,
        "errors": [
            {
                "mailbox": error.mailbox,
                "stage": error.stage,
                "message": error.message,
            }
            for error in report.errors
        ],
        "folders": [
            {
                "mailbox": folder.mailbox,
                "messages": folder.messages,
                "size_bytes": folder.size_bytes,
                "human_size": format_bytes(folder.size_bytes),
                "method": folder.method,
            }
            for folder in report.folders
        ],
        "quota": _quota_to_dict(report.quota) if report.quota is not None else None,
    }


def _quota_to_dict(quota: QuotaReport) -> dict[str, Any]:
    return {
        "root": quota.root,
        "resources": [
            {
                "name": resource.name,
                "usage": resource.usage,
                "limit": resource.limit,
                "unit": resource.unit,
                "usage_bytes": resource.usage_bytes,
                "limit_bytes": resource.limit_bytes,
            }
            for resource in quota.resources
        ],
    }
