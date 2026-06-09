"""Shared report models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SizeMethod = Literal["status-size", "rfc822-size"]
DeletionMode = Literal["dry-run", "execute"]
ExpungeMethod = Literal["none", "uid-expunge", "folder-expunge"]
FolderDeletionSizeMethod = Literal["status-size", "rfc822-size", "mixed", "status-messages"]


@dataclass(frozen=True)
class FolderReport:
    mailbox: str
    messages: int
    size_bytes: int
    method: SizeMethod


@dataclass(frozen=True)
class QuotaResource:
    name: str
    usage: int
    limit: int

    @property
    def unit(self) -> str:
        return "KiB" if self.name.upper() == "STORAGE" else "count"

    @property
    def usage_bytes(self) -> int | None:
        if self.name.upper() != "STORAGE":
            return None
        return self.usage * 1024

    @property
    def limit_bytes(self) -> int | None:
        if self.name.upper() != "STORAGE":
            return None
        return self.limit * 1024


@dataclass(frozen=True)
class QuotaReport:
    root: str
    resources: list[QuotaResource]


@dataclass(frozen=True)
class ReportError:
    mailbox: str | None
    stage: str
    message: str


@dataclass(frozen=True)
class AccountReport:
    folders: list[FolderReport]
    quota: QuotaReport | None
    capabilities: list[str]
    errors: list[ReportError]


@dataclass(frozen=True)
class MessageSummary:
    uid: int
    date: str
    from_header: str
    subject: str
    size_bytes: int


@dataclass(frozen=True)
class DeletionReport:
    mailbox: str
    mode: DeletionMode
    search_criteria: list[str]
    selected_messages: int
    searched_messages: int
    matched_messages: int
    affected_messages: int
    affected_size_bytes: int
    marked_deleted_messages: int
    expunged_messages: int
    expunge_method: ExpungeMethod
    uid_sample: list[int]
    warnings: list[str]
    preview_messages: list[MessageSummary] = field(default_factory=list)


@dataclass(frozen=True)
class FolderDeletionItem:
    mailbox: str
    messages: int
    size_bytes: int | None
    size_method: FolderDeletionSizeMethod
    deleted: bool


@dataclass(frozen=True)
class FolderDeletionReport:
    mailbox: str
    mode: DeletionMode
    messages: int
    size_bytes: int | None
    size_method: FolderDeletionSizeMethod
    deleted: bool
    warnings: list[str]
    recursive: bool = False
    mailboxes: list[FolderDeletionItem] = field(default_factory=list)
