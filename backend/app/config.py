import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = os.environ.get(
    "MINCHALLE_DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'minchalle.db'}",
)
