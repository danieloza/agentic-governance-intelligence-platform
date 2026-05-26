from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import write_audit_log
from app.auth import create_scoped_token, get_tenant_header, get_token_payload
from app.config import get_settings
from app.database import Base, engine, get_db
from app.graph import list_graph_edges, record_governed_tool_call
from app.models import Agent, ApprovalRecord, AuditLog, GraphEdge
from app.policies import TOOL_SCOPE_MAP, evaluate_tool_access
from app.platform import (
    build_automation_detail,
    build_incident_detail,
    build_intelligence_detail,
    build_layer_detail,
    build_platform_activity,
    build_platform_overview,
    build_readiness_detail,
    build_regression_detail,
    build_runtime_detail,
)
from app.redaction import redact_pii
from app.schemas import (
    AgentAuthManifest,
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    ApprovalRequest,
    ApprovalResponse,
    AuditLogResponse,
    BrandInsightRequest,
    BrandReportRequest,
    EmployeePolicySearchRequest,
    ExpenseReviewRequest,
    GraphEdgeResponse,
    InvoiceSummaryRequest,
    ContractClauseRequest,
    ContractRiskRequest,
    ManifestPolicyRules,
    McpToolInvocationRequest,
    OpsReportRequest,
    RevocationRequest,
    RevocationResponse,
    TokenRequest,
    TokenResponse,
    ToolResponse,
    VALID_SCOPES,
)
from app.tools import (
    finance_create_expense_review,
    finance_get_invoice_summary,
    brand_analyze_market_signals,
    brand_create_report,
    hr_search_employee_policy,
    legal_search_contract_clause,
    legal_summarize_contract_risk,
    mcp_invoke_tool,
    ops_create_report,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    if settings.demo_seed_enabled and settings.environment != "test":
        seed_demo_data()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Agentic Governance Intelligence Platform combines scoped agent auth, MCP tool governance, "
        "brand intelligence workflows, graph relationships and auditability in one FastAPI control plane."
    ),
    lifespan=lifespan,
)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def parse_scopes(value: str | None) -> list[str]:
    if not value:
        return []
    return [scope for scope in value.split(",") if scope]


