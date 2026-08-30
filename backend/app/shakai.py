from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from .shakai_regions import REGIONS, codes_for_kenkatachi

MAX_STEP = 6
WORD_STEP_FROM = 5

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "shakai"

PREFECTURES: tuple[dict[str, str | int], ...] = (
    {"code": "hokkaido", "name": "ほっかいどう", "capital": "さっぽろ", "grade": 4},
    {"code": "aomori", "name": "あおもりけん", "capital": "あおもり", "grade": 4},
    {"code": "iwate", "name": "いわてけん", "capital": "もりおか", "grade": 4},
    {"code": "miyagi", "name": "みやぎけん", "capital": "せんだい", "grade": 4},
    {"code": "akita", "name": "あきたけん", "capital": "あきた", "grade": 5},
    {"code": "yamagata", "name": "やまがたけん", "capital": "やまがた", "grade": 5},
    {"code": "fukushima", "name": "ふくしまけん", "capital": "ふくしま", "grade": 4},
    {"code": "ibaraki", "name": "いばらきけん", "capital": "みと", "grade": 5},
    {"code": "tochigi", "name": "とちぎけん", "capital": "うつのみや", "grade": 5},
    {"code": "gunma", "name": "ぐんまけん", "capital": "まえばし", "grade": 5},
    {"code": "saitama", "name": "さいたまけん", "capital": "さいたま", "grade": 4},
    {"code": "chiba", "name": "ちばけん", "capital": "ちば", "grade": 4},
    {"code": "tokyo", "name": "とうきょうと", "capital": "しんじゅく", "grade": 3},
    {"code": "kanagawa", "name": "かながわけん", "capital": "よこはま", "grade": 4},
    {"code": "niigata", "name": "にいがたけん", "capital": "にいがた", "grade": 4},
    {"code": "toyama", "name": "とやまけん", "capital": "とやま", "grade": 5},
    {"code": "ishikawa", "name": "いしかわけん", "capital": "かなざわ", "grade": 5},
    {"code": "fukui", "name": "ふくいけん", "capital": "ふくい", "grade": 5},
    {"code": "yamanashi", "name": "やまなしけん", "capital": "こうふ", "grade": 5},
    {"code": "nagano", "name": "ながのけん", "capital": "ながの", "grade": 4},
    {"code": "gifu", "name": "ぎふけん", "capital": "ぎふ", "grade": 5},
    {"code": "shizuoka", "name": "しずおかけん", "capital": "しずおか", "grade": 3},
    {"code": "aichi", "name": "あいちけん", "capital": "なごや", "grade": 4},
    {"code": "mie", "name": "みえけん", "capital": "つ", "grade": 5},
    {"code": "shiga", "name": "しがけん", "capital": "おつ", "grade": 5},
    {"code": "kyoto", "name": "きょうとふ", "capital": "きょうと", "grade": 3},
    {"code": "osaka", "name": "おおさかふ", "capital": "おおさか", "grade": 3},
    {"code": "hyogo", "name": "ひょうごけん", "capital": "こうべ", "grade": 4},
    {"code": "nara", "name": "ならけん", "capital": "なら", "grade": 4},
    {"code": "wakayama", "name": "わかやまけん", "capital": "わかやま", "grade": 5},
    {"code": "tottori", "name": "とっとりけん", "capital": "とっとり", "grade": 5},
    {"code": "shimane", "name": "しまねけん", "capital": "まつえ", "grade": 5},
    {"code": "okayama", "name": "おかやまけん", "capital": "おかやま", "grade": 5},
    {"code": "hiroshima", "name": "ひろしまけん", "capital": "ひろしま", "grade": 4},
    {"code": "yamaguchi", "name": "やまぐちけん", "capital": "やまぐち", "grade": 5},
    {"code": "tokushima", "name": "とくしまけん", "capital": "とくしま", "grade": 5},
    {"code": "kagawa", "name": "かがわけん", "capital": "たかまつ", "grade": 5},
    {"code": "ehime", "name": "えひめけん", "capital": "まつやま", "grade": 5},
    {"code": "kochi", "name": "こうちけん", "capital": "こうち", "grade": 5},
    {"code": "fukuoka", "name": "ふくおかけん", "capital": "ふくおか", "grade": 4},
    {"code": "saga", "name": "さがけん", "capital": "さが", "grade": 5},
    {"code": "nagasaki", "name": "ながさきけん", "capital": "ながさき", "grade": 5},
    {"code": "kumamoto", "name": "くまもとけん", "capital": "くまもと", "grade": 5},
    {"code": "oita", "name": "おおいたけん", "capital": "おおいた", "grade": 5},
    {"code": "miyazaki", "name": "みやざきけん", "capital": "みやざき", "grade": 5},
    {"code": "kagoshima", "name": "かごしまけん", "capital": "かごしま", "grade": 5},
    {"code": "okinawa", "name": "おきなわけん", "capital": "なは", "grade": 4},
)

