from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .generate import MATH_KINDS
from .models import DrillProgress

MAX_STEP = 100
PERFECT_NEEDED = 5


def step_label(step: int) -> str:
    s = min(max(step, 1), MAX_STEP)
    if s <= 17:
        return "小1のうち"
    if s <= 34:
        return "小2のうち"
    if s <= 51:
        return "小3のうち"
    if s <= 68:
        return "小4のうち"
    if s <= 84:
        return "小5のうち"
    return "小6のうち"


def ensure_progress(db: Session, member_id: int, kind: str) -> DrillProgress:
    row = db.scalars(
        select(DrillProgress).where(
            DrillProgress.member_id == member_id,
            DrillProgress.kind == kind,
        )
    ).first()
    if row is not None:
        return row
    row = DrillProgress(member_id=member_id, kind=kind, step=1, perfect_streak=0)
    db.add(row)
    db.flush()
    return row


def ensure_all_math(db: Session, member_id: int) -> list[DrillProgress]:
    return [ensure_progress(db, member_id, kind) for kind in MATH_KINDS]


def apply_perfect_streak(progress: DrillProgress, correct_count: int) -> bool:
    """Update streak after a finished session. Returns True if step increased."""
    if correct_count == 10:
        progress.perfect_streak += 1
    else:
        progress.perfect_streak = 0
        return False
    if progress.perfect_streak < PERFECT_NEEDED:
        return False
    if progress.step >= MAX_STEP:
        progress.perfect_streak = 0
        return False
    progress.step += 1
    progress.perfect_streak = 0
    return True
