from pathlib import Path

from pytest import MonkeyPatch

from imap_cleanup.cli import build_parser, load_environment


def test_load_environment_reads_dotenv_from_current_directory(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("IMAP_CLEANUP_HOST", raising=False)
    monkeypatch.delenv("IMAP_CLEANUP_PORT", raising=False)
    monkeypatch.delenv("IMAP_CLEANUP_USERNAME", raising=False)
    monkeypatch.delenv("IMAP_CLEANUP_PASSWORD", raising=False)
    tmp_path.joinpath(".env").write_text(
        "\n".join(
            [
                "IMAP_CLEANUP_HOST=imap.example.com",
                "IMAP_CLEANUP_PORT=1143",
                "IMAP_CLEANUP_USERNAME=user@example.com",
                "IMAP_CLEANUP_PASSWORD=app-password",
            ]
        ),
        encoding="utf-8",
    )

    load_environment()
    args = build_parser().parse_args(["folders"])

    assert args.host == "imap.example.com"
    assert args.port == 1143
    assert args.username == "user@example.com"
    assert args.password == "app-password"


def test_load_environment_does_not_override_existing_environment(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("IMAP_CLEANUP_HOST", "imap.from-shell.example.com")
    tmp_path.joinpath(".env").write_text(
        "IMAP_CLEANUP_HOST=imap.from-dotenv.example.com\n",
        encoding="utf-8",
    )

    load_environment()
    args = build_parser().parse_args(["folders"])

    assert args.host == "imap.from-shell.example.com"


def test_command_line_flags_override_dotenv_defaults(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("IMAP_CLEANUP_HOST", raising=False)
    tmp_path.joinpath(".env").write_text(
        "IMAP_CLEANUP_HOST=imap.from-dotenv.example.com\n",
        encoding="utf-8",
    )

    load_environment()
    args = build_parser().parse_args(["folders", "--host", "imap.from-flag.example.com"])

    assert args.host == "imap.from-flag.example.com"


def test_delete_command_parses_selectors() -> None:
    args = build_parser().parse_args(
        [
            "delete",
            "--host",
            "imap.example.com",
            "--username",
            "user@example.com",
            "--password",
            "secret",
            "--mailbox",
            "Archive",
            "--before",
            "2026-01-01",
            "--larger-than",
            "25MiB",
            "--limit",
            "10",
            "--execute",
        ]
    )

    assert args.command == "delete"
    assert args.mailbox == "Archive"
    assert args.before.isoformat() == "2026-01-01"
    assert args.larger_than == 25 * 1024 * 1024
    assert args.limit == 10
    assert args.execute is True
