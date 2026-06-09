<p align="center">
  <a href="configuration.md">← Configuration</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="folders.md">Folders →</a>
</p>

---

# Common IMAP Terms

Short definitions for IMAP terms and acronyms used by mail clients, servers, and this CLI.

## Core concepts

| Term            | Definition                                                                              |
| --------------- | --------------------------------------------------------------------------------------- |
| IMAP            | Internet Message Access Protocol; a protocol for reading and managing mail on a server. |
| IMAP4rev1       | The widely supported IMAP version used by most modern servers.                          |
| Server          | The mail service that stores mailboxes and messages.                                    |
| Client          | Software that connects to the server, such as this CLI or a mail app.                   |
| Mailbox         | An IMAP folder containing messages, such as `INBOX`, `Sent`, or `Archive`.              |
| Folder          | Common user-facing name for an IMAP mailbox.                                            |
| Message         | One email item stored in a mailbox.                                                     |
| INBOX           | The standard primary mailbox every IMAP account exposes.                                |
| UID             | Unique identifier for a message within one mailbox.                                     |
| Sequence number | Temporary message number that can change when the mailbox changes.                      |
| Flag            | Server-side message state, such as `\Seen` or `\Deleted`.                               |
| Keyword         | A custom flag supported by some servers.                                                |
| Internal date   | Server-assigned message date used by IMAP date searches.                                |
| Capability      | A server-advertised feature or extension.                                               |
| Quota           | Server-reported account or storage limit, when supported.                               |

## Common commands and flags

| Term         | Definition                                                     |
| ------------ | -------------------------------------------------------------- |
| `CAPABILITY` | Lists server-supported IMAP features.                          |
| `LIST`       | Lists available mailboxes.                                     |
| `SELECT`     | Opens a mailbox for reading and writing.                       |
| `EXAMINE`    | Opens a mailbox read-only.                                     |
| `STATUS`     | Gets mailbox metadata without opening the mailbox.             |
| `SEARCH`     | Finds messages matching criteria such as date or flags.        |
| `FETCH`      | Retrieves message data or metadata.                            |
| `STORE`      | Changes message flags.                                         |
| `EXPUNGE`    | Permanently removes messages marked `\Deleted`.                |
| `\Seen`      | Message has been read.                                         |
| `\Answered`  | Message has been replied to.                                   |
| `\Flagged`   | Message is starred or flagged.                                 |
| `\Draft`     | Message is a draft.                                            |
| `\Deleted`   | Message is marked for removal, but not removed until expunged. |

## Cleanup terms

| Term           | Definition                                                                        |
| -------------- | --------------------------------------------------------------------------------- |
| Dry run        | Preview mode that reports what would happen without changing mail.                |
| Execute        | Mode that applies the requested deletion action.                                  |
| Preview        | Optional output showing sample messages that match delete criteria.               |
| Selector       | A filter that chooses messages, such as date, size, or `--all`.                   |
| `BEFORE`       | IMAP search key for messages with an internal date before a date.                 |
| `SINCE`        | IMAP search key for messages with an internal date on or after a date.            |
| Size filter    | Local filter based on each message's reported byte size.                          |
| `RFC822.SIZE`  | IMAP message size field, usually encoded bytes; can be summed as a size fallback. |
| `STATUS=SIZE`  | Extension that lets a server report total mailbox size directly.                  |
| UID expunge    | Expunge operation that removes only specific UIDs.                                |
| Folder expunge | Expunge operation that removes all `\Deleted` messages in the selected mailbox.   |
| Delete mailbox | Remove a mailbox/folder itself using IMAP `DELETE`.                               |

## Acronyms and extensions

| Acronym  | Definition                                                                      |
| -------- | ------------------------------------------------------------------------------- |
| MIME     | Format for message bodies, attachments, and content types.                      |
| RFC      | Standards document series used to define IMAP and email behavior.               |
| SASL     | Authentication framework used by many IMAP servers.                             |
| SSL      | Older name commonly used for encrypted connections; TLS is the modern protocol. |
| TLS      | Encryption protocol used to protect IMAP connections.                           |
| STARTTLS | Command that upgrades a plaintext connection to TLS.                            |
| UIDPLUS  | IMAP extension that supports UID-based operations, including `UID EXPUNGE`.     |
| QUOTA    | IMAP extension for reporting storage limits and usage.                          |
| IDLE     | IMAP extension for real-time mailbox change notifications.                      |
| MOVE     | IMAP extension for moving messages between mailboxes.                           |
| UTF-7    | Encoding family behind IMAP's modified UTF-7 mailbox-name format.               |

---

<p align="center">
  <a href="configuration.md">← Configuration</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="README.md">Docs</a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="folders.md">Folders →</a>
</p>
