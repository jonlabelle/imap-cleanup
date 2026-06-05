"""IMAP reporting and cleanup operations."""

from __future__ import annotations

import imaplib
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, replace
from datetime import date
from typing import Any, Protocol, cast

from imap_cleanup.models import (
    AccountReport,
    DeletionMode,
    DeletionReport,
    ExpungeMethod,
    FolderDeletionItem,
    FolderDeletionReport,
    FolderDeletionSizeMethod,
    FolderReport,
    MessageSummary,
    QuotaReport,
    ReportError,
)
from imap_cleanup.parsing import (
    MailboxListEntry,
    RawImapData,
    parse_capabilities,
    parse_fetch_message_summaries,
    parse_fetch_size_by_uid,
    parse_fetch_sizes,
    parse_list_entries,
    parse_list_response,
    parse_quota_response,
    parse_select_count,
    parse_status_response,
    parse_uid_search_response,
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
        *args: str | None,
    ) -> ImapResponse: ...

    def getquotaroot(self, mailbox: str) -> ImapResponse: ...

    def expunge(self) -> ImapResponse: ...

    def delete(self, mailbox: str) -> ImapResponse: ...


@dataclass(frozen=True)
class ConnectionConfig:
    host: str
    port: int
    username: str
    password: str
    use_ssl: bool = True


@dataclass(frozen=True)
class DeletionOptions:
    mailbox: str
    all_messages: bool = False
    before: date | None = None
    since: date | None = None
    larger_than: int | None = None
    smaller_than: int | None = None
    limit: int | None = None
    preview: bool = False
    preview_limit: int = 10
    execute: bool = False
    expunge: bool = False
    allow_folder_expunge: bool = False


@dataclass(frozen=True)
class FolderDeletionOptions:
    mailbox: str
    execute: bool = False
    recursive: bool = False


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


def build_deletion_report(config: ConnectionConfig, options: DeletionOptions) -> DeletionReport:
    try:
        client = open_connection(config)
    except OSError as exc:
        raise ImapCleanupError(f"failed to connect to {config.host}:{config.port}: {exc}") from exc

    try:
        _call("LOGIN", lambda: client.login(config.username, config.password))
        return collect_deletion_report(client, options)
    finally:
        with suppress(Exception):
            client.logout()


def build_folder_deletion_report(
    config: ConnectionConfig,
    options: FolderDeletionOptions,
) -> FolderDeletionReport:
    try:
        client = open_connection(config)
    except OSError as exc:
        raise ImapCleanupError(f"failed to connect to {config.host}:{config.port}: {exc}") from exc

    try:
        _call("LOGIN", lambda: client.login(config.username, config.password))
        return collect_folder_deletion_report(client, options)
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


def collect_deletion_report(client: ImapConnection, options: DeletionOptions) -> DeletionReport:
    capabilities = _read_capabilities(client)
    mailbox_arg = quote_mailbox(options.mailbox)
    mode: DeletionMode = "execute" if options.execute else "dry-run"
    select_operation = "SELECT" if options.execute else "EXAMINE"
    select_data = _call(
        f"{select_operation} {mailbox_arg}",
        lambda: client.select(mailbox_arg, readonly=not options.execute),
    )
    selected_messages = parse_select_count(select_data)
    if selected_messages is None:
        raise ImapOperationError(f"{select_operation} {mailbox_arg} did not return a message count")

    search_criteria = _search_criteria(options)
    search_data = _call(
        f"UID SEARCH {mailbox_arg}",
        lambda: client.uid("SEARCH", None, *search_criteria),
    )
    searched_uids = parse_uid_search_response(search_data)
    sizes = _fetch_uid_sizes(client, searched_uids)
    matched_uids = _filter_uids_by_size(searched_uids, sizes, options)
    affected_uids = matched_uids[: options.limit] if options.limit is not None else matched_uids
    warnings = _deletion_warnings(options, searched_uids, sizes)
    preview_messages: list[MessageSummary] = []
    if options.preview and affected_uids:
        preview_uids = affected_uids[: options.preview_limit]
        preview_messages = _fetch_message_summaries(client, preview_uids, sizes)
        if len(preview_uids) < len(affected_uids):
            warnings.append(
                "Preview limited to first "
                f"{len(preview_uids):,} of {len(affected_uids):,} affected messages."
            )

    marked_deleted_messages = 0
    expunged_messages = 0
    expunge_method: ExpungeMethod = "none"
    if options.execute and affected_uids:
        if options.expunge:
            _validate_expunge_options(capabilities, options)
        _mark_deleted(client, affected_uids)
        marked_deleted_messages = len(affected_uids)
        if options.expunge:
            expunged_messages, expunge_method = _expunge_deleted(
                client,
                affected_uids,
                capabilities,
                options,
                warnings,
            )

    return DeletionReport(
        mailbox=options.mailbox,
        mode=mode,
        search_criteria=search_criteria,
        selected_messages=selected_messages,
        searched_messages=len(searched_uids),
        matched_messages=len(matched_uids),
        affected_messages=len(affected_uids),
        affected_size_bytes=sum(sizes.get(uid, 0) for uid in affected_uids),
        marked_deleted_messages=marked_deleted_messages,
        expunged_messages=expunged_messages,
        expunge_method=expunge_method,
        uid_sample=affected_uids[:10],
        warnings=warnings,
        preview_messages=preview_messages,
    )


