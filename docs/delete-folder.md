<p align="center">
  <a href="delete.md">← Delete Messages</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="examples.md">Examples →</a>
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

| Field              | Description                                               |
| ------------------ | --------------------------------------------------------- |
| Mailbox            | Target mailbox name                                       |
| Mode               | `dry-run` or `execute`                                    |
| Recursive          | Whether child mailboxes are included                      |
| Mailboxes affected | Number of mailboxes listed for deletion                   |
| Messages affected  | Total messages reported by IMAP `STATUS`                  |
| Total size         | Total mailbox size when the server supports `STATUS=SIZE` |
| Deleted mailboxes  | Whether IMAP `DELETE` was executed successfully           |

The table output also lists each affected mailbox. JSON output includes the same data in a `mailboxes` array.

## Caveats

- `delete-folder` sends IMAP `DELETE` for the named mailbox. Provider behavior can vary, but the command is intended to remove the folder and messages stored only in that folder.
- Child mailboxes are included only when `--recursive` is passed. Recursive execution deletes child mailboxes before parent mailboxes.
- Non-selectable parents are not deleted; with `--recursive`, selectable descendants under that parent can still be deleted.
- Gmail-style labels are not normal folders. Deleting a label/mailbox may not remove the underlying message when the same message also has other labels.

---

<p align="center">
  <a href="delete.md">← Delete Messages</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="examples.md">Examples →</a>
</p>
