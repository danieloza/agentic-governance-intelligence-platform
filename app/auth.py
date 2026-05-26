from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def create_scoped_token(
    *,
    agent_id: int,
    tenant_id: str,
    owner_user_id: str,
    scopes: list[str],
    expires_in_hours: int,
) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
    payload = {
        "agent_id": agent_id,
        "tenant_id": tenant_id,
        "owner_user_id": owner_user_id,
        "scopes": scopes,
        "exp": expires_at,
        "token_type": "agent_scoped_token",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_scoped_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}") from exc

    if payload.get("token_type") != "agent_scoped_token":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    return payload


def get_token_payload(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return decode_scoped_token(credentials.credentials)


def get_tenant_header(x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing X-Tenant-ID header")
    return x_tenant_id
