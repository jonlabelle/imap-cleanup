from __future__ import annotations

from datetime import date

from imap_cleanup.imap_client import (
    DeletionOptions,
    FolderDeletionOptions,
    collect_account_report,
    collect_deletion_report,
    collect_folder_deletion_report,
    quote_mailbox,
)
from imap_cleanup.parsing import RawImapData

ImapResponse = tuple[str, list[RawImapData] | None]


class FakeImapConnection:
    def __init__(
        self,
        *,
        capabilities: bytes = b"IMAP4rev1",
        list_data: list[RawImapData] | None = None,
        status_response: ImapResponse | None = None,
        select_response: ImapResponse | None = None,
        select_responses: dict[str, ImapResponse] | None = None,
        search_response: ImapResponse | None = None,
        search_responses: dict[str, ImapResponse] | None = None,
        fetch_response: ImapResponse | None = None,
        fetch_responses: dict[str, ImapResponse] | None = None,
        preview_fetch_response: ImapResponse | None = None,
        preview_fetch_responses: dict[str, ImapResponse] | None = None,
        store_response: ImapResponse | None = None,
        uid_expunge_response: ImapResponse | None = None,
        quota_response: ImapResponse | None = None,
        expunge_response: ImapResponse | None = None,
        delete_response: ImapResponse | None = None,
    ) -> None:
        self.capabilities = capabilities
        self.list_data = list_data or [b'(\\HasNoChildren) "/" "INBOX"']
        self.status_response = status_response or (
            "OK",
            [b'"INBOX" (MESSAGES 2 SIZE 30)'],
        )
        self.select_response = select_response or ("OK", [b"2"])
        self.select_responses = select_responses or {}
        self.search_response = search_response or ("OK", [b"101 102"])
        self.search_responses = search_responses or {}
        self.fetch_response = fetch_response or (
            "OK",
            [
                b"1 (UID 101 RFC822.SIZE 10)",
                b"2 (UID 102 RFC822.SIZE 20)",
            ],
        )
        self.fetch_responses = fetch_responses or {}
        self.preview_fetch_response = preview_fetch_response or (
            "OK",
            [
                (
                    b"1 (UID 101 RFC822.SIZE 10 BODY[HEADER.FIELDS (DATE FROM SUBJECT)] {95}",
                    b"Date: Wed, 01 Jan 2025 12:00:00 +0000\r\n"
                    b"From: Sender One <one@example.com>\r\n"
                    b"Subject: First\r\n\r\n",
                ),
                b")",
                (
                    b"2 (UID 102 RFC822.SIZE 20 BODY[HEADER.FIELDS (DATE FROM SUBJECT)] {96}",
                    b"Date: Thu, 02 Jan 2025 12:00:00 +0000\r\n"
                    b"From: Sender Two <two@example.com>\r\n"
                    b"Subject: Second\r\n\r\n",
                ),
                b")",
            ],
        )
        self.preview_fetch_responses = preview_fetch_responses or {}
        self.store_response = store_response or ("OK", [])
        self.uid_expunge_response = uid_expunge_response or ("OK", [])
        self.quota_response = quota_response or (
            "OK",
            [b'* QUOTA "" (STORAGE 1 2)'],
        )
        self.expunge_response = expunge_response or ("OK", [b"1", b"2"])
        self.delete_response = delete_response or ("OK", [])
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.selected_mailbox: str | None = None

    def login(self, user: str, password: str) -> ImapResponse:
        self.calls.append(("login", (user, password)))
        return "OK", []

    def logout(self) -> ImapResponse:
        self.calls.append(("logout", ()))
        return "OK", []

    def capability(self) -> ImapResponse:
        self.calls.append(("capability", ()))
        return "OK", [self.capabilities]

    def list(self) -> ImapResponse:
        self.calls.append(("list", ()))
        return "OK", self.list_data

    def status(self, mailbox: str, names: str) -> ImapResponse:
        self.calls.append(("status", (mailbox, names)))
        return self.status_response

    def select(
        self,
        mailbox: str = "INBOX",
        readonly: bool = False,
    ) -> ImapResponse:
        self.calls.append(("select", (mailbox, readonly)))
        self.selected_mailbox = mailbox
        return self.select_responses.get(mailbox, self.select_response)

    def uid(self, command: str, *args: str | None) -> ImapResponse:
        self.calls.append(("uid", (command, *args)))
        if command == "SEARCH":
            return self.search_responses.get(self.selected_mailbox or "", self.search_response)
        if command == "FETCH" and any(isinstance(arg, str) and "BODY.PEEK" in arg for arg in args):
            return self.preview_fetch_responses.get(
                self.selected_mailbox or "",
                self.preview_fetch_response,
            )
        if command == "STORE":
            return self.store_response
        if command == "EXPUNGE":
            return self.uid_expunge_response
        return self.fetch_responses.get(self.selected_mailbox or "", self.fetch_response)

    def getquotaroot(self, mailbox: str) -> ImapResponse:
        self.calls.append(("getquotaroot", (mailbox,)))
        return self.quota_response

    def expunge(self) -> ImapResponse:
        self.calls.append(("expunge", ()))
        return self.expunge_response

    def delete(self, mailbox: str) -> ImapResponse:
        self.calls.append(("delete", (mailbox,)))
        return self.delete_response


