from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent, AuditLog, Incident, ToolCall
from app.schemas import ObservabilitySummary

router = APIRouter(prefix="/observability", tags=["Observability"])


@router.get("/summary", response_model=ObservabilitySummary, summary="Get governance observability summary")
def observability_summary(db: Session = Depends(get_db)) -> ObservabilitySummary:
    agents = list(db.scalars(select(Agent)).all())
    tool_calls = list(db.scalars(select(ToolCall)).all())
    audit_logs = list(db.scalars(select(AuditLog)).all())

    tool_counter = Counter(call.tool_name for call in tool_calls)
    scope_counter = Counter()
    for agent in agents:
        for scope in (agent.requested_scopes or "").split(","):
            if scope:
                scope_counter[scope] += 1

    return ObservabilitySummary(
        total_agents=len(agents),
        approved_agents=sum(1 for agent in agents if agent.status == "approved"),
        revoked_agents=sum(1 for agent in agents if agent.status == "revoked"),
        total_tool_calls=len(tool_calls),
        allowed_tool_calls=sum(1 for call in tool_calls if call.decision == "allowed"),
        denied_tool_calls=sum(1 for call in tool_calls if call.decision == "denied"),
        open_incidents=db.scalar(select(func.count(Incident.id)).where(Incident.status == "open")) or 0,
        high_risk_events=sum(1 for log in audit_logs if log.risk_level == "high"),
        redaction_events=sum(1 for log in audit_logs if log.pii_redacted),
        most_used_tools=[{"tool_name": name, "count": count} for name, count in tool_counter.most_common(5)],
        most_requested_scopes=[{"scope": name, "count": count} for name, count in scope_counter.most_common(5)],
    )
