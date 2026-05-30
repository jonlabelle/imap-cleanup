# IMAP Cleanup CLI

[![Version][version-badge]][latest-release]
[![CI][ci-badge]][ci-workflow]

> `imap-cleanup` is a command-line tool for inspecting and cleaning up IMAP mailboxes. It reports folder sizes and account quotas, and can find and delete messages by date or size.

## Requirements

- Python (see [.python-version](.python-version))
- [uv](https://docs.astral.sh/uv/)
- An IMAP account. App-specific passwords are recommended when your provider supports them.

## Install

```bash
git clone https://github.com/jonlabelle/imap-cleanup.git
cd imap-cleanup
uv sync --dev
uv run imap-cleanup folders \
  --host imap.example.com \
  --username user@example.com \
  --password "$APP_PASSWORD"
```

You can also pass credentials through environment variables:

```bash
export IMAP_CLEANUP_HOST=imap.example.com
export IMAP_CLEANUP_USERNAME=user@example.com
export IMAP_CLEANUP_PASSWORD="$APP_PASSWORD"

uv run imap-cleanup folders
```

Or use a local `.env` file. Copy the sample and fill in your account details:

```bash
cp .env.example .env
```

```bash
IMAP_CLEANUP_HOST=imap.example.com
IMAP_CLEANUP_PORT=993
IMAP_CLEANUP_USERNAME=user@example.com
IMAP_CLEANUP_PASSWORD=replace-with-an-app-password
```

The `.env` file is git-ignored and loaded automatically. Shell environment
variables won't be overwritten, and command-line flags always win.

**Common flags:**

- `--port`, or `IMAP_CLEANUP_PORT`, defaults to `993`
- `--ssl` / `--no-ssl`, defaults to SSL enabled
- `--format table|json`, defaults to `table`

## Folders

The `folders` command lists all selectable mailboxes sorted by size:

```text
Mailbox  Messages  Size bytes     Size     Method
-------  --------  -------------  -------  -----------
Sent     3,102     8,697,308,774  8.1 GiB  rfc822-size
INBOX    12,440    5,153,960,755  4.8 GiB  status-size
```

If the server supports `STATUS=SIZE`, folder sizes are queried directly.
Otherwise the CLI opens each folder and sums each message's `RFC822.SIZE`. If
`QUOTA` is available, it also fetches `GETQUOTAROOT` and shows quota usage.

A few things worth knowing:

- Folder size is raw bytes, so base64-encoded attachments count roughly one
  third larger than the original file.
- Gmail-style labels can cause the same message to be counted in multiple
  mailboxes.
- Messages marked `\Deleted` may keep counting toward folder size until the
  mailbox is expunged.

## Delete

The `delete` command targets a single mailbox and is a dry run by default. It
shows how many messages match, their total size, and a sample of affected UIDs
without touching anything:

```bash
uv run imap-cleanup delete \
  --mailbox Archive \
  --before 2025-01-01 \
  --larger-than 25MiB
```

Add `--preview` to see a list of the actual messages that would be affected.
It fetches UID, `Date`, `From`, `Subject`, and `RFC822.SIZE` for the first
matched UIDs using `BODY.PEEK`. Use `--preview-limit` to control how many are
shown (default: 10), and `--format json` for JSON output.

At least one selector is required:

- `--before YYYY-MM-DD` and `--since YYYY-MM-DD` use IMAP date search keys and
  can be combined with each other and size filters.
- `--larger-than SIZE` and `--smaller-than SIZE` filter by `RFC822.SIZE`.
- When both date or both size bounds are provided, the lower bound must be
  below the upper bound.
- `--all` matches everything before applying size filters and can't be combined
  with date selectors.
- `--limit N` caps how many matching messages are affected.

When you're ready to actually delete, pass `--execute`. This marks matching
messages with the IMAP `\Deleted` flag:

```bash
uv run imap-cleanup delete \
  --mailbox Archive \
  --before 2025-01-01 \
  --execute
```

To permanently remove them in the same run, add `--expunge`. If the server
supports `UIDPLUS`, only the matched UIDs are expunged:

```bash
uv run imap-cleanup delete \
  --mailbox Archive \
  --before 2025-01-01 \
  --execute \
  --expunge
```

If `UIDPLUS` isn't available, the CLI won't expunge unless you also pass
`--allow-folder-expunge`. Be careful with that one -- folder-wide expunge
permanently removes every message already marked `\Deleted` in the folder,
not just the ones from the current run.

## Development

Requires [uv](https://docs.astral.sh/uv/). Simply run `uv sync --dev` to install dependencies and get started.

The CLI is built on [imaplib](https://docs.python.org/3/library/imaplib.html) and [argparse](https://docs.python.org/3/library/argparse.html) from the standard library.

<details>
<summary>Commands</summary>

```bash
uv sync --dev                # Install dependencies
uv run ruff check .          # Lint
uv run ruff format --check . # Check formatting
uv run mypy .                # Type check
uv run pytest                # Run tests
```

</details>

<details>
<summary>VS Code</summary>

This repository includes VS Code tasks and launch configurations for the local `uv` workflow.

**Useful tasks:**

- `uv: sync` — Install dependencies
- `uv: check all` — Lint, format check, and type check
- `uv: pytest` — Run tests
- `uv: build package` — Build a wheel distribution in `dist/`
- `imap-cleanup: folders` — Run the `folders` command with interactive prompts for credentials
- `imap-cleanup: folders json` — Run the `folders` command with JSON output and interactive prompts for credentials

**Debug launch configurations:**

- `imap-cleanup: folders` — Run the `folders` command with interactive prompts for credentials
- `imap-cleanup: folders json` — Run the `folders` command with JSON output and interactive prompts for credentials

</details>

## License

[MIT License](LICENSE).

[ci-badge]: https://github.com/jonlabelle/imap-cleanup/actions/workflows/ci.yml/badge.svg?branch=main
[ci-workflow]: https://github.com/jonlabelle/imap-cleanup/actions/workflows/ci.yml
[latest-release]: https://github.com/jonlabelle/imap-cleanup/releases/latest
[version-badge]: https://img.shields.io/github/v/release/jonlabelle/imap-cleanup?label=version&sort=semver
