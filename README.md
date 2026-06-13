# IMAP Cleanup CLI

[![Version][version-badge]][latest-release]
[![CI][ci-badge]][ci-workflow]

> `imap-cleanup` is a command-line tool for inspecting and cleaning up IMAP mailboxes. It reports folder sizes and account quotas, can find and delete messages by date or size, and can delete whole folders.

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
uv run imap-cleanup folders
```

> Credentials are loaded from a `.env` file or environment variables. See [Configuration](docs/configuration.md) for setup details.

Representative output:

<!-- doc-example:start folders-table -->

```console
$ uv run imap-cleanup folders

Quota root "": STORAGE 4.6 GiB / 15.0 GiB

Mailbox  Messages  Size bytes     Size       Method
-------  --------  -------------  ---------  -----------
Archive  1,250     3,221,225,472  3.0 GiB    status-size
Sent     420       786,432,000    750.0 MiB  status-size
INBOX    80        94,371,840     90.0 MiB   status-size

Caveats:
- Gmail-style labels are reported as mailboxes; one message can appear in multiple
  labels, so summed mailbox sizes can exceed account storage or quota.
- Messages marked \Deleted may still count until the mailbox is expunged; the
  report reflects what the server returns at scan time.
```

<!-- doc-example:end folders-table -->

## Commands

- **[`folders`](docs/folders.md)** — List all mailboxes sorted by size, with optional quota usage.
- **[`delete`](docs/delete.md)** — Dry-run or mark messages deleted from a mailbox by date, size, or both.
- **[`delete-folder`](docs/delete-folder.md)** — Dry-run or delete an entire mailbox/folder, optionally including child folders.

Each command page includes an Examples section with worked usage.

## Development

Requires [uv](https://docs.astral.sh/uv/). Simply run `uv sync --dev` to install dependencies and get started.

The CLI is built on [imaplib](https://docs.python.org/3/library/imaplib.html) and [argparse](https://docs.python.org/3/library/argparse.html) from the standard library.

README and command examples are generated from fixtures through the production renderers. Refresh them with `uv run python scripts/render_doc_examples.py --write`; `uv run pytest` verifies they are current.

<details>
<summary>Commands</summary>

```bash
uv sync --dev                # Install dependencies
uv build                     # Build wheel distribution in dist/
uv run ruff check .          # Lint
uv run ruff format --check . # Check formatting
uv run ruff format .         # Format code
uv run mypy .                # Type check
uv run pytest                # Run tests

# Refresh generated docs examples
uv run python scripts/render_doc_examples.py --write
```

</details>

<details>
<summary>VS Code</summary>

This repository includes VS Code tasks and launch configurations for the local `uv` workflow.

**Useful tasks:**

- `uv: sync` — Install dependencies
- `uv: check all` — Lint, format check, type check, and run tests
- `uv: pytest` — Run tests
- `uv: ruff format` — Format code with Ruff
- `uv: build package` — Build wheel distribution in `dist/`
- `imap-cleanup: folders` — Run the `folders` command
- `imap-cleanup: folders json` — Run the `folders` command with JSON output
- `imap-cleanup: delete dry run` — Dry run on `Archive` messages before `2025-01-01`
- `imap-cleanup: delete dry run json` — Same dry run with JSON output
- `imap-cleanup: delete folder dry run` — Check the `Old Projects` folder before deletion
- `imap-cleanup: delete folder dry run json` — Check the same folder with JSON output
- `imap-cleanup: delete folder recursive dry run` — Check `Old Projects` and child folders before deletion
- `imap-cleanup: delete folder recursive dry run json` — Check the same folder tree with JSON output

**Debug launch configurations:**

- `imap-cleanup: folders` — Run the `folders` command
- `imap-cleanup: folders json` — Run the `folders` command with JSON output
- `imap-cleanup: delete dry run` — Dry run on `Archive` messages before `2025-01-01`
- `imap-cleanup: delete dry run json` — Same dry run with JSON output
- `imap-cleanup: delete folder dry run` — Check the `Old Projects` folder before deletion
- `imap-cleanup: delete folder dry run json` — Check the same folder with JSON output
- `imap-cleanup: delete folder recursive dry run` — Check `Old Projects` and child folders before deletion
- `imap-cleanup: delete folder recursive dry run json` — Check the same folder tree with JSON output

The delete and delete-folder entries are dry-run configurations and do not pass `--execute`.

</details>

## License

[MIT License](LICENSE).

[ci-badge]: https://github.com/jonlabelle/imap-cleanup/actions/workflows/ci.yml/badge.svg?branch=main
[ci-workflow]: https://github.com/jonlabelle/imap-cleanup/actions/workflows/ci.yml
[latest-release]: https://github.com/jonlabelle/imap-cleanup/releases/latest
[version-badge]: https://img.shields.io/github/v/release/jonlabelle/imap-cleanup?label=version&sort=semver
