from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Household(Base):
    __tablename__ = "households"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))

    members: Mapped[list[Member]] = relationship(back_populates="household")


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
