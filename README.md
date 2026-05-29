# imap-cleanup

`imap-cleanup` is a personal IMAP tool for finding the largest folders in a
mailbox account.

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

Optional connection flags:

- `--port`, or `IMAP_CLEANUP_PORT`, defaults to `993`
- `--ssl` / `--no-ssl`, defaults to SSL enabled
- `--format table|json`, defaults to `table`

## What it reports

The `folders` command prints selectable mailboxes with message counts and folder
sizes:

```text
Mailbox  Messages  Size bytes     Size     Method
-------  --------  -------------  -------  -----------
INBOX    12,440    5,153,960,755  4.8 GiB  status-size
Sent     3,102     8,697,308,774  8.1 GiB  rfc822-size
```

When the server advertises `STATUS=SIZE`, the tool asks the server for folder
sizes directly. Otherwise, it opens each folder and sums each message's
`RFC822.SIZE`.

When the server advertises `QUOTA`, the command also tries `GETQUOTAROOT` and
shows quota usage if the server returns it.

Gmail-style labels are reported independently. A single message can appear in
multiple labels, so summed folder totals may exceed account quota usage.

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
