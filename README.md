# IMAP Cleanup CLI

[![Version][version-badge]][latest-release]
[![CI][ci-badge]][ci-workflow]

> `imap-cleanup` is a command-line tool for inspecting and cleaning up IMAP mailboxes. It reports folder sizes and account quotas, and can find and delete messages by date or size.

## Requirements

- Python (see [version](.python-version))
- [uv](https://docs.astral.sh/uv/)
- An IMAP account. App-specific passwords are recommended when your provider supports them.

## Install

Clone the repository and install dependencies:

```bash
git clone https://github.com/jonlabelle/imap-cleanup.git
cd imap-cleanup
uv sync --dev
```

## Quick start

List all mailboxes sorted by size:

```bash
uv run imap-cleanup folders \
  --host imap.example.com \
  --username user@example.com \
  --password "$APP_PASSWORD"
```

> Credentials can also come from environment variables or a `.env` file. See [Configuration](docs/configuration.md) for the full details.

## Commands

- **[`folders`](docs/folders.md)** — List all mailboxes sorted by size, with optional quota usage.
- **[`delete`](docs/delete.md)** — Dry-run or mark messages deleted from a mailbox by date, size, or both.

See [Examples](docs/examples.md) for worked end-to-end usage.

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
- `uv: check all` — Lint, format check, type check, and run tests
- `uv: pytest` — Run tests
- `uv: build package` — Build a wheel distribution in `dist/`
- `imap-cleanup: folders` — Run the `folders` command
- `imap-cleanup: folders json` — Run the `folders` command with JSON output

**Debug launch configurations:**

- `imap-cleanup: folders` — Run the `folders` command
- `imap-cleanup: folders json` — Run the `folders` command with JSON output

</details>

## License

[MIT License](LICENSE).

[ci-badge]: https://github.com/jonlabelle/imap-cleanup/actions/workflows/ci.yml/badge.svg?branch=main
[ci-workflow]: https://github.com/jonlabelle/imap-cleanup/actions/workflows/ci.yml
[latest-release]: https://github.com/jonlabelle/imap-cleanup/releases/latest
[version-badge]: https://img.shields.io/github/v/release/jonlabelle/imap-cleanup?label=version&sort=semver
