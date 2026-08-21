"""In-process login lock. One backend worker is enough for this slice."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Lock

MAX_FAILURES = 5
LOCK_MINUTES = 15

_guard = Lock()
_failures: dict[str, int] = {}
_locked_until: dict[str, datetime] = {}


def reset_login_guard() -> None:
    with _guard:
        _failures.clear()
        _locked_until.clear()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _key(email: str) -> str:
    return (email or "").strip().lower()


def locked_until(email: str) -> datetime | None:
    key = _key(email)
    if not key:
        return None
    with _guard:
        until = _locked_until.get(key)
        if until is None:
            return None
        if until <= _now():
            _locked_until.pop(key, None)
            _failures.pop(key, None)
            return None
        return until


def record_failure(email: str) -> datetime | None:
    key = _key(email)
    if not key:
        return None
    with _guard:
        until = _locked_until.get(key)
        if until and until > _now():
            return until
        count = _failures.get(key, 0) + 1
        _failures[key] = count
        if count >= MAX_FAILURES:
            until = _now() + timedelta(minutes=LOCK_MINUTES)
            _locked_until[key] = until
            return until
        return None


def record_success(email: str) -> None:
    key = _key(email)
    if not key:
        return
    with _guard:
        _failures.pop(key, None)
        _locked_until.pop(key, None)
