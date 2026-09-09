from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import demo_family, parse_role, require_child, require_parent
from .ledger import balance_of, now_utc
from .models import Household, Member, PointLedger, PromiseCheck, PromiseItem, PromiseSettlement
from .timeutil import today_jst

router = APIRouter(prefix="/api/promises", tags=["promises"])

SETTLE_LOOKBACK_DAYS = 14


class PromiseItemOut(BaseModel):
    id: int
    name: str
    penalty: int
    enabled: bool
    checked: bool = False
    locked: bool = False

    model_config = {"from_attributes": True}


class PromiseDayOut(BaseModel):
    day: date
    items: list[PromiseItemOut]
    settled_yesterday: bool = False
    deducted_total: int = 0


class PromiseItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    penalty: int = Field(ge=1, le=999)
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name required")
        return value


class PromiseItemPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    penalty: int | None = Field(default=None, ge=1, le=999)
    enabled: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("name required")
        return value


class CheckIn(BaseModel):
    checked: bool


def _hh(family: tuple[Household, Member, Member]) -> Household:
    return family[0]


def _child(family: tuple[Household, Member, Member]) -> Member:
    return family[1]


def _item_day(item: PromiseItem) -> date:
    created = item.created_at
    if hasattr(created, "date"):
        return created.date()
    return created  # type: ignore[return-value]


def _checked_map(db: Session, member_id: int, day: date) -> dict[int, bool]:
    rows = db.scalars(
        select(PromiseCheck).where(PromiseCheck.member_id == member_id, PromiseCheck.day == day)
    ).all()
    return {row.item_id: row.checked for row in rows}


def _is_settled(db: Session, member_id: int, day: date) -> bool:
    return (
        db.scalars(
            select(PromiseSettlement).where(
                PromiseSettlement.member_id == member_id, PromiseSettlement.day == day
            )
        ).first()
        is not None
    )


def settle_pending(db: Session, household_id: int, member_id: int) -> int:
    """Settle unfinished past days. Returns total points deducted just now."""
    today = today_jst()
    yesterday = today - timedelta(days=1)
    start = today - timedelta(days=SETTLE_LOOKBACK_DAYS)

    existing = db.scalars(
        select(PromiseSettlement).where(PromiseSettlement.member_id == member_id).limit(1)
    ).first()
    if existing is None:
        # First run: mark older days settled without charging (avoid surprise penalties).
        bootstrap_day = start
        while bootstrap_day < yesterday:
            db.add(
                PromiseSettlement(
                    member_id=member_id,
                    day=bootstrap_day,
                    created_at=now_utc(),
                )
            )
            bootstrap_day += timedelta(days=1)
        db.commit()

    items = db.scalars(
        select(PromiseItem).where(PromiseItem.household_id == household_id, PromiseItem.enabled.is_(True))
    ).all()
    deducted_total = 0
    day = start
    while day < today:
        if _is_settled(db, member_id, day):
            day += timedelta(days=1)
            continue
        checks = _checked_map(db, member_id, day)
        balance = balance_of(db, member_id)
        for item in items:
            if _item_day(item) > day:
                continue
            if checks.get(item.id, False):
                continue
            take = min(item.penalty, balance)
            if take <= 0:
                continue
            db.add(
                PointLedger(
                    member_id=member_id,
                    delta=-take,
                    reason=f"おやくそく: {item.name}",
                    event_key="promise_miss",
                    related_id=item.id,
                    created_at=now_utc(),
                )
            )
            balance -= take
            deducted_total += take
        db.add(
            PromiseSettlement(
                member_id=member_id,
                day=day,
                created_at=now_utc(),
            )
        )
        day += timedelta(days=1)
    db.commit()
    return deducted_total


@router.get("", response_model=PromiseDayOut)
def get_today_promises(
    _role: str = Depends(parse_role),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    child = _child(family)
    deducted = settle_pending(db, _hh(family).id, child.id)
    today = today_jst()
    items = db.scalars(
        select(PromiseItem)
        .where(PromiseItem.household_id == _hh(family).id)
        .order_by(PromiseItem.id)
    ).all()
    checks = _checked_map(db, child.id, today)
    out: list[PromiseItemOut] = []
    for item in items:
        if not item.enabled and _role == "child":
            continue
        out.append(
            PromiseItemOut(
                id=item.id,
                name=item.name,
                penalty=item.penalty,
                enabled=item.enabled,
                checked=checks.get(item.id, False),
                locked=False,
            )
        )
    return PromiseDayOut(
        day=today,
        items=out,
        settled_yesterday=_is_settled(db, child.id, today - timedelta(days=1)),
        deducted_total=deducted,
    )


@router.post("/items", response_model=PromiseItemOut, status_code=201)
def create_item(
    body: PromiseItemIn,
    _role: str = Depends(require_parent),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    item = PromiseItem(
        household_id=_hh(family).id,
        name=body.name,
        penalty=body.penalty,
        enabled=body.enabled,
        created_at=now_utc(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return PromiseItemOut(
        id=item.id,
        name=item.name,
        penalty=item.penalty,
        enabled=item.enabled,
        checked=False,
        locked=False,
    )


@router.patch("/items/{item_id}", response_model=PromiseItemOut)
def patch_item(
    item_id: int,
    body: PromiseItemPatch,
    _role: str = Depends(require_parent),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    item = db.get(PromiseItem, item_id)
    if item is None or item.household_id != _hh(family).id:
        raise HTTPException(404, "item not found")
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    checks = _checked_map(db, _child(family).id, today_jst())
    return PromiseItemOut(
        id=item.id,
        name=item.name,
        penalty=item.penalty,
        enabled=item.enabled,
        checked=checks.get(item.id, False),
        locked=False,
    )


@router.delete("/items/{item_id}", status_code=204)
def delete_item(
    item_id: int,
    _role: str = Depends(require_parent),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    item = db.get(PromiseItem, item_id)
    if item is None or item.household_id != _hh(family).id:
        raise HTTPException(404, "item not found")
    for row in db.scalars(select(PromiseCheck).where(PromiseCheck.item_id == item_id)).all():
        db.delete(row)
    db.delete(item)
    db.commit()


@router.put("/checks/{item_id}", response_model=PromiseItemOut)
def set_check(
    item_id: int,
    body: CheckIn,
    _role: str = Depends(require_child),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    child = _child(family)
    settle_pending(db, _hh(family).id, child.id)
    item = db.get(PromiseItem, item_id)
    if item is None or item.household_id != _hh(family).id or not item.enabled:
        raise HTTPException(404, "item not found")
    today = today_jst()
    row = db.scalars(
        select(PromiseCheck).where(
            PromiseCheck.member_id == child.id,
            PromiseCheck.item_id == item_id,
            PromiseCheck.day == today,
        )
    ).first()
    if row is None:
        row = PromiseCheck(member_id=child.id, item_id=item_id, day=today, checked=body.checked)
        db.add(row)
    else:
        row.checked = body.checked
    db.commit()
    return PromiseItemOut(
        id=item.id,
        name=item.name,
        penalty=item.penalty,
        enabled=item.enabled,
        checked=body.checked,
        locked=False,
    )
