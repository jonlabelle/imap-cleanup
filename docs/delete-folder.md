<p align="center">
  <a href="delete.md">← Delete Messages</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
</p>

---

# Delete Folder

The `delete-folder` command deletes an IMAP mailbox/folder and the messages stored in that mailbox. It is always a dry run unless you pass `--execute`.

```bash
uv run imap-cleanup delete-folder --mailbox "Old Projects"
```

Use `delete-folder` when you want the folder itself removed. Use [`delete`](delete.md) when you want to keep the folder but mark selected messages `\Deleted`.

`delete-mailbox` is accepted as an alias for `delete-folder`.

## Lifecycle

```plaintext
dry run  →  execute
```

1. Run without `--execute` to confirm the mailbox name and message count.
2. Add `--recursive` to include selectable child mailboxes in the dry run.
3. Add `--execute` to send IMAP `DELETE` for the listed mailbox or mailboxes.

## All flags

| Flag          | Default | Description                                                         |
| ------------- | ------- | ------------------------------------------------------------------- |
| `--mailbox`   | —       | Mailbox/folder to delete. Required.                                 |
| `--recursive` | off     | Also delete selectable child mailboxes below `--mailbox`.           |
| `--execute`   | off     | Actually delete the mailbox/folder. Without this, always a dry run. |
| `--format`    | `table` | Output format: `table` or `json`.                                   |

## Output fields

| Field              | Description                                        |
| ------------------ | -------------------------------------------------- |
| Mailbox            | Target mailbox name                                |
| Mode               | `dry-run` or `execute`                             |
| Recursive          | Whether child mailboxes are included               |
| Mailboxes affected | Number of mailboxes listed for deletion            |
| Messages affected  | Total messages reported for affected mailboxes     |
| Total size         | Total mailbox size when a size method is available |
| Deleted mailboxes  | Whether IMAP `DELETE` was executed successfully    |

The table output also lists each affected mailbox with its size method. JSON output includes the same data in a `mailboxes` array and includes a top-level `size_method`.

## Examples

The output shown below is representative. Mailbox names, counts, sizes, and size methods depend
on your IMAP server and account.

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

Warnings:
- Deleting a mailbox removes messages stored in that mailbox.
- Recursive delete enabled; child mailboxes are deleted before parents.

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

Example JSON output:

```json
{
  "deleted": false,
  "human_size": "600.0 MiB",
  "mailbox": "Old Projects",
  "mailboxes": [
    {
      "deleted": false,
      "human_size": "600.0 MiB",
      "mailbox": "Old Projects",
      "messages": 120,
      "size_bytes": 629145600,
      "size_method": "status-size"
    }
  ],
  "messages": 120,
  "mode": "dry-run",
  "recursive": false,
  "size_bytes": 629145600,
  "size_method": "status-size",
  "warnings": [
    "Deleting a mailbox removes messages stored in that mailbox.",
    "Child mailboxes are not deleted recursively unless --recursive is set."
  ]
}
```

## Size methods

`delete-folder` can report sizes with these methods:

- **`status-size`** — the server supports `STATUS=SIZE` and returned mailbox size directly.
- **`rfc822-size`** — dry-run fallback when direct size is unavailable. The CLI opens the mailbox read-only and sums each message's `RFC822.SIZE`.
- **`mixed`** — recursive JSON totals were calculated from more than one known size method.
- **`status-messages`** — only a message count was available; size is reported as unknown.

Recursive totals add up per-mailbox sizes when every affected mailbox returns a known size. If any affected mailbox only returns `status-messages`, the total size is unknown.

## Caveats

- `delete-folder` sends IMAP `DELETE` for the named mailbox. Provider behavior can vary, but the command is intended to remove the folder and messages stored only in that folder.
- Child mailboxes are included only when `--recursive` is passed. Recursive execution deletes child mailboxes before parent mailboxes.
- Non-selectable parents are not deleted; with `--recursive`, selectable descendants under that parent can still be deleted.
- The `rfc822-size` fallback is used for dry runs only. Execute mode avoids opening the target mailbox before `DELETE`; run a dry run first when you need fallback size totals on servers without `STATUS=SIZE`.
- `rfc822-size` is the encoded message size, so attachment-heavy mailboxes can report larger than the original attachment files.
- Gmail-style labels are not normal folders. Deleting a label/mailbox may not remove the underlying message when the same message also has other labels.

---

<p align="center">
  <a href="delete.md">← Delete Messages</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
</p>
