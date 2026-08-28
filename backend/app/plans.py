from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import demo_family, parse_role, require_parent
from .album import record_album
from .ledger import award
from .models import Household, Member, StudyPlan
from .timeutil import today_jst, week_bounds

Subject = Literal["こくご", "さんすう", "りか", "しゃかい", "そのた"]

router = APIRouter(prefix="/api/plans", tags=["plans"])


class PlanOut(BaseModel):
    id: int
    plan_date: date
    subject: str
    title: str
    minutes: int
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class PlanIn(BaseModel):
    plan_date: date
    subject: Subject
    title: str = Field(min_length=1, max_length=120)
    minutes: int = Field(ge=1, le=240)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title required")
        return value


class PlanPatch(BaseModel):
    plan_date: date | None = None
    subject: Subject | None = None
    title: str | None = Field(default=None, min_length=1, max_length=120)
    minutes: int | None = Field(default=None, ge=1, le=240)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("title required")
        return value


def _child(family: tuple[Household, Member, Member]) -> Member:
    return family[1]


def _get_plan(db: Session, plan_id: int, child_id: int) -> StudyPlan:
    plan = db.get(StudyPlan, plan_id)
    if plan is None or plan.member_id != child_id:
        raise HTTPException(404, "plan not found")
    return plan


@router.get("", response_model=list[PlanOut])
def list_plans(
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    _role: str = Depends(parse_role),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    if (from_ is None) ^ (to is None):
        raise HTTPException(400, "from and to must be used together")
    start, end = (from_, to) if from_ is not None and to is not None else week_bounds(today_jst())
    child = _child(family)
    plans = db.scalars(
        select(StudyPlan)
        .where(
            StudyPlan.member_id == child.id,
            StudyPlan.plan_date >= start,
            StudyPlan.plan_date <= end,
        )
        .order_by(StudyPlan.plan_date, StudyPlan.id)
    ).all()
    return plans


@router.post("", response_model=PlanOut, status_code=201)
def create_plan(
    body: PlanIn,
    _role: str = Depends(require_parent),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    child = _child(family)
    plan = StudyPlan(
        member_id=child.id,
        plan_date=body.plan_date,
        subject=body.subject,
        title=body.title,
        minutes=body.minutes,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.patch("/{plan_id}", response_model=PlanOut)
def update_plan(
    plan_id: int,
    body: PlanPatch,
    _role: str = Depends(require_parent),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    plan = _get_plan(db, plan_id, _child(family).id)
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=204)
def delete_plan(
    plan_id: int,
    _role: str = Depends(require_parent),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    plan = _get_plan(db, plan_id, _child(family).id)
    db.delete(plan)
    db.commit()


@router.post("/{plan_id}/complete", response_model=PlanOut)
def complete_plan(
    plan_id: int,
    _role: str = Depends(parse_role),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    plan = _get_plan(db, plan_id, _child(family).id)
    if plan.completed_at is not None:
        raise HTTPException(409, "already completed")
    plan.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    award(
        db,
        household_id=family[0].id,
        member_id=plan.member_id,
        event_key="plan_complete",
        reason=f"けいかく: {plan.title}",
        related_id=plan.id,
    )
    record_album(
        db,
        member_id=plan.member_id,
        kind="plan",
        title="けいかくをやりきった",
        body=f"{plan.subject} ・ {plan.title}",
        related_id=plan.id,
    )
    db.commit()
    db.refresh(plan)
    return plan
