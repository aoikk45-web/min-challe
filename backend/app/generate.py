from __future__ import annotations

import random
import unicodedata

from .kokugo import pick_ten

MATH_KINDS = ("たしざん", "ひきざん", "かけざん", "わりざん")
KOKUGO_KINDS = ("かんじのよみ", "じゅくごのよみ")
KINDS = MATH_KINDS + KOKUGO_KINDS

_WORD: dict[str, tuple[str, ...]] = {
    "たしざん": (
        "あめが {a}こ あります。{b}こ もらいました。ぜんぶで なんこ？",
        "バスに {a}人 のっています。{b}人 のりました。なん人？",
        "シールが {a}まい あります。{b}まい もらいました。ぜんぶで なんまい？",
    ),
    "ひきざん": (
        "シールが {a}まい あります。{b}まい つかいました。のこりは なんまい？",
        "あめが {a}こ あります。{b}こ たべました。のこりは なんこ？",
        "ほんが {a}さつ あります。{b}さつ かしました。のこりは なんさつ？",
    ),
    "かけざん": (
        "はこが {a}つ あります。ひとつに {b}こ はいっています。ぜんぶで なんこ？",
        "{a}人に {b}こずつ わたします。なんこ いります？",
        "れつが {a}つ あります。ひとつに {b}こです。ぜんぶで なんこ？",
    ),
    "わりざん": (
        "{a}こを {b}人で わけます。1人 なんこ？",
        "{a}まいの カードを {b}人で わけます。1人 なんまい？",
        "{a}こ を {b}はこに 同じ数ずつ いれます。1はこ なんこ？",
    ),
}


def normalize_reading(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).strip().replace(" ", "").replace("　", "")
    chars: list[str] = []
    for ch in text:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            chars.append(chr(code - 0x60))
        else:
            chars.append(ch)
    return "".join(chars)


def generate_ten(kind: str, grade: int) -> list[tuple[str, str]]:
    if kind not in KINDS:
        raise ValueError(f"unknown kind: {kind}")
    grade = min(max(grade, 1), 6)
    if kind in KOKUGO_KINDS:
        return pick_ten(kind)
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    _fill(out, seen, kind, grade, 8, word=False)
    _fill(out, seen, kind, grade, 10, word=True)
    return out


def _fill(
    out: list[tuple[str, str]],
    seen: set[str],
    kind: str,
    grade: int,
    target: int,
    *,
    word: bool,
) -> None:
    for _ in range(80):
        if len(out) >= target:
            return
        prompt, answer = _one(kind, grade, word=word)
        if prompt in seen:
            continue
        seen.add(prompt)
        out.append((prompt, str(answer)))
    while len(out) < target:
        prompt, answer = _one(kind, grade, word=word)
        out.append((prompt, str(answer)))


def _one(kind: str, grade: int, *, word: bool = False) -> tuple[str, int]:
    op, a, b, answer = _operands(kind, grade)
    if word:
        return random.choice(_WORD[op]).format(a=a, b=b), answer
    return _equation(op, a, b), answer


def _equation(op: str, a: int, b: int) -> str:
    if op == "たしざん":
        return f"{a} + {b}"
    if op == "ひきざん":
        return f"{a} - {b}"
    if op == "かけざん":
        return f"{a} × {b}"
    return f"{a} ÷ {b}"


def _operands(kind: str, grade: int) -> tuple[str, int, int, int]:
    if kind == "わりざん" and grade <= 1:
        a, b, answer = _add_nums(1)
        return "たしざん", a, b, answer
    if kind == "たしざん":
        a, b, answer = _add_nums(grade)
        return kind, a, b, answer
    if kind == "ひきざん":
        a, b, answer = _sub_nums(grade)
        return kind, a, b, answer
    if kind == "かけざん":
        a, b, answer = _mul_nums(grade)
        return kind, a, b, answer
    a, b, answer = _div_nums(grade)
    return kind, a, b, answer


def _span(grade: int) -> tuple[int, int]:
    if grade <= 1:
        return 1, 9
    if grade == 2:
        return 10, 99
    return 100, 999


def _add_nums(grade: int) -> tuple[int, int, int]:
    lo, hi = _span(grade)
    a = random.randint(lo, hi)
    b = random.randint(lo, hi)
    if grade >= 4 and (a % 10) + (b % 10) < 10:
        b = b - (b % 10) + random.randint(10 - (a % 10), 9)
        if b > hi:
            b = hi
    return a, b, a + b


def _sub_nums(grade: int) -> tuple[int, int, int]:
    lo, hi = _span(grade)
    a = random.randint(lo, hi)
    b = random.randint(lo, a)
    return a, b, a - b


def _mul_nums(grade: int) -> tuple[int, int, int]:
    if grade <= 1:
        a, b = 2, random.randint(1, 9)
    elif grade == 2:
        a, b = random.randint(1, 9), random.randint(1, 9)
    elif grade == 3:
        a, b = random.randint(10, 99), random.randint(2, 9)
    else:
        a, b = random.randint(10, 99), random.randint(10, 99)
    return a, b, a * b


def _div_nums(grade: int) -> tuple[int, int, int]:
    if grade == 2:
        b = random.randint(2, 9)
        q = random.randint(1, 9)
        return b * q, b, q
    if grade == 3:
        b = random.randint(2, 9)
        q_lo = max(2, (10 + b - 1) // b)
        q_hi = 99 // b
        q = random.randint(q_lo, q_hi)
        return b * q, b, q
    b = random.randint(2, 9)
    q_lo = max(12, (100 + b - 1) // b)
    q_hi = 999 // b
    q = random.randint(q_lo, q_hi)
    return b * q, b, q
