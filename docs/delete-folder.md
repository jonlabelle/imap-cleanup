<p align="center">
  <a href="delete.md">← Delete Messages</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="terms.md">Common IMAP Terms →</a>
</p>

---

# Delete Folder

The `delete-folder` command deletes an IMAP mailbox/folder and the messages stored in that mailbox. It is always a dry run unless you pass `--execute`. In dry-run mode a sample of affected messages is shown automatically.

<!-- doc-example:start delete-folder-command -->

```console
# Installed binary
imap-cleanup delete-folder --mailbox "Old Projects"

# Source checkout
uv run imap-cleanup delete-folder --mailbox "Old Projects"
```

<!-- doc-example:end delete-folder-command -->

Use `delete-folder` when you want the folder itself removed. Use [`delete`](delete.md) when you want to keep the folder but mark selected messages `\Deleted`.

`delete-mailbox` is accepted as an alias for `delete-folder`.

## Lifecycle

```plaintext
dry run  →  execute
```

1. Run without `--execute` to see the mailbox name, message count, and a sample of messages.
2. Add `--recursive` to include selectable child mailboxes in the dry run.
3. Add `--execute` to send IMAP `DELETE` for the listed mailbox or mailboxes.

## All flags

| Flag               | Default | Description                                                         |
| ------------------ | ------- | ------------------------------------------------------------------- |
| `--mailbox`        | —       | Mailbox/folder to delete. Required.                                 |
| `--recursive`      | off     | Also delete selectable child mailboxes below `--mailbox`.           |
| `--sample-limit N` | `10`    | How many message summaries to show in dry-run output.               |
| `--execute`        | off     | Actually delete the mailbox/folder. Without this, always a dry run. |
| `--format`         | `table` | Output format: `table` or `json`.                                   |

## Output fields

| Field              | Description                                         |
| ------------------ | --------------------------------------------------- |
| Mailbox            | Target mailbox name                                 |
| Mode               | `dry-run` or `execute`                              |
| Recursive          | Whether child mailboxes are included                |
| Mailboxes affected | Number of mailboxes listed for deletion             |
| Messages affected  | Total messages reported for affected mailboxes      |
| Total size         | Total mailbox size when a size method is available  |
| Deleted mailboxes  | Whether IMAP `DELETE` was executed successfully     |
| Messages           | Sample of message summaries shown in dry-run output |

The table output also lists each affected mailbox with its size method. In dry-run mode, table output shows message summaries under the affected mailbox, and JSON output includes per-mailbox `sample_messages` arrays. JSON output also includes a top-level `size_method`.

## Examples

The output shown below is representative. Mailbox names, counts, sizes, and size methods depend
on your IMAP server and account.

### Dry run

Check the message count before deleting the folder itself:

<!-- doc-example:start delete-folder-command -->

```console
# Installed binary
imap-cleanup delete-folder --mailbox "Old Projects"

# Source checkout
uv run imap-cleanup delete-folder --mailbox "Old Projects"
```

<!-- doc-example:end delete-folder-command -->

### Execute

Delete the folder and the messages stored in that folder:

<!-- doc-example:start delete-folder-execute-command -->

```console
# Installed binary
imap-cleanup delete-folder --mailbox "Old Projects" --execute

# Source checkout
uv run imap-cleanup delete-folder --mailbox "Old Projects" --execute
```

<!-- doc-example:end delete-folder-execute-command -->

### Recursive preview

Check the folder and all selectable child folders, plus a sample of messages, before deleting
anything:

<!-- doc-example:start delete-folder-recursive -->
```console
# Installed binary
$ imap-cleanup delete-folder --mailbox "Old Projects" --recursive --sample-limit 3

# Source checkout
$ uv run imap-cleanup delete-folder --mailbox "Old Projects" --recursive --sample-limit 3

# Output
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

Messages (Old Projects):
UID    Date                            From                                 Subject              Size
-----  ------------------------------  -----------------------------------  -------------------  -------
12044  Mon, 18 Mar 2024 14:22:10 +...  Statements <statements@example.com>  Quarterly statement  9.0 MiB
12087  Thu, 05 Dec 2024 09:08:33 +...  Receipts <receipts@example.com>      Travel receipt       7.4 MiB

Messages (Old Projects/2022):
UID    Date                            From                               Subject                 Size
-----  ------------------------------  ---------------------------------  ----------------------  --------
22410  Tue, 09 Aug 2022 16:45:00 +...  Build System <builds@example.com>  Project export archive  13.0 MiB

Warnings:
- Deleting a mailbox removes messages stored in that mailbox.
- Recursive delete enabled; child mailboxes are deleted before parents.
- Showing first 3 of 340 affected messages.

Pass --execute to delete these mailboxes and all messages they contain.
```
<!-- doc-example:end delete-folder-recursive -->

Fetch a wider sample when the folder tree is large:

<!-- doc-example:start delete-folder-recursive-sample-command -->

```console
# Installed binary
imap-cleanup delete-folder --mailbox "Old Projects" --recursive --sample-limit 25

# Source checkout
uv run imap-cleanup delete-folder --mailbox "Old Projects" --recursive --sample-limit 25
```

<!-- doc-example:end delete-folder-recursive-sample-command -->

### Recursive execute

Delete child folders first, then the parent folder:

<!-- doc-example:start delete-folder-recursive-execute-command -->

```console
# Installed binary
imap-cleanup delete-folder --mailbox "Old Projects" --recursive --execute

# Source checkout
uv run imap-cleanup delete-folder --mailbox "Old Projects" --recursive --execute
```

<!-- doc-example:end delete-folder-recursive-execute-command -->

### JSON output

<!-- doc-example:start delete-folder-json-command -->

```console
# Installed binary
imap-cleanup delete-folder --mailbox "Old Projects" --format json

# Source checkout
uv run imap-cleanup delete-folder --mailbox "Old Projects" --format json
```

<!-- doc-example:end delete-folder-json-command -->

Example JSON output:

<!-- doc-example:start delete-folder-json -->

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
      "sample_messages": [],
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

<!-- doc-example:end delete-folder-json -->

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
- Dry-run mode opens affected mailboxes read-only, searches `ALL`, and fetches a sample of message headers with `BODY.PEEK`; it does not delete anything unless `--execute` is also passed.
- `--sample-limit` is a report-wide cap for recursive runs, so the first affected mailboxes may use the available slots.
- The `rfc822-size` fallback is used for dry runs only. Execute mode without a prior dry run avoids opening the target mailbox before `DELETE`; run a dry run first when you need fallback size totals on servers without `STATUS=SIZE`.
- `rfc822-size` is the encoded message size, so attachment-heavy mailboxes can report larger than the original attachment files.
- Gmail-style labels are not normal folders. Deleting a label/mailbox may not remove the underlying message when the same message also has other labels.

---

<p align="center">
  <a href="delete.md">← Delete Messages</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="terms.md">Common IMAP Terms →</a>
</p>
