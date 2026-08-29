from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import get_db
from .deps import demo_family, parse_role, require_child
from .drill_progress import (
    MAX_STEP,
    PERFECT_NEEDED,
    apply_perfect_streak,
    ensure_all_progress,
    ensure_progress,
    step_label,
)
from .generate import KINDS, KOKUGO_KINDS, MATH_KINDS, PROGRESS_KINDS, generate_ten, normalize_reading
from .album import record_album
from .ledger import award
from .models import DrillQuestion, DrillSession, Household, Member

Kind = Literal["たしざん", "ひきざん", "かけざん", "わりざん", "かんじのよみ", "じゅくごのよみ"]

router = APIRouter(prefix="/api/drills", tags=["drills"])


class StartIn(BaseModel):
    kind: Kind


class AnswerIn(BaseModel):
    question_id: int
    answer: int | str


class ProgressOut(BaseModel):
    kind: str
    step: int
    perfect_streak: int
    step_label: str
    max_step: int = MAX_STEP
    perfect_needed: int = PERFECT_NEEDED


class QuestionOut(BaseModel):
    id: int
    seq: int
    prompt: str
    child_answer: str | None
    is_correct: bool | None
    correct: str | None


class SessionOut(BaseModel):
    id: int
    kind: str
    grade: int
    step: int | None = None
    status: str
    correct_count: int | None
    duration_sec: int | None
    started_at: datetime
    finished_at: datetime | None
    questions: list[QuestionOut]
    perfect_streak: int | None = None
    step_label: str | None = None
    step_up: bool = False
    max_step: int = MAX_STEP
    perfect_needed: int = PERFECT_NEEDED


class HistoryItem(BaseModel):
    id: int
    kind: str
    grade: int
    step: int | None = None
    status: str
    correct_count: int | None
    duration_sec: int | None
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _child(family: tuple[Household, Member, Member]) -> Member:
    return family[1]


def _serialize(
    session: DrillSession,
    *,
    step_up: bool = False,
    perfect_streak: int | None = None,
) -> SessionOut:
    questions = sorted(session.questions, key=lambda q: q.seq)
    finished = session.status == "finished"
    label = step_label(session.step) if session.step is not None else None
    return SessionOut(
        id=session.id,
        kind=session.kind,
        grade=session.grade,
        step=session.step,
        status=session.status,
        correct_count=session.correct_count,
        duration_sec=session.duration_sec,
        started_at=session.started_at,
        finished_at=session.finished_at,
        questions=[
            QuestionOut(
                id=q.id,
                seq=q.seq,
                prompt=q.prompt,
                child_answer=q.child_answer,
                is_correct=q.is_correct,
                correct=q.correct if finished or q.child_answer is not None else None,
            )
            for q in questions
        ],
        perfect_streak=perfect_streak,
        step_label=label,
        step_up=step_up,
    )


def _get_session(db: Session, session_id: int, child_id: int) -> DrillSession:
    session = db.scalars(
        select(DrillSession)
        .options(selectinload(DrillSession.questions))
        .where(DrillSession.id == session_id, DrillSession.member_id == child_id)
    ).first()
    if session is None:
        raise HTTPException(404, "drill not found")
    return session


