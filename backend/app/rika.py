from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

RIKA_KINDS = (
    "いきもののせいかつ",
    "じしゃくとでんき",
    "たいようとかげ",
    "ひかりとおと",
    "てんきとみず",
)
RIKA_MAX_STEP = 6

RIKA_STAGE_LABELS: tuple[str, ...] = (
    "ゆうきのいま",
    "3年生のふつう",
    "4年生の範囲",
    "5年生の範囲",
    "6年生のふつう",
    "6年生のチャレンジ",
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "rika"

_KIND_FILES: dict[str, str] = {
    "いきもののせいかつ": "ikimono.json",
    "じしゃくとでんき": "denki.json",
    "たいようとかげ": "taiyo.json",
    "ひかりとおと": "hikari.json",
    "てんきとみず": "tenki.json",
}

_bank_cache: dict[str, list[dict]] = {}
_bank_mtime: dict[str, float] = {}


@dataclass
class GeneratedQuestion:
    prompt: str
    correct: str
    choices: list[str] | None = None
    image_url: str | None = None

    def __iter__(self):
        yield self.prompt
        yield self.correct


def max_grade_for_step(step: int) -> int:
    step = min(max(step, 1), RIKA_MAX_STEP)
    if step <= 2:
        return 3
    if step == 3:
        return 4
    if step == 4:
        return 5
    return 6


def _load_bank(kind: str) -> list[dict]:
    filename = _KIND_FILES.get(kind)
    if filename is None:
        raise ValueError(f"unknown rika kind: {kind}")
    path = DATA_DIR / filename
    mtime = path.stat().st_mtime
    if kind not in _bank_cache or _bank_mtime.get(kind) != mtime:
        _bank_cache[kind] = json.loads(path.read_text(encoding="utf-8"))
        _bank_mtime[kind] = mtime
    return _bank_cache[kind]


def _image_url(image: str | None) -> str | None:
    if not image:
        return None
    if image.startswith("/"):
        return image
    return f"/rika/{image}"


def _pool(kind: str, step: int) -> list[dict]:
    max_grade = max_grade_for_step(step)
    return [row for row in _load_bank(kind) if int(row["grade"]) <= max_grade]


def _one(entry: dict) -> GeneratedQuestion:
    choices = list(entry["choices"])
    random.shuffle(choices)
    return GeneratedQuestion(
        prompt=str(entry["prompt"]),
        correct=str(entry["correct"]),
        choices=choices,
        image_url=_image_url(entry.get("image")),
    )


def pick_ten(kind: str, step: int = 1) -> list[GeneratedQuestion]:
    if kind not in RIKA_KINDS:
        raise ValueError(f"unknown rika kind: {kind}")
    step = min(max(step, 1), RIKA_MAX_STEP)
    pool = _pool(kind, step)
    if not pool:
        raise ValueError(f"no questions for {kind} at step {step}")

    seen: set[str] = set()
    out: list[GeneratedQuestion] = []
    shuffled = list(pool)
    random.shuffle(shuffled)
    for entry in shuffled:
        if len(out) >= 10:
            break
        key = str(entry["prompt"])
        if key in seen:
            continue
        seen.add(key)
        out.append(_one(entry))

    while len(out) < 10:
        entry = random.choice(pool)
        out.append(_one(entry))
    return out
