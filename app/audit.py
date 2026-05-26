from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuditLog


def write_audit_log(
    db: Session,
    *,
    tenant_id: str | None,
    agent_id: int | None,
    owner_user_id: str | None,
    action: str,
    decision: str,
    reason: str,
    tool_name: str | None = None,
    requested_scope: str | None = None,
    pii_redacted: bool = True,
    latency_ms: int | None = None,
) -> AuditLog:
    settings = get_settings()
    log = AuditLog(
        tenant_id=tenant_id,
        agent_id=agent_id,
        owner_user_id=owner_user_id,
        action=action,
        tool_name=tool_name,
        requested_scope=requested_scope,
        decision=decision,
        reason=reason,
        policy_version=settings.policy_version,
        pii_redacted=pii_redacted,
        latency_ms=latency_ms,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
