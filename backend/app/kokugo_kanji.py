"""Grade lookup and furigana annotation for kokugo reading drills."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import pykakasi

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "kokugo"
MAX_GRADE_DEFAULT = 3
_FW_FURIGANA_RE = re.compile(r"([^（\s]+)（([^）]+)）")
_HW_FURIGANA_RE = re.compile(r"([一-龥]+)\(([^)]+)\)")
_HIPPARI_BAD_RE = re.compile(r"引っ張\(ぱ\)")
_HIPPARI_PLAIN_RE = re.compile(r"引っ張(?!\()")
_KATAZUKE_NORMALIZE_RE = re.compile(r"片づ(?!く)")
_kakasi = pykakasi.kakasi()

# pykakasi misreads とこ for floor; elementary stories use ゆか.
WORD_READING_OVERRIDES: dict[str, str] = {
    "床": "ゆか",
    # pykakasi reads 引っ張る as ひっぱつ; override for grade-3 stories.
    "引っ張る": "ひっぱる",
    "引っ張って": "ひっぱって",
    "引っ張った": "ひっぱった",
    "引っ張り": "ひっぱり",
}

# 熟語として読みを明示する語（低学年漢字を含むものも対象）
COMPOUND_READINGS: dict[str, str] = {
    "絵本": "えほん",
    "一緒": "いっしょ",
    "体験": "たいけん",
    "何度": "なんど",
}

# バンク未収録でも、小学1〜2年生の常用漢字にはルビを付けない。
KYOUIKU_GRADE_1_2 = frozenset(
    "一右雨円王音下火花貝学気九休玉金空月犬見五口校左三山子四糸字耳七車手十出女小上森人水正生青夕石赤千川先早草足村大棚男竹中虫町天田土二日入年白八百文木本名目立力林六引"
    "羽雲園遠何科夏家歌画回会海絵外角楽活間丸岩顔汽記帰弓牛魚京強教近兄形計元言原戸古午後語工公広交光考行高黄合谷国黒今才細作算止市矢姉思紙寺自時室社弱首秋週春書少場色食心新親図数西声星晴切雪船線前組走多太体台地池知茶昼長鳥朝直通弟店点電刀冬当東答頭同道読内南肉馬番必父風分聞米歩母方北毎妹万明役野友用曜洋里理留立旅竜面"
)

# 3年生が読む想定の漢字（バンク未収録分）
KYOUIKU_GRADE_3_SUPPLEMENT = frozenset("部屋平")


@lru_cache(maxsize=1)
def _kanji_rows() -> tuple[dict, ...]:
    return tuple(json.loads((DATA_DIR / "kanji.json").read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def _jukugo_rows() -> tuple[dict, ...]:
    path = DATA_DIR / "jukugo.json"
    if not path.exists():
        return ()
    return tuple(json.loads(path.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def kanji_grade_map() -> dict[str, int]:
    return {row["char"]: int(row["grade"]) for row in _kanji_rows()}


@lru_cache(maxsize=1)
def kanji_reading_options() -> dict[str, tuple[str, ...]]:
    out: dict[str, tuple[str, ...]] = {}
    for row in _kanji_rows():
        readings = tuple(str(item) for item in (row.get("readings") or []) if item)
        if readings:
            out[row["char"]] = readings
    return out


_DAKUTEN_PAIRS = {
    "か": "が",
    "き": "ぎ",
    "く": "ぐ",
    "け": "げ",
    "こ": "ご",
    "さ": "ざ",
    "し": "じ",
    "す": "ず",
    "せ": "ぜ",
    "そ": "ぞ",
    "た": "だ",
    "ち": "ぢ",
    "つ": "づ",
    "て": "で",
    "と": "ど",
    "は": "ば",
    "ひ": "び",
    "ふ": "ぶ",
    "へ": "べ",
    "ほ": "ぼ",
}


def _with_dakuten_variants(readings: tuple[str, ...]) -> tuple[str, ...]:
    out = list(readings)
    for reading in readings:
        if not reading:
            continue
        voiced = _DAKUTEN_PAIRS.get(reading[0])
        if voiced:
            alt = voiced + reading[1:]
            if alt not in out:
                out.append(alt)
    return tuple(out)


@lru_cache(maxsize=2048)
def readings_for_char(ch: str) -> tuple[str, ...]:
    options = list(kanji_reading_options().get(ch, ()))
    for item in _kakasi.convert(ch):
        hira = item.get("hira") or ""
        if hira and all(_is_kana(c) or c in "ーっゃゅょぁぃぅぇぉ" for c in hira):
            if hira not in options:
                options.append(hira)
    return _with_dakuten_variants(tuple(options))


@lru_cache(maxsize=1)
def jukugo_reading_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for row in _jukugo_rows():
        word = str(row["word"])
        reading = str(row["reading"])
        out[word] = reading
    for word, reading in WORD_READING_OVERRIDES.items():
        out[word] = reading
    for word, reading in COMPOUND_READINGS.items():
        out[word] = reading
    return out


def _is_kanji(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff"


def _is_kana(ch: str) -> bool:
    return "\u3040" <= ch <= "\u309f" or ch in "ーっゃゅょぁぃぅぇぉ"


def kanji_grade(ch: str) -> int | None:
    return kanji_grade_map().get(ch)


@lru_cache(maxsize=1)
def grade_1_3_chars() -> frozenset[str]:
    return frozenset(ch for ch, grade in kanji_grade_map().items() if grade <= MAX_GRADE_DEFAULT)


@lru_cache(maxsize=1)
def skip_furigana_chars() -> frozenset[str]:
    return grade_1_3_chars() | KYOUIKU_GRADE_1_2 | KYOUIKU_GRADE_3_SUPPLEMENT


def needs_furigana(ch: str, *, max_grade: int = MAX_GRADE_DEFAULT) -> bool:
    if ch in skip_furigana_chars():
        return False
    grade = kanji_grade(ch)
    if grade is not None:
        return grade > max_grade
    return True


def strip_furigana(text: str) -> str:
    """Remove 片(かた) / 洗濯物(せんたくもの) / 昆虫（こんちゅう） style annotations."""
    if not text:
        return text
    plain = _FW_FURIGANA_RE.sub(r"\1", text)
    return _HW_FURIGANA_RE.sub(r"\1", plain)


def _is_pure_kanji_compound(surface: str) -> bool:
    if len(surface) < 2:
        return False
    return all(_is_kanji(ch) for ch in surface)


def _compound_needs_annotation(surface: str, *, max_grade: int = MAX_GRADE_DEFAULT) -> bool:
    if not _is_pure_kanji_compound(surface):
        return False
    if surface in COMPOUND_READINGS:
        return True
    return any(needs_furigana(ch, max_grade=max_grade) for ch in surface)


def _normalize_for_kakasi(text: str) -> str:
    return _KATAZUKE_NORMALIZE_RE.sub("片付", text)


def _split_yomi(word: str, yomi: str, index: int) -> str | None:
    n = len(word)
    if index < 0 or index >= n:
        return None
    if n == 1:
        return yomi
    if len(yomi) % n == 0:
        size = len(yomi) // n
        return yomi[index * size : (index + 1) * size]
    moras: list[str] = []
    i = 0
    while i < len(yomi):
        if i + 1 < len(yomi) and yomi[i + 1] in "ゃゅょぁぃぅぇぉ":
            moras.append(yomi[i : i + 2])
            i += 2
        elif yomi[i] == "っ" and i + 1 < len(yomi):
            moras.append(yomi[i : i + 2])
            i += 2
        else:
            moras.append(yomi[i])
            i += 1
    if len(moras) < n:
        return None
    base, extra = divmod(len(moras), n)
    pos = 0
    for j in range(n):
        take = base + (1 if j < extra else 0)
        if j == index:
            return "".join(moras[pos : pos + take])
        pos += take
    return None


def _split_word_readings(word: str, yomi: str) -> list[str] | None:
    kanji_chars = [ch for ch in word if _is_kanji(ch)]
    if not kanji_chars:
        return None
    per_char = [list(readings_for_char(ch)) for ch in kanji_chars]
    if not all(per_char):
        return None

    def search(i: int, pos: int) -> list[str] | None:
        if i == len(kanji_chars):
            return [] if pos == len(yomi) else None
        for reading in per_char[i]:
            if yomi.startswith(reading, pos):
                rest = search(i + 1, pos + len(reading))
                if rest is not None:
                    return [reading] + rest
        return None

    return search(0, 0)


def _to_moras(text: str) -> list[str]:
    moras: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "っ":
            moras.append("っ")
            i += 1
        elif i + 1 < len(text) and text[i + 1] in "ゃゅょぁぃぅぇぉ":
            moras.append(text[i : i + 2])
            i += 2
        else:
            moras.append(text[i])
            i += 1
    return moras


def _mora_compositions(total: int, parts: int) -> list[tuple[int, ...]]:
    if parts == 1:
        return [(total,)] if total > 0 else []
    out: list[tuple[int, ...]] = []
    for first in range(1, total - parts + 2):
        for rest in _mora_compositions(total - first, parts - 1):
            out.append((first, *rest))
    return out


def _score_kanji_parts(chars: list[str], parts: list[str]) -> int:
    score = 0
    for ch, part in zip(chars, parts):
        if part in readings_for_char(ch):
            score += 3
        if part.startswith("っ") and len(part) > 1:
            score -= 5
        if part.startswith("ん") and len(part) > 1:
            score -= 2
    return score


def _split_by_mora_groups(word: str, yomi: str) -> list[str] | None:
    kanji_chars = [ch for ch in word if _is_kanji(ch)]
    kanji_count = len(kanji_chars)
    if kanji_count <= 0:
        return None
    if kanji_count == 1:
        return [yomi]
    moras = _to_moras(yomi)
    if len(moras) < kanji_count:
        return None
    best: list[str] | None = None
    best_score = -999
    for comp in _mora_compositions(len(moras), kanji_count):
        parts: list[str] = []
        pos = 0
        for size in comp:
            parts.append("".join(moras[pos : pos + size]))
            pos += size
        if "".join(parts) != yomi:
            continue
        score = _score_kanji_parts(kanji_chars, parts)
        if score > best_score:
            best_score = score
            best = parts
    return best


def _split_reading_across_kanji(word: str, yomi: str) -> list[str] | None:
    kanji_indices = [i for i, ch in enumerate(word) if _is_kanji(ch)]
    if not kanji_indices:
        return None
    kanji_word = "".join(word[i] for i in kanji_indices)
    mora_parts = _split_by_mora_groups(kanji_word, yomi)
    if mora_parts and len(mora_parts) == len(kanji_indices):
        return mora_parts
    parts = _split_word_readings(kanji_word, yomi)
    if parts and len(parts) == len(kanji_indices):
        return parts
    if len(kanji_indices) == 1:
        return [yomi]
    return None


def _kanji_readings_pure_kanji(surface: str, reading: str) -> dict[int, str]:
    kanji_indices = [i for i, ch in enumerate(surface) if _is_kanji(ch)]
    if not kanji_indices:
        return {}
    kanji_word = "".join(surface[i] for i in kanji_indices)
    parts = _split_reading_across_kanji(kanji_word, reading)
    if not parts:
        if len(kanji_indices) == 1:
            parts = [reading]
        else:
            return {}
    out: dict[int, str] = {}
    for idx, part in zip(kanji_indices, parts):
        out[idx] = part
    return out


def _kanji_readings_okurigana_aware(surface: str, reading: str) -> dict[int, str]:
    """Assign readings per kanji, peeling okurigana from the following kana."""
    out: dict[int, str] = {}
    ri = 0
    i = 0
    while i < len(surface):
        ch = surface[i]
        if not _is_kanji(ch):
            if ri < len(reading) and reading[ri] == ch:
                ri += 1
            i += 1
            continue

        kanji_indices: list[int] = []
        while i < len(surface) and _is_kanji(surface[i]):
            kanji_indices.append(i)
            i += 1

        okuri_start = i
        while i < len(surface) and _is_kana(surface[i]):
            i += 1
        okuri = surface[okuri_start:i]
        remaining = reading[ri:]
        if not remaining:
            break

        matched = False
        max_klen = len(remaining) - len(okuri) if okuri else len(remaining)
        for klen in range(max_klen, -1, -1):
            kanji_reading = remaining[:klen]
            rest = remaining[klen:]
            if okuri and not rest.startswith(okuri):
                continue
            if not okuri and klen != len(remaining):
                continue
            if len(kanji_indices) == 1:
                out[kanji_indices[0]] = kanji_reading
            else:
                kanji_word = "".join(surface[j] for j in kanji_indices)
                parts = _split_reading_across_kanji(kanji_word, kanji_reading)
                if not parts:
                    continue
                for idx, part in zip(kanji_indices, parts):
                    out[idx] = part
            ri += klen + len(okuri)
            matched = True
            break

        if not matched and kanji_indices and okuri:
            # fallback: longest prefix of remaining that leaves okuri at end
            if remaining.endswith(okuri) and len(remaining) > len(okuri):
                kanji_reading = remaining[: -len(okuri)]
                if len(kanji_indices) == 1:
                    out[kanji_indices[0]] = kanji_reading
                    ri += len(kanji_reading) + len(okuri)
                else:
                    kanji_word = "".join(surface[j] for j in kanji_indices)
                    parts = _split_reading_across_kanji(kanji_word, kanji_reading)
                    if parts:
                        for idx, part in zip(kanji_indices, parts):
                            out[idx] = part
                        ri += len(kanji_reading) + len(okuri)

    return out


def _kanji_readings_for_word(surface: str, reading: str) -> dict[int, str]:
    """Map character index in surface -> hiragana reading for that kanji."""
    if not any(_is_kanji(ch) for ch in surface):
        return {}
    if any(_is_kana(ch) for ch in surface):
        return _kanji_readings_okurigana_aware(surface, reading)
    return _kanji_readings_pure_kanji(surface, reading)


def _longest_word_matches(text: str, word_map: dict[str, str]) -> list[tuple[int, int, str, str]]:
    if not word_map:
        return []
    words = sorted(word_map, key=len, reverse=True)
    spans: list[tuple[int, int, str, str]] = []
    used = [False] * len(text)
    for start in range(len(text)):
        if used[start]:
            continue
        for word in words:
            end = start + len(word)
            if end > len(text) or text[start:end] != word:
                continue
            if any(used[i] for i in range(start, end)):
                continue
            spans.append((start, end, word, word_map[word]))
            for i in range(start, end):
                used[i] = True
            break
    return spans


def _apply_word_span(
    text: str,
    start: int,
    end: int,
    surface: str,
    reading: str,
    compounds: list[tuple[int, int, str]],
    readings: dict[int, str],
    *,
    max_grade: int,
) -> None:
    if _compound_needs_annotation(surface, max_grade=max_grade):
        compounds.append((start, end, reading))
        return
    local = _kanji_readings_for_word(surface, reading)
    for local_i, yomi in local.items():
        readings[start + local_i] = yomi


def _contextual_kanji_readings(
    text: str,
    *,
    max_grade: int = MAX_GRADE_DEFAULT,
) -> tuple[list[tuple[int, int, str]], dict[int, str]]:
    plain = strip_furigana(text)
    compounds: list[tuple[int, int, str]] = []
    readings: dict[int, str] = {}
    covered = [False] * len(plain)

    for start, end, surface, reading in _longest_word_matches(plain, jukugo_reading_map()):
        _apply_word_span(plain, start, end, surface, reading, compounds, readings, max_grade=max_grade)
        for i in range(start, end):
            covered[i] = True

    pos = 0
    while pos < len(plain):
        while pos < len(plain) and covered[pos]:
            pos += 1
        if pos >= len(plain):
            break
        gap_start = pos
        while pos < len(plain) and not covered[pos]:
            pos += 1
        gap = plain[gap_start:pos]
        kakasi_text = _normalize_for_kakasi(gap)
        offset = 0
        for item in _kakasi.convert(kakasi_text):
            orig = item["orig"]
            hira = item["hira"]
            if not orig:
                continue
            if kakasi_text[offset : offset + len(orig)] != orig:
                found = kakasi_text.find(orig, offset)
                if found < 0:
                    continue
                offset = found
            abs_start = gap_start + offset
            abs_end = abs_start + len(orig)
            if _compound_needs_annotation(orig, max_grade=max_grade):
                compounds.append((abs_start, abs_end, hira))
            else:
                local = _kanji_readings_for_word(orig, hira)
                for local_i, yomi in local.items():
                    readings[abs_start + local_i] = yomi
            offset += len(orig)

    return compounds, readings


def _normalize_hippari_furigana(text: str) -> str:
    """引 is grade-1 skip; annotate 張(はっぱ) in 引っ張〜."""
    text = _HIPPARI_BAD_RE.sub("引っ張(はっぱ)", text)
    return _HIPPARI_PLAIN_RE.sub("引っ張(はっぱ)", text)


def annotate_furigana(text: str, *, max_grade: int = MAX_GRADE_DEFAULT) -> str:
    """Add furigana: 準備(じゅんび) for compounds, 座(すわ)って for okurigana verbs."""
    if not text:
        return text
    plain = strip_furigana(text)
    compounds, char_readings = _contextual_kanji_readings(plain, max_grade=max_grade)
    compound_at: dict[int, tuple[int, str]] = {start: (end, reading) for start, end, reading in compounds}
    out: list[str] = []
    i = 0
    while i < len(plain):
        if i in compound_at:
            end, reading = compound_at[i]
            out.append(plain[i:end])
            out.append(f"({reading})")
            i = end
            continue
        ch = plain[i]
        if _is_kanji(ch) and needs_furigana(ch, max_grade=max_grade):
            reading = char_readings.get(i)
            if reading:
                out.append(f"{ch}({reading})")
                i += 1
                continue
        out.append(ch)
        i += 1
    return _normalize_hippari_furigana("".join(out))


def unannotated_high_grade_kanji(text: str, *, max_grade: int = MAX_GRADE_DEFAULT) -> list[str]:
    """Kanji that still need inline (よみ) after annotation."""
    missing: list[str] = []
    i = 0
    while i < len(text):
        if not _is_kanji(text[i]):
            i += 1
            continue
        start = i
        while i < len(text) and _is_kanji(text[i]):
            i += 1
        if i < len(text) and text[i] == "(":
            close = text.find(")", i + 1)
            i = (close + 1) if close >= 0 else i + 1
            continue
        for j in range(start, i):
            ch = text[j]
            if needs_furigana(ch, max_grade=max_grade):
                missing.append(ch)
    return missing