def collect_folder_deletion_report(
    client: ImapConnection,
    options: FolderDeletionOptions,
) -> FolderDeletionReport:
    capabilities = _read_capabilities(client)
    mailboxes, warnings = _folder_deletion_mailboxes(client, options)
    supports_status_size = "STATUS=SIZE" in capabilities
    items = [
        _folder_deletion_item(client, mailbox, supports_status_size=supports_status_size)
        for mailbox in mailboxes
    ]
    mode: DeletionMode = "execute" if options.execute else "dry-run"
    warnings = _folder_deletion_warnings(options) + warnings

    if options.execute:
        for mailbox in reversed(mailboxes):
            mailbox_arg = quote_mailbox(mailbox)

            def delete_command(mailbox_arg: str = mailbox_arg) -> ImapResponse:
                return client.delete(mailbox_arg)

            _call(f"DELETE {mailbox_arg}", delete_command)
        items = [replace(item, deleted=True) for item in items]

    messages = sum(item.messages for item in items)
    size_bytes = _folder_deletion_total_size(items)
    deleted = bool(items) and all(item.deleted for item in items)

    return FolderDeletionReport(
        mailbox=options.mailbox,
        mode=mode,
        messages=messages,
        size_bytes=size_bytes,
        size_method="status-size" if size_bytes is not None else "status-messages",
        deleted=deleted,
        warnings=warnings,
        recursive=options.recursive,
        mailboxes=items,
    )


def _read_capabilities(client: ImapConnection) -> set[str]:
    data = _call("CAPABILITY", client.capability)
    return parse_capabilities(data)


def _list_mailboxes(client: ImapConnection) -> list[str]:
    data = _call("LIST", client.list)
    return parse_list_response(data)


