from __future__ import annotations

from imap_cleanup.imap_client import collect_account_report
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
        fetch_response: ImapResponse | None = None,
        quota_response: ImapResponse | None = None,
    ) -> None:
        self.capabilities = capabilities
        self.list_data = list_data or [b'(\\HasNoChildren) "/" "INBOX"']
        self.status_response = status_response or (
            "OK",
            [b'"INBOX" (MESSAGES 2 SIZE 30)'],
        )
        self.select_response = select_response or ("OK", [b"2"])
        self.fetch_response = fetch_response or (
            "OK",
            [
                b"1 (UID 1 RFC822.SIZE 10)",
                b"2 (UID 2 RFC822.SIZE 20)",
            ],
        )
        self.quota_response = quota_response or (
            "OK",
            [b'* QUOTA "" (STORAGE 1 2)'],
        )
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

    def uid(self, command: str, *args: str) -> ImapResponse:
        self.calls.append(("uid", (command, *args)))
        return self.fetch_response

    def getquotaroot(self, mailbox: str) -> ImapResponse:
        self.calls.append(("getquotaroot", (mailbox,)))
        return self.quota_response


def test_collect_report_uses_status_size_when_supported() -> None:
    client = FakeImapConnection(capabilities=b"IMAP4rev1 STATUS=SIZE")

    report = collect_account_report(client)

    assert report.folders[0].mailbox == "INBOX"
    assert report.folders[0].messages == 2
    assert report.folders[0].size_bytes == 30
    assert report.folders[0].method == "status-size"
    assert ("status", ("INBOX", "(MESSAGES SIZE)")) in client.calls
    assert not any(call[0] == "uid" for call in client.calls)


def test_collect_report_falls_back_to_rfc822_size_without_capability() -> None:
    client = FakeImapConnection()

    report = collect_account_report(client)

    assert report.folders[0].method == "rfc822-size"
    assert report.folders[0].size_bytes == 30
    assert not any(call[0] == "status" for call in client.calls)
    assert ("select", ("INBOX", True)) in client.calls
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
    assert ("getquotaroot", ("INBOX",)) in client.calls
