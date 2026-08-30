"""理科バンクの最低問題数を検証する。"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "rika"
MIN_PER_GRADE = 15


def test_rika_bank_has_enough_questions_per_grade():
    for filename in ("ikimono.json", "denki.json", "taiyo.json", "hikari.json", "tenki.json"):
        rows = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))
        counts = Counter(row["grade"] for row in rows)
        for grade in (3, 4, 5, 6):
            assert counts[grade] >= MIN_PER_GRADE, f"{filename} grade {grade}: {counts[grade]}"
        for row in rows:
            assert row["correct"] in row["choices"]
            assert len(row["choices"]) == 4
            assert 3 <= row["grade"] <= 6