def seed_demo_data() -> None:
    with Session(engine) as db:
        has_agents = db.scalar(select(func.count(Agent.id)))
        if has_agents:
            return

        now = datetime.now(timezone.utc)
        demo_agents = [
            Agent(
                tenant_id="enterprise-hr",
                agent_name="HR Policy Assistant",
                agent_type="mcp_client",
                requested_scopes="hr:policy:read",
                approved_scopes="hr:policy:read",
                owner_user_id="anna.kowalska",
                reason="HR Department",
                status="approved",
                approved_by="daniel.ozarski",
                approval_expires_at=now + timedelta(hours=24),
            ),
            Agent(
                tenant_id="enterprise-finance",
                agent_name="Finance Invoice Agent",
                agent_type="service_agent",
                requested_scopes="finance:invoice:read,finance:expense:create",
                approved_scopes="finance:invoice:read",
                owner_user_id="michal.nowak",
                reason="Finance Department",
                status="pending_approval",
            ),
            Agent(
                tenant_id="enterprise-legal",
                agent_name="Legal Contract Analyst",
                agent_type="mcp_client",
                requested_scopes="legal:contract:read,legal:risk:summarize",
                approved_scopes="legal:contract:read",
                owner_user_id="justyna.zz",
                reason="Legal Department",
                status="approved",
                approved_by="daniel.ozarski",
                approval_expires_at=now + timedelta(hours=12),
            ),
            Agent(
                tenant_id="enterprise-ops",
                agent_name="Ops Report Builder",
                agent_type="workflow_agent",
                requested_scopes="ops:report:create",
                approved_scopes="ops:report:create",
                owner_user_id="piotr.wrobel",
                reason="Operations",
                status="revoked",
                approved_by="daniel.ozarski",
                approval_expires_at=now + timedelta(hours=6),
                revoked_at=now - timedelta(minutes=30),
                revoked_by="daniel.ozarski",
                revocation_reason="Workflow frozen after policy review",
            ),
            Agent(
                tenant_id="enterprise-platform",
                agent_name="MCP Tool Broker",
                agent_type="mcp_gateway_agent",
                requested_scopes="mcp:tool:invoke,mcp:approval:write",
                approved_scopes="mcp:tool:invoke",
                owner_user_id="platform.owner",
                reason="Governed MCP tool routing",
                status="approved",
                approved_by="platform.admin",
                approval_expires_at=now + timedelta(hours=10),
            ),
            Agent(
                tenant_id="enterprise-marketing",
                agent_name="Brand Insight Agent",
                agent_type="brand_intelligence_agent",
                requested_scopes="brand:insight:read,brand:report:create",
                approved_scopes="brand:insight:read",
                owner_user_id="marketing.owner",
                reason="Market signal analysis",
                status="approved",
                approved_by="platform.admin",
                approval_expires_at=now + timedelta(hours=10),
            ),
        ]
        db.add_all(demo_agents)
        db.commit()

        agents = list(db.scalars(select(Agent)).all())
        by_name = {agent.agent_name: agent for agent in agents}

        demo_logs = [
            AuditLog(
                tenant_id="enterprise-finance",
                agent_id=by_name["Finance Invoice Agent"].id,
                owner_user_id="michal.nowak",
                action="registration",
                decision="pending",
                reason="Agent registered and waiting for approval",
                policy_version=settings.policy_version,
                pii_redacted=True,
            ),
            AuditLog(
                tenant_id="enterprise-hr",
                agent_id=by_name["HR Policy Assistant"].id,
                owner_user_id="anna.kowalska",
                action="approval",
                tool_name=None,
                decision="allowed",
                reason="Approved by daniel.ozarski",
                policy_version=settings.policy_version,
                pii_redacted=True,
            ),
            AuditLog(
                tenant_id="enterprise-hr",
                agent_id=by_name["HR Policy Assistant"].id,
                owner_user_id="anna.kowalska",
                action="token_issuing",
                decision="allowed",
                reason="Scoped token issued",
                policy_version=settings.policy_version,
                pii_redacted=True,
            ),
            AuditLog(
                tenant_id="enterprise-legal",
                agent_id=by_name["Legal Contract Analyst"].id,
                owner_user_id="justyna.zz",
                action="denied_tool_call",
                tool_name="legal.search_contract_clause",
                requested_scope="legal:contract:read",
                decision="denied",
                reason="default_deny: required scope missing from token",
                policy_version=settings.policy_version,
                pii_redacted=True,
                latency_ms=18,
            ),
            AuditLog(
                tenant_id="enterprise-hr",
                agent_id=by_name["HR Policy Assistant"].id,
                owner_user_id="anna.kowalska",
                action="allowed_tool_call",
                tool_name="hr.search_employee_policy",
                requested_scope="hr:policy:read",
                decision="allowed",
                reason="allowed",
                policy_version=settings.policy_version,
                pii_redacted=True,
                latency_ms=11,
            ),
            AuditLog(
                tenant_id="enterprise-ops",
                agent_id=by_name["Ops Report Builder"].id,
                owner_user_id="piotr.wrobel",
                action="revocation",
                decision="revoked",
                reason="Revoked by daniel.ozarski: Workflow frozen after policy review",
                policy_version=settings.policy_version,
                pii_redacted=True,
            ),
            AuditLog(
                tenant_id="enterprise-platform",
                agent_id=by_name["MCP Tool Broker"].id,
                owner_user_id="platform.owner",
                action="allowed_tool_call",
                tool_name="mcp.invoke_tool",
                requested_scope="mcp:tool:invoke",
                decision="allowed",
                reason="MCP request routed through policy boundary",
                policy_version=settings.policy_version,
                pii_redacted=True,
                latency_ms=22,
            ),
            AuditLog(
                tenant_id="enterprise-marketing",
                agent_id=by_name["Brand Insight Agent"].id,
                owner_user_id="marketing.owner",
                action="allowed_tool_call",
                tool_name="brand.analyze_market_signals",
                requested_scope="brand:insight:read",
                decision="allowed",
                reason="Market signals converted into structured insight candidates",
                policy_version=settings.policy_version,
                pii_redacted=True,
                latency_ms=31,
            ),
            AuditLog(
                tenant_id="enterprise-marketing",
                agent_id=by_name["Brand Insight Agent"].id,
                owner_user_id="marketing.owner",
                action="denied_tool_call",
                tool_name="brand.create_report",
                requested_scope="brand:report:create",
                decision="denied",
                reason="default_deny: required scope missing from token",
                policy_version=settings.policy_version,
                pii_redacted=True,
                latency_ms=16,
            ),
        ]
        db.add_all(demo_logs)
        db.commit()

        demo_edges = [
            GraphEdge(
                tenant_id="enterprise-hr",
                source_type="agent",
                source_id=str(by_name["HR Policy Assistant"].id),
                relation="approved_for_scope",
                target_type="scope",
                target_id="hr:policy:read",
                metadata_json="{}",
            ),
            GraphEdge(
                tenant_id="enterprise-hr",
                source_type="scope",
                source_id="hr:policy:read",
                relation="allows_tool",
                target_type="tool",
                target_id="hr.search_employee_policy",
                metadata_json="{}",
            ),
            GraphEdge(
                tenant_id="enterprise-hr",
                source_type="tool",
                source_id="hr.search_employee_policy",
                relation="produced",
                target_type="policy_result",
                target_id="Remote Work Policy",
                metadata_json='{"seeded": true}',
            ),
            GraphEdge(
                tenant_id="enterprise-legal",
                source_type="agent",
                source_id=str(by_name["Legal Contract Analyst"].id),
                relation="called_tool",
                target_type="tool",
                target_id="legal.search_contract_clause",
                metadata_json='{"decision": "denied"}',
            ),
            GraphEdge(
                tenant_id="enterprise-platform",
                source_type="agent",
                source_id=str(by_name["MCP Tool Broker"].id),
                relation="called_tool",
                target_type="tool",
                target_id="mcp.invoke_tool",
                metadata_json='{"scope": "mcp:tool:invoke"}',
            ),
            GraphEdge(
                tenant_id="enterprise-platform",
                source_type="tool",
                source_id="mcp.invoke_tool",
                relation="produced",
                target_type="mcp_request",
                target_id="MCP-SEEDED-001",
                metadata_json='{"approval_required": true}',
            ),
            GraphEdge(
                tenant_id="enterprise-marketing",
                source_type="agent",
                source_id=str(by_name["Brand Insight Agent"].id),
                relation="called_tool",
                target_type="tool",
                target_id="brand.analyze_market_signals",
                metadata_json='{"scope": "brand:insight:read"}',
            ),
            GraphEdge(
                tenant_id="enterprise-marketing",
                source_type="tool",
                source_id="brand.analyze_market_signals",
                relation="produced",
                target_type="brand_insight",
                target_id="BI-SEEDED-001",
                metadata_json='{"signals": 3}',
            ),
        ]
        db.add_all(demo_edges)
        db.commit()


