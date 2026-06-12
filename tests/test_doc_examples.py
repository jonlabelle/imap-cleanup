"""Tests for fixture-backed documentation example generation.

These checks keep README and command transcripts synchronized with the CLI
renderers while allowing formatter-only Markdown changes, such as Prettier's JSON
and marker spacing choices, to remain stable.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def test_generated_doc_examples_are_current() -> None:
    env = os.environ.copy()
    pythonpath = str(ROOT / "src")
    if env.get("PYTHONPATH"):
        pythonpath = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONPATH"] = pythonpath

    result = subprocess.run(
        [
            sys.executable,
            "scripts/render_doc_examples.py",
            "--check",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_generated_doc_examples_ignore_prettier_only_region_formatting() -> None:
    render_doc_examples = _load_render_doc_examples()
    content = """Intro
<!-- doc-example:start sample -->

```json
{
  "items": ["a", "b"]
}
```

<!-- doc-example:end sample -->
"""
    generated = """```json
{
  "items": [
    "a",
    "b"
  ]
}
```"""

    updated, used = render_doc_examples._replace_examples(
        content,
        {"sample": generated},
        path=Path("doc.md"),
    )

    assert updated == content
    assert used == {"sample"}


def test_generated_doc_examples_rewrite_actual_content_changes() -> None:
    render_doc_examples = _load_render_doc_examples()
    content = """Intro
<!-- doc-example:start sample -->

```json
{
  "items": ["a", "b"]
}
```

<!-- doc-example:end sample -->
"""
    generated = """```json
{
  "items": [
    "a",
    "c"
  ]
}
```"""

    updated, used = render_doc_examples._replace_examples(
        content,
        {"sample": generated},
        path=Path("doc.md"),
    )

    assert updated != content
    assert '"c"' in updated
    assert used == {"sample"}


def _load_render_doc_examples() -> Any:
    module_path = ROOT / "scripts/render_doc_examples.py"
    spec = importlib.util.spec_from_file_location("render_doc_examples", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
