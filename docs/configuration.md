<p align="center">
  <a href="../README.md">← Project README</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="folders.md">Folders →</a>
</p>

---

# Configuration

Every command shares the same connection flags and environment variable support.

## Connection flags

| Flag                 | Description          | Default |
| -------------------- | -------------------- | ------- |
| `--host`             | IMAP server hostname | —       |
| `--port`             | IMAP port            | `993`   |
| `--username`         | Account username     | —       |
| `--password`         | Account password     | —       |
| `--ssl` / `--no-ssl` | Connect over TLS     | enabled |

`--host`, `--username`, and `--password` are required. Everything else has a sensible default.

## Environment variables

You can supply any connection value through the environment instead of flags:

| Variable                | Corresponding flag |
| ----------------------- | ------------------ |
| `IMAP_CLEANUP_HOST`     | `--host`           |
| `IMAP_CLEANUP_PORT`     | `--port`           |
| `IMAP_CLEANUP_USERNAME` | `--username`       |
| `IMAP_CLEANUP_PASSWORD` | `--password`       |

`IMAP_CLEANUP_PORT` must be an integer; the CLI exits immediately with an error if it isn't.

## .env file

Copy the sample and fill in your account details:

```bash
cp .env.example .env
```

```dotenv
IMAP_CLEANUP_HOST=imap.example.com
IMAP_CLEANUP_PORT=993
IMAP_CLEANUP_USERNAME=user@example.com
IMAP_CLEANUP_PASSWORD=replace-with-an-app-password
```

The `.env` file is git-ignored and loaded automatically.

**Precedence (lowest to highest):** `.env` file → shell environment → CLI flags

Shell environment variables are never overwritten by `.env`, and CLI flags always win over both.

## Output format

All commands accept `--format`:

| Value   | Description                           |
| ------- | ------------------------------------- |
| `table` | Human-readable table output (default) |
| `json`  | Machine-readable JSON                 |

## Exit codes

| Code | Meaning                      |
| ---- | ---------------------------- |
| `0`  | Success                      |
| `1`  | IMAP error                   |
| `2`  | Missing or invalid arguments |

---

<p align="center">
  <a href="../README.md">← Project README</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="folders.md">Folders →</a>
</p>
