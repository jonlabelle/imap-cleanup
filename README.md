# imap-cleanup

[![Version][version-badge]][latest-release]
[![CI][ci-badge]][ci-workflow]

`imap-cleanup` is a personal IMAP CLI for mailbox reporting and cleanup. It can
list folder sizes, show account quota when available, dry-run cleanup searches,
mark matched messages `\Deleted`, and expunge them when requested.

This repository is public so it can be cloned, forked, and run locally. The tool
is not published to PyPI and does not include Python package registry publishing
configuration.

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- An IMAP account. App-specific passwords are recommended when your provider
  supports them.

## Install and run from a clone

```bash
git clone https://github.com/jonlabelle/imap-cleanup.git
cd imap-cleanup
uv sync --dev
uv run imap-cleanup folders \
  --host imap.example.com \
  --username user@example.com \
  --password "$APP_PASSWORD"
```

Credentials can also be supplied through environment variables:

```bash
export IMAP_CLEANUP_HOST=imap.example.com
export IMAP_CLEANUP_USERNAME=user@example.com
export IMAP_CLEANUP_PASSWORD="$APP_PASSWORD"

uv run imap-cleanup folders
```

You can also use a local `.env` file. Start from the sample file and fill in
your account details:

```bash
cp .env.example .env
```

```bash
IMAP_CLEANUP_HOST=imap.example.com
IMAP_CLEANUP_PORT=993
IMAP_CLEANUP_USERNAME=user@example.com
IMAP_CLEANUP_PASSWORD=replace-with-an-app-password
```

The `.env` file is ignored by git. The CLI loads it automatically from the
current project directory before reading `IMAP_CLEANUP_*` values. Existing shell
environment variables are not overwritten, and command-line flags take
precedence over both.

Common flags:

- `--port`, or `IMAP_CLEANUP_PORT`, defaults to `993`
- `--ssl` / `--no-ssl`, defaults to SSL enabled
- `--format table|json`, defaults to `table`

## Delete messages

The `delete` command targets a single mailbox and defaults to a dry run. It
prints how many messages match, their total size, and a sample of affected UIDs
without changing the account:

```bash
uv run imap-cleanup delete \
  --mailbox Archive \
  --before 2025-01-01 \
  --larger-than 25MiB
```

The command requires at least one selector. Selector rules:

- `--before YYYY-MM-DD` and `--since YYYY-MM-DD` use IMAP date search keys and
  can be combined with each other and size filters.
- `--larger-than SIZE` and `--smaller-than SIZE` filter by `RFC822.SIZE`.
- When both date or size bounds are used, the lower bound must be below the
  upper bound.
- Size-only filters search the whole folder first.
- `--all` searches the whole folder first and cannot be combined with date
  selectors.
- `--limit N` caps how many matching messages are affected.

To apply the deletion, pass `--execute`. This marks matching messages with the
IMAP `\Deleted` flag:

```bash
uv run imap-cleanup delete \
  --mailbox Archive \
  --before 2025-01-01 \
  --execute
```

Messages marked `\Deleted` are not always permanently removed until expunged. To
permanently remove the messages in the same run, pass `--execute` and
`--expunge`. When the server supports `UIDPLUS`, the CLI uses UID-scoped expunge
so only the matched UIDs are expunged:

```bash
uv run imap-cleanup delete \
  --mailbox Archive \
  --before 2025-01-01 \
  --execute \
  --expunge
```

If the server does not advertise `UIDPLUS`, the CLI refuses folder-wide expunge
unless `--allow-folder-expunge` is also set. Plain folder expunge can
permanently remove every message already marked `\Deleted` in that selected
folder, including messages not matched by the current run.

## Folder reports

The `folders` command prints selectable mailboxes sorted by largest reported
size first:

```text
Mailbox  Messages  Size bytes     Size     Method
-------  --------  -------------  -------  -----------
Sent     3,102     8,697,308,774  8.1 GiB  rfc822-size
INBOX    12,440    5,153,960,755  4.8 GiB  status-size
```

When the server advertises `STATUS=SIZE`, the tool asks the server for folder
sizes directly. If direct size lookup is unavailable or fails, it opens each
folder and sums each message's `RFC822.SIZE`.

When the server advertises `QUOTA`, the command also tries `GETQUOTAROOT` and
shows quota usage if the server returns it.

Important notes:

- Folder size includes the raw email, including encoded attachments.
- Base64-encoded attachments can count about one third larger than the original
  file.
- The table output always warns that Gmail-style labels can double-count the
  same message across mailboxes.
- The table output always warns that messages marked `\Deleted` may continue to
  count until the mailbox is expunged.
- `STATUS=SIZE` and `QUOTA` are optional IMAP extensions. The CLI falls back to
  `RFC822.SIZE` per message when folder size is not available directly.

## Development

```bash
uv sync --dev
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

### VS Code

This repository includes VS Code tasks and launch configurations for the local
`uv` workflow.

Useful tasks:

- `uv: sync`
- `uv: check all`
- `uv: pytest`
- `uv: build package`
- `imap-cleanup: folders`
- `imap-cleanup: folders json`

Debug launch configurations:

- `imap-cleanup: folders`
- `imap-cleanup: folders json`

[ci-badge]: https://github.com/jonlabelle/imap-cleanup/actions/workflows/ci.yml/badge.svg?branch=main
[ci-workflow]: https://github.com/jonlabelle/imap-cleanup/actions/workflows/ci.yml
[latest-release]: https://github.com/jonlabelle/imap-cleanup/releases/latest
[version-badge]: https://img.shields.io/github/v/release/jonlabelle/imap-cleanup?label=version&sort=semver
