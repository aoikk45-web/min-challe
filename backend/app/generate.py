from __future__ import annotations

import random
import unicodedata

from .kokugo import pick_ten

MATH_KINDS = ("たしざん", "ひきざん", "かけざん", "わりざん")
KOKUGO_KINDS = ("かんじのよみ", "じゅくごのよみ")
KINDS = MATH_KINDS + KOKUGO_KINDS


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
    for _ in range(80):
        if len(out) >= 10:
            break
        prompt, answer = _one(kind, grade)
        if prompt in seen:
            continue
        seen.add(prompt)
        out.append((prompt, str(answer)))
    while len(out) < 10:
        prompt, answer = _one(kind, grade)
        out.append((prompt, str(answer)))
    return out


def _one(kind: str, grade: int) -> tuple[str, int]:
    if kind == "たしざん":
        return _add(grade)
    if kind == "ひきざん":
        return _sub(grade)
    if kind == "かけざん":
        return _mul(grade)
    return _div(grade)


def _span(grade: int) -> tuple[int, int]:
    if grade <= 1:
        return 1, 9
    if grade == 2:
        return 10, 99
    return 100, 999


def _add(grade: int) -> tuple[str, int]:
    lo, hi = _span(grade)
    a = random.randint(lo, hi)
    b = random.randint(lo, hi)
    if grade >= 4 and (a % 10) + (b % 10) < 10:
        b = b - (b % 10) + random.randint(10 - (a % 10), 9)
        if b > hi:
            b = hi
    return f"{a} + {b}", a + b


def _sub(grade: int) -> tuple[str, int]:
    lo, hi = _span(grade)
    a = random.randint(lo, hi)
    b = random.randint(lo, a)
    return f"{a} - {b}", a - b


def _mul(grade: int) -> tuple[str, int]:
    if grade <= 1:
        a, b = 2, random.randint(1, 9)
    elif grade == 2:
        a, b = random.randint(1, 9), random.randint(1, 9)
    elif grade == 3:
        a, b = random.randint(10, 99), random.randint(2, 9)
    else:
        a, b = random.randint(10, 99), random.randint(10, 99)
    return f"{a} × {b}", a * b


def _div(grade: int) -> tuple[str, int]:
    if grade <= 1:
        return _add(1)
    if grade == 2:
        b = random.randint(2, 9)
        q = random.randint(1, 9)
        return f"{b * q} ÷ {b}", q
    if grade == 3:
        b = random.randint(2, 9)
        q_lo = max(2, (10 + b - 1) // b)
        q_hi = 99 // b
        q = random.randint(q_lo, q_hi)
        return f"{b * q} ÷ {b}", q
    b = random.randint(2, 9)
    q_lo = max(12, (100 + b - 1) // b)
    q_hi = 999 // b
    q = random.randint(q_lo, q_hi)
    return f"{b * q} ÷ {b}", q
