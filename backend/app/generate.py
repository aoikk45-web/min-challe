from __future__ import annotations

import random
import unicodedata

from .kokugo import pick_ten as kokugo_pick_ten
from .shakai import GeneratedQuestion, pick_ten as shakai_pick_ten

MATH_KINDS = ("たしざん", "ひきざん", "かけざん", "わりざん")
KOKUGO_KINDS = ("かんじのよみ", "じゅくごのよみ")
SHAKAI_KINDS = ("とどうふけん", "にほんのちり", "ちずきごう", "けんのかたち")
KINDS = MATH_KINDS + KOKUGO_KINDS + SHAKAI_KINDS
PROGRESS_KINDS = KINDS

MAX_STEP = 100
SHAKAI_MAX_STEP = 6
WORD_STEP_FROM = 40

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


def kokugo_reading_matches(given: str, correct: str) -> bool:
    from .kokugo_natural import JUKUGO_READING_ALTERNATES

    g = normalize_reading(given)
    c = normalize_reading(correct)
    if g == c:
        return True
    return g in JUKUGO_READING_ALTERNATES.get(c, set())


def _step_band(step: int) -> tuple[int, float]:
    s = min(max(step, 1), MAX_STEP) - 1
    grade = min(6, s // 17 + 1)
    sub = s % 17
    t = sub / 16.0
    return grade, t


def generate_ten(kind: str, step: int = 1) -> list[GeneratedQuestion]:
    if kind not in KINDS:
        raise ValueError(f"unknown kind: {kind}")
    if kind in KOKUGO_KINDS:
        return [GeneratedQuestion(prompt, correct) for prompt, correct in kokugo_pick_ten(kind, step)]
    if kind in SHAKAI_KINDS:
        return shakai_pick_ten(kind, step)
    step = min(max(step, 1), MAX_STEP)
    seen: set[str] = set()
    out: list[GeneratedQuestion] = []
    use_words = step >= WORD_STEP_FROM
    if use_words:
        _fill(out, seen, kind, step, 8, word=False)
        _fill(out, seen, kind, step, 10, word=True)
    else:
        _fill(out, seen, kind, step, 10, word=False)
    return out


def _fill(
    out: list[GeneratedQuestion],
    seen: set[str],
    kind: str,
    step: int,
    target: int,
    *,
    word: bool,
) -> None:
    for _ in range(120):
        if len(out) >= target:
            return
        prompt, answer = _one(kind, step, word=word)
        if prompt in seen:
            continue
        seen.add(prompt)
        out.append(GeneratedQuestion(prompt, str(answer)))
    while len(out) < target:
        prompt, answer = _one(kind, step, word=word)
        out.append(GeneratedQuestion(prompt, str(answer)))


def _one(kind: str, step: int, *, word: bool = False) -> tuple[str, int]:
    op, a, b, answer = _operands(kind, step)
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


def _operands(kind: str, step: int) -> tuple[str, int, int, int]:
    if kind == "わりざん" and step < 22:
        return _operands("たしざん", step)
    if kind == "かけざん" and step < 12:
        return _operands("たしざん", step)
    if kind == "たしざん":
        a, b, answer = _add_nums(step)
        return kind, a, b, answer
    if kind == "ひきざん":
        a, b, answer = _sub_nums(step)
        return kind, a, b, answer
    if kind == "かけざん":
        a, b, answer = _mul_nums(step)
        return kind, a, b, answer
    a, b, answer = _div_nums(step)
    return kind, a, b, answer


def _lerp_int(lo: int, hi: int, t: float) -> int:
    return int(round(lo + (hi - lo) * t))


def _add_nums(step: int) -> tuple[int, int, int]:
    grade, t = _step_band(step)
    if grade == 1:
        hi = _lerp_int(5, 9, t)
        a = random.randint(1, hi)
        b = random.randint(1, hi)
        return a, b, a + b
    lo, hi = _span(grade)
    if grade < 6:
        nlo, nhi = _span(grade + 1)
        hi = _lerp_int(hi, nhi, t)
    a = random.randint(lo, hi)
    b = random.randint(lo, hi)
    if grade >= 4 and (a % 10) + (b % 10) < 10:
        bump = random.randint(max(1, 10 - (a % 10)), 9)
        b = min(hi, b - (b % 10) + bump)
    return a, b, a + b


def _sub_nums(step: int) -> tuple[int, int, int]:
    grade, t = _step_band(step)
    if grade == 1:
        hi = _lerp_int(5, 9, t)
        a = random.randint(1, hi)
        b = random.randint(1, a)
        return a, b, a - b
    lo, hi = _span(grade)
    if grade < 6:
        nlo, nhi = _span(grade + 1)
        hi = _lerp_int(hi, nhi, t)
    a = random.randint(lo, hi)
    b = random.randint(lo, a)
    return a, b, a - b


def _mul_nums(step: int) -> tuple[int, int, int]:
    grade, t = _step_band(step)
    if grade == 1:
        b = _lerp_int(1, 9, t)
        return 2, b, 2 * b
    if grade == 2:
        a = _lerp_int(1, 9, t)
        b = random.randint(1, 9)
        return a, b, a * b
    if grade == 3:
        a = _lerp_int(10, 99, t)
        b = random.randint(2, 9)
        return a, b, a * b
    a = _lerp_int(10, 99, t)
    b = _lerp_int(10, 99, t)
    return a, b, a * b


def _div_nums(step: int) -> tuple[int, int, int]:
    grade, t = _step_band(step)
    if grade <= 2:
        b = random.randint(2, 9)
        q = _lerp_int(1, 9, t)
        return b * q, b, q
    if grade == 3:
        b = random.randint(2, 9)
        q_lo = max(2, (10 + b - 1) // b)
        q_hi = 99 // b
        q = _lerp_int(q_lo, q_hi, t)
        return b * q, b, q
    b = random.randint(2, 9)
    q_lo = max(12, (100 + b - 1) // b)
    q_hi = 999 // b
    q = _lerp_int(q_lo, q_hi, t)
    return b * q, b, q


def _span(grade: int) -> tuple[int, int]:
    if grade <= 1:
        return 1, 9
    if grade == 2:
        return 10, 99
    return 100, 999
