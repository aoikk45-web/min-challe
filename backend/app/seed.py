from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import AlbumEntry, Household, Member, PointLedger, PointRule, Reward, StudyPlan
from .timeutil import today_jst

HOUSEHOLD_ID = 1

DEFAULT_RULES = [
    ("drill_complete", "ドリルを1回やりきる", 10),
    ("drill_perfect", "全問正解ボーナス", 5),
    ("plan_complete", "計画を1つ完了", 8),
    ("stamp", "できたねスタンプ", 3),
    ("custom_test100", "テスト100点", 20),
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
        if child is not None and db.query(StudyPlan).filter(StudyPlan.member_id == child.id).count() == 0:
            _seed_plans(db, child.id)
        if db.query(PointRule).filter(PointRule.household_id == HOUSEHOLD_ID).count() == 0:
            _seed_points(db, HOUSEHOLD_ID, child.id if child else None)
        elif (
            db.query(PointRule)
            .filter(PointRule.household_id == HOUSEHOLD_ID, PointRule.event_key == "custom_test100")
            .count()
            == 0
        ):
            db.add(
                PointRule(
                    household_id=HOUSEHOLD_ID,
                    event_key="custom_test100",
                    label="テスト100点",
                    points=20,
                    enabled=True,
                )
            )
        if child is not None and db.query(AlbumEntry).filter(AlbumEntry.member_id == child.id).count() == 0:
            _seed_album(db, child.id)
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
    _seed_points(db, hh.id, child.id)
    _seed_album(db, child.id)


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


def _seed_points(db: Session, household_id: int, child_id: int | None) -> None:
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
    db.add_all(
        [
            Reward(household_id=household_id, name="ゲーム 15ふん", cost=30, enabled=True),
            Reward(household_id=household_id, name="すきなおやつ", cost=50, enabled=True),
        ]
    )
    if child_id is None:
        return
    db.flush()
    completed = db.query(StudyPlan).filter(StudyPlan.member_id == child_id, StudyPlan.completed_at.is_not(None)).all()
    for plan in completed:
        db.add(
            PointLedger(
                member_id=child_id,
                delta=8,
                reason=f"けいかく: {plan.title}",
                event_key="plan_complete",
                related_id=plan.id,
                created_at=plan.completed_at,
            )
        )
    db.add(
        PointLedger(
            member_id=child_id,
            delta=10,
            reason="ドリル: たしざん",
            event_key="drill_complete",
            related_id=None,
            created_at=datetime.now().replace(hour=16, minute=0, second=0, microsecond=0),
        )
    )
    db.add(
        PointLedger(
            member_id=child_id,
            delta=3,
            reason="できたねスタンプ ・おうちの片付け",
            event_key="stamp",
            related_id=None,
            created_at=datetime.now().replace(hour=17, minute=0, second=0, microsecond=0),
        )
    )


def _seed_album(db: Session, child_id: int) -> None:
    from .album import record_album

    completed = db.query(StudyPlan).filter(StudyPlan.member_id == child_id, StudyPlan.completed_at.is_not(None)).all()
    for plan in completed:
        record_album(
            db,
            member_id=child_id,
            kind="plan",
            title="けいかくをやりきった",
            body=f"{plan.subject} ・ {plan.title}",
            related_id=plan.id,
            created_at=plan.completed_at,
        )
    record_album(
        db,
        member_id=child_id,
        kind="drill",
        title="ドリルをやりきった",
        body="たしざん 8/10",
        created_at=datetime.now() - timedelta(hours=5),
    )
    record_album(
        db,
        member_id=child_id,
        kind="stamp",
        title="できたねスタンプ",
        body="おうちの片付け",
        created_at=datetime.now() - timedelta(hours=3),
    )
    record_album(
        db,
        member_id=child_id,
        kind="memo",
        title="がんばってるね",
        body="音読の声がはっきりしてきたよ。",
        created_at=datetime.now() - timedelta(hours=1),
    )
