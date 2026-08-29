from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Household(Base):
    __tablename__ = "households"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))

    members: Mapped[list[Member]] = relationship(back_populates="household")
    point_rules: Mapped[list[PointRule]] = relationship(back_populates="household")
    rewards: Mapped[list[Reward]] = relationship(back_populates="household")


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"))
    display_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(16))
    grade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avatar: Mapped[str] = mapped_column(String(8), default="⭐")

    household: Mapped[Household] = relationship(back_populates="members")
    study_plans: Mapped[list[StudyPlan]] = relationship(back_populates="member")
    drill_sessions: Mapped[list[DrillSession]] = relationship(back_populates="member")
    drill_progress: Mapped[list["DrillProgress"]] = relationship(back_populates="member")
    point_ledger: Mapped[list[PointLedger]] = relationship(back_populates="member")
    album_entries: Mapped[list[AlbumEntry]] = relationship(back_populates="member")


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    plan_date: Mapped[date] = mapped_column(Date)
    subject: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(120))
    minutes: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    member: Mapped[Member] = relationship(back_populates="study_plans")


class DrillSession(Base):
    __tablename__ = "drill_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    kind: Mapped[str] = mapped_column(String(16))
    grade: Mapped[int] = mapped_column(Integer)
    step: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="in_progress")
    correct_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    member: Mapped[Member] = relationship(back_populates="drill_sessions")
    questions: Mapped[list[DrillQuestion]] = relationship(back_populates="session")


class DrillQuestion(Base):
    __tablename__ = "drill_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("drill_sessions.id"))
    seq: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[str] = mapped_column(String(400))
    correct: Mapped[str] = mapped_column(String(40))
    choices_json: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    child_answer: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    session: Mapped[DrillSession] = relationship(back_populates="questions")


class DrillProgress(Base):
    __tablename__ = "drill_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    kind: Mapped[str] = mapped_column(String(16))
    step: Mapped[int] = mapped_column(Integer, default=1)
    perfect_streak: Mapped[int] = mapped_column(Integer, default=0)

    member: Mapped[Member] = relationship(back_populates="drill_progress")


class PointRule(Base):
    __tablename__ = "point_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"))
    event_key: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(80))
    points: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    household: Mapped[Household] = relationship(back_populates="point_rules")


class Reward(Base):
    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"))
    name: Mapped[str] = mapped_column(String(80))
    cost: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    household: Mapped[Household] = relationship(back_populates="rewards")


class PointLedger(Base):
    __tablename__ = "point_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(120))
    event_key: Mapped[str] = mapped_column(String(40))
    related_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)

    member: Mapped[Member] = relationship(back_populates="point_ledger")


class AlbumEntry(Base):
    __tablename__ = "album_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    kind: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(80))
    body: Mapped[str] = mapped_column(String(200), default="")
    stamp: Mapped[str] = mapped_column(String(8))
    related_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)

    member: Mapped[Member] = relationship(back_populates="album_entries")
