"""Parsing helpers for IMAP server responses."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator

from imap_cleanup.models import QuotaReport, QuotaResource

RawImapData = bytes | str | tuple[bytes | str, bytes | str] | None

_FETCH_SIZE_RE = re.compile(r"\bRFC822\.SIZE\s+(\d+)\b", re.IGNORECASE)


def parse_capabilities(data: Iterable[RawImapData]) -> set[str]:
    capabilities: set[str] = set()
    for line in iter_response_text(data):
        for token in line.split():
            capabilities.add(token.upper())
    return capabilities


def parse_list_response(data: Iterable[RawImapData]) -> list[str]:
    mailboxes: list[str] = []
    for line in iter_response_text(data):
        tokens = tokenize_imap(line)
        if not tokens or _has_attribute(tokens, "\\NOSELECT"):
            continue
        mailbox = tokens[-1]
        if mailbox and mailbox.upper() != "NIL":
            mailboxes.append(mailbox)
    return mailboxes


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
            continue
        if isinstance(item, tuple):
            parts = [_decode_response_part(part) for part in item if part]
            if parts:
                yield " ".join(parts)
            continue
        yield _decode_response_part(item)


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


def _decode_response_part(part: bytes | str) -> str:
    if isinstance(part, bytes):
        return part.decode("utf-8", errors="replace")
    return part


def _has_attribute(tokens: list[str], attribute: str) -> bool:
    expected = attribute.upper()
    try:
        start = tokens.index("(")
        end = tokens.index(")")
    except ValueError:
        return False
    return any(token.upper() == expected for token in tokens[start + 1 : end])
