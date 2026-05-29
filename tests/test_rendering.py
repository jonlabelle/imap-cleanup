import json

from imap_cleanup.models import AccountReport, FolderReport, QuotaReport, QuotaResource, ReportError
from imap_cleanup.rendering import format_bytes, render_json, render_table


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
