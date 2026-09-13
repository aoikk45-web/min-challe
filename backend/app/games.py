from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import demo_family, require_child
from .ledger import award, balance_of, now_utc
from .models import DrillSession, Household, Member, PointLedger
from .seed import ensure_builtin_rules

router = APIRouter(prefix="/api/games", tags=["games"])

GameName = Literal["cups", "memory", "invaders", "breakout", "racing", "family"]

DRILLS_PER_PLAY = 3

GAME_REASONS: dict[str, str] = {
    "cups": "カップゲームできた",
    "memory": "しんけいすいじゃくできた",
    "invaders": "インベーダーできた",
    "breakout": "ブロックくずしできた",
    "racing": "くるまレースできた",
    "family": "4世代あわせできた",
}


class ClearIn(BaseModel):
    game: GameName


class ClearOut(BaseModel):
    points_earned: int
    balance: int


class PlayIn(BaseModel):
    game: GameName


class AccessOut(BaseModel):
    drills_finished: int
    plays_used: int
    plays_remaining: int
    drills_toward_next: int
    drills_per_play: int


def _access_for(db: Session, member_id: int) -> AccessOut:
    drills_finished = int(
        db.scalar(
            select(func.count())
            .select_from(DrillSession)
            .where(DrillSession.member_id == member_id, DrillSession.status == "finished")
        )
        or 0
    )
    plays_used = int(
        db.scalar(
            select(func.count())
            .select_from(PointLedger)
            .where(PointLedger.member_id == member_id, PointLedger.event_key == "game_play")
        )
        or 0
    )
    earned = drills_finished // DRILLS_PER_PLAY
    remaining = max(0, earned - plays_used)
    return AccessOut(
        drills_finished=drills_finished,
        plays_used=plays_used,
        plays_remaining=remaining,
        drills_toward_next=drills_finished % DRILLS_PER_PLAY,
        drills_per_play=DRILLS_PER_PLAY,
    )


@router.get("/access", response_model=AccessOut)
def game_access(
    _role: str = Depends(require_child),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    _household, child, _parent = family
    return _access_for(db, child.id)


@router.post("/play", response_model=AccessOut)
def start_game_play(
    body: PlayIn,
    _role: str = Depends(require_child),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    """ミニゲームを1回はじめるときにチケットを1枚使う（ドリル3回で1枚）。"""
    _household, child, _parent = family
    access = _access_for(db, child.id)
    if access.plays_remaining <= 0:
        raise HTTPException(
            403,
            f"ドリルを{DRILLS_PER_PLAY}回やるとミニゲームが1回できます",
        )
    db.add(
        PointLedger(
            member_id=child.id,
            delta=0,
            reason=f"ミニゲーム開始: {body.game}",
            event_key="game_play",
            related_id=None,
            created_at=now_utc(),
        )
    )
    db.commit()
    return _access_for(db, child.id)


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
