from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from .kokugo_kanji import annotate_furigana

MAX_STEP = 6
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "kokugo"

_bank_cache: list[dict] | None = None
_bank_mtime: float = 0.0


@dataclass
class DokkaiQuestion:
    prompt: str
    correct: str
    choices: list[str]
    explanation: str
    qtype: str


@dataclass
class DokkaiStory:
    story_id: str
    title: str
    passage: str
    questions: list[DokkaiQuestion]


def _bank() -> list[dict]:
    global _bank_cache, _bank_mtime
    path = DATA_DIR / "dokkai.json"
    if not path.exists():
        return []
    mtime = path.stat().st_mtime
    if _bank_cache is None or mtime != _bank_mtime:
        _bank_cache = json.loads(path.read_text(encoding="utf-8"))
        _bank_mtime = mtime
    return _bank_cache


def _story_pool(step: int) -> list[dict]:
    step = min(max(step, 1), MAX_STEP)
    rows = [row for row in _bank() if int(row["stage"]) <= step]
    if not rows:
        return []
    preferred = [row for row in rows if int(row["stage"]) == step]
    return preferred or rows


def _shuffle_choices(choices: list[str]) -> list[str]:
    out = list(choices)
    random.shuffle(out)
    return out


def _to_story(row: dict) -> DokkaiStory:
    questions = []
    for q in row["questions"]:
        correct = annotate_furigana(str(q["correct"]))
        choices = _shuffle_choices([annotate_furigana(str(c)) for c in q["choices"]])
        questions.append(
            DokkaiQuestion(
                prompt=annotate_furigana(str(q["prompt"])),
                correct=correct,
                choices=choices,
                explanation=annotate_furigana(str(q["explanation"])),
                qtype=str(q.get("type", "fact")),
            )
        )
    return DokkaiStory(
        story_id=str(row["id"]),
        title=annotate_furigana(str(row["title"])),
        passage=annotate_furigana(str(row["passage"])),
        questions=questions,
    )


def pick_story(step: int = 1) -> DokkaiStory:
    pool = _story_pool(step)
    if not pool:
        raise ValueError("dokkai bank empty")
    row = random.choice(pool)
    return _to_story(row)


def pick_three(step: int = 1) -> DokkaiStory:
    story = pick_story(step)
    if len(story.questions) != 3:
        raise ValueError(f"story {story.story_id} must have 3 questions")
    return story