def _list_mailbox_entries(client: ImapConnection) -> list[MailboxListEntry]:
    data = _call("LIST", client.list)
    return parse_list_entries(data)


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
    mailbox_arg = quote_mailbox(mailbox)
    data = _call(
        f"STATUS {mailbox_arg}",
        lambda: client.status(mailbox_arg, "(MESSAGES SIZE)"),
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
    mailbox_arg = quote_mailbox(mailbox)
    select_data = _call(
        f"EXAMINE {mailbox_arg}",
        lambda: client.select(mailbox_arg, readonly=True),
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
    mailbox_arg = quote_mailbox(mailbox)
    data = _call(
        f"GETQUOTAROOT {mailbox_arg}",
        lambda: client.getquotaroot(mailbox_arg),
    )
    return parse_quota_response(data)


def _folder_deletion_mailboxes(
    client: ImapConnection,
    options: FolderDeletionOptions,
) -> tuple[list[str], list[str]]:
    if not options.recursive:
        return [options.mailbox], []

    entries = _list_mailbox_entries(client)
    matching_entries = [
        entry for entry in entries if _is_target_or_child_mailbox(entry, options.mailbox)
    ]
    mailboxes = [
        entry.name
        for entry in sorted(matching_entries, key=_mailbox_parent_first_sort_key)
        if entry.selectable
    ]
    if not mailboxes:
        raise ImapOperationError(
            f'LIST did not return selectable mailbox "{options.mailbox}" or descendants'
        )

    warnings: list[str] = []
    target_entry = next(
        (entry for entry in matching_entries if entry.name == options.mailbox),
        None,
    )
    if target_entry is not None and not target_entry.selectable:
        warnings.append(
            f'Target mailbox "{options.mailbox}" is not selectable; '
            "only selectable descendants will be deleted."
        )
    elif target_entry is None and options.mailbox not in mailboxes:
        warnings.append(
            f'Target mailbox "{options.mailbox}" was not listed as selectable; '
            "only selectable descendants will be deleted."
        )
    return mailboxes, warnings


def _is_target_or_child_mailbox(entry: MailboxListEntry, target: str) -> bool:
    if entry.name == target:
        return True
    if entry.delimiter is None:
        return False
    return entry.name.startswith(f"{target}{entry.delimiter}")


def _mailbox_parent_first_sort_key(entry: MailboxListEntry) -> tuple[int, str]:
    delimiter = entry.delimiter or "\0"
    depth = entry.name.count(delimiter) if entry.delimiter is not None else 0
    return depth, entry.name.casefold()


def _folder_deletion_item(
    client: ImapConnection,
    mailbox: str,
    *,
    supports_status_size: bool,
) -> FolderDeletionItem:
    messages, size_bytes, size_method = _folder_deletion_status(
        client,
        mailbox,
        supports_status_size=supports_status_size,
    )
    return FolderDeletionItem(
        mailbox=mailbox,
        messages=messages,
        size_bytes=size_bytes,
        size_method=size_method,
        deleted=False,
    )


def _folder_deletion_total_size(items: list[FolderDeletionItem]) -> int | None:
    if not items or any(item.size_bytes is None for item in items):
        return None
    return sum(item.size_bytes for item in items if item.size_bytes is not None)


def _folder_deletion_warnings(options: FolderDeletionOptions) -> list[str]:
    warnings = ["Deleting a mailbox removes messages stored in that mailbox."]
    if options.recursive:
        warnings.append("Recursive delete enabled; child mailboxes are deleted before parents.")
    else:
        warnings.append("Child mailboxes are not deleted recursively unless --recursive is set.")
    return warnings


def _folder_deletion_status(
    client: ImapConnection,
    mailbox: str,
    *,
    supports_status_size: bool,
) -> tuple[int, int | None, FolderDeletionSizeMethod]:
    if supports_status_size:
        with suppress(ImapCleanupError):
            return _folder_deletion_status_with_size(client, mailbox)
    messages = _folder_deletion_message_count(client, mailbox)
    return messages, None, "status-messages"


def _folder_deletion_status_with_size(
    client: ImapConnection,
    mailbox: str,
) -> tuple[int, int, FolderDeletionSizeMethod]:
    mailbox_arg = quote_mailbox(mailbox)
    data = _call(
        f"STATUS {mailbox_arg}",
        lambda: client.status(mailbox_arg, "(MESSAGES SIZE)"),
    )
    values = parse_status_response(data)
    messages = values.get("MESSAGES")
    size_bytes = values.get("SIZE")
    if messages is None or size_bytes is None:
        raise ImapOperationError(f'STATUS "{mailbox}" did not return MESSAGES and SIZE')
    return messages, size_bytes, "status-size"


def _folder_deletion_message_count(client: ImapConnection, mailbox: str) -> int:
    mailbox_arg = quote_mailbox(mailbox)
    data = _call(
        f"STATUS {mailbox_arg}",
        lambda: client.status(mailbox_arg, "(MESSAGES)"),
    )
    messages = parse_status_response(data).get("MESSAGES")
    if messages is None:
        raise ImapOperationError(f'STATUS "{mailbox}" did not return MESSAGES')
    return messages


def _quota_mailbox(mailboxes: list[str]) -> str:
    for mailbox in mailboxes:
        if mailbox.upper() == "INBOX":
            return mailbox
    return mailboxes[0] if mailboxes else "INBOX"


def quote_mailbox(mailbox: str) -> str:
    escaped = mailbox.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _search_criteria(options: DeletionOptions) -> list[str]:
    criteria: list[str] = []
    if options.since is not None:
        criteria.extend(["SINCE", _format_imap_date(options.since)])
    if options.before is not None:
        criteria.extend(["BEFORE", _format_imap_date(options.before)])
    return criteria or ["ALL"]


def _format_imap_date(value: date) -> str:
    months = (
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    )
    return f"{value.day:02d}-{months[value.month - 1]}-{value.year:04d}"


def _fetch_uid_sizes(client: ImapConnection, uids: list[int]) -> dict[int, int]:
    sizes: dict[int, int] = {}
    for batch in _uid_batches(uids):
        uid_set = _uid_set(batch)

        def fetch_command(uid_set: str = uid_set) -> ImapResponse:
            return client.uid("FETCH", uid_set, "(UID RFC822.SIZE)")

        data = _call(
            "UID FETCH sizes",
            fetch_command,
        )
        sizes.update(parse_fetch_size_by_uid(data))
    return sizes


def _fetch_message_summaries(
    client: ImapConnection,
    uids: list[int],
    sizes: dict[int, int],
) -> list[MessageSummary]:
    summaries_by_uid: dict[int, MessageSummary] = {}
    for batch in _uid_batches(uids):
        uid_set = _uid_set(batch)

        def fetch_command(uid_set: str = uid_set) -> ImapResponse:
            return client.uid(
                "FETCH",
                uid_set,
                "(UID RFC822.SIZE BODY.PEEK[HEADER.FIELDS (DATE FROM SUBJECT)])",
            )

        data = _call(
            "UID FETCH preview",
            fetch_command,
        )
        for summary in parse_fetch_message_summaries(data):
            summaries_by_uid[summary.uid] = _summary_with_size(summary, sizes)

    return [
        summaries_by_uid.get(
            uid,
            MessageSummary(
                uid=uid,
                date="",
                from_header="",
                subject="",
                size_bytes=sizes.get(uid, 0),
            ),
        )
        for uid in uids
    ]


def _summary_with_size(summary: MessageSummary, sizes: dict[int, int]) -> MessageSummary:
    if summary.size_bytes or summary.uid not in sizes:
        return summary
    return replace(summary, size_bytes=sizes[summary.uid])


def _filter_uids_by_size(
    uids: list[int],
    sizes: dict[int, int],
    options: DeletionOptions,
) -> list[int]:
    matched: list[int] = []
    for uid in uids:
        size = sizes.get(uid)
        if options.larger_than is not None and (size is None or size <= options.larger_than):
            continue
        if options.smaller_than is not None and (size is None or size >= options.smaller_than):
            continue
        matched.append(uid)
    return matched


def _deletion_warnings(
    options: DeletionOptions,
    searched_uids: list[int],
    sizes: dict[int, int],
) -> list[str]:
    warnings: list[str] = []
    if options.expunge and not options.execute:
        warnings.append("Dry run only; no messages will be marked deleted or expunged.")
    missing_sizes = len(searched_uids) - len(sizes)
    if missing_sizes > 0:
        warnings.append(f"{missing_sizes:,} searched message(s) did not return RFC822.SIZE.")
    return warnings


def _mark_deleted(client: ImapConnection, uids: list[int]) -> None:
    for batch in _uid_batches(uids):
        uid_set = _uid_set(batch)

        def store_command(uid_set: str = uid_set) -> ImapResponse:
            return client.uid("STORE", uid_set, "+FLAGS.SILENT", r"(\Deleted)")

        _call(
            "UID STORE +FLAGS.SILENT \\Deleted",
            store_command,
        )


def _expunge_deleted(
    client: ImapConnection,
    uids: list[int],
    capabilities: set[str],
    options: DeletionOptions,
    warnings: list[str],
) -> tuple[int, ExpungeMethod]:
    if "UIDPLUS" in capabilities:
        for batch in _uid_batches(uids):
            uid_set = _uid_set(batch)

            def expunge_command(uid_set: str = uid_set) -> ImapResponse:
                return client.uid("EXPUNGE", uid_set)

            _call(
                "UID EXPUNGE",
                expunge_command,
            )
        return len(uids), "uid-expunge"

    _validate_expunge_options(capabilities, options)

    data = _call("EXPUNGE", client.expunge)
    warnings.append(
        "Used folder-wide EXPUNGE; servers without UIDPLUS can permanently remove every "
        "message already marked \\Deleted in the selected mailbox."
    )
    return _count_expunge_responses(data), "folder-expunge"


def _validate_expunge_options(capabilities: set[str], options: DeletionOptions) -> None:
    if "UIDPLUS" not in capabilities and not options.allow_folder_expunge:
        raise ImapOperationError(
            "server does not advertise UIDPLUS; refusing folder-wide EXPUNGE unless "
            "--allow-folder-expunge is set"
        )


def _count_expunge_responses(data: list[RawImapData]) -> int:
    count = 0
    for item in data:
        if item is not None:
            count += 1
    return count


def _uid_batches(uids: list[int], size: int = 500) -> list[list[int]]:
    return [uids[index : index + size] for index in range(0, len(uids), size)]


def _uid_set(uids: list[int]) -> str:
    return ",".join(str(uid) for uid in uids)


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
