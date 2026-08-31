"""Reset local demo database to fresh おおの家 / ゆうき (G3) state.

Usage (API stopped recommended):
    cd backend
    .\\.venv\\Scripts\\python.exe scripts\\reset_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.seed import reset_and_seed


def main() -> None:
    reset_and_seed()
    print("Demo reset complete: おおの家 / ゆうき (小学3年) / おうちの人")


if __name__ == "__main__":
    main()