_FALLBACK_SYMBOLS: tuple[dict[str, str | int], ...] = (
    {"id": "school", "name": "がっこう", "grade": 1},
    {"id": "post", "name": "ゆうびんきょく", "grade": 2},
    {"id": "hospital", "name": "びょういん", "grade": 2},
    {"id": "police", "name": "けいさつしょ", "grade": 2},
    {"id": "shrine", "name": "じんじゃ", "grade": 3},
    {"id": "temple", "name": "じいん", "grade": 3},
    {"id": "fire_station", "name": "しょうぼうしょ", "grade": 2},
    {"id": "sightseeing", "name": "かんこうじょ", "grade": 3},
    {"id": "station", "name": "えき", "grade": 2},
    {"id": "library", "name": "としょかん", "grade": 3},
    {"id": "city_hall", "name": "しやくしょ", "grade": 4},
    {"id": "port", "name": "こうわん", "grade": 4},
)

_symbols_cache: tuple[dict[str, str | int], ...] | None = None
_symbols_mtime: float = 0.0


def _symbols() -> tuple[dict[str, str | int], ...]:
    global _symbols_cache, _symbols_mtime
    path = DATA_DIR / "symbols.json"
    if not path.exists():
        return _FALLBACK_SYMBOLS
    mtime = path.stat().st_mtime
    if _symbols_cache is None or mtime != _symbols_mtime:
        _symbols_cache = tuple(json.loads(path.read_text(encoding="utf-8")))
        _symbols_mtime = mtime
    return _symbols_cache

CAPITAL_CONTEXTS: tuple[str, ...] = (
    "くにの りょうどいっぱい は どうちょうしょ がある まちです。",
    "けんの ちゅうしんちに ある まちです。",
    "たくさんの ひとが すんでいる まちです。",
)


@dataclass
class GeneratedQuestion:
    prompt: str
    correct: str
    choices: list[str] | None = None
    image_url: str | None = None

    def __iter__(self):
        yield self.prompt
        yield self.correct


def _max_grade_for_step(step: int) -> int:
    return min(max(step, 1), MAX_STEP)


_chiri_cache: list[dict] | None = None
_chiri_mtime: float = 0.0


def _chiri_bank() -> list[dict]:
    global _chiri_cache, _chiri_mtime
    path = DATA_DIR / "chiri.json"
    mtime = path.stat().st_mtime
    if _chiri_cache is None or mtime != _chiri_mtime:
        _chiri_cache = json.loads(path.read_text(encoding="utf-8"))
        _chiri_mtime = mtime
    return _chiri_cache


def _shuffle_choices(correct: str, pool: list[str]) -> list[str]:
    wrong = [item for item in pool if item != correct]
    picks = random.sample(wrong, min(3, len(wrong)))
    while len(picks) < 3 and wrong:
        extra = random.choice(wrong)
        if extra not in picks:
            picks.append(extra)
    options = picks + [correct]
    random.shuffle(options)
    return options


def _pref_pool(step: int) -> list[dict]:
    max_grade = _max_grade_for_step(step)
    return [row for row in PREFECTURES if int(row["grade"]) <= max_grade]


def _symbol_pool(step: int) -> list[dict]:
    max_grade = _max_grade_for_step(step)
    return [row for row in _symbols() if int(row["grade"]) <= max_grade]


def _symbol_choice_pool(step: int) -> list[str]:
    pool = _symbol_pool(step)
    if len(pool) >= 4:
        return [str(row["name"]) for row in pool]
    max_grade = _max_grade_for_step(step)
    names = [str(row["name"]) for row in _symbols() if int(row["grade"]) <= max_grade]
    if len(names) >= 4:
        return names
    return [str(row["name"]) for row in _symbols()]


def _chiri_pool(step: int) -> list[dict]:
    max_grade = _max_grade_for_step(step)
    return [row for row in _chiri_bank() if row["grade"] <= max_grade]


def _one_todofuken(step: int, *, with_context: bool) -> GeneratedQuestion:
    pool = _pref_pool(step) or list(PREFECTURES)
    pref = random.choice(pool)
    name = str(pref["name"])
    capital = str(pref["capital"])
    capitals = [str(row["capital"]) for row in PREFECTURES]
    prompt = f"{name}の けんちょうしょざいちは？"
    if with_context:
        prompt = f"{random.choice(CAPITAL_CONTEXTS)}\n{prompt}"
    return GeneratedQuestion(
        prompt=prompt,
        correct=capital,
        choices=_shuffle_choices(capital, capitals),
    )


