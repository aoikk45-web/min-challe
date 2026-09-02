import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.shakai import PREFECTURES, capital_prompt_for_pref, capital_prompt_is_wrong

NAME_TO_CODE = {str(p["name"]): str(p["code"]) for p in PREFECTURES}

con = sqlite3.connect(Path("data/minchalle.db"))
cur = con.cursor()
cur.execute("SELECT id, prompt FROM drill_questions WHERE prompt LIKE '%しょざいち%'")
rows = cur.fetchall()
updated = 0
for qid, prompt in rows:
    if not capital_prompt_is_wrong(prompt):
        continue
    lines = prompt.split("\n")
    last = lines[-1].strip()
    if "の " not in last or not last.endswith("は？"):
        continue
    name = last.split("の ", 1)[0]
    code = NAME_TO_CODE.get(name)
    if not code:
        continue
    lines[-1] = capital_prompt_for_pref(name, code)
    new_prompt = "\n".join(lines)
    if new_prompt != prompt:
        cur.execute("UPDATE drill_questions SET prompt = ? WHERE id = ?", (new_prompt, qid))
        print(f"#{qid}: {last!r} -> {lines[-1]!r}")
        updated += 1
con.commit()
print("updated", updated)
con.close()
