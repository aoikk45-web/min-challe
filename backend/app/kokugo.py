from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path

MAX_STEP = 100
WORD_STEP_FROM = 40

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "kokugo"


@lru_cache(maxsize=1)
def _kanji_bank() -> list[dict]:
    return json.loads((DATA_DIR / "kanji.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _jukugo_bank() -> list[dict]:
    return json.loads((DATA_DIR / "jukugo.json").read_text(encoding="utf-8"))


def _max_grade_for_step(step: int) -> int:
    s = min(max(step, 1), MAX_STEP) - 1
    return min(6, s // 17 + 1)


def _pool(kind: str, step: int) -> list[dict]:
    max_grade = _max_grade_for_step(step)
    bank = _kanji_bank() if kind == "かんじのよみ" else _jukugo_bank()
    return [row for row in bank if row["grade"] <= max_grade]


def _reading_for(entry: dict) -> str:
    if "readings" in entry:
        return entry["readings"][0]
    return entry["reading"]


def _target(entry: dict) -> str:
    return entry.get("char") or entry["word"]


def _prompt_direct(entry: dict) -> tuple[str, str]:
    return _target(entry), _reading_for(entry)


def _prompt_sentence(entry: dict) -> tuple[str, str]:
    target = _target(entry)
    reading = _reading_for(entry)
    sentence = random.choice(entry["sentences"])
    display = sentence.replace(f"**{target}**", target)
    return f"{display}\n{target}の よみは？", reading


def _one(kind: str, step: int, *, sentence: bool) -> tuple[str, str]:
    pool = _pool(kind, step)
    if not pool:
        pool = _kanji_bank() if kind == "かんじのよみ" else _jukugo_bank()
    entry = random.choice(pool)
    if sentence and entry.get("sentences"):
        return _prompt_sentence(entry)
    return _prompt_direct(entry)


def pick_ten(kind: str, step: int = 1) -> list[tuple[str, str]]:
    step = min(max(step, 1), MAX_STEP)
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    use_sentences = step >= WORD_STEP_FROM

    def fill(target: int, sentence: bool) -> None:
        for _ in range(200):
            if len(out) >= target:
                return
            prompt, answer = _one(kind, step, sentence=sentence)
            if prompt in seen:
                continue
            seen.add(prompt)
            out.append((prompt, answer))
        while len(out) < target:
            prompt, answer = _one(kind, step, sentence=sentence)
            out.append((prompt, answer))

    if use_sentences:
        fill(8, sentence=False)
        fill(10, sentence=True)
    else:
        fill(10, sentence=False)
    return out
