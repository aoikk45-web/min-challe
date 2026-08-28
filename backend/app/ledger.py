from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import PointLedger, PointRule

BUILTIN_KEYS = ("drill_complete", "drill_perfect", "plan_complete", "stamp")


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def balance_of(db: Session, member_id: int) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(PointLedger.delta), 0)).where(PointLedger.member_id == member_id)
    )
    return int(total or 0)


def _rule(db: Session, household_id: int, event_key: str) -> PointRule | None:
    return db.scalars(
        select(PointRule).where(PointRule.household_id == household_id, PointRule.event_key == event_key)
    ).first()


def award(
    db: Session,
    *,
    household_id: int,
    member_id: int,
    event_key: str,
    reason: str,
    related_id: int | None = None,
) -> int:
    if related_id is not None:
        exists = db.scalars(
            select(PointLedger).where(
                PointLedger.member_id == member_id,
                PointLedger.event_key == event_key,
                PointLedger.related_id == related_id,
            )
        ).first()
        if exists is not None:
            return 0
    rule = _rule(db, household_id, event_key)
    if rule is None or not rule.enabled or rule.points == 0:
        return 0
    db.add(
        PointLedger(
            member_id=member_id,
            delta=rule.points,
            reason=reason,
            event_key=event_key,
            related_id=related_id,
            created_at=now_utc(),
        )
    )
    return rule.points
