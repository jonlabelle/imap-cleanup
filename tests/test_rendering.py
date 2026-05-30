import json

from imap_cleanup.models import (
    AccountReport,
    DeletionReport,
    FolderReport,
    QuotaReport,
    QuotaResource,
    ReportError,
)
from imap_cleanup.rendering import (
    format_bytes,
    render_deletion_json,
    render_deletion_table,
    render_json,
    render_table,
)


def test_format_bytes_uses_binary_units() -> None:
    assert format_bytes(0) == "0 B"
    assert format_bytes(1024) == "1.0 KiB"
    assert format_bytes(5 * 1024 * 1024) == "5.0 MiB"


def test_render_table_includes_quota_folders_and_errors() -> None:
    report = AccountReport(
        folders=[FolderReport("INBOX", 2, 30, "status-size")],
        quota=QuotaReport(root="", resources=[QuotaResource("STORAGE", 1, 2)]),
        capabilities=["QUOTA", "STATUS=SIZE"],
        errors=[ReportError(mailbox="Archive", stage="folder", message="EXAMINE failed")],
    )

    table = render_table(report)

    assert "Quota root" in table
    assert "INBOX" in table
    assert "status-size" in table
    assert "Archive [folder]: EXAMINE failed" in table


def test_render_table_sorts_folders_by_size_and_includes_caveats() -> None:
    report = AccountReport(
        folders=[
            FolderReport("Small", 1, 10, "rfc822-size"),
            FolderReport("Large", 2, 200, "status-size"),
            FolderReport("Medium", 3, 100, "rfc822-size"),
        ],
        quota=None,
        capabilities=[],
        errors=[],
    )

    table = render_table(report)

    assert table.index("Large") < table.index("Medium") < table.index("Small")
    assert "Gmail-style labels are reported as mailboxes" in table
    assert "Messages marked \\Deleted may still count until the mailbox is expunged" in table


def test_render_json_matches_report_schema() -> None:
    report = AccountReport(
        folders=[FolderReport("INBOX", 2, 30, "rfc822-size")],
        quota=None,
        capabilities=["IMAP4REV1"],
        errors=[],
    )

    payload = json.loads(render_json(report))

    assert payload["quota"] is None
    assert payload["capabilities"] == ["IMAP4REV1"]
    assert payload["folders"][0] == {
        "mailbox": "INBOX",
        "messages": 2,
        "size_bytes": 30,
        "human_size": "30 B",
        "method": "rfc822-size",
    }
    assert payload["errors"] == []


def test_render_deletion_table_includes_action_summary() -> None:
    report = DeletionReport(
        mailbox="Archive",
        mode="dry-run",
        search_criteria=["BEFORE", "01-Jan-2026"],
        selected_messages=10,
        searched_messages=4,
        matched_messages=2,
        affected_messages=2,
        affected_size_bytes=2048,
        marked_deleted_messages=0,
        expunged_messages=0,
        expunge_method="none",
        uid_sample=[101, 102],
        warnings=["Dry run only."],
    )

    table = render_deletion_table(report)

    assert "Archive" in table
    assert "2.0 KiB" in table
    assert "Pass --execute" in table
    assert "Dry run only." in table


def test_render_deletion_json_matches_report_schema() -> None:
    report = DeletionReport(
        mailbox="Archive",
        mode="execute",
        search_criteria=["ALL"],
        selected_messages=10,
        searched_messages=4,
        matched_messages=4,
        affected_messages=1,
        affected_size_bytes=30,
        marked_deleted_messages=1,
        expunged_messages=1,
        expunge_method="uid-expunge",
        uid_sample=[101],
        warnings=[],
    )

    payload = json.loads(render_deletion_json(report))

    assert payload["mailbox"] == "Archive"
    assert payload["mode"] == "execute"
    assert payload["affected_human_size"] == "30 B"
    assert payload["expunge_method"] == "uid-expunge"
