"""Load 90 grade-3 reading comprehension stories from dokkai_stories.json."""

from __future__ import annotations

import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "data" / "kokugo" / "dokkai_stories.json"


def all_stories() -> list[dict]:
    """Return all 90 reading comprehension stories."""
    return json.loads(SOURCE.read_text(encoding="utf-8"))
