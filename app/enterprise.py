from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Agent
from app.policies import TOOL_SCOPE_MAP, evaluate_tool_access

router = APIRouter(prefix="/enterprise", tags=["Enterprise Layers"])


class PolicySimulationRequest(BaseModel):
    agent_id: int | None = None
    tenant_id: str = Field(default="local", min_length=2, max_length=120)
    tool_name: str = Field(min_length=2, max_length=160)
    token_scopes: list[str] = Field(default_factory=list)
    proposed_policy_version: str | None = None
    dry_run: bool = True


class PolicySimulationResponse(BaseModel):
    decision: Literal["allowed", "denied"]
    reason: str
    required_scope: str
    risk_level: str
    approval_preview: str
    blast_radius: dict[str, Any]
    dry_run: bool


ENTERPRISE_LAYERS: list[dict[str, Any]] = [
    {
        "key": "policy-simulation-studio",
        "name": "Policy Simulation Studio",
        "layer": "Governance",
        "status": "available",
        "maturity": "MVP",
        "summary": "Dry-run policy changes, simulate tool calls and preview approval impact before rollout.",
        "capabilities": ["simulate tool call", "simulate scopes", "dry-run mode", "approval preview", "blast radius analysis"],
        "route": "/enterprise/policy/simulate",
    },
    {
        "key": "agent-memory-governance",
        "name": "Agent Memory Governance",
        "layer": "Governance",
        "status": "designed",
        "maturity": "roadmap",
        "summary": "Controls what agents can remember, for how long and across which isolation boundary.",
        "capabilities": ["memory TTL", "memory isolation", "memory redaction", "retention policy", "cross-agent boundaries"],
        "route": "/enterprise/memory/policies",
    },
    {
        "key": "human-oversight-center",
        "name": "Human Oversight Center",
        "layer": "Oversight",
        "status": "available",
        "maturity": "MVP",
        "summary": "Approval inbox, review queue, escalations and intervention timeline for risky agent actions.",
        "capabilities": ["approval inbox", "review queue", "manual overrides", "approval chains", "intervention timeline"],
        "route": "/enterprise/oversight/queue",
    },
    {
        "key": "sandbox-execution-layer",
        "name": "Sandbox Execution Layer",
        "layer": "Security",
        "status": "designed",
        "maturity": "roadmap",
        "summary": "Execution boundary for coding agents with filesystem, network and resource controls.",
        "capabilities": ["filesystem sandbox", "network restrictions", "CPU/RAM quotas", "command allowlists", "ephemeral environments"],
        "route": "/enterprise/sandbox/profile",
    },
    {
        "key": "cost-token-intelligence",
        "name": "Cost & Token Intelligence",
        "layer": "Intelligence",
        "status": "available",
        "maturity": "MVP",
        "summary": "Tracks token usage, model costs, anomalies and budget thresholds for governed agent runs.",
        "capabilities": ["token tracking", "model usage", "cost anomalies", "run cost breakdown", "budget thresholds"],
        "route": "/enterprise/cost/summary",
    },
    {
        "key": "inference-router",
        "name": "Inference Router",
        "layer": "Inference",
        "status": "designed",
        "maturity": "roadmap",
        "summary": "Routes workloads across model providers by policy, latency, cost and fallback strategy.",
        "capabilities": ["provider routing", "fallback models", "latency-aware routing", "cost-aware routing", "local model support"],
        "route": "/enterprise/inference/routes",
    },
    {
        "key": "agent-trust-engine",
        "name": "Agent Trust Engine",
        "layer": "Risk",
        "status": "available",
        "maturity": "MVP",
        "summary": "Scores agents using incident history, denied actions, approval frequency and scope sensitivity.",
        "capabilities": ["risk score", "incident history", "approval frequency", "scope sensitivity", "failure history"],
        "route": "/enterprise/trust/summary",
    },
    {
        "key": "replay-forensics-studio",
        "name": "Replay & Forensics Studio",
        "layer": "Operations",
        "status": "available",
        "maturity": "MVP",
        "summary": "Reconstructs timelines for denied calls, incidents and high-risk decisions.",
        "capabilities": ["timeline reconstruction", "incident replay", "tool-call replay", "decision comparison", "state snapshots"],
        "route": "/enterprise/forensics/timeline",
    },
    {
        "key": "organizations-layer",
        "name": "Organizations Layer",
        "layer": "Shared Platform",
        "status": "designed",
        "maturity": "roadmap",
        "summary": "Tenant isolation for org policies, workspaces, tools, scopes and audit history.",
        "capabilities": ["org isolation", "tenant policies", "workspace separation", "per-org audit", "per-org scopes"],
        "route": "/enterprise/orgs/summary",
    },
    {
        "key": "context-governance-layer",
        "name": "Knowledge & Context Governance",
        "layer": "Context",
        "status": "designed",
        "maturity": "roadmap",
        "summary": "Controls approved knowledge sources, document sensitivity, retrieval logs and source attribution.",
        "capabilities": ["approved sources", "context filtering", "RAG audit", "document sensitivity", "retrieval logging"],
        "route": "/enterprise/context/sources",
    },
]