def get_agent_or_404(db: Session, agent_id: int) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


def validate_scopes(scopes: list[str], *, tenant_id: str | None, agent_id: int | None, owner_user_id: str, db: Session) -> None:
    invalid = [scope for scope in scopes if scope not in VALID_SCOPES]
    if invalid:
        write_audit_log(
            db,
            tenant_id=tenant_id,
            agent_id=agent_id,
            owner_user_id=owner_user_id,
            action="invalid_scope_attempt",
            decision="denied",
            reason=f"Invalid scopes requested: {', '.join(invalid)}",
            requested_scope=",".join(invalid),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"invalid_scopes": invalid})


def build_tool_response(
    *,
    tool_name: str,
    required_scope: str,
    payload: dict,
    db: Session | None = None,
    tenant_id: str | None = None,
    agent: Agent | None = None,
    output_type: str = "tool_output",
    output_id: str | None = None,
) -> ToolResponse:
    redacted_payload = redact_pii(payload)
    if db is not None and tenant_id is not None and agent is not None:
        record_governed_tool_call(
            db,
            tenant_id=tenant_id,
            agent_id=agent.id,
            owner_user_id=agent.owner_user_id,
            tool_name=tool_name,
            scope=required_scope,
            output_type=output_type,
            output_id=output_id or str(redacted_payload.get("id") or redacted_payload.get("report_id") or redacted_payload.get("insight_id") or tool_name),
        )
    return ToolResponse(
        tool_name=tool_name,
        scope_used=required_scope,
        policy_version=settings.policy_version,
        pii_redacted=True,
        data=redacted_payload,
    )


def enforce_tool_policy(
    *,
    tool_name: str,
    token_payload: dict,
    tenant_id: str,
    db: Session,
) -> tuple[Agent, str]:
    started = perf_counter()
    agent_id = int(token_payload["agent_id"])
    agent = db.get(Agent, agent_id)
    decision = evaluate_tool_access(
        agent=agent,
        token_payload=token_payload,
        tool_name=tool_name,
        policy_version=settings.policy_version,
    )
    latency_ms = int((perf_counter() - started) * 1000)
    owner_user_id = token_payload.get("owner_user_id")
    token_tenant_id = token_payload.get("tenant_id")

    if token_tenant_id != tenant_id:
        write_audit_log(
            db,
            tenant_id=token_tenant_id,
            agent_id=agent_id,
            owner_user_id=owner_user_id,
            action="policy_failure",
            tool_name=tool_name,
            requested_scope=TOOL_SCOPE_MAP.get(tool_name),
            decision="denied",
            reason="default_deny: request tenant does not match token tenant",
            pii_redacted=True,
            latency_ms=latency_ms,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="default_deny: request tenant does not match token tenant")

    if not decision.allowed:
        action = "policy_failure" if "default_deny" in decision.reason else "denied_tool_call"
        write_audit_log(
            db,
            tenant_id=token_tenant_id,
            agent_id=agent_id,
            owner_user_id=owner_user_id,
            action=action,
            tool_name=tool_name,
            requested_scope=decision.required_scope,
            decision="denied",
            reason=decision.reason,
            pii_redacted=decision.pii_redaction_required,
            latency_ms=latency_ms,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)

    write_audit_log(
        db,
        tenant_id=token_tenant_id,
        agent_id=agent_id,
        owner_user_id=owner_user_id,
        action="allowed_tool_call",
        tool_name=tool_name,
        requested_scope=decision.required_scope,
        decision="allowed",
        reason=decision.reason,
        pii_redacted=decision.pii_redaction_required,
        latency_ms=latency_ms,
    )
    return agent, decision.required_scope


