from __future__ import annotations

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .database import get_db
from .models import Household, Member
from .seed import HOUSEHOLD_ID


def parse_role(role: str = Query(default="child")) -> str:
    if role not in ("child", "parent"):
        raise HTTPException(400, "role must be child or parent")
    return role


def require_parent(role: str = Depends(parse_role)) -> str:
    if role != "parent":
        raise HTTPException(403, "parent only")
    return role


def require_child(role: str = Depends(parse_role)) -> str:
    if role != "child":
        raise HTTPException(403, "child only")
    return role


def demo_family(db: Session = Depends(get_db)) -> tuple[Household, Member, Member]:
    hh = db.get(Household, HOUSEHOLD_ID)
    if hh is None:
        raise HTTPException(500, "demo household missing")
    child = next((m for m in hh.members if m.role == "child"), None)
    parent = next((m for m in hh.members if m.role == "parent"), None)
    if child is None or parent is None:
        raise HTTPException(500, "demo members missing")
    return hh, child, parent
