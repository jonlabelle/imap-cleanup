<p align="center">
  <a href="folders.md">← Folders</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="delete-folder.md">Delete Folder →</a>
</p>

---

# Delete

The `delete` command targets messages in a single mailbox while keeping the mailbox/folder itself. By default it's always a dry run — nothing is modified until you pass `--execute`.

> [!Note]
> Use [`delete-folder`](delete-folder.md) when you want to remove the mailbox/folder itself and the messages it contains.

## Lifecycle

```plaintext
dry run  →  execute  →  expunge
```

1. Run without `--execute` to see which messages match, how much space they use, and a sample of the affected messages.
2. Add `--execute` to mark matching messages `\Deleted`.
3. Add `--expunge` (with `--execute`) to permanently remove them in the same run.

## Selectors

At least one selector is required. They control which messages are matched:

| Flag                  | Description                                                         |
| --------------------- | ------------------------------------------------------------------- |
| `--before YYYY-MM-DD` | Messages received before this date (IMAP `BEFORE` key)              |
| `--since YYYY-MM-DD`  | Messages received on or after this date (IMAP `SINCE` key)          |
| `--larger-than SIZE`  | Only messages larger than SIZE (applied locally after IMAP search)  |
| `--smaller-than SIZE` | Only messages smaller than SIZE (applied locally after IMAP search) |
| `--all`               | Match all messages before applying size filters                     |
| `--uid UID`           | Target one or more specific messages by UID (repeatable)            |

**Rules:**

- `--all` is mutually exclusive with `--before` and `--since`.
- When both `--since` and `--before` are given, `--since` must be the earlier date.
- When both `--larger-than` and `--smaller-than` are given, `--larger-than` must be the smaller value.
- `--larger-than` and `--smaller-than` can be freely combined with date selectors.
- `--uid` is mutually exclusive with `--all`, `--before`, `--since`, `--larger-than`, and `--smaller-than`.

## Size units

`--larger-than` and `--smaller-than` accept bytes or any of these units (case-insensitive, decimals accepted):

`B`, `K` / `KB` / `KiB`, `M` / `MB` / `MiB`, `G` / `GB` / `GiB`, `T` / `TB` / `TiB`

Examples: `500B`, `25MiB`, `1.5GiB`, `500MB`

## All flags

| Flag                     | Default | Description                                                                           |
| ------------------------ | ------- | ------------------------------------------------------------------------------------- |
| `--mailbox`              | —       | Mailbox to operate on. Required.                                                      |
| `--before`               | —       | Match messages before this date.                                                      |
| `--since`                | —       | Match messages on or after this date.                                                 |
| `--larger-than`          | —       | Filter by minimum message size.                                                       |
| `--smaller-than`         | —       | Filter by maximum message size.                                                       |
| `--all`                  | —       | Match every message (before size filters).                                            |
| `--uid UID`              | —       | Target specific messages by UID. Repeatable. Mutually exclusive with other selectors. |
| `--limit N`              | —       | Cap how many matched messages are affected.                                           |
| `--sample-limit N`       | `10`    | How many message summaries to show in dry-run output.                                 |
| `--execute`              | off     | Mark matched messages `\Deleted`. Without this, always a dry run.                     |
| `--expunge`              | off     | Permanently remove messages after marking deleted. Requires `--execute`.              |
| `--allow-folder-expunge` | off     | Permit folder-wide EXPUNGE when the server lacks UIDPLUS. Requires `--expunge`.       |
| `--format`               | `table` | Output format: `table` or `json`.                                                     |

## Output fields

| Field               | Description                                                    |
| ------------------- | -------------------------------------------------------------- |
| Mailbox             | Target mailbox name                                            |
| Mode                | `dry-run` or `execute`                                         |
| Criteria            | IMAP search string sent to the server                          |
| Messages in mailbox | Total messages currently in the mailbox                        |
| Search matches      | UIDs returned by the IMAP search                               |
| Filter matches      | UIDs remaining after local size filters                        |
| Affected messages   | Final count after applying `--limit`                           |
| Affected size       | Combined size of affected messages                             |
| Marked deleted      | Messages flagged `\Deleted` (0 in dry-run mode)                |
| Expunged            | Messages permanently removed (0 unless `--expunge` was passed) |
| Expunge method      | `none`, `uid-expunge` (UIDPLUS), or `folder-expunge`           |
| UID sample          | First few affected UIDs                                        |

## Examples

The output shown below is representative. Mailbox names, counts, UIDs, sizes, and message
metadata depend on your IMAP server and account.

### Dry run: messages before a date

See what would be deleted from `Archive` before January 1, 2025, without touching anything.
Includes a sample of affected message headers:

<!-- doc-example:start delete-dry-run -->

```console
$ uv run imap-cleanup delete --mailbox Archive --before 2025-01-01

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

Messages:
UID    Date                            From                                 Subject              Size
-----  ------------------------------  -----------------------------------  -------------------  -------
12044  Mon, 18 Mar 2024 14:22:10 +...  Statements <statements@example.com>  Quarterly statement  9.0 MiB
12087  Thu, 05 Dec 2024 09:08:33 +...  Receipts <receipts@example.com>      Travel receipt       7.4 MiB

Pass --execute to mark these messages \Deleted.
```

<!-- doc-example:end delete-dry-run -->

To show more message summaries:

```console
uv run imap-cleanup delete --mailbox Archive --before 2025-01-01 --sample-limit 50
```

### Dry run: messages larger than a size

Messages in `Sent` larger than 25 MiB:

```console
uv run imap-cleanup delete --mailbox Sent --larger-than 25MiB
```

### Dry run: messages smaller than a size

Messages in `Archive` smaller than 100 KiB:

```console
uv run imap-cleanup delete --mailbox Archive --smaller-than 100KiB
```

### Dry run: combining date and size

Messages in `Archive` older than January 1, 2025, and larger than 10 MiB:

```console
uv run imap-cleanup delete --mailbox Archive --before 2025-01-01 --larger-than 10MiB
```

### Date range

Messages in `Archive` received between January 1, 2020, and January 1, 2023:

```console
uv run imap-cleanup delete --mailbox Archive --since 2020-01-01 --before 2023-01-01
```

### Match everything with a size filter

Match all messages in `Trash` larger than 1 MiB:

```console
uv run imap-cleanup delete --mailbox Trash --all --larger-than 1MiB
```

`--all` cannot be combined with `--before` or `--since`.

### Limit how many messages are affected

Mark at most 100 messages even if more match:

```console
uv run imap-cleanup delete --mailbox Archive --before 2025-01-01 --limit 100
```

### Execute: mark messages deleted

Add `--execute` to actually mark matched messages `\Deleted`:

```console
uv run imap-cleanup delete \
  --mailbox Archive \
  --before 2025-01-01 \
  --execute
```

### Execute and expunge

Mark deleted and permanently remove in the same run. Uses `UID EXPUNGE` if the server supports
UIDPLUS:

```console
uv run imap-cleanup delete \
  --mailbox Archive \
  --before 2025-01-01 \
  --execute \
  --expunge
```

### Expunge on a server without UIDPLUS

Pass `--allow-folder-expunge` to permit a folder-wide expunge. This permanently removes **all**
messages already marked `\Deleted` in the folder, not just the ones from the current run:

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

<!-- doc-example:start delete-json -->
```json
{
  "affected_human_size": "2.8 GiB",
  "affected_messages": 390,
  "affected_size_bytes": 3006477107,
  "expunge_method": "none",
  "expunged_messages": 0,
  "mailbox": "Archive",
  "marked_deleted_messages": 0,
  "matched_messages": 390,
  "mode": "dry-run",
  "sample_messages": [],
  "search_criteria": [
    "BEFORE",
    "01-Jan-2025"
  ],
  "searched_messages": 390,
  "selected_messages": 1250,
  "uid_sample": [
    12044,
    12045,
    12046,
    12047,
    12048
  ],
  "warnings": []
}
```
<!-- doc-example:end delete-json -->

### Delete specific messages by UID

Dry run — preview one or more messages by UID:

<!-- doc-example:start delete-uid-dry-run -->
```console
$ uv run imap-cleanup delete --mailbox Archive --uid 12044 --uid 12087

Mailbox              Archive
Mode                 dry-run
Criteria             UID 12044,12087
Messages in mailbox  1,250
Search matches       2
Filter matches       2
Affected messages    2
Affected size        16.4 MiB
Marked deleted       0
Expunged             0
Expunge method       none
UID sample           12044, 12087

Messages:
UID    Date                            From                                 Subject              Size
-----  ------------------------------  -----------------------------------  -------------------  -------
12044  Mon, 18 Mar 2024 14:22:10 +...  Statements <statements@example.com>  Quarterly statement  9.0 MiB
12087  Thu, 05 Dec 2024 09:08:33 +...  Receipts <receipts@example.com>      Travel receipt       7.4 MiB

Pass --execute to mark these messages \Deleted.
```
<!-- doc-example:end delete-uid-dry-run -->

Mark them deleted:

```console
uv run imap-cleanup delete --mailbox Archive --uid 12044 --uid 12087 --execute
```

Mark deleted and expunge in one run:

```console
uv run imap-cleanup delete \
  --mailbox Archive \
  --uid 12044 \
  --uid 12087 \
  --execute \
  --expunge
```

UID-targeted JSON output:

```console
uv run imap-cleanup delete --mailbox Archive --uid 12044 --uid 12087 --format json
```

Example JSON output:

<!-- doc-example:start delete-uid-json -->
```json
{
  "affected_human_size": "16.4 MiB",
  "affected_messages": 2,
  "affected_size_bytes": 17196646,
  "expunge_method": "none",
  "expunged_messages": 0,
  "mailbox": "Archive",
  "marked_deleted_messages": 0,
  "matched_messages": 2,
  "mode": "dry-run",
  "sample_messages": [
    {
      "date": "Mon, 18 Mar 2024 14:22:10 +0000",
      "from": "Statements <statements@example.com>",
      "human_size": "9.0 MiB",
      "size_bytes": 9437184,
      "subject": "Quarterly statement",
      "uid": 12044
    },
    {
      "date": "Thu, 05 Dec 2024 09:08:33 +0000",
      "from": "Receipts <receipts@example.com>",
      "human_size": "7.4 MiB",
      "size_bytes": 7759462,
      "subject": "Travel receipt",
      "uid": 12087
    }
  ],
  "search_criteria": [
    "UID",
    "12044,12087"
  ],
  "searched_messages": 2,
  "selected_messages": 1250,
  "uid_sample": [
    12044,
    12087
  ],
  "warnings": []
}
```
<!-- doc-example:end delete-uid-json -->

## Expunge

When `--expunge` is passed, the CLI prefers `UID EXPUNGE`, available when the server advertises the UIDPLUS extension. This removes only the specific UIDs from the current run.

If the server doesn't support UIDPLUS, `--expunge` alone does nothing. You also need to pass `--allow-folder-expunge`, which permits a folder-wide `EXPUNGE`. That permanently removes **all** messages already marked `\Deleted` in the folder — not just the ones from the current run. Use it carefully.

---

<p align="center">
  <a href="folders.md">← Folders</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="delete-folder.md">Delete Folder →</a>
</p>