@app.get("/", include_in_schema=False)
def dashboard_home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/dashboard/overview", tags=["dashboard"])
def dashboard_overview(db: Session = Depends(get_db)) -> dict:
    agents = list(db.scalars(select(Agent).order_by(Agent.created_at.desc())).all())
    audit_logs = list(db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc())).all())

    total_agents = len(agents)
    total_tenants = len({agent.tenant_id for agent in agents})
    pending_approvals = sum(1 for agent in agents if agent.status == "pending_approval")
    approved_agents = sum(1 for agent in agents if agent.status == "approved")
    revoked_agents = sum(1 for agent in agents if agent.status == "revoked")
    active_tokens = sum(1 for log in audit_logs if log.action == "token_issuing" and log.decision == "allowed")
    denied_requests = sum(1 for log in audit_logs if log.decision == "denied")

    scope_counts: dict[str, int] = {scope: 0 for scope in VALID_SCOPES}
    for agent in agents:
        for scope in parse_scopes(agent.approved_scopes):
            if scope in scope_counts:
                scope_counts[scope] += 1

    max_scope_count = max(scope_counts.values()) if scope_counts else 1
    scope_distribution = [
        {"scope": scope, "count": count, "percent": int((count / max_scope_count) * 100) if max_scope_count else 0}
        for scope, count in scope_counts.items()
    ]

    allowed_counts = [44, 55, 68, 68, 50, 43, 48]
    denied_counts = [4, 6, 9, 18, 7, 8, 11]

    return {
        "metrics": {
            "total_agents": total_agents,
            "pending_approvals": pending_approvals,
            "approved_agents": approved_agents,
            "revoked_agents": revoked_agents,
            "active_tokens": active_tokens,
            "denied_requests": denied_requests,
            "sparkline": [
                [22, 29, 25, 36, 30, 40, 33, 47],
                [12, 14, 18, 15, 13, 19, 16, 26],
                [18, 24, 20, 28, 25, 30, 27, 34],
                [9, 12, 18, 14, 17, 19, 16, 28],
            ],
            "total_tenants": total_tenants,
        },
        "scope_distribution": scope_distribution,
        "tool_usage": [
            {"label": "May 19", "allowed": allowed_counts[0] * 2, "denied": denied_counts[0] * 6},
            {"label": "May 20", "allowed": allowed_counts[1] * 2, "denied": denied_counts[1] * 6},
            {"label": "May 21", "allowed": allowed_counts[2] * 2, "denied": denied_counts[2] * 6},
            {"label": "May 22", "allowed": allowed_counts[3] * 2, "denied": denied_counts[3] * 6},
            {"label": "May 23", "allowed": allowed_counts[4] * 2, "denied": denied_counts[4] * 6},
            {"label": "May 24", "allowed": allowed_counts[5] * 2, "denied": denied_counts[5] * 6},
            {"label": "May 25", "allowed": allowed_counts[6] * 2, "denied": denied_counts[6] * 6},
        ],
        "policy_controls": [
            {"name": "Default policy", "detail": "Default deny on every tool access"},
            {"name": "PII redaction", "detail": "Enabled for responses and audit-safe outputs"},
            {"name": "Secret redaction", "detail": "Enabled for MCP arguments, tokens and API keys"},
            {"name": "Audit logging", "detail": "Registration, token issue, policy decision and revocation"},
            {"name": "MCP security", "detail": "MCP tool invocation is governed through scoped access"},
            {"name": "Brand intelligence", "detail": "Market insight workflows require approved business scopes"},
            {"name": "Relationship graph", "detail": "Allowed tool calls write explainable graph edges"},
            {"name": "Token expiration", "detail": "Short-lived scoped JWT credentials"},
            {"name": "Policy version", "detail": settings.policy_version},
        ],
    }


@app.get("/platform/overview", tags=["platform"])
def platform_overview(db: Session = Depends(get_db)) -> dict:
    return build_platform_overview(db)


@app.get("/platform/activity", tags=["platform"])
def platform_activity(db: Session = Depends(get_db)) -> dict:
    return build_platform_activity(db)


@app.get("/platform/layers/{layer_key}", tags=["platform"])
def platform_layer(layer_key: str, db: Session = Depends(get_db)) -> dict:
    return build_layer_detail(layer_key, db)


@app.get("/platform/runtime", tags=["platform"])
def platform_runtime() -> dict:
    return build_runtime_detail()


@app.get("/platform/automation", tags=["platform"])
def platform_automation() -> dict:
    return build_automation_detail()


