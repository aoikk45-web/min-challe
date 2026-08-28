from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Household, Member

HOUSEHOLD_ID = 1


def seed_if_empty() -> None:
    db = SessionLocal()
    try:
        if db.get(Household, HOUSEHOLD_ID):
            return
        _seed(db)
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
    db.add_all(
        [
            Member(
                household_id=hh.id,
                display_name="おかあさん",
                role="parent",
                avatar="🌷",
            ),
            Member(
                household_id=hh.id,
                display_name="みんすけ",
                role="child",
                grade=3,
                avatar="🌟",
            ),
        ]
    )