def _one_chiri(step: int, *, with_context: bool) -> GeneratedQuestion:
    pool = _chiri_pool(step) or _chiri_bank()
    entry = random.choice(pool)
    prompt = entry["prompt"]
    if with_context and entry.get("context"):
        prompt = f"{entry['context']}\n{prompt}"
    choices = list(entry["choices"])
    random.shuffle(choices)
    return GeneratedQuestion(prompt=prompt, correct=entry["correct"], choices=choices)


def _one_chizukigo(step: int, *, symbol: dict | None = None) -> GeneratedQuestion:
    pool = _symbol_pool(step) or list(_symbols())
    picked = symbol or random.choice(pool)
    name = str(picked["name"])
    return GeneratedQuestion(
        prompt="この きごうは なに？",
        correct=name,
        choices=_shuffle_choices(name, _symbol_choice_pool(step)),
        image_url=f"/shakai/symbols/{picked['id']}.png",
    )


def pick_ten_chizukigo(step: int = 1) -> list[GeneratedQuestion]:
    """Pick 10 distinct symbols available at the current step."""
    step = min(max(step, 1), MAX_STEP)
    symbols = list(_symbols())
    pool = list(_symbol_pool(step))
    seen_ids = {row["id"] for row in pool}
    max_grade = _max_grade_for_step(step)
    for grade in range(1, max_grade + 1):
        for row in symbols:
            if len(pool) >= 10:
                break
            if int(row["grade"]) <= grade and row["id"] not in seen_ids:
                pool.append(row)
                seen_ids.add(row["id"])
        if len(pool) >= 10:
            break
    if len(pool) < 10:
        for row in symbols:
            if len(pool) >= 10:
                break
            if row["id"] not in seen_ids:
                pool.append(row)
                seen_ids.add(row["id"])
    random.shuffle(pool)
    chosen = pool[:10]
    return [_one_chizukigo(step, symbol=row) for row in chosen]


def _kenkatachi_choices(code: str, correct: str) -> list[str]:
    region_codes = set(codes_for_kenkatachi(code))
    region_names = [str(row["name"]) for row in PREFECTURES if str(row["code"]) in region_codes]
    if code == "okinawa":
        kyushu_names = [
            str(row["name"])
            for row in PREFECTURES
            if str(row["code"]) in REGIONS["kyushu"] and str(row["code"]) != "okinawa"
        ]
        wrong = random.sample(kyushu_names, 3)
        options = wrong + [correct]
        random.shuffle(options)
        return options
    return _shuffle_choices(correct, region_names)


def _one_kenkatachi(step: int, *, with_context: bool) -> GeneratedQuestion:
    pool = _pref_pool(step) or list(PREFECTURES)
    pref = random.choice(pool)
    name = str(pref["name"])
    code = str(pref["code"])
    prompt = "いろが ついた とちは どの けん？"
    if with_context:
        prompt = f"この ちいきの ちずで みどりに なっている ばしょです。\n{prompt}"
    return GeneratedQuestion(
        prompt=prompt,
        correct=name,
        choices=_kenkatachi_choices(code, name),
        image_url=f"/shakai/maps/{code}.svg",
    )


def _one(kind: str, step: int, *, with_context: bool) -> GeneratedQuestion:
    if kind == "とどうふけん":
        return _one_todofuken(step, with_context=with_context)
    if kind == "にほんのちり":
        return _one_chiri(step, with_context=with_context)
    if kind == "ちずきごう":
        return _one_chizukigo(step)
    if kind == "けんのかたち":
        return _one_kenkatachi(step, with_context=with_context)
    raise ValueError(f"unknown shakai kind: {kind}")


def pick_ten(kind: str, step: int = 1) -> list[GeneratedQuestion]:
    if kind == "ちずきごう":
        return pick_ten_chizukigo(step)
    step = min(max(step, 1), MAX_STEP)
    seen: set[str] = set()
    out: list[GeneratedQuestion] = []
    use_context = step >= WORD_STEP_FROM

    def fill(target: int, with_context: bool) -> None:
        for _ in range(200):
            if len(out) >= target:
                return
            question = _one(kind, step, with_context=with_context)
            key = f"{question.prompt}|{question.image_url or ''}"
            if key in seen:
                continue
            seen.add(key)
            out.append(question)
        while len(out) < target:
            out.append(_one(kind, step, with_context=with_context))

    if use_context and kind != "ちずきごう":
        fill(8, with_context=False)
        fill(10, with_context=True)
    else:
        fill(10, with_context=False)
    return out
