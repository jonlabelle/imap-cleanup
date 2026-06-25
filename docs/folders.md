<p align="center">
  <a href="configuration.md">← Configuration</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="delete.md">Delete →</a>
</p>

---

# Folders

The `folders` command connects to your account and lists every selectable mailbox sorted by size descending.

<!-- doc-example:start folders-command -->

```console
# Installed binary
imap-cleanup folders

# Source checkout
uv run imap-cleanup folders
```

<!-- doc-example:end folders-command -->

## Output

<!-- doc-example:start folders-table -->
```console
# Installed binary
$ imap-cleanup folders

# Source checkout
$ uv run imap-cleanup folders

# Output
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

The `Method` column tells you how the size was calculated:

- **`status-size`** — the server supports `STATUS=SIZE` and reported the folder size directly.
- **`rfc822-size`** — the server doesn't support `STATUS=SIZE`; the CLI opened each folder and summed every message's `RFC822.SIZE` field.

If the server supports the `QUOTA` extension, a quota usage line appears above the table.

## JSON output

<!-- doc-example:start folders-json-command -->

```console
# Installed binary
imap-cleanup folders --format json

# Source checkout
uv run imap-cleanup folders --format json
```

<!-- doc-example:end folders-json-command -->

The response includes `capabilities`, `folders`, `quota`, and any `errors` encountered per-mailbox during scanning. Each folder entry includes `mailbox`, `messages`, `size_bytes`, `human_size`, and `method`.

## Examples

The output shown below is representative. Mailbox names, counts, sizes, quota data, and
capabilities depend on your IMAP server and account.

### List all mailboxes

<!-- doc-example:start folders-table -->
```console
# Installed binary
$ imap-cleanup folders

# Source checkout
$ uv run imap-cleanup folders

# Output
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

### JSON output

<!-- doc-example:start folders-json-command -->

```console
# Installed binary
imap-cleanup folders --format json

# Source checkout
uv run imap-cleanup folders --format json
```

<!-- doc-example:end folders-json-command -->

Example JSON output:

<!-- doc-example:start folders-json -->

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
    },
    {
      "human_size": "750.0 MiB",
      "mailbox": "Sent",
      "messages": 420,
      "method": "status-size",
      "size_bytes": 786432000
    },
    {
      "human_size": "90.0 MiB",
      "mailbox": "INBOX",
      "messages": 80,
      "method": "status-size",
      "size_bytes": 94371840
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

<!-- doc-example:end folders-json -->

## Caveats

- **`rfc822-size` is the encoded size.** Base64-encoded attachments are stored roughly one third larger than the original file, so the reported size can be meaningfully higher than what the attachment actually occupied on disk.
- **Gmail-style labels are reported as mailboxes.** One message can appear in multiple labels, so summed mailbox sizes can exceed account storage or quota.
- **Messages marked `\Deleted` may still be counted** until the mailbox is expunged. The report reflects whatever the server returns at scan time.

---

<p align="center">
  <a href="configuration.md">← Configuration</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="delete.md">Delete →</a>
</p>
