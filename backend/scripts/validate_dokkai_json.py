"""Validate dokkai stories JSON before import."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.kokugo_kanji import annotate_furigana, unannotated_high_grade_kanji  # noqa: E402


def validate(path: Path) -> list[str]:
    stories = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if not isinstance(stories, list):
        return ["root must be a JSON array"]

    counts: dict[int, int] = {}
    seen: set[str] = set()
    for row in stories:
        sid = str(row.get("id", ""))
        if sid in seen:
            errors.append(f"{sid}: duplicate id")
        seen.add(sid)
        stage = int(row["stage"])
        counts[stage] = counts.get(stage, 0) + 1
        if len(row.get("questions", [])) != 3:
            errors.append(f"{sid}: expected 3 questions")
        for i, q in enumerate(row.get("questions", []), start=1):
            if q.get("correct") not in q.get("choices", []):
                errors.append(f"{sid} q{i}: correct not in choices")
            if len(q.get("choices", [])) != 4:
                errors.append(f"{sid} q{i}: expected 4 choices")
            if q.get("type") not in ("fact", "reason", "learning"):
                errors.append(f"{sid} q{i}: bad type {q.get('type')!r}")
        for field in ["title", "passage"]:
            bad = unannotated_high_grade_kanji(annotate_furigana(str(row[field])))
            if bad:
                errors.append(f"{sid} {field}: unannotated kanji {sorted(set(bad))}")
        for q in row.get("questions", []):
            for key in ("prompt", "explanation"):
                bad = unannotated_high_grade_kanji(annotate_furigana(str(q[key])))
                if bad:
                    errors.append(f"{sid} {key}: unannotated kanji {sorted(set(bad))}")
            for choice in q.get("choices", []):
                bad = unannotated_high_grade_kanji(annotate_furigana(str(choice)))
                if bad:
                    errors.append(f"{sid} choice: unannotated kanji {sorted(set(bad))}")

    for stage in range(1, 7):
        if counts.get(stage, 0) != 15:
            errors.append(f"stage {stage}: expected 15 stories, got {counts.get(stage, 0)}")
    if len(stories) != 90:
        errors.append(f"expected 90 stories, got {len(stories)}")
    return errors


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "backend" / "data" / "kokugo" / "dokkai_stories.json"
    errs = validate(target)
    if errs:
        print(f"FAILED ({len(errs)} issues):")
        for e in errs:
            print(" ", e)
        raise SystemExit(1)
    print(f"OK: {target}")