def test_collect_report_uses_status_size_when_supported() -> None:
    client = FakeImapConnection(capabilities=b"IMAP4rev1 STATUS=SIZE")

    report = collect_account_report(client)

    assert report.folders[0].mailbox == "INBOX"
    assert report.folders[0].messages == 2
    assert report.folders[0].size_bytes == 30
    assert report.folders[0].method == "status-size"
    assert ("status", ('"INBOX"', "(MESSAGES SIZE)")) in client.calls
    assert not any(call[0] == "uid" for call in client.calls)


def test_collect_report_falls_back_to_rfc822_size_without_capability() -> None:
    client = FakeImapConnection()

    report = collect_account_report(client)

    assert report.folders[0].method == "rfc822-size"
    assert report.folders[0].size_bytes == 30
    assert not any(call[0] == "status" for call in client.calls)
    assert ("select", ('"INBOX"', True)) in client.calls
    assert ("uid", ("FETCH", "1:*", "(UID RFC822.SIZE)")) in client.calls


def test_collect_report_falls_back_when_status_size_fails() -> None:
    client = FakeImapConnection(
        capabilities=b"IMAP4rev1 STATUS=SIZE",
        status_response=("BAD", [b"STATUS=SIZE unsupported here"]),
    )

    report = collect_account_report(client)

    assert report.folders[0].method == "rfc822-size"
    assert report.errors == []


def test_collect_report_does_not_fetch_empty_folders() -> None:
    client = FakeImapConnection(select_response=("OK", [b"0"]))

    report = collect_account_report(client)

    assert report.folders[0].messages == 0
    assert report.folders[0].size_bytes == 0
    assert not any(call[0] == "uid" for call in client.calls)


def test_collect_report_records_per_folder_failure() -> None:
    client = FakeImapConnection(select_response=("NO", [b"permission denied"]))

    report = collect_account_report(client)

    assert report.folders == []
    assert len(report.errors) == 1
    assert report.errors[0].mailbox == "INBOX"
    assert report.errors[0].stage == "folder"
    assert "permission denied" in report.errors[0].message


def test_collect_report_includes_quota_when_supported() -> None:
    client = FakeImapConnection(capabilities=b"IMAP4rev1 QUOTA")

    report = collect_account_report(client)

    assert report.quota is not None
    assert report.quota.resources[0].name == "STORAGE"
    assert ("getquotaroot", ('"INBOX"',)) in client.calls


