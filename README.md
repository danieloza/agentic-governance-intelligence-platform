# Agentic Governance Intelligence Platform

[![FastAPI](https://img.shields.io/badge/FASTAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python 3.12](https://img.shields.io/badge/PYTHON_3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLALCHEMY-D71F00?style=for-the-badge)](https://www.sqlalchemy.org/)
[![Scoped JWT](https://img.shields.io/badge/SCOPED_JWT-111827?style=for-the-badge)](#product-thesis)
[![MCP Security](https://img.shields.io/badge/MCP_SECURITY-6D28D9?style=for-the-badge)](#platform-modules)
[![Audit Ready](https://img.shields.io/badge/AUDIT_READY-0F766E?style=for-the-badge)](#auditability-and-graph-traceability)
[![CI](https://img.shields.io/badge/CI-passing-16A34A?style=for-the-badge)](.github/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/LICENSE-MIT-0F172A?style=for-the-badge)](LICENSE)

**Agentic Governance Intelligence Platform** is a FastAPI-based control plane for governed enterprise AI agents.

It combines scoped agent authentication, MCP tool security, workflow approvals, runtime monitoring, incident review, regression checks, brand intelligence, PII/secret redaction, audit logs and graph-based traceability.

This is **not a chatbot**. It is the governance, security and operations layer around AI agents that need to use business tools safely.

![AGIP overview](docs/screenshots/overview.png)

## Product Thesis

AI agents should not receive unrestricted API keys, direct database credentials or unreviewed access to sensitive business systems.

In a real organization, agents need a control plane that can answer:

- who owns this agent?
- which scopes were requested?
- which scopes were approved by a human?
- which tool did the agent try to call?
- was the action allowed, denied, revoked or routed to approval?
- what data was redacted?
- what audit evidence explains the decision?
- what graph relationship connects the agent, scope, tool and output?

AGIP models that control plane.

```text
AI Agent
  -> Registration
  -> Human approval
  -> Short-lived scoped token
  -> Tool gateway
  -> Policy engine
  -> PII / secret redaction
  -> Audit log
  -> Relationship graph
  -> Operator dashboard
```

## What This Demonstrates

This project is designed as a portfolio-grade backend and platform prototype. It demonstrates:

- FastAPI service design with clean module boundaries
- scoped JWT credentials for agents
- human approval and revocation flows
- policy-enforced tool access
- MCP-style tool gateway governance
- workflow control-plane decisions
- audit logging for allowed and denied actions
- PII and secret redaction
- graph-based explainability
- operator-facing dashboard over real backend data
- pytest coverage for auth, approval, revocation, policy, tools, graph and redaction

## Platform Modules

### Governance Layer

| Module | Purpose |
| --- | --- |
| Agent Governance Gateway | Agent registration, approval, scoped credentials, revocation and audit logs. |
| MCP Security Gateway | Policy boundary for MCP tool calls, risky actions and redacted tool arguments. |
| Automation Control Plane | Workflow execution decisions with plan checks, approval routing and execution logging. |

### Runtime / Operations Layer

| Module | Purpose |
| --- | --- |
| Agent Runtime Control Tower v2 | Runtime runs, traces, blocked actions, replay signals and operational health. |
| LLM Incident Review Console | Incident review for prompt injection, PII exposure, unauthorized access and regressions. |
| Agent Regression Lab | Scenario-based regression checks before agent rollout. |

### Intelligence Layer

| Module | Purpose |
| --- | --- |
| Brand Insight Engine | Governed market and competitor signal analysis. |
| Agent Intel MCP | Repository intelligence, agent pattern clustering and MCP-oriented analysis. |
| Inference Readiness Advisor | Readiness scoring for model/runtime deployment decisions. |

### Shared Platform

| Module | Purpose |
| --- | --- |
| Scoped Auth | Short-lived JWTs, agent ownership and approved scopes. |
| Policy Engine | Default-deny tool-to-scope enforcement. |
| PII / Secret Redaction | Masks sensitive fields before responses and logs. |
| Audit Logs | Reviewable event history for registrations, approvals, tokens, revocations and tool calls. |
| Graph Relationships | Explainable edges across agents, scopes, tools and outputs. |

## Screenshots

### Control Tower

![Control Tower](docs/screenshots/overview.png)

### MCP Security Gateway

![MCP Security Gateway](docs/screenshots/mcp-security-gateway.png)

### Automation Control Plane

![Automation Control Plane](docs/screenshots/automation-control-plane.png)

### Brand Insight Engine

![Brand Insight Engine](docs/screenshots/brand-insight-engine.png)

### Incident Review Console

![Incident Review Console](docs/screenshots/incident-review-console.png)

### Relationship Graph

![Relationship Graph](docs/screenshots/relationship-graph.png)

### Audit Logs

![Audit Logs](docs/screenshots/audit-logs.png)

## Architecture

```text
                +---------------------------+
                |        AI Agent           |
                +-------------+-------------+
                              |
                              v
                  POST /agent-auth/register
                              |
                              v
                +---------------------------+
                |     Human Approval        |
                +-------------+-------------+
                              |
                              v
                    POST /agent-auth/token
                              |
                              v
                +---------------------------+
                |   Short-lived JWT Token   |
                +-------------+-------------+
                              |
                              v
                +---------------------------+
                |       Tool Gateway        |
                +-------------+-------------+
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
   Policy Engine       PII Redaction        Audit Logger
          |                   |                   |
          +-------------------+-------------------+
                              |
                              v
                +---------------------------+
                |  Relationship Graph       |
                +-------------+-------------+
                              |
                              v
                +---------------------------+
                |  Operator Dashboard       |
                +---------------------------+
```

## Auditability And Graph Traceability

Every important action is auditable:

- registration
- approval
- token issuing
- revocation
- allowed tool call
- denied tool call
- policy failure
- invalid scope attempt
- MCP invocation
- Brand Insight decision

The graph layer turns runtime decisions into explainable relationships:

```text
agent -> approved_for_scope -> scope
scope -> allows_tool -> tool
agent -> called_tool -> tool
tool -> produced -> output
```

This allows an operator to ask:

```text
Which agent created this output?
Which scope allowed it?
Which tenant owned the action?
Which audit record explains the decision?
Was anything redacted?
```

## API Surface

### Agent Auth

- `GET /.well-known/agent-auth.json`
- `POST /agent-auth/register`
- `POST /agent-auth/approve/{agent_id}`
- `POST /agent-auth/token`
- `POST /agent-auth/revoke/{agent_id}`
- `GET /agent-auth/audit`

### Tool Gateway

- `POST /tools/hr/search_employee_policy`
- `POST /tools/finance/get_invoice_summary`
- `POST /tools/finance/create_expense_review`
- `POST /tools/legal/search_contract_clause`
- `POST /tools/legal/summarize_contract_risk`
- `POST /tools/ops/create_report`
- `POST /tools/mcp/invoke_tool`
- `POST /tools/brand/analyze_market_signals`
- `POST /tools/brand/create_report`

### Platform Dashboard APIs

- `GET /platform/overview`
- `GET /platform/activity`
- `GET /platform/runtime`
- `GET /platform/automation`
- `GET /platform/incidents`
- `GET /platform/regression`
- `GET /platform/readiness`
- `GET /platform/intelligence`
- `GET /graph/edges`
- `GET /graph/agents/{agent_id}/explain`

## Example Demo Flow

This is the core story to show in an interview or portfolio walkthrough:

1. A new agent registers and requests scopes.
2. An admin approves only the scopes that are justified.
3. The agent receives a short-lived scoped JWT.
4. The agent tries to call a governed tool.
5. The policy engine checks approval, revocation, tenant boundary and required scope.
6. The response is redacted.
7. The decision is written to audit logs.
8. A graph edge explains the relationship between agent, scope, tool and output.
9. The dashboard shows activity, incidents, audit logs and graph relationships.

## Local Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8015
```

Open:

- Dashboard: `http://127.0.0.1:8015/`
- OpenAPI Docs: `http://127.0.0.1:8015/docs`

## Run Tests

```powershell
python -m pytest -q
```

Current test suite covers:

- registering agents
- rejecting invalid scopes
- approving agents
- issuing scoped tokens
- refusing tokens for pending agents
- denying calls after revocation
- allowing calls with the required scope
- denying calls without the required scope
- MCP tool governance
- Brand Insight governance
- graph edge creation
- audit log creation
- PII and secret redaction
- dashboard/platform endpoints

## Curl Walkthrough

### 1. Register Agent

```bash
curl -X POST http://127.0.0.1:8015/agent-auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "enterprise-marketing",
    "agent_name": "Market Signal Agent",
    "agent_type": "brand-intel-agent",
    "requested_scopes": ["brand:insight:read", "mcp:tool:invoke"],
    "reason": "Analyze market signals through governed tools",
    "owner_user_id": "marketing.owner"
  }'
```

### 2. Approve Agent

```bash
curl -X POST http://127.0.0.1:8015/agent-auth/approve/1 \
  -H "Content-Type: application/json" \
  -d '{
    "approved_scopes": ["brand:insight:read", "mcp:tool:invoke"],
    "approved_by": "platform.admin",
    "expires_in_hours": 8
  }'
```

### 3. Issue Token

```bash
curl -X POST http://127.0.0.1:8015/agent-auth/token \
  -H "Content-Type: application/json" \
  -d '{"agent_id": 1}'
```

### 4. Call Governed Brand Insight Tool

```bash
curl -X POST http://127.0.0.1:8015/tools/brand/analyze_market_signals \
  -H "Authorization: Bearer <TOKEN>" \
  -H "X-Tenant-ID: enterprise-marketing" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "Example Platform",
    "competitor_names": ["Competitor A", "Competitor B"],
    "signals": [
      "Competitor changed pricing page",
      "Users mention onboarding friction"
    ]
  }'
```

### 5. Inspect Audit Logs

```bash
curl http://127.0.0.1:8015/agent-auth/audit
```

### 6. Inspect Graph Edges

```bash
curl http://127.0.0.1:8015/graph/edges
```

## Project Structure

```text
agentic-governance-intelligence-platform/
  app/
    main.py
    auth.py
    policies.py
    tools.py
    graph.py
    audit.py
    redaction.py
    platform.py
    models.py
    schemas.py
    database.py
    config.py
    static/
      index.html
      dashboard.css
      dashboard.js
  docs/
    ARCHITECTURE.md
    ENTERPRISE_POSITIONING.md
    screenshots/
  examples/
    sample_agent_client.py
  tests/
  .github/workflows/ci.yml
  README.md
  LICENSE
  requirements.txt
```

## Interview Framing

Short version:

> I built an Agentic Governance Intelligence Platform: a FastAPI control plane for enterprise AI agents that need scoped, auditable and revocable access to internal tools.

Technical version:

> The system combines agent registration, human approval, short-lived scoped JWTs, MCP tool governance, workflow approvals, PII/secret redaction, audit logs, incident review, regression checks, graph-based traceability and an operator dashboard. The core idea is that agents should never directly access sensitive systems. They should operate through a policy-enforced gateway that can explain, audit and revoke every action.

## License

This project is licensed under the [MIT License](LICENSE).
