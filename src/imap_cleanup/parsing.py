"""Parsing helpers for IMAP server responses."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from typing import Any

from imap_cleanup.models import MessageSummary, QuotaReport, QuotaResource

_RawPart = bytes | bytearray | memoryview | str
RawImapData = _RawPart | tuple[_RawPart, _RawPart] | list[Any] | None

_FETCH_SIZE_RE = re.compile(r"\bRFC822\.SIZE\s+(\d+)\b", re.IGNORECASE)
_FETCH_UID_RE = re.compile(r"\bUID\s+(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class MailboxListEntry:
    name: str
    delimiter: str | None
    selectable: bool


def parse_capabilities(data: Iterable[RawImapData]) -> set[str]:
    capabilities: set[str] = set()
    for line in iter_response_text(data):
        for token in line.split():
            capabilities.add(token.upper())
    return capabilities


def parse_list_response(data: Iterable[RawImapData]) -> list[str]:
    return [entry.name for entry in parse_list_entries(data) if entry.selectable]


def parse_list_entries(data: Iterable[RawImapData]) -> list[MailboxListEntry]:
    entries: list[MailboxListEntry] = []
    for line in iter_response_text(data):
        tokens = tokenize_imap(line)
        if len(tokens) < 2:
            continue
        mailbox = tokens[-1]
        if mailbox and mailbox.upper() != "NIL":
            delimiter = tokens[-2]
            entries.append(
                MailboxListEntry(
                    name=mailbox,
                    delimiter=None if delimiter.upper() == "NIL" else delimiter,
                    selectable=not _has_attribute(tokens, "\\NOSELECT"),
                )
            )
    return entries


def parse_status_response(data: Iterable[RawImapData]) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in iter_response_text(data):
        tokens = tokenize_imap(line)
        for index, token in enumerate(tokens[:-1]):
            next_token = tokens[index + 1]
            if next_token.isdigit():
                values[token.upper()] = int(next_token)
    return values


def parse_select_count(data: Iterable[RawImapData]) -> int | None:
    for line in iter_response_text(data):
        tokens = tokenize_imap(line)
        if tokens and tokens[0].isdigit():
            return int(tokens[0])
    return None


def parse_fetch_sizes(data: Iterable[RawImapData]) -> list[int]:
    sizes: list[int] = []
    for line in iter_response_text(data):
        for match in _FETCH_SIZE_RE.finditer(line):
            sizes.append(int(match.group(1)))
    return sizes


def parse_fetch_size_by_uid(data: Iterable[RawImapData]) -> dict[int, int]:
    sizes: dict[int, int] = {}
    for line in iter_response_text(data):
        uid = _FETCH_UID_RE.search(line)
        size = _FETCH_SIZE_RE.search(line)
        if uid is not None and size is not None:
            sizes[int(uid.group(1))] = int(size.group(1))
    return sizes


def parse_fetch_message_summaries(data: Iterable[RawImapData]) -> list[MessageSummary]:
    summaries: list[MessageSummary] = []
    for item in data:
        summary = _parse_fetch_message_summary(item)
        if summary is not None:
            summaries.append(summary)
    return summaries


def parse_uid_search_response(data: Iterable[RawImapData]) -> list[int]:
    uids: list[int] = []
    for line in iter_response_text(data):
        for token in line.split():
            if token.isdigit():
                uids.append(int(token))
    return uids


def parse_quota_response(data: Iterable[RawImapData]) -> QuotaReport | None:
    for line in iter_response_text(data):
        tokens = tokenize_imap(line)
        if "(" not in tokens or ")" not in tokens:
            continue

        open_index = tokens.index("(")
        close_index = len(tokens) - 1 - tokens[::-1].index(")")
        if close_index <= open_index:
            continue

        prefix = [token for token in tokens[:open_index] if token.upper() not in {"*", "QUOTA"}]
        root = prefix[-1] if prefix else ""
        body = tokens[open_index + 1 : close_index]
        resources: list[QuotaResource] = []

        index = 0
        while index + 2 < len(body):
            name = body[index].upper()
            usage = body[index + 1]
            limit = body[index + 2]
            if usage.isdigit() and limit.isdigit():
                resources.append(QuotaResource(name=name, usage=int(usage), limit=int(limit)))
            index += 3

        if resources:
            return QuotaReport(root=root, resources=resources)
    return None


def tokenize_imap(value: str) -> list[str]:
    tokens: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char.isspace():
            index += 1
            continue
        if char in "()":
            tokens.append(char)
            index += 1
            continue
        if char == '"':
            token, index = _read_quoted(value, index + 1)
            tokens.append(token)
            continue

        start = index
        while index < len(value) and not value[index].isspace() and value[index] not in "()":
            index += 1
        tokens.append(value[start:index])
    return tokens


def iter_response_text(data: Iterable[RawImapData]) -> Iterator[str]:
    for item in data:
        if item is None:
            pass
        elif isinstance(item, list):
            yield from iter_response_text(item)
        elif isinstance(item, tuple):
            parts = [_decode_response_part(part) for part in item if part]
            if parts:
                yield " ".join(parts)
        else:
            yield _decode_response_part(item)


def _parse_fetch_message_summary(item: RawImapData) -> MessageSummary | None:
    if item is None or isinstance(item, list):
        return None
    if isinstance(item, tuple):
        metadata = _decode_response_part(item[0])
        headers = _response_part_bytes(item[1])
    else:
        metadata = _decode_response_part(item)
        headers = b""

    uid_match = _FETCH_UID_RE.search(metadata)
    if uid_match is None:
        return None

    size_match = _FETCH_SIZE_RE.search(metadata)
    header_values = _parse_header_values(headers)
    return MessageSummary(
        uid=int(uid_match.group(1)),
        date=header_values["date"],
        from_header=header_values["from"],
        subject=header_values["subject"],
        size_bytes=int(size_match.group(1)) if size_match is not None else 0,
    )


def _parse_header_values(headers: bytes) -> dict[str, str]:
    message = BytesParser(policy=policy.default).parsebytes(headers)
    return {
        "date": _message_header(message, "date"),
        "from": _message_header(message, "from"),
        "subject": _message_header(message, "subject"),
    }


def _message_header(message: object, name: str) -> str:
    value = message.get(name, "")  # type: ignore[attr-defined]
    return str(value) if value is not None else ""


def _read_quoted(value: str, index: int) -> tuple[str, int]:
    chars: list[str] = []
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            chars.append(value[index + 1])
            index += 2
            continue
        if char == '"':
            return "".join(chars), index + 1
        chars.append(char)
        index += 1
    return "".join(chars), index


def _decode_response_part(part: _RawPart) -> str:
    if isinstance(part, (bytes, bytearray, memoryview)):
        return bytes(part).decode("utf-8", errors="replace")
    return part


def _response_part_bytes(part: _RawPart) -> bytes:
    if isinstance(part, (bytes, bytearray, memoryview)):
        return bytes(part)
    return part.encode("utf-8", errors="replace")


def _has_attribute(tokens: list[str], attribute: str) -> bool:
    expected = attribute.upper()
    try:
        start = tokens.index("(")
        end = tokens.index(")")
    except ValueError:
        return False
    return any(token.upper() == expected for token in tokens[start + 1 : end])
