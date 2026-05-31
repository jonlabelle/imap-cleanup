from imap_cleanup.models import QuotaReport
from imap_cleanup.parsing import (
    parse_capabilities,
    parse_fetch_message_summaries,
    parse_fetch_size_by_uid,
    parse_fetch_sizes,
    parse_list_response,
    parse_quota_response,
    parse_select_count,
    parse_status_response,
    parse_uid_search_response,
    tokenize_imap,
)


def test_tokenize_imap_handles_quoted_strings() -> None:
    assert tokenize_imap(r'(\HasNoChildren) "/" "Sent \"Archive\""') == [
        "(",
        r"\HasNoChildren",
        ")",
        "/",
        'Sent "Archive"',
    ]


def test_parse_capabilities_normalizes_tokens() -> None:
    capabilities = parse_capabilities([b"IMAP4rev1 UIDPLUS STATUS=SIZE quota"])

    assert capabilities == {"IMAP4REV1", "UIDPLUS", "STATUS=SIZE", "QUOTA"}


def test_parse_list_response_returns_selectable_mailboxes() -> None:
    mailboxes = parse_list_response(
        [
            b'(\\HasNoChildren) "/" "INBOX"',
            b'(\\HasChildren \\Noselect) "/" "[Gmail]"',
            b'(\\HasNoChildren) "/" "[Gmail]/Sent Mail"',
        ]
    )

    assert mailboxes == ["INBOX", "[Gmail]/Sent Mail"]


def test_parse_status_response_extracts_messages_and_size() -> None:
    values = parse_status_response([b'"INBOX" (MESSAGES 1240 SIZE 987654321)'])

    assert values["MESSAGES"] == 1240
    assert values["SIZE"] == 987654321


def test_parse_select_count_reads_first_numeric_token() -> None:
    assert parse_select_count([b"42"]) == 42
    assert parse_select_count([b"OK [READ-ONLY] Selected"]) is None


def test_parse_fetch_sizes_sums_tuple_and_byte_responses() -> None:
    sizes = parse_fetch_sizes(
        [
            b"1 (UID 101 RFC822.SIZE 10)",
            (b"2 (UID 102 RFC822.SIZE 25)", b""),
            b"3 (UID 103 RFC822.SIZE 35)",
        ]
    )

    assert sizes == [10, 25, 35]


def test_parse_fetch_size_by_uid_maps_sizes() -> None:
    sizes = parse_fetch_size_by_uid(
        [
            b"1 (UID 101 RFC822.SIZE 10)",
            b"2 (RFC822.SIZE 25 UID 102)",
        ]
    )

    assert sizes == {101: 10, 102: 25}


def test_parse_fetch_message_summaries_reads_headers_and_metadata() -> None:
    summaries = parse_fetch_message_summaries(
        [
            (
                b"1 (UID 101 RFC822.SIZE 2048 BODY[HEADER.FIELDS (DATE FROM SUBJECT)] {120}",
                b"Date: Wed, 01 Jan 2025 12:00:00 +0000\r\n"
                b"From: Sender <sender@example.com>\r\n"
                b"Subject: =?utf-8?q?Quarterly_report?=\r\n\r\n",
            ),
            b")",
        ]
    )

    assert len(summaries) == 1
    assert summaries[0].uid == 101
    assert summaries[0].date == "Wed, 01 Jan 2025 12:00:00 +0000"
    assert summaries[0].from_header == "Sender <sender@example.com>"
    assert summaries[0].subject == "Quarterly report"
    assert summaries[0].size_bytes == 2048


def test_parse_uid_search_response_reads_uids() -> None:
    assert parse_uid_search_response([b"101 102 103"]) == [101, 102, 103]


def test_parse_quota_response_extracts_storage_resource() -> None:
    quota = parse_quota_response([b'* QUOTA "" (STORAGE 725000 1048576 MESSAGE 50 1000)'])

    assert isinstance(quota, QuotaReport)
    assert quota.root == ""
    assert quota.resources[0].name == "STORAGE"
    assert quota.resources[0].usage == 725000
    assert quota.resources[0].limit == 1048576
    assert quota.resources[0].usage_bytes == 742400000
    assert quota.resources[1].name == "MESSAGE"


def test_parse_quota_response_handles_nested_list_format() -> None:
    # Python 3.14+ imaplib.getquotaroot returns nested lists:
    # (typ, [[QUOTAROOT responses...], [QUOTA responses]])
    quota = parse_quota_response([[b'INBOX ""'], [b'"" (STORAGE 725000 1048576)']])

    assert isinstance(quota, QuotaReport)
    assert quota.root == ""
    assert quota.resources[0].name == "STORAGE"
    assert quota.resources[0].usage == 725000
    assert quota.resources[0].limit == 1048576
