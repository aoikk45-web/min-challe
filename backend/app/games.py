from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db
from .deps import demo_family, require_child
from .ledger import award, balance_of
from .models import Household, Member
from .seed import ensure_builtin_rules

router = APIRouter(prefix="/api/games", tags=["games"])

GameName = Literal["cups", "memory", "invaders", "breakout", "racing"]

GAME_REASONS: dict[str, str] = {
    "cups": "カップゲームできた",
    "memory": "しんけいすいじゃくできた",
    "invaders": "インベーダーできた",
    "breakout": "ブロックくずしできた",
    "racing": "くるまレースできた",
}


class ClearIn(BaseModel):
    game: GameName


class ClearOut(BaseModel):
    points_earned: int
    balance: int


@router.post("/clear", response_model=ClearOut)
def clear_game(
    body: ClearIn,
    _role: str = Depends(require_child),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    household, child, _parent = family
    ensure_builtin_rules(db, household.id)
    points = award(
        db,
        household_id=household.id,
        member_id=child.id,
        event_key="game_clear",
        reason=GAME_REASONS[body.game],
        related_id=None,
    )
    db.commit()
    return ClearOut(points_earned=points, balance=balance_of(db, child.id))
