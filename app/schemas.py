from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


VALID_SCOPES = [
    "hr:policy:read",
    "finance:invoice:read",
    "finance:expense:create",
    "legal:contract:read",
    "legal:risk:summarize",
    "ops:report:create",
    "mcp:tool:invoke",
    "mcp:approval:write",
    "brand:insight:read",
    "brand:report:create",
    "dev:repo:read",
    "dev:patch:propose",
    "dev:test:run",
]


class ManifestPolicyRules(BaseModel):
    default_deny: bool
    short_lived_scoped_tokens: bool
    human_approval_required: bool
    pii_redaction_enabled: bool
    audit_logging_enabled: bool
    revocation_supported: bool
    tenant_isolation_enabled: bool


class AgentAuthManifest(BaseModel):
    service_name: str
    issuer: str
    auth_flows_supported: list[str]
    credential_type: str
    token_endpoint: str
    approval_endpoint: str
    revocation_endpoint: str
    audit_endpoint: str
    available_scopes: list[str]
    policy_rules: ManifestPolicyRules


class AgentRegistrationRequest(BaseModel):
    tenant_id: str = Field(min_length=2, max_length=120)
    agent_name: str = Field(min_length=2, max_length=255)
    agent_type: str = Field(min_length=2, max_length=100)
    requested_scopes: list[str] = Field(min_length=1)
    reason: str = Field(min_length=5)
    owner_user_id: str = Field(min_length=2, max_length=255)
    callback_url: HttpUrl | None = None


class AgentRegistrationResponse(BaseModel):
    agent_id: int
    tenant_id: str
    status: str
    requested_scopes: list[str]


class ApprovalRequest(BaseModel):
    approved_scopes: list[str] = Field(min_length=1)
    approved_by: str = Field(min_length=2)
    expires_in_hours: int = Field(ge=1, le=168)


class ApprovalResponse(BaseModel):
    agent_id: int
    tenant_id: str
    status: str
    approved_scopes: list[str]
    expires_at: datetime


class TokenRequest(BaseModel):
    agent_id: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_at: datetime
    tenant_id: str
    scopes: list[str]


class RevocationRequest(BaseModel):
    revoked_by: str = Field(min_length=2)
    reason: str = Field(min_length=3)


class RevocationResponse(BaseModel):
    agent_id: int
    tenant_id: str
    status: str
    revoked_at: datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    tenant_id: str | None
    agent_id: int | None
    owner_user_id: str | None
    action: str
    tool_name: str | None
    requested_scope: str | None
    decision: str
    reason: str
    risk_level: str
    policy_version: str
    pii_redacted: bool
    latency_ms: int | None


class AuditLogFilters(BaseModel):
    tenant_id: str | None = None
    agent_id: int | None = None
    decision: str | None = None
    tool_name: str | None = None
    scope: str | None = None
    user_id: str | None = None
    risk_level: str | None = None


class ToolResponse(BaseModel):
    tool_name: str
    scope_used: str
    policy_version: str
    pii_redacted: bool
    data: dict[str, Any]


class DevReadRepoFileRequest(BaseModel):
    path: str = Field(min_length=1, max_length=300)


class DevProposePatchRequest(BaseModel):
    path: str = Field(min_length=1, max_length=300)
    patch_summary: str = Field(min_length=5, max_length=500)


class DevRunTestRequest(BaseModel):
    test_command: str = Field(default="pytest -q", min_length=2, max_length=200)


class RunStartRequest(BaseModel):
    agent_id: int
    objective: str = Field(min_length=5, max_length=1000)


class RunFinishRequest(BaseModel):
    status: Literal["completed", "failed", "blocked"]
    risk_score: float = Field(default=0.0, ge=0, le=100)


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    agent_id: int
    objective: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    risk_score: float
    tool_call_count: int
    blocked_call_count: int


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    agent_id: int
    run_id: int | None
    related_tool_call_id: int | None
    severity: str
    title: str
    description: str
    policy_reason: str
    status: str
    created_at: datetime
    resolved_at: datetime | None


class IncidentResolveRequest(BaseModel):
    resolved_by: str = Field(min_length=2, max_length=255)
    resolution_note: str = Field(min_length=3, max_length=1000)


class RegressionCaseRequest(BaseModel):
    tenant_id: str = Field(default="local", min_length=2, max_length=120)
    name: str = Field(min_length=2, max_length=255)
    agent_type: str = Field(min_length=2, max_length=100)
    requested_tool: str = Field(min_length=2, max_length=160)
    token_scopes: list[str] = Field(default_factory=list)
    expected_decision: Literal["allowed", "denied"]
    expected_reason_contains: str = Field(min_length=1, max_length=255)


class RegressionCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    name: str
    agent_type: str
    requested_tool: str
    token_scopes: str
    expected_decision: str
    expected_reason_contains: str
    created_at: datetime


class RegressionRunRequest(BaseModel):
    tenant_id: str | None = Field(default=None, max_length=120)


class RegressionCaseResult(BaseModel):
    case_id: int
    name: str
    expected_decision: str
    actual_decision: str
    reason: str
    passed: bool


class RegressionRunResponse(BaseModel):
    total_cases: int
    passed: int
    failed: int
    results: list[RegressionCaseResult]


class ObservabilitySummary(BaseModel):
    total_agents: int
    approved_agents: int
    revoked_agents: int
    total_tool_calls: int
    allowed_tool_calls: int
    denied_tool_calls: int
    open_incidents: int
    high_risk_events: int
    redaction_events: int
    most_used_tools: list[dict[str, Any]]
    most_requested_scopes: list[dict[str, Any]]


class GraphEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    source_type: str
    source_id: str
    relation: str
    target_type: str
    target_id: str
    metadata_json: str | None
    created_at: datetime


class EmployeePolicySearchRequest(BaseModel):
    employee_query: str


class InvoiceSummaryRequest(BaseModel):
    invoice_id: str


class ExpenseReviewRequest(BaseModel):
    expense_title: str
    amount: float
    currency: str = "PLN"


class ContractClauseRequest(BaseModel):
    contract_id: str
    clause_query: str


class ContractRiskRequest(BaseModel):
    contract_id: str


class OpsReportRequest(BaseModel):
    report_name: str
    department: str


class McpToolInvocationRequest(BaseModel):
    mcp_server_id: str = Field(min_length=2, max_length=120)
    tool_name: str = Field(min_length=2, max_length=160)
    justification: str = Field(min_length=5)
    estimated_tokens: int = Field(default=500, ge=1, le=100_000)
    arguments: dict[str, Any] = Field(default_factory=dict)


class BrandInsightRequest(BaseModel):
    brand_name: str = Field(min_length=2, max_length=120)
    competitor_names: list[str] = Field(default_factory=list)
    signals: list[str] = Field(min_length=1)


class BrandReportRequest(BaseModel):
    brand_name: str = Field(min_length=2, max_length=120)
    report_name: str = Field(min_length=2, max_length=160)
    insight_ids: list[str] = Field(default_factory=list)
