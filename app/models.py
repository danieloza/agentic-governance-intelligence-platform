from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    requested_scopes: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    callback_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending_approval", nullable=False, index=True)
    approved_scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    approvals: Mapped[list[ApprovalRecord]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="agent", cascade="all, delete-orphan")


class ApprovalRecord(Base):
    __tablename__ = "approval_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), nullable=False, index=True)
    approved_scopes: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    agent: Mapped[Agent] = relationship(back_populates="approvals")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    tool_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    requested_scope: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    decision: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    pii_redacted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    agent: Mapped[Agent | None] = relationship(back_populates="audit_logs")


class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    relation: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
