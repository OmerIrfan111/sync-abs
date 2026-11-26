import logging
from typing import Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

MAX_FAILED_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60


def _redis():
    from app.services.listing_service import get_redis_client
    return get_redis_client()


def _key(email: str) -> str:
    return f"login:fails:{(email or '').strip().lower()}"


def ensure_not_locked(email: str) -> None:
    """Refuse the attempt outright while an account is locked. Staff passwords
    can be short, so repeated guessing has to be slowed down. If Redis is
    unreachable this does nothing rather than blocking everyone from logging in."""
    r = _redis()
    if not r:
        return
    try:
        count = int(r.get(_key(email)) or 0)
        if count >= MAX_FAILED_ATTEMPTS:
            minutes = max(1, (r.ttl(_key(email)) or LOCK_SECONDS) // 60 + 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many wrong passwords. This account is locked for about {minutes} more minute(s).",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Login throttle unavailable: {exc}")


def record_failure(email: str) -> None:
    r = _redis()
    if not r:
        return
    try:
        key = _key(email)
        count = r.incr(key)
        if count == 1 or count == MAX_FAILED_ATTEMPTS:
            r.expire(key, LOCK_SECONDS)
    except Exception as exc:
        logger.warning(f"Login throttle unavailable: {exc}")


def clear_failures(email: str) -> None:
    r = _redis()
    if not r:
        return
    try:
        r.delete(_key(email))
    except Exception:
        pass
