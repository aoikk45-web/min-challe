"""Fetch all GSI 2022 map symbols and build symbols.json + PNG assets."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

try:
    import httpx
except ImportError:
    httpx = None

ROOT = Path(__file__).resolve().parents[2]
OUT_SYMBOLS = ROOT / "frontend" / "public" / "shakai" / "symbols"
OUT_JSON = ROOT / "backend" / "data" / "shakai" / "symbols.json"
ITIRAN_URL = "https://www.gsi.go.jp/kohokocho/map-sign-tizukigou-2022-itiran.html"
GSI_BASE = "https://www.gsi.go.jp"
LABEL_CROP_FALLBACK_RATIO = 0.78
# 記号ごとの例外（全体ロジックではラベルが残る／記号が切れるものだけ）
SYMBOL_CROP_RATIO_OVERRIDES: dict[str, float] = {
    "ekitikatetu": 0.64,
    "toshokan": 0.75,
}


def _row_density(img) -> list[float]:
    rgba = img.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    return [
        sum(1 for x in range(w) if px[x, y][3] > 128 and sum(px[x, y][:3]) < 700) / w
        for y in range(h)
    ]


def _detect_label_crop_height(row_frac: list[float], h: int) -> int:
    """Keep the symbol graphic and remove only the bottom label band."""
    search_from = int(h * 0.42)
    quiet_thr = 0.026
    min_quiet = 14
    padding = 8

    runs: list[tuple[int, int, int]] = []
    y = h - 1
    while y >= search_from:
        if row_frac[y] < quiet_thr:
            end = y
            while y >= search_from and row_frac[y] < quiet_thr:
                y -= 1
            start = y + 1
            length = end - start + 1
            if length >= min_quiet:
                runs.append((start, end, length))
        y -= 1

    if not runs:
        return int(h * LABEL_CROP_FALLBACK_RATIO)

    bottom_zone = int(h * 0.62)
    candidates = [r for r in runs if r[1] >= bottom_zone] or runs
    candidates.sort(key=lambda r: (-r[2], r[0]))
    start, _end, _length = candidates[0]
    crop = min(h, start + padding)
    crop = min(crop, int(h * 0.82))
    return max(crop, int(h * 0.62))

# Easier symbols first (grade 1-2), specialized later (grade 5-6).
GRADE_KEYWORDS: list[tuple[int, tuple[str, ...]]] = [
    (
        1,
        (
            "gakkou",
            "yuubin",
            "byouin",
            "kouen",
            "eki",
            "jinjya",
            "jiin",
            "toshokan",
        ),
    ),
    (2, ("keisatu", "shoubou", "hoken", "kouban", "onsen", "kankou", "hakubutu")),
    (3, ("siyakusho", "yakuba", "kouwan", "gyokou", "toudai", "fusya", "entotu")),
    (4, ("tetudou", "jr", "sokou", "dam", "hatuden", "zeimu", "saiban")),
    (
        5,
        (
            "douro",
            "hodou",
            "kousoku",
            "kokudou",
            "todouhuken",
            "tikasuiro",
            "kasen",
            "karegawa",
        ),
    ),
    (
        6,
        (
            "kijun",
            "sankaku",
            "suijun",
            "hyoukou",
            "kyokusen",
            "hojokyo",
            "toushin",
            "higata",
            "mannen",
            "taki",
            "gange",
            "iwadai",
            "sareki",
            "sitti",
            "ta",
            "hatake",
            "jurin",
            "boti",
            "siroato",
            "siseki",
            "tokutei",
            "shozoku",
            "sikuchou",
            "hokkaidou",
        ),
    ),
]


def _powershell_get(url: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
        path = Path(tmp.name)
    ps = f'Invoke-WebRequest -Uri "{url}" -OutFile "{path}" -UseBasicParsing'
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    data = path.read_bytes()
    path.unlink(missing_ok=True)
    return data.decode("utf-8", errors="replace")


def _fetch_html(url: str) -> str:
    if sys.platform == "win32":
        return _powershell_get(url)
    if httpx is not None:
        return httpx.get(url, timeout=30, follow_redirects=True).text
    req = urllib.request.Request(url, headers={"User-Agent": "min-challe-build/1.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="replace")


def _slug_to_id(slug: str) -> str:
    base = slug.removeprefix("map-sign-tizukigou-2022").removesuffix(".htm").removesuffix(".html")
    base = base.lstrip("-_")
    base = re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_")
    return base or "symbol"


def _grade_for_id(symbol_id: str) -> int:
    for grade, keys in GRADE_KEYWORDS:
        if any(key in symbol_id for key in keys):
            return grade
    return 4


def _to_hiragana(label: str) -> str:
    try:
        import pykakasi

        kks = pykakasi.kakasi()
        parts = kks.convert(label)
        return "".join(p["hira"] for p in parts)
    except Exception:
        return label


def _page_urls(slug: str) -> list[str]:
    return [
        f"{GSI_BASE}/KIDS/{slug}",
        f"{GSI_BASE}/kohokocho/{slug}",
    ]


def _parse_symbol_page(html: str) -> tuple[str, str] | None:
    title = re.search(r"<title>地図記号[：:]([^|]+)", html)
    h2 = re.search(r"<h2[^>]*>([^<]+)</h2>", html)
    label = (h2.group(1) if h2 else title.group(1) if title else "").strip()
    png = re.search(r'<a href="(/common/0\d+\.png)"', html)
    if not label or not png:
        return None
    return label, png.group(1)


def _download(url: str, dest: Path) -> None:
    if sys.platform == "win32":
        ps = f'Invoke-WebRequest -Uri "{url}" -OutFile "{dest}" -UseBasicParsing'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
        return
    req = urllib.request.Request(url, headers={"User-Agent": "min-challe-build/1.0"})
    dest.write_bytes(urllib.request.urlopen(req, timeout=60).read())


def _strip_label_png(path: Path, symbol_id: str | None = None) -> None:
    from PIL import Image

    with Image.open(path) as img:
        rgba = img.convert("RGBA")
        w, h = rgba.size
        if symbol_id and symbol_id in SYMBOL_CROP_RATIO_OVERRIDES:
            crop_h = max(1, int(h * SYMBOL_CROP_RATIO_OVERRIDES[symbol_id]))
        else:
            crop_h = _detect_label_crop_height(_row_density(rgba), h)
        cropped = rgba.crop((0, 0, w, crop_h))
    tmp = path.with_suffix(".tmp.png")
    cropped.save(tmp)
    tmp.replace(path)


def _fetch_and_strip_symbol(png_url: str, dest: Path, *, symbol_id: str | None = None) -> None:
    tmp = dest.with_suffix(".download.png")
    _download(png_url, tmp)
    _strip_label_png(tmp, symbol_id)
    tmp.replace(dest)


def recrop_existing_symbols() -> int:
    """Re-download symbol PNGs and apply the current label crop."""
    if not OUT_JSON.exists():
        raise FileNotFoundError(f"missing {OUT_JSON}")
    rows: list[dict] = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    updated = 0
    failed = 0
    for row in rows:
        slug = row.get("gsi_slug")
        if not slug:
            continue
        dest = OUT_SYMBOLS / f"{row['id']}.png"
        parsed = None
        for url in _page_urls(slug):
            try:
                parsed = _parse_symbol_page(_fetch_html(url))
            except Exception:
                continue
            if parsed:
                break
        if not parsed:
            failed += 1
            continue
        _, png_path = parsed
        try:
            _fetch_and_strip_symbol(f"{GSI_BASE}{png_path}", dest, symbol_id=row["id"])
            updated += 1
        except Exception as exc:
            failed += 1
            print(f"skip {row['id']}: {exc}")
        time.sleep(0.05)
    if failed:
        print(f"failed {failed} symbols")
    return updated


def _finalize_grades(rows: list[dict]) -> None:
    """Spread symbols across grades 1-6, keeping facility symbols earlier."""

    def sort_key(row: dict) -> tuple[int, str]:
        hint = _grade_for_id(row["id"])
        if hint <= 2:
            bucket = 0
        elif hint >= 5:
            bucket = 2
        else:
            bucket = 1
        return bucket, row["label"]

    rows.sort(key=sort_key)
    total = len(rows)
    for idx, row in enumerate(rows):
        row["grade"] = min(6, idx * 6 // total + 1)


def main() -> None:
    OUT_SYMBOLS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    itiran = _fetch_html(ITIRAN_URL)
    slugs = sorted(set(re.findall(r"map-sign-tizukigou-2022[a-z0-9\-_\.]+", itiran)))
    print(f"found {len(slugs)} symbol pages")

    rows: list[dict] = []
    seen_ids: set[str] = set()
    for i, slug in enumerate(slugs, start=1):
        symbol_id = _slug_to_id(slug)
        if symbol_id in seen_ids:
            symbol_id = f"{symbol_id}_{i}"
        seen_ids.add(symbol_id)

        parsed = None
        for url in _page_urls(slug):
            try:
                parsed = _parse_symbol_page(_fetch_html(url))
            except Exception:
                continue
            if parsed:
                break
        if not parsed:
            print(f"skip {slug}: no data")
            continue

        label, png_path = parsed
        name = _to_hiragana(label)
        file_name = f"{symbol_id}.png"
        dest = OUT_SYMBOLS / file_name
        _fetch_and_strip_symbol(f"{GSI_BASE}{png_path}", dest, symbol_id=symbol_id)
        rows.append(
            {
                "id": symbol_id,
                "name": name,
                "label": label,
                "grade": 4,
                "gsi_slug": slug,
            }
        )
        print(f"[{len(rows)}] {symbol_id}")
        time.sleep(0.05)

    _finalize_grades(rows)

    rows.sort(key=lambda r: (r["grade"], r["id"]))
    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    for old in OUT_SYMBOLS.glob("*.png"):
        if old.stem not in {r["id"] for r in rows}:
            old.unlink()
    for old in OUT_SYMBOLS.glob("*.svg"):
        old.unlink()

    print(f"saved {len(rows)} symbols -> {OUT_JSON}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--recrop":
        print(f"recropped {recrop_existing_symbols()} symbols")
    else:
        main()
