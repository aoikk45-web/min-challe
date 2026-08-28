from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Household, Member, StudyPlan
from .timeutil import today_jst

HOUSEHOLD_ID = 1


def seed_if_empty() -> None:
    db = SessionLocal()
    try:
        if db.get(Household, HOUSEHOLD_ID) is None:
            _seed(db)
            db.commit()
            return
        child = next((m for m in db.get(Household, HOUSEHOLD_ID).members if m.role == "child"), None)
        if child is not None and db.query(StudyPlan).filter(StudyPlan.member_id == child.id).count() == 0:
            _seed_plans(db, child.id)
            db.commit()
    finally:
        db.close()


def reset_and_seed() -> None:
    from .database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed(db)
        db.commit()
    finally:
        db.close()


def _seed(db: Session) -> None:
    hh = Household(id=HOUSEHOLD_ID, name="さくら家")
    db.add(hh)
    db.flush()
    parent = Member(
        household_id=hh.id,
        display_name="おかあさん",
        role="parent",
        avatar="🌷",
    )
    child = Member(
        household_id=hh.id,
        display_name="みんすけ",
        role="child",
        grade=3,
        avatar="🌟",
    )
    db.add_all([parent, child])
    db.flush()
    _seed_plans(db, child.id)


def _seed_plans(db: Session, child_id: int) -> None:
    today = today_jst()
    monday = today - timedelta(days=today.weekday())
    rows = [
        (monday + timedelta(days=0), "さんすう", "かけ算のれんしゅう", 15),
        (monday + timedelta(days=1), "こくご", "音読", 10),
        (monday + timedelta(days=2), "りか", "植物の観察", 20),
        (monday + timedelta(days=4), "さんすう", "わり算 10もん", 15),
        (monday + timedelta(days=4), "こくご", "漢字ノート", 10),
        (monday + timedelta(days=5), "しゃかい", "地図を見る", 15),
    ]
    for plan_date, subject, title, minutes in rows:
        completed_at = datetime(plan_date.year, plan_date.month, plan_date.day, 18, 0) if plan_date < today else None
        db.add(
            StudyPlan(
                member_id=child_id,
                plan_date=plan_date,
                subject=subject,
                title=title,
                minutes=minutes,
                completed_at=completed_at,
            )
        )
