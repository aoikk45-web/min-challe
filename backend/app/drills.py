from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .database import get_db
from .deps import demo_family, parse_role, require_child
from .drill_progress import (
    MAX_STEP,
    PERFECT_NEEDED,
    apply_perfect_streak,
    ensure_all_progress,
    ensure_progress,
    max_step_for_kind,
    step_label,
)
from .dokkai import pick_three
from .generate import (
    DOKKAI_KINDS,
    KINDS,
    KOKUGO_KINDS,
    MATH_KINDS,
    PROGRESS_KINDS,
    SHAKAI_KINDS,
    RIKA_KINDS,
    generate_ten,
    kokugo_reading_matches,
    normalize_reading,
)
from .album import record_album
from .ledger import award
from .models import DrillQuestion, DrillSession, Household, Member, PointLedger

Kind = Literal[
    "たしざん",
    "ひきざん",
    "かけざん",
    "わりざん",
    "かんじのよみ",
    "じゅくごのよみ",
    "おはなしのどくかい",
    "とどうふけん",
    "にほんのちり",
    "ちずきごう",
    "けんのかたち",
    "いきもののせいかつ",
    "じしゃくとでんき",
]

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
    choices: list[str] | None = None
    image_url: str | None = None
    explanation: str | None = None


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
    points_earned: int | None = None
    passage_title: str | None = None
    passage: str | None = None


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


_LEGACY_SYMBOL_FILES = {
    "camp.svg": "shoubousho.png",
    "park.svg": "kannkousho.png",
    "school.png": "shouchuugakkou.png",
    "school.svg": "shouchuugakkou.png",
    "post.png": "yuubinkyoku.png",
    "post.svg": "yuubinkyoku.png",
    "hospital.png": "byouin.png",
    "hospital.svg": "byouin.png",
    "police.png": "keisatusho.png",
    "police.svg": "keisatusho.png",
    "shrine.png": "jinjya.png",
    "shrine.svg": "jinjya.png",
    "temple.png": "jiin.png",
    "temple.svg": "jiin.png",
    "fire_station.png": "shoubousho.png",
    "fire_station.svg": "shoubousho.png",
    "sightseeing.png": "kannkousho.png",
    "sightseeing.svg": "kannkousho.png",
    "station.png": "ekijrsen.png",
    "station.svg": "ekijrsen.png",
    "library.png": "toshokan.png",
    "library.svg": "toshokan.png",
    "city_hall.png": "siyakusho.png",
    "city_hall.svg": "siyakusho.png",
    "port.png": "kouwan.png",
    "port.svg": "kouwan.png",
}

_LEGACY_SYMBOL_BASENAMES = frozenset(
    {
        "school",
        "post",
        "hospital",
        "police",
        "shrine",
        "temple",
        "fire_station",
        "sightseeing",
        "station",
        "library",
        "city_hall",
        "port",
        "camp",
        "park",
    }
)


def _is_legacy_symbol_url(url: str | None) -> bool:
    if not url or not url.startswith("/shakai/symbols/"):
        return False
    name = url.rsplit("/", 1)[-1]
    if name in _LEGACY_SYMBOL_FILES:
        return True
    base = name.rsplit(".", 1)[0]
    return base in _LEGACY_SYMBOL_BASENAMES or name.endswith(".svg")


def _normalize_image_url(url: str | None) -> str | None:
    if not url or not url.startswith("/shakai/symbols/"):
        return url
    name = url.rsplit("/", 1)[-1]
    if name in _LEGACY_SYMBOL_FILES:
        return f"/shakai/symbols/{_LEGACY_SYMBOL_FILES[name]}"
    if name.endswith(".svg"):
        return f"/shakai/symbols/{name[:-4]}.png"
    return url


def _session_uses_legacy_symbols(session: DrillSession) -> bool:
    if session.kind != "ちずきごう":
        return False
    return any(_is_legacy_symbol_url(q.image_url) for q in session.questions)


def _close_stale_session(session: DrillSession) -> None:
    now = _now()
    session.status = "finished"
    session.finished_at = now
    session.correct_count = sum(1 for q in session.questions if q.is_correct)
    elapsed = (now - session.started_at).total_seconds()
    session.duration_sec = max(0, int(elapsed))


def _parse_choices_json(raw: str | None) -> tuple[list[str] | None, str | None]:
    if not raw:
        return None, None
    data = json.loads(raw)
    if isinstance(data, list):
        return data, None
    if isinstance(data, dict):
        choices = data.get("choices")
        if choices is not None:
            choices = [str(c) for c in choices]
        explanation = data.get("explanation")
        return choices, str(explanation) if explanation else None
    return None, None


