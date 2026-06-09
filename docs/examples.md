<p align="center">
  <a href="delete-folder.md">← Delete Folder</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
</p>

---

# Examples

CLI usage examples for common `imap-cleanup` workflows.

The output shown below is representative. Mailbox names, counts, UIDs, sizes, quota data,
and capabilities depend on your IMAP server and account.

- [Connection setup](#connection-setup)
- [Folders](#folders)
- [Delete](#delete)
- [Delete folder](#delete-folder)

## Connection setup

Copy the sample and fill in your account details:

```bash
cp .env.example .env
```

Edit `.env` with your account details. It's loaded automatically. See [Configuration](configuration.md) for environment variables, CLI flags, and precedence rules.

---

## Folders

### List all mailboxes

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

### JSON output

```console
uv run imap-cleanup folders --format json
```

Example JSON output:

```json
{
  "capabilities": ["IMAP4REV1", "QUOTA", "STATUS=SIZE"],
  "errors": [],
  "folders": [
    {
      "human_size": "3.0 GiB",
      "mailbox": "Archive",
      "messages": 1250,
      "method": "status-size",
      "size_bytes": 3221225472
    }
  ],
  "quota": {
    "resources": [
      {
        "limit": 15728640,
        "limit_bytes": 16106127360,
        "name": "STORAGE",
        "unit": "KiB",
        "usage": 4823449,
        "usage_bytes": 4939211776
      }
    ],
    "root": ""
  }
}
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

### Dry run — messages smaller than a size

Messages in Archive smaller than 100 KiB:

```console
uv run imap-cleanup delete --mailbox Archive --smaller-than 100KiB
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
$ uv run imap-cleanup delete --mailbox Archive --before 2025-01-01 --preview

Mailbox              Archive
Mode                 dry-run
Criteria             BEFORE 01-Jan-2025
Messages in mailbox  1,250
Search matches       390
Filter matches       390
Affected messages    390
Affected size        2.8 GiB
Marked deleted       0
Expunged             0
Expunge method       none
UID sample           12044, 12045, 12046, 12047, 12048

Preview:
UID    Date                            From                                 Subject              Size
-----  ------------------------------  -----------------------------------  -------------------  -------
12044  Mon, 18 Mar 2024 14:22:10 +...  Statements <statements@example.com>  Quarterly statement  9.0 MiB
12087  Thu, 05 Dec 2024 09:08:33 +...  Receipts <receipts@example.com>      Travel receipt       7.4 MiB

Pass --execute to mark these messages \Deleted.
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

Example JSON output:

```json
{
  "affected_human_size": "700.0 MiB",
  "affected_messages": 100,
  "affected_size_bytes": 734003200,
  "expunge_method": "none",
  "expunged_messages": 0,
  "mailbox": "Archive",
  "marked_deleted_messages": 0,
  "matched_messages": 390,
  "mode": "dry-run",
  "preview_messages": [],
  "search_criteria": ["BEFORE", "01-Jan-2025"],
  "searched_messages": 390,
  "selected_messages": 1250,
  "uid_sample": [12044, 12045, 12046, 12047, 12048],
  "warnings": []
}
```

---

## Delete Folder

### Dry run

Check the message count before deleting the folder itself:

```console
uv run imap-cleanup delete-folder --mailbox "Old Projects"
```

### Execute

Delete the folder and the messages stored in that folder:

```console
uv run imap-cleanup delete-folder --mailbox "Old Projects" --execute
```

### Recursive dry run

Check the folder and all selectable child folders before deleting anything:

```console
$ uv run imap-cleanup delete-folder --mailbox "Old Projects" --recursive

Mailbox             Old Projects
Mode                dry-run
Recursive           yes
Mailboxes affected  2
Messages affected   340
Total size          1.6 GiB
Deleted mailboxes   no

Mailboxes:
Mailbox            Messages  Size        Method       Deleted
-----------------  --------  ----------  -----------  -------
Old Projects       120       600.0 MiB   status-size  no
Old Projects/2022  220       1000.0 MiB  status-size  no

Pass --execute to delete these mailboxes and all messages they contain.
```

### Recursive execute

Delete child folders first, then the parent folder:

```console
uv run imap-cleanup delete-folder --mailbox "Old Projects" --recursive --execute
```

### JSON output

```console
uv run imap-cleanup delete-folder --mailbox "Old Projects" --format json
```

---

<p align="center">
  <a href="delete-folder.md">← Delete Folder</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
</p>
