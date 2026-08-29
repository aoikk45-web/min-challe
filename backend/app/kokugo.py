from __future__ import annotations

import json
import random
import re
from pathlib import Path

from .kokugo_natural import is_natural_example

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


def _one(kind: str, step: int) -> tuple[str, str]:
    pool = _pool(kind, step)
    if not pool:
        pool = _kanji_bank() if kind == "かんじのよみ" else _jukugo_bank()
    return _prompt_context(random.choice(pool))


def pick_ten(kind: str, step: int = 1) -> list[tuple[str, str]]:
    step = min(max(step, 1), MAX_STEP)
    seen: set[str] = set()
    out: list[tuple[str, str]] = []

    for _ in range(300):
        if len(out) >= 10:
            break
        prompt, answer = _one(kind, step)
        if prompt in seen:
            continue
        seen.add(prompt)
        out.append((prompt, answer))

    while len(out) < 10:
        prompt, answer = _one(kind, step)
        out.append((prompt, answer))

    return out