def test_collect_report_quotes_mailbox_names_with_spaces() -> None:
    client = FakeImapConnection(
        capabilities=b"IMAP4rev1 STATUS=SIZE",
        list_data=[b'(\\HasNoChildren) "/" "[Gmail]/Sent Mail"'],
    )

    report = collect_account_report(client)

    assert report.folders[0].mailbox == "[Gmail]/Sent Mail"
    assert ("status", ('"[Gmail]/Sent Mail"', "(MESSAGES SIZE)")) in client.calls


def test_quote_mailbox_escapes_special_characters() -> None:
    assert quote_mailbox(r'Sent "Archive" \ 2026') == r'"Sent \"Archive\" \\ 2026"'


def test_delete_dry_run_filters_by_size_without_store() -> None:
    client = FakeImapConnection()

    report = collect_deletion_report(
        client,
        DeletionOptions(
            mailbox="INBOX",
            all_messages=True,
            larger_than=10,
        ),
    )

    assert report.mode == "dry-run"
    assert report.search_criteria == ["ALL"]
    assert report.searched_messages == 2
    assert report.matched_messages == 1
    assert report.affected_messages == 1
    assert report.affected_size_bytes == 20
    assert report.uid_sample == [102]
    assert ("select", ('"INBOX"', True)) in client.calls
    assert ("uid", ("SEARCH", None, "ALL")) in client.calls
    assert not any(call == "STORE" for call, _ in client.calls)


def test_delete_dry_run_preview_fetches_capped_message_summaries_without_store() -> None:
    client = FakeImapConnection()

    report = collect_deletion_report(
        client,
        DeletionOptions(
            mailbox="INBOX",
            all_messages=True,
            preview=True,
            preview_limit=1,
        ),
    )

    assert report.mode == "dry-run"
    assert report.affected_messages == 2
    assert len(report.preview_messages) == 1
    assert report.preview_messages[0].uid == 101
    assert report.preview_messages[0].date == "Wed, 01 Jan 2025 12:00:00 +0000"
    assert report.preview_messages[0].from_header == "Sender One <one@example.com>"
    assert report.preview_messages[0].subject == "First"
    assert report.preview_messages[0].size_bytes == 10
    assert "Preview limited to first 1 of 2 affected messages." in report.warnings
    assert (
        "uid",
        (
            "FETCH",
            "101",
            "(UID RFC822.SIZE BODY.PEEK[HEADER.FIELDS (DATE FROM SUBJECT)])",
        ),
    ) in client.calls
    assert not any(call == "STORE" for call, _ in client.calls)


def test_delete_execute_marks_matching_uids_deleted() -> None:
    client = FakeImapConnection()

    report = collect_deletion_report(
        client,
        DeletionOptions(
            mailbox="INBOX",
            all_messages=True,
            limit=1,
            execute=True,
        ),
    )

    assert report.mode == "execute"
    assert report.affected_messages == 1
    assert report.marked_deleted_messages == 1
    assert ("select", ('"INBOX"', False)) in client.calls
    assert ("uid", ("STORE", "101", "+FLAGS.SILENT", r"(\Deleted)")) in client.calls


def test_delete_execute_uses_date_search_criteria() -> None:
    client = FakeImapConnection()

    report = collect_deletion_report(
        client,
        DeletionOptions(
            mailbox="Archive",
            since=date(2025, 1, 1),
            before=date(2026, 1, 1),
        ),
    )

    assert report.search_criteria == ["SINCE", "01-Jan-2025", "BEFORE", "01-Jan-2026"]
    assert (
        "uid",
        ("SEARCH", None, "SINCE", "01-Jan-2025", "BEFORE", "01-Jan-2026"),
    ) in client.calls


