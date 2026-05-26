from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import write_audit_log
from app.database import get_db
from app.models import Agent, Incident
from app.redaction import redact_pii
from app.schemas import IncidentResolveRequest, IncidentResponse

router = APIRouter(prefix="/incidents", tags=["Incidents"])


def create_incident(
    db: Session,
    *,
    tenant_id: str,
    agent_id: int,
    severity: str,
    title: str,
    description: str,
    policy_reason: str,
    run_id: int | None = None,
    related_tool_call_id: int | None = None,
) -> Incident:
    safe_payload = redact_pii({"description": description, "policy_reason": policy_reason})
    incident = Incident(
        tenant_id=tenant_id,
        agent_id=agent_id,
        run_id=run_id,
        related_tool_call_id=related_tool_call_id,
        severity=severity,
        title=title,
        description=safe_payload["description"],
        policy_reason=safe_payload["policy_reason"],
        status="open",
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@router.get("", response_model=list[IncidentResponse], summary="List incidents")
def list_incidents(
    tenant_id: str | None = Query(default=None),
    agent_id: int | None = Query(default=None),
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> list[Incident]:
    query = select(Incident).order_by(Incident.created_at.desc(), Incident.id.desc())
    if tenant_id:
        query = query.where(Incident.tenant_id == tenant_id)
    if agent_id is not None:
        query = query.where(Incident.agent_id == agent_id)
    if severity:
        query = query.where(Incident.severity == severity)
    if status_filter:
        query = query.where(Incident.status == status_filter)
    return list(db.scalars(query).all())


@router.get("/{incident_id}", response_model=IncidentResponse, summary="Get incident detail")
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


@router.post("/{incident_id}/resolve", response_model=IncidentResponse, summary="Resolve incident")
def resolve_incident(
    incident_id: int,
    payload: IncidentResolveRequest,
    db: Session = Depends(get_db),
) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    incident.status = "resolved"
    incident.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(incident)

    agent = db.get(Agent, incident.agent_id)
    write_audit_log(
        db,
        tenant_id=incident.tenant_id,
        agent_id=incident.agent_id,
        owner_user_id=agent.owner_user_id if agent else None,
        action="incident_resolved",
        decision="allowed",
        reason=f"Resolved by {payload.resolved_by}: {payload.resolution_note}",
        risk_level=incident.severity,
    )
    return incident
