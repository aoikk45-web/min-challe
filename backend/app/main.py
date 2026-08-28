from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Household, Member
from .seed import HOUSEHOLD_ID, seed_if_empty


class MemberOut(BaseModel):
    id: int
    display_name: str
    role: str
    grade: int | None = None
    avatar: str

    model_config = {"from_attributes": True}


class HouseholdOut(BaseModel):
    id: int
    name: str
    child: MemberOut
    parent: MemberOut


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_if_empty()
    yield


app = FastAPI(title="みんチャレ", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


def _household(db: Session) -> tuple[Household, Member, Member]:
    hh = db.get(Household, HOUSEHOLD_ID)
    if hh is None:
        raise HTTPException(500, "demo household missing")
    child = next((m for m in hh.members if m.role == "child"), None)
    parent = next((m for m in hh.members if m.role == "parent"), None)
    if child is None or parent is None:
        raise HTTPException(500, "demo members missing")
    return hh, child, parent


@app.get("/api/household", response_model=HouseholdOut)
def get_household(
    db: Session = Depends(get_db),
    role: str = Query(default="child"),
):
    if role not in ("child", "parent"):
        raise HTTPException(400, "role must be child or parent")
    hh, child, parent = _household(db)
    return HouseholdOut(id=hh.id, name=hh.name, child=child, parent=parent)