def test_delete_execute_expunges_by_uid_when_uidplus_is_supported() -> None:
    client = FakeImapConnection(capabilities=b"IMAP4rev1 UIDPLUS")

    report = collect_deletion_report(
        client,
        DeletionOptions(mailbox="INBOX", all_messages=True, execute=True, expunge=True),
    )

    assert report.expunge_method == "uid-expunge"
    assert report.expunged_messages == 2
    assert ("uid", ("EXPUNGE", "101,102")) in client.calls
    assert not any(call == "expunge" for call, _ in client.calls)


def test_delete_execute_refuses_folder_expunge_without_opt_in() -> None:
    client = FakeImapConnection()

    try:
        collect_deletion_report(
            client,
            DeletionOptions(mailbox="INBOX", all_messages=True, execute=True, expunge=True),
        )
    except Exception as exc:
        assert "--allow-folder-expunge" in str(exc)
    else:
        raise AssertionError("expected unsafe expunge refusal")
    assert not any(call == "STORE" for call, _ in client.calls)


def test_delete_execute_allows_folder_expunge_with_opt_in() -> None:
    client = FakeImapConnection()

    report = collect_deletion_report(
        client,
        DeletionOptions(
            mailbox="INBOX",
            all_messages=True,
            execute=True,
            expunge=True,
            allow_folder_expunge=True,
        ),
    )

    assert report.expunge_method == "folder-expunge"
    assert report.expunged_messages == 2
    assert ("expunge", ()) in client.calls
    assert report.warnings


def test_delete_folder_dry_run_reads_status_without_delete() -> None:
    client = FakeImapConnection(capabilities=b"IMAP4rev1 STATUS=SIZE")

    report = collect_folder_deletion_report(client, FolderDeletionOptions(mailbox="Archive"))

    assert report.mode == "dry-run"
    assert report.mailbox == "Archive"
    assert report.messages == 2
    assert report.size_bytes == 30
    assert report.size_method == "status-size"
    assert report.deleted is False
    assert ("status", ('"Archive"', "(MESSAGES SIZE)")) in client.calls
    assert not any(call == "delete" for call, _ in client.calls)
    assert not any(call == "select" for call, _ in client.calls)


def test_delete_folder_dry_run_falls_back_to_rfc822_size_without_status_size() -> None:
    client = FakeImapConnection(capabilities=b"IMAP4rev1")

    report = collect_folder_deletion_report(client, FolderDeletionOptions(mailbox="Archive"))

    assert report.messages == 2
    assert report.size_bytes == 30
    assert report.size_method == "rfc822-size"
    assert ("select", ('"Archive"', True)) in client.calls
    assert ("uid", ("FETCH", "1:*", "(UID RFC822.SIZE)")) in client.calls
    assert ("status", ('"Archive"', "(MESSAGES)")) not in client.calls


def test_delete_folder_dry_run_falls_back_when_status_size_fails() -> None:
    client = FakeImapConnection(
        capabilities=b"IMAP4rev1 STATUS=SIZE",
        status_response=("BAD", [b"STATUS=SIZE unsupported here"]),
    )

    report = collect_folder_deletion_report(client, FolderDeletionOptions(mailbox="Archive"))

    assert report.messages == 2
    assert report.size_bytes == 30
    assert report.size_method == "rfc822-size"
    assert ("status", ('"Archive"', "(MESSAGES SIZE)")) in client.calls
    assert ("select", ('"Archive"', True)) in client.calls


def test_delete_folder_execute_uses_message_count_when_status_size_is_unavailable() -> None:
    client = FakeImapConnection(
        capabilities=b"IMAP4rev1",
        status_response=("OK", [b'"Archive" (MESSAGES 7)']),
    )

    report = collect_folder_deletion_report(
        client,
        FolderDeletionOptions(mailbox="Archive", execute=True),
    )

    assert report.mode == "execute"
    assert report.messages == 7
    assert report.size_bytes is None
    assert report.size_method == "status-messages"
    assert ("status", ('"Archive"', "(MESSAGES)")) in client.calls
    assert not any(call == "select" for call, _ in client.calls)


