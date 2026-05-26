from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, AuditLog, GraphEdge
from app.schemas import VALID_SCOPES


@dataclass(frozen=True)
class PlatformModule:
    key: str
    name: str
    layer: str
    summary: str
    status: str
    health: int
    route: str
    color: str
    capabilities: tuple[str, ...]


MODULES = [
    PlatformModule(
        key="agent-governance-gateway",
        name="Agent Governance Gateway",
        layer="Governance Layer",
        summary="Registration, approval, scoped JWTs, revocation and audit logs for AI agents.",
        status="operational",
        health=98,
        route="/agent-auth/register",
        color="violet",
        capabilities=("Scoped auth", "Human approval", "Revocation", "Audit trail"),
    ),
    PlatformModule(
        key="mcp-security-gateway",
        name="MCP Security Gateway",
        layer="Governance Layer",
        summary="Policy boundary for MCP tool calls, risky actions and redacted arguments.",
        status="operational",
        health=97,
        route="/tools/mcp/invoke_tool",
        color="violet",
        capabilities=("MCP tool routing", "Risk detection", "Secret redaction", "Policy checks"),
    ),
    PlatformModule(
        key="automation-control-plane",
        name="Automation Control Plane",
        layer="Governance Layer",
        summary="Workflow execution decisions with plan limits, approvals and execution logging.",
        status="operational",
        health=95,
        route="/platform/automation",
        color="violet",
        capabilities=("Workflow catalog", "Entitlements", "Usage limits", "Approval queue"),
    ),
    PlatformModule(
        key="agent-runtime-control-tower",
        name="Agent Runtime Control Tower v2",
        layer="Runtime / Operations",
        summary="Runtime runs, traces, ownership, replay and operational health for agents.",
        status="operational",
        health=96,
        route="/platform/runtime",
        color="blue",
        capabilities=("Run history", "Replay", "Runtime state", "Trace review"),
    ),
    PlatformModule(
        key="llm-incident-review-console",
        name="LLM Incident Review Console",
        layer="Runtime / Operations",
        summary="Incident forensics with evidence, timelines, mitigation tasks and safe replay previews.",
        status="attention",
        health=91,
        route="/platform/incidents",
        color="blue",
        capabilities=("Incident queue", "Evidence", "Mitigation tasks", "Replay preview"),
    ),
    PlatformModule(
        key="agent-regression-lab",
        name="Agent Regression Lab",
        layer="Runtime / Operations",
        summary="Scenario registry, run diffs and regression verdicts before agent rollout.",
        status="operational",
        health=94,
        route="/platform/regression",
        color="blue",
        capabilities=("Scenario tests", "Run diffs", "Replay previews", "Release guardrails"),
    ),
    PlatformModule(
        key="brand-insight-engine",
        name="Brand Insight Engine",
        layer="Intelligence Layer",
        summary="Market signals, competitor mentions and positioning insights through governed tools.",
        status="operational",
        health=96,
        route="/tools/brand/analyze_market_signals",
        color="emerald",
        capabilities=("Signal analysis", "Competitor tracking", "Insight reports", "Human review"),
    ),
    PlatformModule(
        key="agent-intel-mcp",
        name="Agent Intel MCP",
        layer="Intelligence Layer",
        summary="MCP developer-intelligence server for repository scanning, pattern clustering and patch previews.",
        status="operational",
        health=93,
        route="/platform/intelligence",
        color="emerald",
        capabilities=("Repo scanning", "Pattern clustering", "AGENTS.md patch previews", "MCP resources"),
    ),
    PlatformModule(
        key="inference-readiness-advisor",
        name="Inference Readiness Advisor",
        layer="Intelligence Layer",
        summary="Hardware and runtime readiness scoring for local or hosted inference decisions.",
        status="operational",
        health=90,
        route="/platform/readiness",
        color="emerald",
        capabilities=("Model fit", "Runtime strategy", "Bottleneck analysis", "Readiness scoring"),
    ),
]