def _points_earned_for_session(db: Session, member_id: int, session: DrillSession) -> int | None:
    if session.status != "finished":
        return None
    total = db.scalar(
        select(func.coalesce(func.sum(PointLedger.delta), 0)).where(
            PointLedger.member_id == member_id,
            PointLedger.related_id == session.id,
            PointLedger.event_key.in_(("drill_complete", "drill_perfect")),
        )
    )
    return int(total or 0)


def _serialize(
    session: DrillSession,
    *,
    step_up: bool = False,
    perfect_streak: int | None = None,
    points_earned: int | None = None,
) -> SessionOut:
    questions = sorted(session.questions, key=lambda q: q.seq)
    finished = session.status == "finished"
    kind = session.kind
    label = step_label(session.step, kind) if session.step is not None else None
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
        passage_title=session.passage_title,
        passage=session.passage,
        questions=[
            QuestionOut(
                id=q.id,
                seq=q.seq,
                prompt=q.prompt,
                child_answer=q.child_answer,
                is_correct=q.is_correct,
                correct=q.correct if finished or q.child_answer is not None else None,
                choices=choices,
                explanation=explanation if (finished or q.child_answer is not None) else None,
                image_url=_normalize_image_url(q.image_url),
            )
            for q in questions
            for choices, explanation in [_parse_choices_json(q.choices_json)]
        ],
        perfect_streak=perfect_streak,
        step_label=label,
        step_up=step_up,
        max_step=max_step_for_kind(kind),
        points_earned=points_earned,
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
            step_label=step_label(row.step, row.kind),
            max_step=max_step_for_kind(row.kind),
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
        if _session_uses_legacy_symbols(existing):
            _close_stale_session(existing)
            db.flush()
            existing = None
        else:
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
    if kind in DOKKAI_KINDS:
        story = pick_three(gen_step)
        session.passage_title = story.title
        session.passage = story.passage
        for seq, question in enumerate(story.questions, start=1):
            db.add(
                DrillQuestion(
                    session_id=session.id,
                    seq=seq,
                    prompt=question.prompt,
                    correct=question.correct,
                    choices_json=json.dumps(
                        {"choices": question.choices, "explanation": question.explanation},
                        ensure_ascii=False,
                    ),
                )
            )
    else:
        for seq, question in enumerate(generate_ten(kind, gen_step), start=1):
            db.add(
                DrillQuestion(
                    session_id=session.id,
                    seq=seq,
                    prompt=question.prompt,
                    correct=question.correct,
                    choices_json=json.dumps(question.choices, ensure_ascii=False) if question.choices else None,
                    image_url=question.image_url,
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
    points = _points_earned_for_session(db, child.id, session)
    return _serialize(session, perfect_streak=streak, points_earned=points)


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
        question.is_correct = kokugo_reading_matches(given, question.correct)
    elif session.kind in DOKKAI_KINDS or session.kind in SHAKAI_KINDS or session.kind in RIKA_KINDS:
        question.is_correct = normalize_reading(given) == normalize_reading(question.correct)
    else:
        question.is_correct = given.strip() == str(question.correct).strip()

    step_up = False
    streak: int | None = None
    points_earned: int | None = None
    if all(q.child_answer is not None for q in session.questions):
        now = _now()
        session.status = "finished"
        session.finished_at = now
        session.correct_count = sum(1 for q in session.questions if q.is_correct)
        elapsed = (now - session.started_at).total_seconds()
        session.duration_sec = max(0, int(elapsed))
        points_earned = award(
            db,
            household_id=family[0].id,
            member_id=session.member_id,
            event_key="drill_complete",
            reason=f"ドリル: {session.kind}",
            related_id=session.id,
        )
        total_q = len(session.questions)
        if session.correct_count == total_q:
            points_earned += award(
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
            body=f"{session.kind} {session.correct_count}/{total_q}",
            related_id=session.id,
        )
    elif session.kind in PROGRESS_KINDS:
        streak = ensure_progress(db, child.id, session.kind).perfect_streak

    db.commit()
    db.refresh(session)
    if points_earned is None and session.status == "finished":
        points_earned = _points_earned_for_session(db, child.id, session)
    return _serialize(
        _get_session(db, session.id, child.id),
        step_up=step_up,
        perfect_streak=streak,
        points_earned=points_earned,
    )
