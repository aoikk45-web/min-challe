"""Build backend/data/kokugo/dokkai.json from dokkai_stories.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from scripts.validate_dokkai_json import validate  # noqa: E402

SOURCE = ROOT / "backend" / "data" / "kokugo" / "dokkai_stories.json"
OUT = ROOT / "backend" / "data" / "kokugo" / "dokkai.json"


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"missing source: {SOURCE}")
    errors = validate(SOURCE)
    if errors:
        for err in errors:
            print(err)
        raise SystemExit(1)
    stories = json.loads(SOURCE.read_text(encoding="utf-8"))
    counts: dict[int, int] = {}
    for row in stories:
        stage = int(row["stage"])
        counts[stage] = counts.get(stage, 0) + 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(stories, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"dokkai: {len(stories)} stories")
    print(dict(sorted(counts.items())))


if __name__ == "__main__":
    main()