WORKFLOW_EXECUTIONS = [
    {"workflow": "Brand Insight Report", "decision": "allowed", "count": 42, "module": "automation-control-plane"},
    {"workflow": "Market Watch Report", "decision": "approval_required", "count": 11, "module": "automation-control-plane"},
    {"workflow": "Proposal Sender", "decision": "denied", "count": 4, "module": "automation-control-plane"},
    {"workflow": "Lead Triage Agent", "decision": "allowed", "count": 37, "module": "automation-control-plane"},
]

RUNTIME_RUNS = [
    {"agent": "Brand Monitoring Agent", "status": "completed", "latency_ms": 412, "tool_calls": 8, "cost_usd": 1.34},
    {"agent": "Content Analysis Agent", "status": "completed", "latency_ms": 388, "tool_calls": 5, "cost_usd": 0.92},
    {"agent": "Reputation Guard Agent", "status": "approval_required", "latency_ms": 520, "tool_calls": 7, "cost_usd": 1.71},
    {"agent": "Insight Discovery Agent", "status": "completed", "latency_ms": 447, "tool_calls": 6, "cost_usd": 1.12},
    {"agent": "Compliance Watchdog", "status": "blocked", "latency_ms": 601, "tool_calls": 3, "cost_usd": 0.48},
]

INCIDENTS = [
    {"id": "inc-1001", "title": "Unauthorized MCP write attempt", "severity": "high", "module": "mcp-security-gateway", "age": "12m"},
    {"id": "inc-1002", "title": "Prompt injection pattern detected", "severity": "medium", "module": "llm-incident-review-console", "age": "34m"},
    {"id": "inc-1003", "title": "PII exposure blocked by redaction", "severity": "high", "module": "agent-governance-gateway", "age": "1h"},
    {"id": "inc-1004", "title": "Regression diff changed tool order", "severity": "low", "module": "agent-regression-lab", "age": "2h"},
]

REGRESSION_RUNS = [
    {"scenario": "MCP write requires approval", "baseline": "pass", "candidate": "pass", "verdict": "stable", "latency_delta": -4},
    {"scenario": "Hybrid RAG avoids SQL hallucination", "baseline": "pass", "candidate": "fail", "verdict": "regression", "latency_delta": 13},
    {"scenario": "Brand insight report remains scoped", "baseline": "pass", "candidate": "pass", "verdict": "stable", "latency_delta": 7},
]

READINESS_ASSESSMENTS = [
    {"profile": "starter-chat", "score": 82, "runtime": "Ollama", "recommendation": "safe for chat and light RAG"},
    {"profile": "private-rag", "score": 76, "runtime": "llama.cpp", "recommendation": "use quantized 7B or hosted fallback"},
    {"profile": "agent-runner", "score": 87, "runtime": "vLLM", "recommendation": "ready with monitoring and budget guardrails"},
]

INTELLIGENCE_SIGNALS = [
    {"title": "Brand sentiment improved", "value": 24, "unit": "%", "module": "brand-insight-engine"},
    {"title": "Reusable agent patterns clustered", "value": 18, "unit": "patterns", "module": "agent-intel-mcp"},
    {"title": "Inference readiness score", "value": 87, "unit": "/100", "module": "inference-readiness-advisor"},
]


def module_dict(module: PlatformModule) -> dict[str, Any]:
    return {
        "key": module.key,
        "name": module.name,
        "layer": module.layer,
        "summary": module.summary,
        "status": module.status,
        "health": module.health,
        "route": module.route,
        "color": module.color,
        "capabilities": list(module.capabilities),
    }


def _audit_logs(db: Session) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())).all())


def _agents(db: Session) -> list[Agent]:
    return list(db.scalars(select(Agent).order_by(Agent.created_at.asc(), Agent.id.asc())).all())


def _graph_edges(db: Session) -> list[GraphEdge]:
    return list(db.scalars(select(GraphEdge).order_by(GraphEdge.created_at.asc(), GraphEdge.id.asc())).all())


