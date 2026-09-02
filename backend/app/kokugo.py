from __future__ import annotations

import json
import random
import re
from pathlib import Path

from .kokugo_natural import is_natural_example
from .shakai import GeneratedQuestion

MAX_STEP = 100
WORD_STEP_FROM = 40

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "kokugo"

_kanji_cache: list[dict] | None = None
_kanji_mtime: float = 0.0
_jukugo_cache: list[dict] | None = None
_jukugo_mtime: float = 0.0


def _load_bank(path: Path, cache_attr: str, mtime_attr: str) -> list[dict]:
    global _kanji_cache, _kanji_mtime, _jukugo_cache, _jukugo_mtime
    mtime = path.stat().st_mtime
    if path.name == "kanji.json":
        if _kanji_cache is None or mtime != _kanji_mtime:
            _kanji_cache = json.loads(path.read_text(encoding="utf-8"))
            _kanji_mtime = mtime
        return _kanji_cache
    if _jukugo_cache is None or mtime != _jukugo_mtime:
        _jukugo_cache = json.loads(path.read_text(encoding="utf-8"))
        _jukugo_mtime = mtime
    return _jukugo_cache


def _kanji_bank() -> list[dict]:
    return _load_bank(DATA_DIR / "kanji.json", "kanji", "kanji_mtime")


def _jukugo_bank() -> list[dict]:
    return _load_bank(DATA_DIR / "jukugo.json", "jukugo", "jukugo_mtime")


def _max_grade_for_step(step: int) -> int:
    s = min(max(step, 1), MAX_STEP) - 1
    return min(6, s // 17 + 1)


def _pool(kind: str, step: int) -> list[dict]:
    max_grade = _max_grade_for_step(step)
    bank = _kanji_bank() if kind == "かんじのよみ" else _jukugo_bank()
    return [row for row in bank if row["grade"] <= max_grade]


def _target(entry: dict) -> str:
    return entry.get("char") or entry["word"]


def _plain_sentence(sentence: str) -> str:
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", sentence)


def _is_valid_example(target: str, sentence: str) -> bool:
    return is_natural_example(target, sentence)


def _reading_for_entry(entry: dict, sentence: str) -> str:
    examples = entry.get("examples") or []
    for ex in examples:
        if ex["sentence"] == sentence:
            return ex["reading"]
    if "readings" in entry:
        return entry["readings"][0]
    return entry["reading"]


def _pick_example(entry: dict) -> tuple[str, str]:
    examples = entry.get("examples") or []
    target = _target(entry)
    valid = [ex for ex in examples if _is_valid_example(target, ex["sentence"])]
    if valid:
        picked = random.choice(valid)
        return picked["sentence"], picked["reading"]
    reading = entry["readings"][0] if "readings" in entry else entry["reading"]
    sentence = random.choice(entry.get("sentences") or [f"**{_target(entry)}**"])
    return sentence, reading


def _prompt_context(entry: dict) -> tuple[str, str]:
    target = _target(entry)
    sentence, reading = _pick_example(entry)
    display = sentence.replace(f"**{target}**", target)
    return f"{display}\n「{target}」の よみは？", reading


def _reading_pool(kind: str, step: int) -> list[str]:
    pool = _pool(kind, step)
    if not pool:
        pool = _kanji_bank() if kind == "かんじのよみ" else _jukugo_bank()
    readings: set[str] = set()
    for entry in pool:
        for ex in entry.get("examples") or []:
            readings.add(ex["reading"])
        if "readings" in entry:
            readings.update(entry["readings"])
        elif "reading" in entry:
            readings.add(entry["reading"])
    return sorted(readings)


def _shuffle_reading_choices(correct: str, pool: list[str]) -> list[str]:
    wrong = [item for item in pool if item != correct]
    picks = random.sample(wrong, min(3, len(wrong)))
    while len(picks) < 3 and wrong:
        extra = random.choice(wrong)
        if extra not in picks:
            picks.append(extra)
    options = picks + [correct]
    random.shuffle(options)
    return options


def _one(kind: str, step: int) -> GeneratedQuestion:
    pool = _pool(kind, step)
    if not pool:
        pool = _kanji_bank() if kind == "かんじのよみ" else _jukugo_bank()
    entry = random.choice(pool)
    prompt, answer = _prompt_context(entry)
    choice_pool = _reading_pool(kind, step)
    choices = _shuffle_reading_choices(answer, choice_pool)
    return GeneratedQuestion(prompt=prompt, correct=answer, choices=choices)


def pick_ten(kind: str, step: int = 1) -> list[GeneratedQuestion]:
    step = min(max(step, 1), MAX_STEP)
    seen: set[str] = set()
    out: list[GeneratedQuestion] = []

    for _ in range(300):
        if len(out) >= 10:
            break
        question = _one(kind, step)
        if question.prompt in seen:
            continue
        seen.add(question.prompt)
        out.append(question)

    while len(out) < 10:
        out.append(_one(kind, step))

    return out
