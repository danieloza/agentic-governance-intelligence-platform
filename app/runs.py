from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.audit import write_audit_log
from app.database import get_db
from app.models import Agent, AgentRun, ToolCall
from app.schemas import RunFinishRequest, RunResponse, RunStartRequest

router = APIRouter(prefix="/runs", tags=["Runs"])


@router.post("/start", response_model=RunResponse, status_code=status.HTTP_201_CREATED, summary="Start agent run")
def start_run(payload: RunStartRequest, db: Session = Depends(get_db)) -> AgentRun:
    agent = db.get(Agent, payload.agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.status == "revoked":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent is revoked")

    run = AgentRun(
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        objective=payload.objective,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    write_audit_log(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        owner_user_id=agent.owner_user_id,
        action="run_started",
        decision="allowed",
        reason=f"Run started: {payload.objective}",
    )
    return run


@router.post("/{run_id}/finish", response_model=RunResponse, summary="Finish agent run")
def finish_run(run_id: int, payload: RunFinishRequest, db: Session = Depends(get_db)) -> AgentRun:
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    tool_counts = db.execute(
        select(
            func.count(ToolCall.id),
            func.sum(case((ToolCall.decision == "denied", 1), else_=0)),
        ).where(ToolCall.run_id == run.id)
    ).one()
    run.status = payload.status
    run.finished_at = datetime.now(timezone.utc)
    run.risk_score = payload.risk_score
    run.tool_call_count = int(tool_counts[0] or 0)
    run.blocked_call_count = int(tool_counts[1] or 0)
    db.commit()
    db.refresh(run)

    agent = db.get(Agent, run.agent_id)
    write_audit_log(
        db,
        tenant_id=run.tenant_id,
        agent_id=run.agent_id,
        owner_user_id=agent.owner_user_id if agent else None,
        action="run_finished",
        decision="allowed" if payload.status == "completed" else "denied",
        reason=f"Run finished with status {payload.status}",
        risk_level="high" if payload.risk_score >= 70 else "medium" if payload.risk_score >= 30 else "low",
    )
    return run


@router.get("", response_model=list[RunResponse], summary="List agent runs")
def list_runs(
    agent_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> list[AgentRun]:
    query = select(AgentRun).order_by(AgentRun.started_at.desc(), AgentRun.id.desc())
    if agent_id is not None:
        query = query.where(AgentRun.agent_id == agent_id)
    if status_filter:
        query = query.where(AgentRun.status == status_filter)
    return list(db.scalars(query).all())


@router.get("/{run_id}", response_model=RunResponse, summary="Get agent run detail")
def get_run(run_id: int, db: Session = Depends(get_db)) -> AgentRun:
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run
