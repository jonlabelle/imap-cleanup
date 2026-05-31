<p align="center">
  <a href="delete.md">← Delete</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="../README.md">Project README →</a>
</p>

---

# Examples

## Connection setup

### Pass credentials as flags

```bash
uv run imap-cleanup folders \
  --host imap.example.com \
  --username user@example.com \
  --password "$APP_PASSWORD"
```

### Pass credentials through the environment

```bash
export IMAP_CLEANUP_HOST=imap.example.com
export IMAP_CLEANUP_USERNAME=user@example.com
export IMAP_CLEANUP_PASSWORD="$APP_PASSWORD"

uv run imap-cleanup folders
```

### Use a .env file

```console
cp .env.example .env
```

Edit `.env` with your account details. It's loaded automatically and shell environment variables always take precedence. See [Configuration](configuration.md) for the full precedence rules.

---

## Folders

### List all mailboxes

```console
uv run imap-cleanup folders
```

### JSON output

```console
uv run imap-cleanup folders --format json
```

---

## Delete

### Dry run — messages before a date

See what would be deleted from Archive before January 1, 2025, without touching anything:

```console
uv run imap-cleanup delete --mailbox Archive --before 2025-01-01
```

### Dry run — messages larger than a size

Messages in Sent larger than 25 MiB:

```console
uv run imap-cleanup delete --mailbox Sent --larger-than 25MiB
```

### Dry run — combining date and size

Messages in Archive older than 2025-01-01 and larger than 10 MiB:

```console
uv run imap-cleanup delete --mailbox Archive --before 2025-01-01 --larger-than 10MiB
```

### Date range

Messages in Archive received between 2020-01-01 and 2023-01-01:

```console
uv run imap-cleanup delete --mailbox Archive --since 2020-01-01 --before 2023-01-01
```

### Preview affected messages

Inspect the actual messages that would be affected before committing. Shows UID, Date, From, Subject, and size for the first 10 matches:

```console
uv run imap-cleanup delete --mailbox Archive --before 2025-01-01 --preview
```

Show more:

```console
uv run imap-cleanup delete --mailbox Archive --before 2025-01-01 --preview --preview-limit 50
```

### Match everything with a size filter

Match all messages in Trash larger than 1 MiB:

```console
uv run imap-cleanup delete --mailbox Trash --all --larger-than 1MiB
```

`--all` cannot be combined with `--before` or `--since`.

### Limit how many messages are affected

Mark at most 100 messages even if more match:

```console
uv run imap-cleanup delete --mailbox Archive --before 2025-01-01 --limit 100
```

### Execute — mark messages deleted

Add `--execute` to actually mark matched messages `\Deleted`:

```console
uv run imap-cleanup delete \
  --mailbox Archive \
  --before 2025-01-01 \
  --execute
```

### Execute and expunge

Mark deleted and permanently remove in the same run. Uses `UID EXPUNGE` if the server supports UIDPLUS:

```console
uv run imap-cleanup delete \
  --mailbox Archive \
  --before 2025-01-01 \
  --execute \
  --expunge
```

### Expunge on a server without UIDPLUS

Pass `--allow-folder-expunge` to permit a folder-wide expunge. This permanently removes **all** messages already marked `\Deleted` in the folder, not just the ones from the current run:

```console
uv run imap-cleanup delete \
  --mailbox Archive \
  --before 2025-01-01 \
  --execute \
  --expunge \
  --allow-folder-expunge
```

### JSON output

```console
uv run imap-cleanup delete --mailbox Archive --before 2025-01-01 --format json
```

---

<p align="center">
  <a href="delete.md">← Delete</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="../README.md">Project README →</a>
</p>