def test_delete_folder_execute_deletes_quoted_mailbox() -> None:
    client = FakeImapConnection(capabilities=b"IMAP4rev1 STATUS=SIZE")

    report = collect_folder_deletion_report(
        client,
        FolderDeletionOptions(mailbox="Old Projects", execute=True),
    )

    assert report.mode == "execute"
    assert report.deleted is True
    assert ("delete", ('"Old Projects"',)) in client.calls


def test_delete_folder_recursive_dry_run_reports_selectable_descendants() -> None:
    client = FakeImapConnection(
        capabilities=b"IMAP4rev1 STATUS=SIZE",
        list_data=[
            b'(\\HasChildren) "/" "Archive"',
            b'(\\HasChildren) "/" "Archive/2025"',
            b'(\\HasNoChildren) "/" "Archive/2025/January"',
            b'(\\HasNoChildren) "/" "Archive Later"',
        ],
    )

    report = collect_folder_deletion_report(
        client,
        FolderDeletionOptions(mailbox="Archive", recursive=True),
    )

    assert report.recursive is True
    assert report.mailboxes[0].mailbox == "Archive"
    assert report.mailboxes[1].mailbox == "Archive/2025"
    assert report.mailboxes[2].mailbox == "Archive/2025/January"
    assert len(report.mailboxes) == 3
    assert report.messages == 6
    assert report.size_bytes == 90
    assert report.deleted is False
    assert ("status", ('"Archive Later"', "(MESSAGES SIZE)")) not in client.calls
    assert not any(call == "delete" for call, _ in client.calls)


def test_delete_folder_recursive_dry_run_preview_fetches_capped_messages_without_delete() -> None:
    client = FakeImapConnection(
        capabilities=b"IMAP4rev1 STATUS=SIZE",
        list_data=[
            b'(\\HasChildren) "/" "Archive"',
            b'(\\HasNoChildren) "/" "Archive/2025"',
        ],
        search_responses={
            '"Archive"': ("OK", [b"101 102"]),
            '"Archive/2025"': ("OK", [b"201 202"]),
        },
        preview_fetch_responses={
            '"Archive"': (
                "OK",
                [
                    (
                        b"1 (UID 101 RFC822.SIZE 10 BODY[HEADER.FIELDS (DATE FROM SUBJECT)] {94}",
                        b"Date: Wed, 01 Jan 2025 12:00:00 +0000\r\n"
                        b"From: Sender One <one@example.com>\r\n"
                        b"Subject: First\r\n\r\n",
                    ),
                    b")",
                    (
                        b"2 (UID 102 RFC822.SIZE 20 BODY[HEADER.FIELDS (DATE FROM SUBJECT)] {96}",
                        b"Date: Thu, 02 Jan 2025 12:00:00 +0000\r\n"
                        b"From: Sender Two <two@example.com>\r\n"
                        b"Subject: Second\r\n\r\n",
                    ),
                    b")",
                ],
            ),
            '"Archive/2025"': (
                "OK",
                [
                    (
                        b"1 (UID 201 RFC822.SIZE 30 BODY[HEADER.FIELDS (DATE FROM SUBJECT)] {94}",
                        b"Date: Fri, 03 Jan 2025 12:00:00 +0000\r\n"
                        b"From: Sender Three <three@example.com>\r\n"
                        b"Subject: Third\r\n\r\n",
                    ),
                    b")",
                ],
            ),
        },
    )

    report = collect_folder_deletion_report(
        client,
        FolderDeletionOptions(mailbox="Archive", recursive=True, preview=True, preview_limit=3),
    )

    assert [[message.uid for message in item.preview_messages] for item in report.mailboxes] == [
        [101, 102],
        [201],
    ]
    assert report.mailboxes[0].preview_messages[0].subject == "First"
    assert report.mailboxes[1].preview_messages[0].from_header == (
        "Sender Three <three@example.com>"
    )
    assert "Preview limited to first 3 of 4 affected messages." in report.warnings
    assert (
        "uid",
        (
            "FETCH",
            "101,102",
            "(UID RFC822.SIZE BODY.PEEK[HEADER.FIELDS (DATE FROM SUBJECT)])",
        ),
    ) in client.calls
    assert (
        "uid",
        (
            "FETCH",
            "201",
            "(UID RFC822.SIZE BODY.PEEK[HEADER.FIELDS (DATE FROM SUBJECT)])",
        ),
    ) in client.calls
    assert not any(call == "delete" for call, _ in client.calls)