@router.get("/layers", summary="List AGIP enterprise governance layers")
def list_enterprise_layers() -> dict[str, Any]:
    available = sum(1 for layer in ENTERPRISE_LAYERS if layer["status"] == "available")
    return {
        "layers": ENTERPRISE_LAYERS,
        "summary": {
            "total_layers": len(ENTERPRISE_LAYERS),
            "available_layers": available,
            "roadmap_layers": len(ENTERPRISE_LAYERS) - available,
        },
    }


@router.post("/policy/simulate", response_model=PolicySimulationResponse, summary="Dry-run a tool policy decision")
def simulate_policy(payload: PolicySimulationRequest, db: Session = Depends(get_db)) -> PolicySimulationResponse:
    settings = get_settings()
    agent = db.get(Agent, payload.agent_id) if payload.agent_id is not None else None
    if payload.agent_id is not None and agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    token_payload = {
        "agent_id": payload.agent_id if payload.agent_id is not None else -1,
        "tenant_id": payload.tenant_id,
        "scopes": payload.token_scopes,
        "exp": 4_102_444_800,
    }
    decision = evaluate_tool_access(
        agent=agent,
        token_payload=token_payload,
        tool_name=payload.tool_name,
        policy_version=payload.proposed_policy_version or settings.policy_version,
    )
    required_scope = decision.required_scope or TOOL_SCOPE_MAP.get(payload.tool_name, "")
    missing_scope = bool(required_scope and required_scope not in payload.token_scopes)
    approval_preview = "human approval required" if decision.risk_level == "high" else "standard approval path"
    if missing_scope:
        approval_preview = f"add scope {required_scope} before approval"

    return PolicySimulationResponse(
        decision="allowed" if decision.allowed else "denied",
        reason=decision.reason,
        required_scope=required_scope,
        risk_level=decision.risk_level,
        approval_preview=approval_preview,
        blast_radius={
            "affected_tool": payload.tool_name,
            "scope_sensitivity": "high" if decision.risk_level == "high" else "standard",
            "agents_with_scope": _count_agents_with_scope(db, required_scope),
            "requires_incident_watch": decision.risk_level in {"medium", "high"},
        },
        dry_run=payload.dry_run,
    )


@router.get("/memory/policies", summary="Preview memory governance policies")
def memory_policies() -> dict[str, Any]:
    return {
        "default_ttl_hours": 24,
        "pii_memory": "blocked",
        "cross_agent_memory": "denied_by_default",
        "retention": [
            {"class": "conversation", "ttl_hours": 24, "redaction": "enabled"},
            {"class": "tool_result", "ttl_hours": 12, "redaction": "enabled"},
            {"class": "incident_evidence", "ttl_hours": 720, "redaction": "enabled"},
        ],
    }


@router.get("/oversight/queue", summary="List human oversight queue preview")
def oversight_queue() -> dict[str, Any]:
    return {
        "items": [
            {"title": "High-risk dev patch proposal", "risk": "high", "chain": ["owner", "security"], "sla": "15m"},
            {"title": "Finance expense workflow", "risk": "medium", "chain": ["owner"], "sla": "1h"},
            {"title": "Context source approval", "risk": "medium", "chain": ["knowledge-owner"], "sla": "4h"},
        ]
    }


