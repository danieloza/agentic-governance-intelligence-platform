# Product Vision

AGIP is a local-first AI governance platform for autonomous agents.

It is designed as the control plane between AI agents and business or developer tools. The platform makes agent behavior governable before an agent can touch sensitive systems.

## Product Shapes

AGIP can be described through six product lenses:

| Lens | Meaning |
| --- | --- |
| AI Gateway | Agents call tools through a controlled gateway instead of direct credentials. |
| Agent Firewall | Default-deny policy checks block unknown, unapproved or revoked actions. |
| Governance Control Plane | Registration, approval, scoped tokens, revocation and policy versions live in one place. |
| Runtime Observatory | Operators see runs, tool calls, denied actions, redaction and health signals. |
| Incident Review Console | Denied or risky calls become reviewable incidents with policy reasons. |
| Regression Lab | Policy scenarios can be replayed to catch access-control regressions. |

## Product Tiers

### Open-source Local Core

- SQLite-backed MVP
- FastAPI API surface
- local operator dashboard
- scoped JWTs
- mock governed tools
- audit logs, incidents and regression cases

### Pro Dashboard

- richer operator UI
- saved filters
- replay timelines
- team workflows
- historical metrics
- policy preview panels

### Enterprise Governance

- PostgreSQL deployment
- SSO/RBAC
- row-level tenant isolation
- real MCP proxying
- approval routing
- OpenTelemetry traces
- long-term audit retention
- SIEM/export integrations

## Positioning

AGIP is not a chatbot. It is infrastructure for organizations that want autonomous AI agents to operate inside real workflows without handing those agents unrestricted keys, database credentials or unreviewed tool access.
