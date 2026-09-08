"""Mirror of frontend catchUpKinds ranking (L21). Keep in sync with frontend/src/catchUpKinds.ts."""

from __future__ import annotations

HUNDRED_STEP = {
    "たしざん",
    "ひきざん",
    "かけざん",
    "わりざん",
    "かんじのよみ",
    "じゅくごのよみ",
}
RIKA_EIGO = {
    "いきもののせいかつ",
    "じしゃくとでんき",
    "たいようとかげ",
    "ひかりとおと",
    "てんきとみず",
    "たんご",
    "あいさつ",
}


def expected_step_for_kind(kind: str, school_grade: int, max_step: int) -> int:
    grade = min(max(school_grade, 1), 6)
    if max_step >= 100 or kind in HUNDRED_STEP:
        return (grade - 1) * 17 + 1
    if kind in RIKA_EIGO:
        if grade <= 2:
            return 1
        if grade == 3:
            return 2
        return min(6, grade - 1)
    return min(max(max_step, 1), grade)


def rank_catch_up_kinds(progress: list[dict], school_grade: int, *, top_n: int = 3) -> dict:
    all_rows: list[dict] = []
    for row in progress:
        step = int(row["step"])
        expected = expected_step_for_kind(row["kind"], school_grade, int(row["max_step"]))
        lag = expected - step
        all_rows.append(
            {
                "kind": row["kind"],
                "step": step,
                "expected": expected,
                "lag": lag,
                "step_label": row.get("step_label", ""),
            }
        )

    def key(r: dict) -> tuple:
        return (-r["lag"], r["step"], r["kind"])

    behind = [r for r in all_rows if r["lag"] > 0]
    if behind:
        ranked = sorted(behind, key=key)[:top_n]
        return {"mode": "behind", "kinds": ranked}
    ranked = sorted(all_rows, key=key)[:top_n]
    return {"mode": "slowest", "kinds": ranked}


def test_expected_math_grade3_is_step_35():
    assert expected_step_for_kind("たしざん", 3, 100) == 35
    assert expected_step_for_kind("かんじのよみ", 3, 100) == 35


def test_expected_rika_grade3_is_stage_2():
    assert expected_step_for_kind("いきもののせいかつ", 3, 6) == 2
    assert expected_step_for_kind("たんご", 3, 6) == 2


def test_expected_shakai_grade3_is_stage_3():
    assert expected_step_for_kind("とどうふけん", 3, 6) == 3


def test_rank_catch_up_most_behind_first():
    progress = [
        {"kind": "たしざん", "step": 40, "max_step": 100, "step_label": "小3のうち"},
        {"kind": "かけざん", "step": 10, "max_step": 100, "step_label": "小1のうち"},
        {"kind": "ひきざん", "step": 20, "max_step": 100, "step_label": "小2のうち"},
        {"kind": "たんご", "step": 1, "max_step": 6, "step_label": "ステージ1"},
    ]
    result = rank_catch_up_kinds(progress, 3)
    assert result["mode"] == "behind"
    assert [row["kind"] for row in result["kinds"]] == ["かけざん", "ひきざん", "たんご"]
    assert "たしざん" not in [row["kind"] for row in result["kinds"]]


def test_rank_fallback_to_slowest_when_none_behind():
    progress = [
        {"kind": "たしざん", "step": 40, "max_step": 100, "step_label": "小3のうち"},
        {"kind": "かけざん", "step": 50, "max_step": 100, "step_label": "小3のうち"},
        {"kind": "ひきざん", "step": 60, "max_step": 100, "step_label": "小4のうち"},
        {"kind": "たんご", "step": 3, "max_step": 6, "step_label": "ステージ3"},
    ]
    result = rank_catch_up_kinds(progress, 3)
    assert result["mode"] == "slowest"
    # lag: たしざん 35-40=-5, かけざん 35-50=-15, ひきざん 35-60=-25, たんご 2-3=-1
    assert [row["kind"] for row in result["kinds"]] == ["たんご", "たしざん", "かけざん"]
