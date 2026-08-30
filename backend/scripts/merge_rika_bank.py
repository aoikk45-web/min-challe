"""理科ドリルバンクのマージ・検証・書き出し。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "rika"

KIND_FILES = {
    "いきもののせいかつ": "ikimono.json",
    "じしゃくとでんき": "denki.json",
}


def _load_extra():
    from scripts.rika_bank_data import DENKI_EXTRA, IKIMONO_EXTRA

    return {
        "いきもののせいかつ": IKIMONO_EXTRA,
        "じしゃくとでんき": DENKI_EXTRA,
    }


def _entry(kind: str, prompt: str, choices: list[str], correct: str, grade: int) -> dict:
    if correct not in choices:
        raise ValueError(f"correct not in choices: {prompt!r}")
    if len(choices) != 4:
        raise ValueError(f"need 4 choices: {prompt!r}")
    return {
        "prompt": prompt,
        "choices": choices,
        "correct": correct,
        "grade": grade,
        "kind": kind,
        "image": None,
    }


def merge_bank(kind: str, existing: list[dict], extra: list[tuple]) -> list[dict]:
    seen = {row["prompt"] for row in existing}
    out = list(existing)
    for prompt, choices, correct, grade in extra:
        if prompt in seen:
            continue
        out.append(_entry(kind, prompt, choices, correct, grade))
        seen.add(prompt)
    return sorted(out, key=lambda r: (r["grade"], r["prompt"]))


def main() -> int:
    extras = _load_extra()
    for kind, filename in KIND_FILES.items():
        path = DATA_DIR / filename
        existing = json.loads(path.read_text(encoding="utf-8"))
        merged = merge_bank(kind, existing, extras[kind])
        path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        from collections import Counter

        counts = Counter(row["grade"] for row in merged)
        print(f"{kind}: {len(merged)} questions {dict(sorted(counts.items()))}")
        for grade in (3, 4, 5, 6):
            if counts.get(grade, 0) < 15:
                print(f"  warning: grade {grade} has only {counts.get(grade, 0)} questions")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