@router.get("/progress", response_model=list[ProgressOut])
def drill_progress_list(
    _role: str = Depends(parse_role),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    child = _child(family)
    rows = ensure_all_progress(db, child.id)
    return [
        ProgressOut(
            kind=row.kind,
            step=row.step,
            perfect_streak=row.perfect_streak,
            step_label=step_label(row.step),
        )
        for row in rows
    ]


@router.post("/start", response_model=SessionOut)
def start_drill(
    body: StartIn,
    _role: str = Depends(require_child),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    child = _child(family)
    existing = db.scalars(
        select(DrillSession)
        .options(selectinload(DrillSession.questions))
        .where(DrillSession.member_id == child.id, DrillSession.status == "in_progress")
        .order_by(DrillSession.id.desc())
    ).first()
    if existing is not None:
        streak = None
        if existing.kind in PROGRESS_KINDS:
            streak = ensure_progress(db, child.id, existing.kind).perfect_streak
        return _serialize(existing, perfect_streak=streak)

    school_grade = child.grade or 3
    kind = body.kind if body.kind in KINDS else "たしざん"
    drill_step: int | None = None
    streak: int | None = None
    if kind in PROGRESS_KINDS:
        progress = ensure_progress(db, child.id, kind)
        drill_step = progress.step
        streak = progress.perfect_streak
    session = DrillSession(
        member_id=child.id,
        kind=kind,
        grade=school_grade,
        step=drill_step,
        status="in_progress",
        started_at=_now(),
    )
    db.add(session)
    db.flush()
    gen_step = drill_step if drill_step is not None else 1
    for seq, (prompt, correct) in enumerate(generate_ten(kind, gen_step), start=1):
        db.add(
            DrillQuestion(
                session_id=session.id,
                seq=seq,
                prompt=prompt,
                correct=correct,
            )
        )
    db.commit()
    return _serialize(_get_session(db, session.id, child.id), perfect_streak=streak)


@router.get("/history", response_model=list[HistoryItem])
def drill_history(
    _role: str = Depends(parse_role),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    child = _child(family)
    rows = db.scalars(
        select(DrillSession)
        .where(DrillSession.member_id == child.id)
        .order_by(DrillSession.started_at.desc(), DrillSession.id.desc())
    ).all()
    return rows


@router.get("/{session_id}", response_model=SessionOut)
def get_drill(
    session_id: int,
    _role: str = Depends(parse_role),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    child = _child(family)
    session = _get_session(db, session_id, child.id)
    streak = None
    if session.kind in PROGRESS_KINDS:
        streak = ensure_progress(db, child.id, session.kind).perfect_streak
    return _serialize(session, perfect_streak=streak)


@router.post("/{session_id}/answer", response_model=SessionOut)
def answer_drill(
    session_id: int,
    body: AnswerIn,
    _role: str = Depends(require_child),
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    child = _child(family)
    session = _get_session(db, session_id, child.id)
    if session.status != "in_progress":
        raise HTTPException(409, "already finished")
    question = next((q for q in session.questions if q.id == body.question_id), None)
    if question is None:
        raise HTTPException(404, "question not found")
    if question.child_answer is not None:
        raise HTTPException(409, "already answered")
    given = str(body.answer)
    question.child_answer = given
    if session.kind in KOKUGO_KINDS:
        question.is_correct = normalize_reading(given) == normalize_reading(question.correct)
    else:
        question.is_correct = given.strip() == str(question.correct).strip()

    step_up = False
    streak: int | None = None
    if all(q.child_answer is not None for q in session.questions):
        now = _now()
        session.status = "finished"
        session.finished_at = now
        session.correct_count = sum(1 for q in session.questions if q.is_correct)
        elapsed = (now - session.started_at).total_seconds()
        session.duration_sec = max(0, int(elapsed))
        award(
            db,
            household_id=family[0].id,
            member_id=session.member_id,
            event_key="drill_complete",
            reason=f"ドリル: {session.kind}",
            related_id=session.id,
        )
        if session.correct_count == 10:
            award(
                db,
                household_id=family[0].id,
                member_id=session.member_id,
                event_key="drill_perfect",
                reason="全問正解ボーナス",
                related_id=session.id,
            )
        if session.kind in PROGRESS_KINDS:
            progress = ensure_progress(db, child.id, session.kind)
            step_up = apply_perfect_streak(progress, session.correct_count or 0)
            streak = progress.perfect_streak
        record_album(
            db,
            member_id=session.member_id,
            kind="drill",
            title="ドリルをやりきった",
            body=f"{session.kind} {session.correct_count}/10",
            related_id=session.id,
        )
    elif session.kind in PROGRESS_KINDS:
        streak = ensure_progress(db, child.id, session.kind).perfect_streak

    db.commit()
    db.refresh(session)
    return _serialize(_get_session(db, session.id, child.id), step_up=step_up, perfect_streak=streak)
