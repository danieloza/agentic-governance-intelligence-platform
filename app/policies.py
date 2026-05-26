from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.models import Agent

TOOL_SCOPE_MAP = {
    "hr.search_employee_policy": "hr:policy:read",
    "finance.get_invoice_summary": "finance:invoice:read",
    "finance.create_expense_review": "finance:expense:create",
    "legal.search_contract_clause": "legal:contract:read",
    "legal.summarize_contract_risk": "legal:risk:summarize",
    "ops.create_report": "ops:report:create",
    "mcp.invoke_tool": "mcp:tool:invoke",
    "mcp.route_approval": "mcp:approval:write",
    "brand.analyze_market_signals": "brand:insight:read",
    "brand.create_report": "brand:report:create",
}

SENSITIVE_TOOLS = {
    "finance.get_invoice_summary",
    "finance.create_expense_review",
    "legal.search_contract_clause",
    "legal.summarize_contract_risk",
    "mcp.invoke_tool",
    "mcp.route_approval",
    "brand.create_report",
}


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    reason: str
    required_scope: str
    policy_version: str
    pii_redaction_required: bool


def evaluate_tool_access(
    *,
    agent: Agent | None,
    token_payload: dict[str, Any] | None,
    tool_name: str,
    policy_version: str,
) -> PolicyDecision:
    required_scope = TOOL_SCOPE_MAP.get(tool_name, "")
    pii_redaction_required = True

    if not required_scope:
        return PolicyDecision(
            allowed=False,
            reason="default_deny: unknown tool mapping",
            required_scope="",
            policy_version=policy_version,
            pii_redaction_required=pii_redaction_required,
        )

    if agent is None:
        return PolicyDecision(False, "default_deny: agent not found", required_scope, policy_version, pii_redaction_required)

    if agent.revoked_at is not None or agent.status == "revoked":
        return PolicyDecision(False, "default_deny: agent is revoked", required_scope, policy_version, pii_redaction_required)

    if agent.status != "approved":
        return PolicyDecision(False, "default_deny: agent is not approved", required_scope, policy_version, pii_redaction_required)

    if token_payload is None:
        return PolicyDecision(False, "default_deny: missing token", required_scope, policy_version, pii_redaction_required)

    if int(token_payload.get("agent_id", -1)) != agent.id:
        return PolicyDecision(False, "default_deny: token agent mismatch", required_scope, policy_version, pii_redaction_required)

    if token_payload.get("tenant_id") != agent.tenant_id:
        return PolicyDecision(False, "default_deny: tenant mismatch", required_scope, policy_version, pii_redaction_required)

    exp_ts = token_payload.get("exp")
    if exp_ts is None:
        return PolicyDecision(False, "default_deny: token missing expiration", required_scope, policy_version, pii_redaction_required)

    if datetime.fromtimestamp(exp_ts, tz=timezone.utc) <= datetime.now(timezone.utc):
        return PolicyDecision(False, "default_deny: token expired", required_scope, policy_version, pii_redaction_required)

    token_scopes = set(token_payload.get("scopes", []))
    if required_scope not in token_scopes:
        return PolicyDecision(False, "default_deny: required scope missing from token", required_scope, policy_version, pii_redaction_required)

    approved_scopes = set((agent.approved_scopes or "").split(",")) if agent.approved_scopes else set()
    if required_scope not in approved_scopes:
        return PolicyDecision(False, "default_deny: scope not present in approval record", required_scope, policy_version, pii_redaction_required)

    if tool_name in SENSITIVE_TOOLS and agent.approved_by is None:
        return PolicyDecision(False, "default_deny: sensitive tool requires human approval", required_scope, policy_version, pii_redaction_required)

    return PolicyDecision(True, "allowed", required_scope, policy_version, pii_redaction_required)