@app.get("/platform/incidents", tags=["platform"])
def platform_incidents() -> dict:
    return build_incident_detail()


@app.get("/platform/regression", tags=["platform"])
def platform_regression() -> dict:
    return build_regression_detail()


@app.get("/platform/readiness", tags=["platform"])
def platform_readiness() -> dict:
    return build_readiness_detail()


@app.get("/platform/intelligence", tags=["platform"])
def platform_intelligence() -> dict:
    return build_intelligence_detail()


@app.get("/dashboard/access-requests", tags=["dashboard"])
def dashboard_access_requests(db: Session = Depends(get_db)) -> dict:
    agents = list(db.scalars(select(Agent).order_by(Agent.created_at.desc())).all())
    rows = []
    for agent in agents:
        approval_expires_at = ensure_utc(agent.approval_expires_at)
        created_at = ensure_utc(agent.created_at)
        revoked_at = ensure_utc(agent.revoked_at)
        rows.append(
            {
                "agent_id": agent.id,
                "tenant_id": agent.tenant_id,
                "agent_name": agent.agent_name,
                "agent_type": agent.agent_type,
                "requested_scopes": parse_scopes(agent.requested_scopes),
                "approved_scopes": parse_scopes(agent.approved_scopes),
                "owner_user_id": agent.owner_user_id,
                "reason": agent.reason,
                "status": "pending" if agent.status == "pending_approval" else agent.status,
                "approval_window": approval_expires_at.isoformat() if approval_expires_at else "Awaiting approval",
                "approved_by": agent.approved_by,
                "revoked_by": agent.revoked_by,
                "revoked_at": revoked_at.isoformat() if revoked_at else None,
                "revocation_reason": agent.revocation_reason,
                "created_at": created_at.isoformat() if created_at else None,
            }
        )
    return {"rows": rows}


@app.get("/dashboard/recent-activity", tags=["dashboard"])
def dashboard_recent_activity(db: Session = Depends(get_db)) -> dict:
    logs = list(db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).limit(6)).all())
    items = []
    for log in logs:
        title = log.action.replace("_", " ").title()
        timestamp = ensure_utc(log.timestamp)
        items.append(
            {
                "id": log.id,
                "tenant_id": log.tenant_id,
                "agent_id": log.agent_id,
                "owner_user_id": log.owner_user_id,
                "title": title,
                "meta": log.reason,
                "decision": log.decision,
                "icon": "",
                "timestamp": timestamp.strftime("%H:%M UTC") if timestamp else "n/a",
                "timestamp_iso": timestamp.isoformat() if timestamp else None,
                "tool_name": log.tool_name,
                "requested_scope": log.requested_scope,
                "policy_version": log.policy_version,
                "pii_redacted": log.pii_redacted,
                "latency_ms": log.latency_ms,
                "action": log.action,
            }
        )
    return {"items": items}


@app.get("/.well-known/agent-auth.json", response_model=AgentAuthManifest, tags=["agent-auth"])
def get_manifest() -> AgentAuthManifest:
    return AgentAuthManifest(
        auth_flows_supported=["agent_registration", "human_approval", "scoped_jwt_token"],
        credential_type="jwt",
        token_endpoint="/agent-auth/token",
        approval_endpoint="/agent-auth/approve/{agent_id}",
        revocation_endpoint="/agent-auth/revoke/{agent_id}",
        audit_endpoint="/agent-auth/audit",
        available_scopes=VALID_SCOPES,
        policy_rules=ManifestPolicyRules(
            default_deny=True,
            short_lived_scoped_tokens=True,
            human_approval_required=True,
            pii_redaction_enabled=True,
            audit_logging_enabled=True,
            revocation_supported=True,
            tenant_isolation_enabled=True,
        ),
    )


