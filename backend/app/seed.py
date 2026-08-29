from sqlalchemy.orm import Session

from .database import SessionLocal
from .drill_progress import ensure_all_progress
from .models import Household, Member, PointRule

HOUSEHOLD_ID = 1

DEFAULT_RULES = [
    ("drill_complete", "ドリルを1回やりきる", 10),
    ("drill_perfect", "全問正解ボーナス", 5),
    ("plan_complete", "計画を1つ完了", 8),
    ("stamp", "できたねスタンプ", 3),
]


def seed_if_empty() -> None:
    db = SessionLocal()
    try:
        hh = db.get(Household, HOUSEHOLD_ID)
        if hh is None:
            _seed(db)
            db.commit()
            return
        child = next((m for m in hh.members if m.role == "child"), None)
        if db.query(PointRule).filter(PointRule.household_id == HOUSEHOLD_ID).count() == 0:
            _seed_point_rules(db, HOUSEHOLD_ID)
        if child is not None:
            ensure_all_progress(db, child.id)
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
    hh = Household(id=HOUSEHOLD_ID, name="おおの家")
    db.add(hh)
    db.flush()
    parent = Member(
        household_id=hh.id,
        display_name="おうちの人",
        role="parent",
        avatar="🌷",
    )
    child = Member(
        household_id=hh.id,
        display_name="ゆうき",
        role="child",
        grade=3,
        avatar="🌟",
    )
    db.add_all([parent, child])
    db.flush()
    _seed_point_rules(db, hh.id)
    ensure_all_progress(db, child.id)


def _seed_point_rules(db: Session, household_id: int) -> None:
    for key, label, points in DEFAULT_RULES:
        db.add(
            PointRule(
                household_id=household_id,
                event_key=key,
                label=label,
                points=points,
                enabled=True,
            )
        )
