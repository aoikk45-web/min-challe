from __future__ import annotations

import uuid
from datetime import datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import demo_family, parse_role, require_child, require_parent
from .album import record_album
from .ledger import BUILTIN_KEYS, award, balance_of, now_utc
from .models import Household, Member, PointLedger, PointRule, Reward
from .timeutil import JST, today_jst

router = APIRouter(prefix="/api/points", tags=["points"])


class RuleOut(BaseModel):
    id: int
    event_key: str
    label: str
    points: int
    enabled: bool

    model_config = {"from_attributes": True}


class RuleIn(BaseModel):
    id: int | None = None
    event_key: str | None = None
    label: str = Field(min_length=1, max_length=80)
    points: int = Field(ge=0, le=999)
    enabled: bool = True

    @field_validator("label")
    @classmethod
    def strip_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("label required")
        return value


class RewardOut(BaseModel):
    id: int
    name: str
    cost: int
    enabled: bool
    daily_limit: Optional[int] = None
    redeems_today: int = 0

    model_config = {"from_attributes": True}


def _normalize_daily_limit(value: Optional[int]) -> Optional[int]:
    if value is None or value <= 0:
        return None
    return value


def _jst_day_bounds_utc_naive(day=None) -> tuple[datetime, datetime]:
    day = day or today_jst()
    start_jst = datetime.combine(day, time.min, tzinfo=JST)
    end_jst = datetime.combine(day, time.max, tzinfo=JST)
    start_utc = start_jst.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_jst.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def redeems_today(db: Session, member_id: int, reward_id: int) -> int:
    start, end = _jst_day_bounds_utc_naive()
    count = db.scalar(
        select(func.count())
        .select_from(PointLedger)
        .where(
            PointLedger.member_id == member_id,
            PointLedger.event_key == "redeem",
            PointLedger.related_id == reward_id,
            PointLedger.created_at >= start,
            PointLedger.created_at <= end,
        )
    )
    return int(count or 0)


def _reward_out(db: Session, reward: Reward, member_id: int) -> RewardOut:
    return RewardOut(
        id=reward.id,
        name=reward.name,
        cost=reward.cost,
        enabled=reward.enabled,
        daily_limit=reward.daily_limit,
        redeems_today=redeems_today(db, member_id, reward.id),
    )


class RewardIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    cost: int = Field(ge=1, le=9999)
    enabled: bool = True
    daily_limit: Optional[int] = Field(default=None, ge=0, le=99)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name required")
        return value


class RewardPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    cost: int | None = Field(default=None, ge=1, le=9999)
    enabled: bool | None = None
    daily_limit: Optional[int] = Field(default=None, ge=0, le=99)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("name required")
        return value


class LedgerOut(BaseModel):
    id: int
    delta: int
    reason: str
    event_key: str
    created_at: datetime

    model_config = {"from_attributes": True}


class NextReward(BaseModel):
    id: int
    name: str
    cost: int
    remaining: int


class SummaryOut(BaseModel):
    balance: int
    next_reward: NextReward | None
    progress: float


class StampIn(BaseModel):
    note: str = Field(default="", max_length=80)
    event_key: str = Field(default="stamp", max_length=40)

    @field_validator("event_key")
    @classmethod
    def strip_key(cls, value: str) -> str:
        value = value.strip() or "stamp"
        return value


def _child(family: tuple[Household, Member, Member]) -> Member:
    return family[1]


def _hh(family: tuple[Household, Member, Member]) -> Household:
    return family[0]


def _build_summary(db: Session, family: tuple[Household, Member, Member]) -> SummaryOut:
    child = _child(family)
    balance = balance_of(db, child.id)
    rewards = [
        r
        for r in db.scalars(
            select(Reward).where(Reward.household_id == _hh(family).id, Reward.enabled.is_(True))
        ).all()
        if r.cost > 0
    ]
    rewards.sort(key=lambda r: r.cost)
    next_reward = None
    progress = 0.0
    if rewards:
        target = next((r for r in rewards if r.cost > balance), rewards[0])
        remaining = max(0, target.cost - balance)
        next_reward = NextReward(id=target.id, name=target.name, cost=target.cost, remaining=remaining)
        progress = 1.0 if target.cost <= 0 else min(1.0, balance / target.cost)
    return SummaryOut(balance=balance, next_reward=next_reward, progress=round(progress, 3))


