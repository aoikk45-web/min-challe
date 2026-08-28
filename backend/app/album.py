from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import demo_family, parse_role, require_parent
from .models import AlbumEntry, Household, Member
from .timeutil import now_jst

Kind = Literal["plan", "drill", "redeem", "stamp", "memo"]

KIND_STAMPS: dict[str, str] = {
    "plan": "📒",
    "drill": "✨",
    "redeem": "🎁",
    "stamp": "🏅",
    "memo": "📝",
}

router = APIRouter(prefix="/api/album", tags=["album"])


class AlbumOut(BaseModel):
    id: int
    kind: str
    title: str
    body: str
    stamp: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    body: str = Field(default="", max_length=200)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title required")
        return value

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        return value.strip()


def record_album(
    db: Session,
    *,
    member_id: int,
    kind: Kind,
    title: str,
    body: str = "",
    related_id: int | None = None,
    created_at: datetime | None = None,
) -> AlbumEntry:
    if related_id is not None:
        exists = db.scalars(
            select(AlbumEntry).where(
                AlbumEntry.member_id == member_id,
                AlbumEntry.kind == kind,
                AlbumEntry.related_id == related_id,
            )
        ).first()
        if exists is not None:
            return exists
    entry = AlbumEntry(
        member_id=member_id,
        kind=kind,
        title=title,
        body=body,
        stamp=KIND_STAMPS[kind],
        related_id=related_id,
        created_at=created_at or now_jst(),
    )
    db.add(entry)
    return entry


def _child(family: tuple[Household, Member, Member]) -> Member:
    return family[1]


@router.get("", response_model=list[AlbumOut])
def list_album(
    _role: str = Depends(parse_role),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(AlbumEntry)
        .where(AlbumEntry.member_id == _child(family).id)
        .order_by(AlbumEntry.created_at.desc(), AlbumEntry.id.desc())
    ).all()


@router.post("", response_model=AlbumOut, status_code=201)
def add_memo(
    body: MemoIn,
    _role: str = Depends(require_parent),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    entry = record_album(
        db,
        member_id=_child(family).id,
        kind="memo",
        title=body.title,
        body=body.body,
    )
    db.commit()
    db.refresh(entry)
    return entry
