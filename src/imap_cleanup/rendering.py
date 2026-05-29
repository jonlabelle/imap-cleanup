"""Output renderers for CLI reports."""

from __future__ import annotations

import json
from typing import Any

from imap_cleanup.models import (
    AccountReport,
    DeletionReport,
    FolderReport,
    QuotaReport,
    QuotaResource,
)


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


def render_deletion_table(report: DeletionReport) -> str:
    rows = [
        ("Mailbox", report.mailbox),
        ("Mode", report.mode),
        ("Criteria", " ".join(report.search_criteria)),
        ("Messages in mailbox", f"{report.selected_messages:,}"),
        ("Search matches", f"{report.searched_messages:,}"),
        ("Filter matches", f"{report.matched_messages:,}"),
        ("Affected messages", f"{report.affected_messages:,}"),
        ("Affected size", format_bytes(report.affected_size_bytes)),
        ("Marked deleted", f"{report.marked_deleted_messages:,}"),
        ("Expunged", f"{report.expunged_messages:,}"),
        ("Expunge method", report.expunge_method),
    ]
    width = max(len(label) for label, _ in rows)
    lines = [f"{label.ljust(width)}  {value}" for label, value in rows]
    if report.uid_sample:
        sample = ", ".join(str(uid) for uid in report.uid_sample)
        lines.append(f"{'UID sample'.ljust(width)}  {sample}")
    if report.warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in report.warnings)
    if report.mode == "dry-run" and report.affected_messages:
        lines.append("")
        lines.append("Pass --execute to mark these messages \\Deleted.")
    return "\n".join(lines)


def render_deletion_json(report: DeletionReport) -> str:
    return json.dumps(_deletion_report_to_dict(report), indent=2, sort_keys=True)


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


def _deletion_report_to_dict(report: DeletionReport) -> dict[str, Any]:
    return {
        "affected_messages": report.affected_messages,
        "affected_size_bytes": report.affected_size_bytes,
        "affected_human_size": format_bytes(report.affected_size_bytes),
        "expunge_method": report.expunge_method,
        "expunged_messages": report.expunged_messages,
        "mailbox": report.mailbox,
        "marked_deleted_messages": report.marked_deleted_messages,
        "matched_messages": report.matched_messages,
        "mode": report.mode,
        "search_criteria": report.search_criteria,
        "searched_messages": report.searched_messages,
        "selected_messages": report.selected_messages,
        "uid_sample": report.uid_sample,
        "warnings": report.warnings,
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
