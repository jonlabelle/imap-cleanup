"""Shared report models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SizeMethod = Literal["status-size", "rfc822-size"]


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