@router.get("/sandbox/profile", summary="Preview sandbox runtime controls")
def sandbox_profile() -> dict[str, Any]:
    return {
        "filesystem": "workspace_only",
        "network": "deny_by_default",
        "cpu_limit": "2 vCPU",
        "memory_limit": "2 GiB",
        "command_allowlist": ["pytest", "python -m", "ruff", "mypy"],
        "ephemeral": True,
    }


@router.get("/cost/summary", summary="Get cost and token intelligence summary")
def cost_summary() -> dict[str, Any]:
    return {
        "tokens_7d": 1_842_000,
        "estimated_cost_usd": 92.4,
        "budget_threshold_usd": 150,
        "anomalies": [{"agent": "Research Agent", "change": "+38%", "reason": "larger retrieval context"}],
        "by_model": [
            {"model": "fast-governance", "tokens": 940_000, "cost_usd": 28.2},
            {"model": "reasoning-review", "tokens": 610_000, "cost_usd": 48.8},
            {"model": "local-fallback", "tokens": 292_000, "cost_usd": 15.4},
        ],
    }


@router.get("/inference/routes", summary="Preview inference routing policies")
def inference_routes() -> dict[str, Any]:
    return {
        "routes": [
            {"workload": "low-risk classification", "strategy": "lowest_cost", "fallback": "local model"},
            {"workload": "incident review", "strategy": "highest_reasoning", "fallback": "secondary hosted model"},
            {"workload": "PII-sensitive summary", "strategy": "local_first", "fallback": "human review"},
        ]
    }


@router.get("/trust/summary", summary="Get agent trust engine summary")
def trust_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    agents = db.query(Agent).order_by(Agent.id.asc()).all()
    scores = []
    for agent in agents:
        scope_count = len([scope for scope in (agent.approved_scopes or agent.requested_scopes or "").split(",") if scope])
        base = 92 if agent.status == "approved" else 68 if agent.status == "pending_approval" else 30
        scores.append(
            {
                "agent_id": agent.id,
                "agent_name": agent.agent_name,
                "status": agent.status,
                "trust_score": max(0, min(100, base - scope_count * 3)),
                "scope_sensitivity": "high" if scope_count >= 3 else "standard",
            }
        )
    return {"agents": scores, "average_trust": round(sum(item["trust_score"] for item in scores) / max(1, len(scores)), 1)}


@router.get("/forensics/timeline", summary="Preview replay and forensics timeline")
def forensics_timeline() -> dict[str, Any]:
    return {
        "timeline": [
            {"step": "agent token issued", "decision": "allowed", "evidence": "scoped JWT"},
            {"step": "tool call requested", "decision": "pending", "evidence": "scope mapping"},
            {"step": "policy evaluated", "decision": "denied", "evidence": "required scope missing"},
            {"step": "incident opened", "decision": "review", "evidence": "high-risk attempted action"},
        ]
    }


@router.get("/orgs/summary", summary="Preview multi-tenant organization controls")
def orgs_summary() -> dict[str, Any]:
    return {
        "isolation_model": "tenant_id plus future RLS-ready policies",
        "workspaces": ["governance", "runtime", "security", "intelligence"],
        "per_org_controls": ["scopes", "tools", "policies", "audit retention", "budget threshold"],
    }


@router.get("/context/sources", summary="Preview context governance sources")
def context_sources() -> dict[str, Any]:
    return {
        "approved_sources": [
            {"name": "policy handbook", "sensitivity": "internal", "retrieval_logging": True},
            {"name": "contract templates", "sensitivity": "confidential", "retrieval_logging": True},
            {"name": "public product docs", "sensitivity": "public", "retrieval_logging": True},
        ],
        "default_filtering": "deny sensitive context unless scope and policy allow it",
    }


def _count_agents_with_scope(db: Session, scope: str) -> int:
    if not scope:
        return 0
    agents = db.query(Agent).all()
    return sum(1 for agent in agents if scope in set((agent.approved_scopes or "").split(",")))
