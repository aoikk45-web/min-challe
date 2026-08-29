"""Ensure each grade has at least 10 chiri questions."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "backend" / "data" / "shakai" / "chiri.json"
MIN_PER_GRADE = 10
REMOVE_PROMPTS = frozenset({
    "にほんは どの ほうを むいていますか？",
    "うみに まわられた くには？",
})

ADDITIONS: list[dict] = [
    # grade 1
    {"prompt": "にほんの いちばん おおきい しまは？", "correct": "ほっかいどう", "choices": ["ほっかいどう", "ほんしゅう", "きゅうしゅう", "しこく"], "grade": 1},
    {"prompt": "ふじさんは なんですか？", "correct": "やま", "choices": ["やま", "かわ", "うみ", "しま"], "grade": 1},
    {"prompt": "とうきょうは にほんの なにですか？", "correct": "しゅと", "choices": ["しゅと", "やま", "うみ", "しま"], "grade": 1},
    {"prompt": "ほっかいどうは にほんの どこに ありますか？", "correct": "きた", "choices": ["きた", "みなみ", "ひがし", "にし"], "grade": 1},
    {"prompt": "きゅうしゅうは にほんの どこに ありますか？", "correct": "みなみ", "choices": ["みなみ", "きた", "ひがし", "にし"], "grade": 1},
    {"prompt": "にほんで いちばん おおきい しまは？", "correct": "ほんしゅう", "choices": ["ほんしゅう", "しこく", "ほっかいどう", "おきなわ"], "grade": 1},
    {"prompt": "にほんには おおきな しまが 4つ あります。ひとつは？", "correct": "ほんしゅう", "choices": ["ほんしゅう", "ちゅうごく", "かんこく", "たいわん"], "grade": 1},
    {"prompt": "やまで ゆうめいな のは？", "correct": "ふじさん", "choices": ["ふじさん", "びわこ", "とうきょう", "おおさか"], "grade": 1},
    {"prompt": "とうきょうは なにですか？", "correct": "とし", "choices": ["とし", "やま", "うみ", "くに"], "grade": 1},
    {"prompt": "うみに かこまれた くには？", "correct": "にほん", "choices": ["にほん", "ちゅうごく", "かんこく", "アメリカ"], "grade": 1},
    # grade 2
    {"prompt": "にほんの まちで いちばん にんが おおいのは？", "correct": "とうきょう", "choices": ["とうきょう", "おおさか", "よこはま", "なごや"], "grade": 2},
    {"prompt": "おおさかは どの へんに ありますか？", "correct": "きんき", "choices": ["きんき", "かんとう", "とうほく", "きゅうしゅう"], "grade": 2},
    {"prompt": "さっぽろは どの ちほうですか？", "correct": "ほっかいどう", "choices": ["ほっかいどう", "とうほく", "かんとう", "きゅうしゅう"], "grade": 2},
    {"prompt": "4つの おおきな しまの いちばん みなみは？", "correct": "きゅうしゅう", "choices": ["きゅうしゅう", "ほっかいどう", "ほんしゅう", "しこく"], "grade": 2},
    # grade 6
    {"prompt": "つくばかがくだいは どの けんに ありますか？", "correct": "いばらきけん", "choices": ["いばらきけん", "とちぎけん", "さいたまけん", "ちばけん"], "grade": 6},
    {"prompt": "にほんの にばんめに おおきい みずうみは？", "correct": "かすみがうら", "choices": ["かすみがうら", "びわこ", "いなわん", "さるまこ"], "grade": 6},
    {"prompt": "きたのあるぷすで いちばん たかい やまは？", "correct": "おばすだけ", "choices": ["おばすだけ", "ふじさん", "たてやま", "あさひやま"], "grade": 6},
    {"prompt": "しまねけんの ゆうめいな しめいは？", "correct": "いずもたいしゃ", "choices": ["いずもたいしゃ", "めいじじんぐう", "きよみずでら", "とうだいじ"], "grade": 6},
    {"prompt": "にほんで にばんめに おおきい としは？", "correct": "よこはま", "choices": ["よこはま", "おおさか", "なごや", "さっぽろ"], "grade": 6},
    {"prompt": "にほんで さんばんめに おおきい としは？", "correct": "おおさか", "choices": ["おおさか", "よこはま", "なごや", "きょうと"], "grade": 6},
    {"prompt": "にほんで よんばんめに おおきい としは？", "correct": "なごや", "choices": ["なごや", "よこはま", "おおさか", "ふくおか"], "grade": 6},
    {"prompt": "にほんの いちばん ながい てつろは？", "correct": "かましりてつどう", "choices": ["かましりてつどう", "とうほくしんかんせん", "とうかいどう", "さんようどう"], "grade": 6, "context": "ほっかいどうに あります。"},
    {"prompt": "にほんの いちばん おおきい だいがくは？", "correct": "にほんだいがく", "choices": ["にほんだいがく", "きょうとだいがく", "とうきょうだいがく", "おおさかだいがく"], "grade": 6},
    {"prompt": "にほんの いちばん おおきい じんじゃは どこに ありますか？", "correct": "みえけん", "choices": ["みえけん", "きょうとふ", "とうきょうと", "ならけん"], "grade": 6, "context": "いせじんぐうが あります。"},
]


def main() -> None:
    rows = json.loads(OUT.read_text(encoding="utf-8"))
    by_prompt = {row["prompt"]: row for row in rows if row["prompt"] not in REMOVE_PROMPTS}
    for row in ADDITIONS:
        if row["prompt"] not in by_prompt:
            by_prompt[row["prompt"]] = row
    merged = list(by_prompt.values())
    for row in merged:
        assert row["correct"] in row["choices"], row["prompt"]
        assert len(row["choices"]) == 4
    counts = Counter(row["grade"] for row in merged)
    for grade in range(1, 7):
        if counts[grade] < MIN_PER_GRADE:
            raise SystemExit(f"grade {grade} has only {counts[grade]} questions (need {MIN_PER_GRADE})")
    merged.sort(key=lambda r: (r["grade"], r["prompt"]))
    OUT.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"chiri: {len(merged)} questions")
    print(dict(sorted(counts.items())))


if __name__ == "__main__":
    main()
