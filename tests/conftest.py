"""Pytest configuration for repository-level test helpers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_PATH = str(ROOT)

if ROOT_PATH not in sys.path:
    sys.path.insert(0, ROOT_PATH)
