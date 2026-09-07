from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from .database import get_db
from .deps import demo_family
from .models import Household, Member
from .pinutil import hash_pin, verify_pin

router = APIRouter(prefix="/api/auth", tags=["auth"])

PIN_RE = re.compile(r"^\d{4}$")


def _validate_pin(value: str) -> str:
    value = value.strip()
    if not PIN_RE.match(value):
        raise ValueError("PINは4桁の数字にしてね")
    return value


class AuthStatusOut(BaseModel):
    configured: bool
    household_name: str


class SetupIn(BaseModel):
    unlock_pin: str = Field(min_length=4, max_length=4)
    parent_pin: str = Field(min_length=4, max_length=4)

    @field_validator("unlock_pin", "parent_pin")
    @classmethod
    def pin_digits(cls, value: str) -> str:
        return _validate_pin(value)


class PinIn(BaseModel):
    pin: str = Field(min_length=4, max_length=4)

    @field_validator("pin")
    @classmethod
    def pin_digits(cls, value: str) -> str:
        return _validate_pin(value)


class ChangePinsIn(BaseModel):
    current_parent_pin: str = Field(min_length=4, max_length=4)
    unlock_pin: str | None = Field(default=None, min_length=4, max_length=4)
    parent_pin: str | None = Field(default=None, min_length=4, max_length=4)

    @field_validator("current_parent_pin")
    @classmethod
    def current_digits(cls, value: str) -> str:
        return _validate_pin(value)

    @field_validator("unlock_pin", "parent_pin")
    @classmethod
    def optional_digits(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_pin(value)


@router.get("/status", response_model=AuthStatusOut)
def auth_status(
    family: tuple[Household, Member, Member] = Depends(demo_family),
):
    hh = family[0]
    configured = bool(hh.unlock_pin_hash and hh.parent_pin_hash)
    return AuthStatusOut(configured=configured, household_name=hh.name)


@router.post("/setup", status_code=204)
def setup_pins(
    body: SetupIn,
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    hh = family[0]
    if hh.unlock_pin_hash and hh.parent_pin_hash:
        raise HTTPException(400, "すでに設定済みです")
    hh.unlock_pin_hash = hash_pin(body.unlock_pin)
    hh.parent_pin_hash = hash_pin(body.parent_pin)
    db.commit()


@router.post("/unlock", status_code=204)
def unlock_app(
    body: PinIn,
    family: tuple[Household, Member, Member] = Depends(demo_family),
):
    hh = family[0]
    if not hh.unlock_pin_hash:
        raise HTTPException(400, "まだPINがありません")
    if not verify_pin(body.pin, hh.unlock_pin_hash):
        raise HTTPException(401, "PINがちがいます")


@router.post("/verify-parent", status_code=204)
def verify_parent(
    body: PinIn,
    family: tuple[Household, Member, Member] = Depends(demo_family),
):
    hh = family[0]
    if not hh.parent_pin_hash:
        raise HTTPException(400, "まだPINがありません")
    if not verify_pin(body.pin, hh.parent_pin_hash):
        raise HTTPException(401, "PINがちがいます")


@router.post("/change-pins", status_code=204)
def change_pins(
    body: ChangePinsIn,
    family: tuple[Household, Member, Member] = Depends(demo_family),
    db: Session = Depends(get_db),
):
    hh = family[0]
    if not hh.parent_pin_hash or not verify_pin(body.current_parent_pin, hh.parent_pin_hash):
        raise HTTPException(401, "いまのおうちの人PINがちがいます")
    if body.unlock_pin is None and body.parent_pin is None:
        raise HTTPException(400, "変更するPINを入れてね")
    if body.unlock_pin is not None:
        hh.unlock_pin_hash = hash_pin(body.unlock_pin)
    if body.parent_pin is not None:
        hh.parent_pin_hash = hash_pin(body.parent_pin)
    db.commit()
