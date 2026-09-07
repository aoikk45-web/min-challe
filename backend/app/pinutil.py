from __future__ import annotations

import hashlib
import hmac
import secrets

DEFAULT_UNLOCK_PIN = "0000"
DEFAULT_PARENT_PIN = "1234"


def hash_pin(pin: str) -> str:
    salt = secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"{salt}${digest.hex()}"


def verify_pin(pin: str, stored: str | None) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, digest = stored.split("$", 1)
    check = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return hmac.compare_digest(check, digest)


def ensure_default_pins(hh) -> None:
    if not hh.unlock_pin_hash:
        hh.unlock_pin_hash = hash_pin(DEFAULT_UNLOCK_PIN)
    if not hh.parent_pin_hash:
        hh.parent_pin_hash = hash_pin(DEFAULT_PARENT_PIN)
