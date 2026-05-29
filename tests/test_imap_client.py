from __future__ import annotations

from datetime import date

from imap_cleanup.imap_client import (
    DeletionOptions,
    collect_account_report,
    collect_deletion_report,
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
        search_response: ImapResponse | None = None,
        fetch_response: ImapResponse | None = None,
        store_response: ImapResponse | None = None,
        uid_expunge_response: ImapResponse | None = None,
        quota_response: ImapResponse | None = None,
        expunge_response: ImapResponse | None = None,
    ) -> None:
        self.capabilities = capabilities
        self.list_data = list_data or [b'(\\HasNoChildren) "/" "INBOX"']
        self.status_response = status_response or (
            "OK",
            [b'"INBOX" (MESSAGES 2 SIZE 30)'],
        )
        self.select_response = select_response or ("OK", [b"2"])
        self.search_response = search_response or ("OK", [b"101 102"])
        self.fetch_response = fetch_response or (
            "OK",
            [
                b"1 (UID 101 RFC822.SIZE 10)",
                b"2 (UID 102 RFC822.SIZE 20)",
            ],
        )
        self.store_response = store_response or ("OK", [])
        self.uid_expunge_response = uid_expunge_response or ("OK", [])
        self.quota_response = quota_response or (
            "OK",
            [b'* QUOTA "" (STORAGE 1 2)'],
        )
        self.expunge_response = expunge_response or ("OK", [b"1", b"2"])
        self.calls: list[tuple[str, tuple[object, ...]]] = []

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
        return self.select_response

    def uid(self, command: str, *args: str | None) -> ImapResponse:
        self.calls.append(("uid", (command, *args)))
        if command == "SEARCH":
            return self.search_response
        if command == "STORE":
            return self.store_response
        if command == "EXPUNGE":
            return self.uid_expunge_response
        return self.fetch_response

    def getquotaroot(self, mailbox: str) -> ImapResponse:
        self.calls.append(("getquotaroot", (mailbox,)))
        return self.quota_response

    def expunge(self) -> ImapResponse:
        self.calls.append(("expunge", ()))
        return self.expunge_response


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
