import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def test_vscode_uid_delete_presets_are_preview_only() -> None:
    tasks = _load_json(".vscode/tasks.json")["tasks"]
    launches = _load_json(".vscode/launch.json")["configurations"]

    task_args_by_label = {task["label"]: task["args"] for task in tasks if "args" in task}
    launch_args_by_name = {launch["name"]: launch["args"] for launch in launches}

    assert task_args_by_label["imap-cleanup: delete uid dry run"] == [
        "run",
        "imap-cleanup",
        "delete",
        "--mailbox",
        "Archive",
        "--uid",
        "12044",
        "--uid",
        "12087",
    ]
    assert task_args_by_label["imap-cleanup: delete uid dry run json"] == [
        "run",
        "imap-cleanup",
        "delete",
        "--mailbox",
        "Archive",
        "--uid",
        "12044",
        "--uid",
        "12087",
        "--format",
        "json",
    ]
    assert launch_args_by_name["imap-cleanup: delete uid dry run"] == [
        "delete",
        "--mailbox",
        "Archive",
        "--uid",
        "12044",
        "--uid",
        "12087",
    ]
    assert launch_args_by_name["imap-cleanup: delete uid dry run json"] == [
        "delete",
        "--mailbox",
        "Archive",
        "--uid",
        "12044",
        "--uid",
        "12087",
        "--format",
        "json",
    ]

    for args in (
        task_args_by_label["imap-cleanup: delete uid dry run"],
        task_args_by_label["imap-cleanup: delete uid dry run json"],
        launch_args_by_name["imap-cleanup: delete uid dry run"],
        launch_args_by_name["imap-cleanup: delete uid dry run json"],
    ):
        assert "--execute" not in args


def _load_json(path: str) -> Any:
    return json.loads(ROOT.joinpath(path).read_text(encoding="utf-8"))