def build_platform_overview(db: Session) -> dict[str, Any]:
    agents = _agents(db)
    logs = _audit_logs(db)
    edges = _graph_edges(db)

    allowed = sum(1 for log in logs if log.decision == "allowed")
    denied = sum(1 for log in logs if log.decision == "denied")
    pending = sum(1 for agent in agents if agent.status == "pending_approval")
    approved = sum(1 for agent in agents if agent.status == "approved")
    revoked = sum(1 for agent in agents if agent.status == "revoked")
    incidents = len(INCIDENTS) + sum(1 for log in logs if log.action == "policy_failure")
    policy_violations = sum(1 for log in logs if log.decision == "denied")
    runtime_health = round(sum(module.health for module in MODULES) / len(MODULES), 1)
    total_activity = allowed + denied + sum(item["count"] for item in WORKFLOW_EXECUTIONS) + len(RUNTIME_RUNS)

    return {
        "metrics": {
            "total_agents": len(agents),
            "active_agents": approved,
            "pending_approvals": pending,
            "revoked_agents": revoked,
            "incidents_7d": incidents,
            "policy_violations": policy_violations,
            "runtime_health": runtime_health,
            "allowed_tool_calls": allowed,
            "denied_tool_calls": denied,
            "graph_edges": len(edges),
            "modules": len(MODULES),
            "total_activity": total_activity,
        },
        "modules": [module_dict(module) for module in MODULES],
        "architecture": build_architecture(),
        "activity_series": build_activity_series(logs),
        "scope_distribution": build_scope_distribution(agents),
        "compliance": build_compliance(allowed=allowed, denied=denied, incidents=incidents),
        "top_agents": build_top_agents(logs),
    }


def build_architecture() -> list[dict[str, Any]]:
    layer_order = ["Governance Layer", "Runtime / Operations", "Intelligence Layer", "Shared Platform"]
    groups: list[dict[str, Any]] = []
    for layer in layer_order:
        if layer == "Shared Platform":
            groups.append(
                {
                    "layer": layer,
                    "color": "amber",
                    "modules": [
                        {"name": "Scoped Auth", "summary": "Short-lived JWTs, tenant headers and approval state"},
                        {"name": "Policy Engine", "summary": "Default-deny mapping between tools and scopes"},
                        {"name": "Audit Logs", "summary": "Registration, token issue, revocation and tool decisions"},
                        {"name": "PII / Secret Redaction", "summary": "Sensitive fields and MCP secrets are masked"},
                        {"name": "Graph Relationships", "summary": "Explainable edges across agents, tools and outputs"},
                    ],
                }
            )
            continue
        modules = [module_dict(module) for module in MODULES if module.layer == layer]
        groups.append({"layer": layer, "color": modules[0]["color"] if modules else "slate", "modules": modules})
    return groups


def build_activity_series(logs: list[AuditLog]) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    by_day: dict[str, Counter[str]] = {}
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        by_day[day.isoformat()] = Counter({"allowed": 0, "denied": 0, "pending": 0})
    for log in logs:
        day = log.timestamp.date().isoformat() if log.timestamp else today.isoformat()
        if day not in by_day:
            day = today.isoformat()
        if log.decision in {"allowed", "denied", "pending"}:
            by_day[day][log.decision] += 1
    for index, counter in enumerate(by_day.values()):
        counter["runtime"] += len(RUNTIME_RUNS) + index
        counter["workflow"] += sum(item["count"] for item in WORKFLOW_EXECUTIONS) // 14 + index
    return [
        {"date": day, "allowed": counts["allowed"], "denied": counts["denied"], "pending": counts["pending"], "runtime": counts["runtime"], "workflow": counts["workflow"]}
        for day, counts in by_day.items()
    ]


def build_scope_distribution(agents: list[Agent]) -> list[dict[str, Any]]:
    counts = Counter()
    for agent in agents:
        scopes = [scope for scope in (agent.approved_scopes or agent.requested_scopes or "").split(",") if scope]
        counts.update(scopes)
    return [{"scope": scope, "count": counts.get(scope, 0)} for scope in VALID_SCOPES]


def build_compliance(*, allowed: int, denied: int, incidents: int) -> dict[str, Any]:
    total = max(1, allowed + denied + incidents)
    compliant = max(0, allowed)
    warnings = max(0, incidents)
    violations = max(0, denied)
    return {
        "compliant": round((compliant / total) * 100),
        "warnings": round((warnings / total) * 100),
        "violations": round((violations / total) * 100),
        "raw": {"allowed": allowed, "denied": denied, "incidents": incidents},
    }


