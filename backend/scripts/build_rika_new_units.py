"""新規理科単元3種の JSON バンクを書き出す。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "rika"

OUTPUT = {
    "たいようとかげ": "taiyo.json",
    "ひかりとおと": "hikari.json",
    "てんきとみず": "tenki.json",
}


def main() -> int:
    from scripts.rika_new_units_data import HIKARI_BANK, TAIYO_BANK, TENKI_BANK

    banks = {
        "たいようとかげ": TAIYO_BANK,
        "ひかりとおと": HIKARI_BANK,
        "てんきとみず": TENKI_BANK,
    }
    for kind, rows in banks.items():
        out = []
        seen: set[str] = set()
        for prompt, choices, correct, grade, kind_name in rows:
            if prompt in seen:
                continue
            seen.add(prompt)
            out.append(
                {
                    "prompt": prompt,
                    "choices": choices,
                    "correct": correct,
                    "grade": grade,
                    "kind": kind_name,
                    "image": None,
                }
            )
        out.sort(key=lambda r: (r["grade"], r["prompt"]))
        path = DATA_DIR / OUTPUT[kind]
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path.name}: {len(out)} questions")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
