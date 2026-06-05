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
2. Add `--execute` to send IMAP `DELETE` for that mailbox.

## All flags

| Flag        | Default | Description                                                         |
| ----------- | ------- | ------------------------------------------------------------------- |
| `--mailbox` | —       | Mailbox/folder to delete. Required.                                 |
| `--execute` | off     | Actually delete the mailbox/folder. Without this, always a dry run. |
| `--format`  | `table` | Output format: `table` or `json`.                                   |

## Output fields

| Field               | Description                                         |
| ------------------- | --------------------------------------------------- |
| Mailbox             | Target mailbox name                                 |
| Mode                | `dry-run` or `execute`                              |
| Messages in mailbox | Total messages reported by IMAP `STATUS`            |
| Size                | Mailbox size when the server supports `STATUS=SIZE` |
| Size method         | `status-size` or `status-messages`                  |
| Deleted mailbox     | Whether IMAP `DELETE` was executed successfully     |

## Caveats

- `delete-folder` sends IMAP `DELETE` for the named mailbox. Provider behavior can vary, but the command is intended to remove the folder and messages stored only in that folder.
- Child mailboxes are not deleted recursively. Delete child folders separately if your provider keeps nested folders as separate mailboxes.
- Gmail-style labels are not normal folders. Deleting a label/mailbox may not remove the underlying message when the same message also has other labels.

---

<p align="center">
  <a href="delete.md">← Delete Messages</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="examples.md">Examples →</a>
</p>
