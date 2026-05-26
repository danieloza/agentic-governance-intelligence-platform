from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GraphEdge


def write_graph_edge(
    db: Session,
    *,
    tenant_id: str,
    source_type: str,
    source_id: str | int,
    relation: str,
    target_type: str,
    target_id: str | int,
    metadata: dict[str, Any] | None = None,
) -> GraphEdge:
    edge = GraphEdge(
        tenant_id=tenant_id,
        source_type=source_type,
        source_id=str(source_id),
        relation=relation,
        target_type=target_type,
        target_id=str(target_id),
        metadata_json=json.dumps(metadata or {}, sort_keys=True),
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge


def record_governed_tool_call(
    db: Session,
    *,
    tenant_id: str,
    agent_id: int,
    owner_user_id: str,
    tool_name: str,
    scope: str,
    output_type: str,
    output_id: str,
) -> None:
    write_graph_edge(
        db,
        tenant_id=tenant_id,
        source_type="agent",
        source_id=agent_id,
        relation="owned_by",
        target_type="user",
        target_id=owner_user_id,
    )
    write_graph_edge(
        db,
        tenant_id=tenant_id,
        source_type="agent",
        source_id=agent_id,
        relation="approved_for_scope",
        target_type="scope",
        target_id=scope,
    )
    write_graph_edge(
        db,
        tenant_id=tenant_id,
        source_type="scope",
        source_id=scope,
        relation="allows_tool",
        target_type="tool",
        target_id=tool_name,
    )
    write_graph_edge(
        db,
        tenant_id=tenant_id,
        source_type="agent",
        source_id=agent_id,
        relation="called_tool",
        target_type="tool",
        target_id=tool_name,
        metadata={"scope": scope},
    )
    write_graph_edge(
        db,
        tenant_id=tenant_id,
        source_type="tool",
        source_id=tool_name,
        relation="produced",
        target_type=output_type,
        target_id=output_id,
        metadata={"agent_id": agent_id, "scope": scope},
    )


def list_graph_edges(
    db: Session,
    *,
    tenant_id: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    relation: str | None = None,
    target_type: str | None = None,
) -> list[GraphEdge]:
    query = select(GraphEdge).order_by(GraphEdge.created_at.desc(), GraphEdge.id.desc())
    if tenant_id:
        query = query.where(GraphEdge.tenant_id == tenant_id)
    if source_type:
        query = query.where(GraphEdge.source_type == source_type)
    if source_id:
        query = query.where(GraphEdge.source_id == source_id)
    if relation:
        query = query.where(GraphEdge.relation == relation)
    if target_type:
        query = query.where(GraphEdge.target_type == target_type)
    return list(db.scalars(query).all())