@app.post("/agent-auth/register", response_model=AgentRegistrationResponse, status_code=status.HTTP_201_CREATED, tags=["agent-auth"])
def register_agent(payload: AgentRegistrationRequest, db: Session = Depends(get_db)) -> AgentRegistrationResponse:
    validate_scopes(payload.requested_scopes, tenant_id=payload.tenant_id, agent_id=None, owner_user_id=payload.owner_user_id, db=db)
    agent = Agent(
        tenant_id=payload.tenant_id,
        agent_name=payload.agent_name,
        agent_type=payload.agent_type,
        requested_scopes=",".join(payload.requested_scopes),
        owner_user_id=payload.owner_user_id,
        reason=payload.reason,
        callback_url=str(payload.callback_url) if payload.callback_url else None,
        status="pending_approval",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    write_audit_log(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        owner_user_id=agent.owner_user_id,
        action="registration",
        decision="pending",
        reason="Agent registered and waiting for human approval",
        requested_scope=agent.requested_scopes,
    )
    return AgentRegistrationResponse(agent_id=agent.id, tenant_id=agent.tenant_id, status=agent.status, requested_scopes=payload.requested_scopes)


@app.post("/agent-auth/approve/{agent_id}", response_model=ApprovalResponse, tags=["agent-auth"])
def approve_agent(agent_id: int, payload: ApprovalRequest, db: Session = Depends(get_db)) -> ApprovalResponse:
    agent = get_agent_or_404(db, agent_id)
    validate_scopes(payload.approved_scopes, tenant_id=agent.tenant_id, agent_id=agent.id, owner_user_id=agent.owner_user_id, db=db)

    requested_scopes = set(parse_scopes(agent.requested_scopes))
    approved_scopes = set(payload.approved_scopes)
    if not approved_scopes.issubset(requested_scopes):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approved scopes must be a subset of originally requested scopes")

    expires_at = datetime.now(timezone.utc) + timedelta(hours=payload.expires_in_hours)
    agent.status = "approved"
    agent.approved_scopes = ",".join(payload.approved_scopes)
    agent.approved_by = payload.approved_by
    agent.approval_expires_at = expires_at

    record = ApprovalRecord(
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        approved_scopes=",".join(payload.approved_scopes),
        approved_by=payload.approved_by,
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()
    db.refresh(agent)

    write_audit_log(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        owner_user_id=agent.owner_user_id,
        action="approval",
        decision="allowed",
        reason=f"Approved by {payload.approved_by}",
        requested_scope=agent.approved_scopes,
    )
    return ApprovalResponse(agent_id=agent.id, tenant_id=agent.tenant_id, status=agent.status, approved_scopes=payload.approved_scopes, expires_at=expires_at)


@app.post("/agent-auth/token", response_model=TokenResponse, tags=["agent-auth"])
def issue_token(payload: TokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    agent = get_agent_or_404(db, payload.agent_id)

    if agent.status != "approved":
        write_audit_log(
            db,
            tenant_id=agent.tenant_id,
            agent_id=agent.id,
            owner_user_id=agent.owner_user_id,
            action="token_issuing",
            decision="denied",
            reason="Agent is not approved",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent is not approved")

    if agent.revoked_at is not None or agent.status == "revoked":
        write_audit_log(
            db,
            tenant_id=agent.tenant_id,
            agent_id=agent.id,
            owner_user_id=agent.owner_user_id,
            action="token_issuing",
            decision="revoked",
            reason="Agent is revoked",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent is revoked")

    approval_expires_at = ensure_utc(agent.approval_expires_at)
    now_utc = datetime.now(timezone.utc)

    if approval_expires_at and approval_expires_at <= now_utc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Approval has expired")

    approved_scopes = parse_scopes(agent.approved_scopes)
    expires_in_hours = max(1, min(settings.token_expiry_minutes_default // 60 or 1, 24))
    if approval_expires_at:
        remaining_hours = max(1, int((approval_expires_at - now_utc).total_seconds() // 3600) or 1)
        expires_in_hours = min(expires_in_hours, remaining_hours)

    token, expires_at = create_scoped_token(
        agent_id=agent.id,
        tenant_id=agent.tenant_id,
        owner_user_id=agent.owner_user_id,
        scopes=approved_scopes,
        expires_in_hours=expires_in_hours,
    )
    write_audit_log(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        owner_user_id=agent.owner_user_id,
        action="token_issuing",
        decision="allowed",
        reason="Scoped token issued",
        requested_scope=",".join(approved_scopes),
    )
    return TokenResponse(access_token=token, token_type="bearer", expires_at=expires_at, tenant_id=agent.tenant_id, scopes=approved_scopes)


@app.post("/agent-auth/revoke/{agent_id}", response_model=RevocationResponse, tags=["agent-auth"])
def revoke_agent(agent_id: int, payload: RevocationRequest, db: Session = Depends(get_db)) -> RevocationResponse:
    agent = get_agent_or_404(db, agent_id)
    revoked_at = datetime.now(timezone.utc)
    agent.status = "revoked"
    agent.revoked_at = revoked_at
    agent.revoked_by = payload.revoked_by
    agent.revocation_reason = payload.reason
    db.commit()

    write_audit_log(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        owner_user_id=agent.owner_user_id,
        action="revocation",
        decision="revoked",
        reason=f"Revoked by {payload.revoked_by}: {payload.reason}",
    )
    return RevocationResponse(agent_id=agent.id, tenant_id=agent.tenant_id, status=agent.status, revoked_at=revoked_at)


@app.get("/agent-auth/audit", response_model=list[AuditLogResponse], tags=["agent-auth"])
def get_audit_logs(
    tenant_id: str | None = Query(default=None),
    agent_id: int | None = Query(default=None),
    decision: str | None = Query(default=None),
    tool_name: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
    if tenant_id:
        query = query.where(AuditLog.tenant_id == tenant_id)
    if agent_id is not None:
        query = query.where(AuditLog.agent_id == agent_id)
    if decision:
        query = query.where(AuditLog.decision == decision)
    if tool_name:
        query = query.where(AuditLog.tool_name == tool_name)
    if scope:
        query = query.where(AuditLog.requested_scope == scope)
    if user_id:
        query = query.where(AuditLog.owner_user_id == user_id)
    return list(db.scalars(query).all())


@app.post("/tools/hr/search_employee_policy", response_model=ToolResponse, tags=["tools"])
def tool_hr_search_employee_policy(
    payload: EmployeePolicySearchRequest,
    token_payload: dict = Depends(get_token_payload),
    tenant_id: str = Depends(get_tenant_header),
    db: Session = Depends(get_db),
) -> ToolResponse:
    agent, scope = enforce_tool_policy(tool_name="hr.search_employee_policy", token_payload=token_payload, tenant_id=tenant_id, db=db)
    return build_tool_response(
        tool_name="hr.search_employee_policy",
        required_scope=scope,
        payload=hr_search_employee_policy(payload.employee_query),
        db=db,
        tenant_id=tenant_id,
        agent=agent,
        output_type="policy_result",
        output_id=payload.employee_query,
    )


@app.post("/tools/finance/get_invoice_summary", response_model=ToolResponse, tags=["tools"])
def tool_finance_get_invoice_summary(
    payload: InvoiceSummaryRequest,
    token_payload: dict = Depends(get_token_payload),
    tenant_id: str = Depends(get_tenant_header),
    db: Session = Depends(get_db),
) -> ToolResponse:
    agent, scope = enforce_tool_policy(tool_name="finance.get_invoice_summary", token_payload=token_payload, tenant_id=tenant_id, db=db)
    return build_tool_response(
        tool_name="finance.get_invoice_summary",
        required_scope=scope,
        payload=finance_get_invoice_summary(payload.invoice_id),
        db=db,
        tenant_id=tenant_id,
        agent=agent,
        output_type="invoice_summary",
        output_id=payload.invoice_id,
    )


@app.post("/tools/finance/create_expense_review", response_model=ToolResponse, tags=["tools"])
def tool_finance_create_expense_review(
    payload: ExpenseReviewRequest,
    token_payload: dict = Depends(get_token_payload),
    tenant_id: str = Depends(get_tenant_header),
    db: Session = Depends(get_db),
) -> ToolResponse:
    agent, scope = enforce_tool_policy(tool_name="finance.create_expense_review", token_payload=token_payload, tenant_id=tenant_id, db=db)
    return build_tool_response(
        tool_name="finance.create_expense_review",
        required_scope=scope,
        payload=finance_create_expense_review(payload.expense_title, payload.amount, payload.currency),
        db=db,
        tenant_id=tenant_id,
        agent=agent,
        output_type="expense_review",
        output_id=payload.expense_title,
    )


@app.post("/tools/legal/search_contract_clause", response_model=ToolResponse, tags=["tools"])
def tool_legal_search_contract_clause(
    payload: ContractClauseRequest,
    token_payload: dict = Depends(get_token_payload),
    tenant_id: str = Depends(get_tenant_header),
    db: Session = Depends(get_db),
) -> ToolResponse:
    agent, scope = enforce_tool_policy(tool_name="legal.search_contract_clause", token_payload=token_payload, tenant_id=tenant_id, db=db)
    return build_tool_response(
        tool_name="legal.search_contract_clause",
        required_scope=scope,
        payload=legal_search_contract_clause(payload.contract_id, payload.clause_query),
        db=db,
        tenant_id=tenant_id,
        agent=agent,
        output_type="contract_clause",
        output_id=payload.contract_id,
    )


@app.post("/tools/legal/summarize_contract_risk", response_model=ToolResponse, tags=["tools"])
def tool_legal_summarize_contract_risk(
    payload: ContractRiskRequest,
    token_payload: dict = Depends(get_token_payload),
    tenant_id: str = Depends(get_tenant_header),
    db: Session = Depends(get_db),
) -> ToolResponse:
    agent, scope = enforce_tool_policy(tool_name="legal.summarize_contract_risk", token_payload=token_payload, tenant_id=tenant_id, db=db)
    return build_tool_response(
        tool_name="legal.summarize_contract_risk",
        required_scope=scope,
        payload=legal_summarize_contract_risk(payload.contract_id),
        db=db,
        tenant_id=tenant_id,
        agent=agent,
        output_type="contract_risk_summary",
        output_id=payload.contract_id,
    )


@app.post("/tools/ops/create_report", response_model=ToolResponse, tags=["tools"])
def tool_ops_create_report(
    payload: OpsReportRequest,
    token_payload: dict = Depends(get_token_payload),
    tenant_id: str = Depends(get_tenant_header),
    db: Session = Depends(get_db),
) -> ToolResponse:
    agent, scope = enforce_tool_policy(tool_name="ops.create_report", token_payload=token_payload, tenant_id=tenant_id, db=db)
    return build_tool_response(
        tool_name="ops.create_report",
        required_scope=scope,
        payload=ops_create_report(payload.report_name, payload.department),
        db=db,
        tenant_id=tenant_id,
        agent=agent,
        output_type="ops_report",
        output_id=payload.report_name,
    )


@app.post("/tools/mcp/invoke_tool", response_model=ToolResponse, tags=["mcp-security"])
def tool_mcp_invoke_tool(
    payload: McpToolInvocationRequest,
    token_payload: dict = Depends(get_token_payload),
    tenant_id: str = Depends(get_tenant_header),
    db: Session = Depends(get_db),
) -> ToolResponse:
    agent, scope = enforce_tool_policy(tool_name="mcp.invoke_tool", token_payload=token_payload, tenant_id=tenant_id, db=db)
    tool_payload = mcp_invoke_tool(
        mcp_server_id=payload.mcp_server_id,
        tool_name=payload.tool_name,
        justification=payload.justification,
        estimated_tokens=payload.estimated_tokens,
        arguments=payload.arguments,
    )
    return build_tool_response(
        tool_name="mcp.invoke_tool",
        required_scope=scope,
        payload=tool_payload,
        db=db,
        tenant_id=tenant_id,
        agent=agent,
        output_type="mcp_request",
        output_id=tool_payload["mcp_request_id"],
    )


@app.post("/tools/brand/analyze_market_signals", response_model=ToolResponse, tags=["brand-insight"])
def tool_brand_analyze_market_signals(
    payload: BrandInsightRequest,
    token_payload: dict = Depends(get_token_payload),
    tenant_id: str = Depends(get_tenant_header),
    db: Session = Depends(get_db),
) -> ToolResponse:
    agent, scope = enforce_tool_policy(tool_name="brand.analyze_market_signals", token_payload=token_payload, tenant_id=tenant_id, db=db)
    tool_payload = brand_analyze_market_signals(
        brand_name=payload.brand_name,
        competitor_names=payload.competitor_names,
        signals=payload.signals,
    )
    return build_tool_response(
        tool_name="brand.analyze_market_signals",
        required_scope=scope,
        payload=tool_payload,
        db=db,
        tenant_id=tenant_id,
        agent=agent,
        output_type="brand_insight",
        output_id=tool_payload["insight_id"],
    )


@app.post("/tools/brand/create_report", response_model=ToolResponse, tags=["brand-insight"])
def tool_brand_create_report(
    payload: BrandReportRequest,
    token_payload: dict = Depends(get_token_payload),
    tenant_id: str = Depends(get_tenant_header),
    db: Session = Depends(get_db),
) -> ToolResponse:
    agent, scope = enforce_tool_policy(tool_name="brand.create_report", token_payload=token_payload, tenant_id=tenant_id, db=db)
    tool_payload = brand_create_report(
        brand_name=payload.brand_name,
        report_name=payload.report_name,
        insight_ids=payload.insight_ids,
    )
    return build_tool_response(
        tool_name="brand.create_report",
        required_scope=scope,
        payload=tool_payload,
        db=db,
        tenant_id=tenant_id,
        agent=agent,
        output_type="brand_report",
        output_id=tool_payload["report_id"],
    )


@app.get("/graph/edges", response_model=list[GraphEdgeResponse], tags=["relationship-graph"])
def get_graph_edges(
    tenant_id: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    relation: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[GraphEdge]:
    return list_graph_edges(
        db,
        tenant_id=tenant_id,
        source_type=source_type,
        source_id=source_id,
        relation=relation,
        target_type=target_type,
    )


@app.get("/graph/agents/{agent_id}/explain", tags=["relationship-graph"])
def explain_agent_graph(agent_id: int, db: Session = Depends(get_db)) -> dict:
    agent = get_agent_or_404(db, agent_id)
    outgoing = list_graph_edges(db, tenant_id=agent.tenant_id, source_type="agent", source_id=str(agent.id))
    related_tools = [edge.target_id for edge in outgoing if edge.relation == "called_tool"]
    produced = []
    for tool_name in related_tools:
        produced.extend(list_graph_edges(db, tenant_id=agent.tenant_id, source_type="tool", source_id=tool_name, relation="produced"))
    return {
        "agent": {
            "agent_id": agent.id,
            "tenant_id": agent.tenant_id,
            "agent_name": agent.agent_name,
            "status": agent.status,
            "approved_scopes": parse_scopes(agent.approved_scopes),
        },
        "summary": "Graph explanation connects this agent to approved scopes, governed tools and business outputs.",
        "called_tools": sorted(set(related_tools)),
        "produced_outputs": [
            {"type": edge.target_type, "id": edge.target_id, "metadata": edge.metadata_json}
            for edge in produced
        ],
        "edge_count": len(outgoing) + len(produced),
    }
