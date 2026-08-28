from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .database import Base, engine
from .deps import demo_family, parse_role
from .models import Household, Member
from .album import router as album_router
from .plans import router as plans_router
from .drills import router as drills_router
from .points import router as points_router
from .seed import seed_if_empty


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
app.include_router(plans_router)
app.include_router(drills_router)
app.include_router(points_router)
app.include_router(album_router)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/household", response_model=HouseholdOut)
def get_household(
    family: tuple[Household, Member, Member] = Depends(demo_family),
    _role: str = Depends(parse_role),
):
    hh, child, parent = family
    return HouseholdOut(id=hh.id, name=hh.name, child=child, parent=parent)