@router.get("/summary", response_model=SummaryOut)
def points_summary(
    _role: str = Depends(parse_role),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    return _build_summary(db, family)


@router.get("/ledger", response_model=list[LedgerOut])
def points_ledger(
    _role: str = Depends(parse_role),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    child = _child(family)
    return db.scalars(
        select(PointLedger)
        .where(PointLedger.member_id == child.id)
        .order_by(PointLedger.created_at.desc(), PointLedger.id.desc())
    ).all()


@router.get("/rules", response_model=list[RuleOut])
def list_rules(
    _role: str = Depends(parse_role),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(PointRule).where(PointRule.household_id == _hh(family).id).order_by(PointRule.id)
    ).all()


@router.put("/rules", response_model=list[RuleOut])
def put_rules(
    body: list[RuleIn],
    _role: str = Depends(require_parent),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    hh = _hh(family)
    existing = {r.id: r for r in db.scalars(select(PointRule).where(PointRule.household_id == hh.id)).all()}
    kept: set[int] = set()
    for item in body:
        if item.id is not None and item.id > 0:
            rule = existing.get(item.id)
            if rule is None:
                raise HTTPException(404, "rule not found")
            rule.label = item.label
            rule.points = item.points
            rule.enabled = item.enabled
            kept.add(rule.id)
        else:
            key = item.event_key if item.event_key and item.event_key.startswith("custom_") else f"custom_{uuid.uuid4().hex[:8]}"
            rule = PointRule(
                household_id=hh.id,
                event_key=key,
                label=item.label,
                points=item.points,
                enabled=item.enabled,
            )
            db.add(rule)
            db.flush()
            kept.add(rule.id)
    for rule in existing.values():
        if rule.id not in kept and rule.event_key not in BUILTIN_KEYS:
            db.delete(rule)
    db.commit()
    return db.scalars(select(PointRule).where(PointRule.household_id == hh.id).order_by(PointRule.id)).all()


@router.get("/rewards", response_model=list[RewardOut])
def list_rewards(
    _role: str = Depends(parse_role),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    child = _child(family)
    rewards = db.scalars(
        select(Reward).where(Reward.household_id == _hh(family).id).order_by(Reward.cost, Reward.id)
    ).all()
    return [_reward_out(db, reward, child.id) for reward in rewards]


@router.post("/rewards", response_model=RewardOut, status_code=201)
def create_reward(
    body: RewardIn,
    _role: str = Depends(require_parent),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    reward = Reward(
        household_id=_hh(family).id,
        name=body.name,
        cost=body.cost,
        enabled=body.enabled,
        daily_limit=_normalize_daily_limit(body.daily_limit),
    )
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return _reward_out(db, reward, _child(family).id)


@router.patch("/rewards/{reward_id}", response_model=RewardOut)
def patch_reward(
    reward_id: int,
    body: RewardPatch,
    _role: str = Depends(require_parent),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    reward = db.get(Reward, reward_id)
    if reward is None or reward.household_id != _hh(family).id:
        raise HTTPException(404, "reward not found")
    data = body.model_dump(exclude_unset=True)
    if "daily_limit" in data:
        data["daily_limit"] = _normalize_daily_limit(data["daily_limit"])
    for key, value in data.items():
        setattr(reward, key, value)
    db.commit()
    db.refresh(reward)
    return _reward_out(db, reward, _child(family).id)


@router.delete("/rewards/{reward_id}", status_code=204)
def delete_reward(
    reward_id: int,
    _role: str = Depends(require_parent),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    reward = db.get(Reward, reward_id)
    if reward is None or reward.household_id != _hh(family).id:
        raise HTTPException(404, "reward not found")
    db.delete(reward)
    db.commit()


@router.post("/rewards/{reward_id}/redeem", response_model=SummaryOut)
def redeem_reward(
    reward_id: int,
    _role: str = Depends(require_child),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    child = _child(family)
    reward = db.get(Reward, reward_id)
    if reward is None or reward.household_id != _hh(family).id or not reward.enabled:
        raise HTTPException(404, "reward not found")
    limit = reward.daily_limit
    if limit and limit > 0 and redeems_today(db, child.id, reward.id) >= limit:
        raise HTTPException(400, "きょうは もう こうかん できないよ")
    bal = balance_of(db, child.id)
    if bal < reward.cost:
        raise HTTPException(400, f"あと{reward.cost - bal}点")
    db.add(
        PointLedger(
            member_id=child.id,
            delta=-reward.cost,
            reason=f"ごほうび: {reward.name}",
            event_key="redeem",
            related_id=reward.id,
            created_at=now_utc(),
        )
    )
    record_album(
        db,
        member_id=child.id,
        kind="redeem",
        title="ごほうびとこうかんした",
        body=reward.name,
    )
    db.commit()
    return _build_summary(db, family)


AUTO_AWARD_KEYS = ("drill_complete", "drill_perfect", "plan_complete")


@router.post("/stamp", response_model=SummaryOut)
def give_stamp(
    body: StampIn,
    _role: str = Depends(require_parent),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    event_key = body.event_key
    if event_key in AUTO_AWARD_KEYS or (event_key != "stamp" and not event_key.startswith("custom_")):
        raise HTTPException(400, "このルールでは押せないよ")
    rule = db.scalars(
        select(PointRule).where(PointRule.household_id == _hh(family).id, PointRule.event_key == event_key)
    ).first()
    if rule is None:
        raise HTTPException(404, "rule not found")
    note = body.note.strip()
    reason = f"{rule.label}{(' ・' + note) if note else ''}"
    awarded = award(
        db,
        household_id=_hh(family).id,
        member_id=_child(family).id,
        event_key=event_key,
        reason=reason,
    )
    if awarded == 0:
        raise HTTPException(400, "このルールがオフです")
    record_album(
        db,
        member_id=_child(family).id,
        kind="stamp",
        title=rule.label,
        body=note,
    )
    db.commit()
    return _build_summary(db, family)
