"""사용자 인증 세션 CRUD (Turso DB 기반 영구 저장)."""

import secrets
from datetime import datetime, timedelta, timezone

from jkhenry.repository.db import UserSessionModel, get_engine
from sqlalchemy.orm import Session

_SESSION_DAYS = 30


def create_session(email: str, name: str) -> str:
    token = secrets.token_hex(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=_SESSION_DAYS)
    with Session(get_engine()) as s:
        s.add(UserSessionModel(
            token=token,
            email=email,
            name=name,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
        ))
        s.commit()
    return token


def get_session(token: str) -> dict | None:
    """유효한 세션이면 {'email', 'name', 'token'} 반환, 없거나 만료면 None."""
    if not token:
        return None
    with Session(get_engine()) as s:
        record = s.get(UserSessionModel, token)
        if not record:
            return None
        expires = datetime.fromisoformat(record.expires_at)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            s.delete(record)
            s.commit()
            return None
        return {"email": record.email, "name": record.name, "token": token}


def delete_session(token: str) -> None:
    if not token:
        return
    with Session(get_engine()) as s:
        record = s.get(UserSessionModel, token)
        if record:
            s.delete(record)
            s.commit()
