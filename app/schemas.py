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


class ToolResponse(BaseModel):
    tool_name: str
    scope_used: str
    policy_version: str
    pii_redacted: bool
    data: dict[str, Any]


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