def test_delete_folder_recursive_dry_run_totals_rfc822_size_fallback() -> None:
    client = FakeImapConnection(
        capabilities=b"IMAP4rev1",
        list_data=[
            b'(\\HasChildren) "/" "Archive"',
            b'(\\HasNoChildren) "/" "Archive/2025"',
        ],
        select_responses={
            '"Archive"': ("OK", [b"1"]),
            '"Archive/2025"': ("OK", [b"2"]),
        },
        fetch_responses={
            '"Archive"': ("OK", [b"1 (UID 101 RFC822.SIZE 10)"]),
            '"Archive/2025"': (
                "OK",
                [
                    b"1 (UID 201 RFC822.SIZE 20)",
                    b"2 (UID 202 RFC822.SIZE 30)",
                ],
            ),
        },
    )

    report = collect_folder_deletion_report(
        client,
        FolderDeletionOptions(mailbox="Archive", recursive=True),
    )

    assert report.messages == 3
    assert report.size_bytes == 60
    assert report.size_method == "rfc822-size"
    assert [item.messages for item in report.mailboxes] == [1, 2]
    assert [item.size_bytes for item in report.mailboxes] == [10, 50]
    assert [item.size_method for item in report.mailboxes] == ["rfc822-size", "rfc822-size"]


def test_delete_folder_recursive_execute_deletes_children_before_parent() -> None:
    client = FakeImapConnection(
        capabilities=b"IMAP4rev1 STATUS=SIZE",
        list_data=[
            b'(\\HasChildren) "/" "Archive"',
            b'(\\HasChildren) "/" "Archive/2025"',
            b'(\\HasNoChildren) "/" "Archive/2025/January"',
        ],
    )

    report = collect_folder_deletion_report(
        client,
        FolderDeletionOptions(mailbox="Archive", execute=True, recursive=True),
    )

    assert report.deleted is True
    assert all(item.deleted for item in report.mailboxes)
    assert [args[0] for call, args in client.calls if call == "delete"] == [
        '"Archive/2025/January"',
        '"Archive/2025"',
        '"Archive"',
    ]


def test_delete_folder_recursive_skips_noselect_parent() -> None:
    client = FakeImapConnection(
        list_data=[
            b'(\\HasChildren \\Noselect) "/" "Archive"',
            b'(\\HasNoChildren) "/" "Archive/2025"',
        ],
        select_responses={'"Archive/2025"': ("OK", [b"7"])},
        fetch_responses={
            '"Archive/2025"': (
                "OK",
                [
                    b"1 (UID 201 RFC822.SIZE 1)",
                    b"2 (UID 202 RFC822.SIZE 2)",
                    b"3 (UID 203 RFC822.SIZE 3)",
                    b"4 (UID 204 RFC822.SIZE 4)",
                    b"5 (UID 205 RFC822.SIZE 5)",
                    b"6 (UID 206 RFC822.SIZE 6)",
                    b"7 (UID 207 RFC822.SIZE 7)",
                ],
            ),
        },
    )

    report = collect_folder_deletion_report(
        client,
        FolderDeletionOptions(mailbox="Archive", recursive=True),
    )

    assert [item.mailbox for item in report.mailboxes] == ["Archive/2025"]
    assert report.messages == 7
    assert report.size_bytes == 28
    assert report.size_method == "rfc822-size"
    assert any("not selectable" in warning for warning in report.warnings)
