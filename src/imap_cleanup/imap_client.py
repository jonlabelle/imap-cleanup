"""IMAP account reporting."""

from __future__ import annotations

import imaplib
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Protocol, cast

from imap_cleanup.models import AccountReport, FolderReport, QuotaReport, ReportError
from imap_cleanup.parsing import (
    RawImapData,
    parse_capabilities,
    parse_fetch_sizes,
    parse_list_response,
    parse_quota_response,
    parse_select_count,
    parse_status_response,
)

type ImapResponse = tuple[str, list[RawImapData] | None]


class ImapCleanupError(Exception):
    """Base error for expected IMAP cleanup failures."""


class ImapOperationError(ImapCleanupError):
    """Raised when an IMAP command fails."""


class ImapConnection(Protocol):
    def login(self, user: str, password: str) -> ImapResponse: ...

    def logout(self) -> ImapResponse: ...

    def capability(self) -> ImapResponse: ...

    def list(self) -> ImapResponse: ...

    def status(self, mailbox: str, names: str) -> ImapResponse: ...

    def select(
        self,
        mailbox: str = "INBOX",
        readonly: bool = False,
    ) -> ImapResponse: ...

    def uid(
        self,
        command: str,
        *args: str,
    ) -> ImapResponse: ...

    def getquotaroot(self, mailbox: str) -> ImapResponse: ...


@dataclass(frozen=True)
class ConnectionConfig:
    host: str
    port: int
    username: str
    password: str
    use_ssl: bool = True


def build_account_report(config: ConnectionConfig) -> AccountReport:
    try:
        client = open_connection(config)
    except OSError as exc:
        raise ImapCleanupError(f"failed to connect to {config.host}:{config.port}: {exc}") from exc

    try:
        _call("LOGIN", lambda: client.login(config.username, config.password))
        return collect_account_report(client)
    finally:
        with suppress(Exception):
            client.logout()


def open_connection(config: ConnectionConfig) -> ImapConnection:
    client_class: type[Any] = imaplib.IMAP4_SSL if config.use_ssl else imaplib.IMAP4
    return cast(ImapConnection, client_class(config.host, config.port))


def collect_account_report(client: ImapConnection) -> AccountReport:
    capabilities = _read_capabilities(client)
    mailboxes = _list_mailboxes(client)
    supports_status_size = "STATUS=SIZE" in capabilities

    folders: list[FolderReport] = []
    errors: list[ReportError] = []
    for mailbox in mailboxes:
        try:
            folders.append(_folder_report(client, mailbox, supports_status_size))
        except ImapCleanupError as exc:
            errors.append(ReportError(mailbox=mailbox, stage="folder", message=str(exc)))

    quota = None
    if "QUOTA" in capabilities:
        quota_mailbox = _quota_mailbox(mailboxes)
        try:
            quota = _read_quota(client, quota_mailbox)
        except ImapCleanupError as exc:
            errors.append(ReportError(mailbox=quota_mailbox, stage="quota", message=str(exc)))

    return AccountReport(
        folders=folders,
        quota=quota,
        capabilities=sorted(capabilities),
        errors=errors,
    )


def _read_capabilities(client: ImapConnection) -> set[str]:
    data = _call("CAPABILITY", client.capability)
    return parse_capabilities(data)


def _list_mailboxes(client: ImapConnection) -> list[str]:
    data = _call("LIST", client.list)
    return parse_list_response(data)


def _folder_report(
    client: ImapConnection,
    mailbox: str,
    supports_status_size: bool,
) -> FolderReport:
    if supports_status_size:
        try:
            return _folder_report_with_status_size(client, mailbox)
        except ImapCleanupError:
            pass
    return _folder_report_with_rfc822_size(client, mailbox)


def _folder_report_with_status_size(client: ImapConnection, mailbox: str) -> FolderReport:
    data = _call(
        f'STATUS "{mailbox}"',
        lambda: client.status(mailbox, "(MESSAGES SIZE)"),
    )
    values = parse_status_response(data)
    messages = values.get("MESSAGES")
    size_bytes = values.get("SIZE")
    if messages is None or size_bytes is None:
        raise ImapOperationError(f'STATUS "{mailbox}" did not return MESSAGES and SIZE')
    return FolderReport(
        mailbox=mailbox,
        messages=messages,
        size_bytes=size_bytes,
        method="status-size",
    )


def _folder_report_with_rfc822_size(client: ImapConnection, mailbox: str) -> FolderReport:
    select_data = _call(
        f'EXAMINE "{mailbox}"',
        lambda: client.select(mailbox, readonly=True),
    )
    messages = parse_select_count(select_data)
    if messages is None:
        raise ImapOperationError(f'EXAMINE "{mailbox}" did not return a message count')
    if messages == 0:
        return FolderReport(
            mailbox=mailbox,
            messages=0,
            size_bytes=0,
            method="rfc822-size",
        )

    fetch_data = _call(
        f'UID FETCH "{mailbox}"',
        lambda: client.uid("FETCH", "1:*", "(UID RFC822.SIZE)"),
    )
    sizes = parse_fetch_sizes(fetch_data)
    return FolderReport(
        mailbox=mailbox,
        messages=messages,
        size_bytes=sum(sizes),
        method="rfc822-size",
    )


def _read_quota(client: ImapConnection, mailbox: str) -> QuotaReport | None:
    data = _call(
        f'GETQUOTAROOT "{mailbox}"',
        lambda: client.getquotaroot(mailbox),
    )
    return parse_quota_response(data)


def _quota_mailbox(mailboxes: list[str]) -> str:
    for mailbox in mailboxes:
        if mailbox.upper() == "INBOX":
            return mailbox
    return mailboxes[0] if mailboxes else "INBOX"


def _require_ok(
    response: tuple[str, list[RawImapData] | None],
    operation: str,
) -> list[RawImapData]:
    status, data = response
    if status.upper() != "OK":
        detail = _response_detail(data)
        if detail:
            raise ImapOperationError(f"{operation} failed: {detail}")
        raise ImapOperationError(f"{operation} failed with status {status}")
    return data or []


def _call(operation: str, command: Callable[[], ImapResponse]) -> list[RawImapData]:
    try:
        response = command()
    except (imaplib.IMAP4.error, OSError) as exc:
        raise ImapOperationError(f"{operation} failed: {exc}") from exc
    return _require_ok(response, operation)


def _response_detail(data: list[RawImapData] | None) -> str:
    if not data:
        return ""
    item = data[0]
    if item is None:
        return ""
    if isinstance(item, tuple):
        item = item[0]
    if isinstance(item, bytes):
        return item.decode("utf-8", errors="replace")
    return str(item)
