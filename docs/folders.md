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

```bash
uv run imap-cleanup folders
```

## Output

```console
$ uv run imap-cleanup folders

Quota root "": STORAGE 14.0 GiB / 25.0 GiB

Mailbox  Messages  Size bytes     Size     Method
-------  --------  -------------  -------  -----------
Sent     3,102     8,697,308,774  8.1 GiB  rfc822-size
INBOX    12,440    5,153,960,755  4.8 GiB  status-size
```

The `Method` column tells you how the size was calculated:

- **`status-size`** — the server supports `STATUS=SIZE` and reported the folder size directly.
- **`rfc822-size`** — the server doesn't support `STATUS=SIZE`; the CLI opened each folder and summed every message's `RFC822.SIZE` field.

If the server supports the `QUOTA` extension, a quota usage line appears above the table.

## JSON output

```bash
uv run imap-cleanup folders --format json
```

The response includes `capabilities`, `folders`, `quota`, and any `errors` encountered per-mailbox during scanning. Each folder entry includes `mailbox`, `messages`, `size_bytes`, `human_size`, and `method`.

## Caveats

- **`rfc822-size` is the encoded size.** Base64-encoded attachments are stored roughly one third larger than the original file, so the reported size can be meaningfully higher than what the attachment actually occupied on disk.
- **Messages marked `\Deleted` may still be counted** until the mailbox is expunged. The report reflects whatever the server returns at scan time.

---

<p align="center">
  <a href="configuration.md">← Configuration</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="delete.md">Delete →</a>
</p>
