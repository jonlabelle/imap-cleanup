<p align="center">
  <a href="folders.md">← Folders</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="examples.md">Examples →</a>
</p>

---

# Delete

The `delete` command targets a single mailbox. By default it's always a dry run — nothing is modified until you pass `--execute`.

## Lifecycle

```plaintext
dry run  →  preview  →  execute  →  expunge
```

1. Run without `--execute` to see how many messages match and how much space they use.
2. Add `--preview` to inspect which messages would be affected before committing.
3. Add `--execute` to mark matching messages `\Deleted`.
4. Add `--expunge` (with `--execute`) to permanently remove them in the same run.

## Selectors

At least one selector is required. They control which messages are matched:

| Flag                  | Description                                                         |
| --------------------- | ------------------------------------------------------------------- |
| `--before YYYY-MM-DD` | Messages received before this date (IMAP `BEFORE` key)              |
| `--since YYYY-MM-DD`  | Messages received on or after this date (IMAP `SINCE` key)          |
| `--larger-than SIZE`  | Only messages larger than SIZE (applied locally after IMAP search)  |
| `--smaller-than SIZE` | Only messages smaller than SIZE (applied locally after IMAP search) |
| `--all`               | Match all messages before applying size filters                     |

**Rules:**

- `--all` is mutually exclusive with `--before` and `--since`.
- When both `--since` and `--before` are given, `--since` must be the earlier date.
- When both `--larger-than` and `--smaller-than` are given, `--larger-than` must be the smaller value.
- `--larger-than` and `--smaller-than` can be freely combined with date selectors.

## Size units

`--larger-than` and `--smaller-than` accept bytes or any of these units (case-insensitive, decimals accepted):

`B`, `K` / `KB` / `KiB`, `M` / `MB` / `MiB`, `G` / `GB` / `GiB`, `T` / `TB` / `TiB`

Examples: `500B`, `25MiB`, `1.5GiB`, `500MB`

## All flags

| Flag                     | Default | Description                                                                     |
| ------------------------ | ------- | ------------------------------------------------------------------------------- |
| `--mailbox`              | —       | Mailbox to operate on. Required.                                                |
| `--before`               | —       | Match messages before this date.                                                |
| `--since`                | —       | Match messages on or after this date.                                           |
| `--larger-than`          | —       | Filter by minimum message size.                                                 |
| `--smaller-than`         | —       | Filter by maximum message size.                                                 |
| `--all`                  | —       | Match every message (before size filters).                                      |
| `--limit N`              | —       | Cap how many matched messages are affected.                                     |
| `--preview`              | off     | Fetch and show a sample of affected messages.                                   |
| `--preview-limit N`      | `10`    | How many message summaries `--preview` fetches.                                 |
| `--execute`              | off     | Mark matched messages `\Deleted`. Without this, always a dry run.               |
| `--expunge`              | off     | Permanently remove messages after marking deleted. Requires `--execute`.        |
| `--allow-folder-expunge` | off     | Permit folder-wide EXPUNGE when the server lacks UIDPLUS. Requires `--expunge`. |
| `--format`               | `table` | Output format: `table` or `json`.                                               |

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

## Expunge

When `--expunge` is passed, the CLI prefers `UID EXPUNGE`, available when the server advertises the UIDPLUS extension. This removes only the specific UIDs from the current run.

If the server doesn't support UIDPLUS, `--expunge` alone does nothing. You also need to pass `--allow-folder-expunge`, which permits a folder-wide `EXPUNGE`. That permanently removes **all** messages already marked `\Deleted` in the folder — not just the ones from the current run. Use it carefully.

---

<p align="center">
  <a href="folders.md">← Folders</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="examples.md">Examples →</a>
</p>