def build_top_agents(logs: list[AuditLog]) -> list[dict[str, Any]]:
    by_owner = Counter(log.owner_user_id or "system" for log in logs)
    for run in RUNTIME_RUNS:
        by_owner[run["agent"]] += run["tool_calls"]
    return [
        {"name": name, "actions": count, "trend": 8 if count % 2 == 0 else -3}
        for name, count in by_owner.most_common(6)
    ]


def build_platform_activity(db: Session) -> dict[str, Any]:
    logs = list(reversed(_audit_logs(db)[-12:]))
    audit_items = [
        {
            "title": log.action.replace("_", " ").title(),
            "module": log.tool_name or "agent-auth",
            "decision": log.decision,
            "reason": log.reason,
            "time": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in logs
    ]
    incident_items = [
        {"title": item["title"], "module": item["module"], "decision": item["severity"], "reason": f"{item['severity']} severity", "time": item["age"]}
        for item in INCIDENTS
    ]
    return {"items": incident_items + audit_items}


def build_layer_detail(layer_key: str, db: Session) -> dict[str, Any]:
    overview = build_platform_overview(db)
    modules_by_key = {module.key: module_dict(module) for module in MODULES}
    layer_map = {
        "governance": "Governance Layer",
        "runtime": "Runtime / Operations",
        "intelligence": "Intelligence Layer",
        "shared": "Shared Platform",
    }
    selected_layer = layer_map.get(layer_key)
    selected_modules = [
        module_dict(module)
        for module in MODULES
        if selected_layer is None or module.layer == selected_layer
    ]
    return {
        "layer": selected_layer or "All Modules",
        "modules": selected_modules,
        "metrics": overview["metrics"],
        "module_lookup": modules_by_key,
    }


def build_runtime_detail() -> dict[str, Any]:
    completed = sum(1 for run in RUNTIME_RUNS if run["status"] == "completed")
    blocked = sum(1 for run in RUNTIME_RUNS if run["status"] == "blocked")
    approval_required = sum(1 for run in RUNTIME_RUNS if run["status"] == "approval_required")
    avg_latency = round(sum(run["latency_ms"] for run in RUNTIME_RUNS) / len(RUNTIME_RUNS))
    return {
        "runs": RUNTIME_RUNS,
        "metrics": {
            "completed": completed,
            "blocked": blocked,
            "approval_required": approval_required,
            "avg_latency_ms": avg_latency,
            "total_tool_calls": sum(run["tool_calls"] for run in RUNTIME_RUNS),
            "total_cost_usd": round(sum(run["cost_usd"] for run in RUNTIME_RUNS), 2),
        },
    }


def build_automation_detail() -> dict[str, Any]:
    return {
        "executions": WORKFLOW_EXECUTIONS,
        "metrics": {
            "allowed": sum(item["count"] for item in WORKFLOW_EXECUTIONS if item["decision"] == "allowed"),
            "approval_required": sum(item["count"] for item in WORKFLOW_EXECUTIONS if item["decision"] == "approval_required"),
            "denied": sum(item["count"] for item in WORKFLOW_EXECUTIONS if item["decision"] == "denied"),
            "workflows": len(WORKFLOW_EXECUTIONS),
        },
    }


def build_incident_detail() -> dict[str, Any]:
    severity = Counter(item["severity"] for item in INCIDENTS)
    return {"incidents": INCIDENTS, "metrics": dict(severity)}


def build_regression_detail() -> dict[str, Any]:
    verdicts = Counter(item["verdict"] for item in REGRESSION_RUNS)
    return {"runs": REGRESSION_RUNS, "metrics": dict(verdicts)}


def build_readiness_detail() -> dict[str, Any]:
    avg = round(sum(item["score"] for item in READINESS_ASSESSMENTS) / len(READINESS_ASSESSMENTS))
    return {"assessments": READINESS_ASSESSMENTS, "metrics": {"average_score": avg, "profiles": len(READINESS_ASSESSMENTS)}}


def build_intelligence_detail() -> dict[str, Any]:
    return {"signals": INTELLIGENCE_SIGNALS, "metrics": {"signals": len(INTELLIGENCE_SIGNALS), "total_value": sum(item["value"] for item in INTELLIGENCE_SIGNALS)}}
