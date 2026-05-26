# Architecture

Agentic Governance Intelligence Platform is one FastAPI control plane with four layers:

```text
1. Agent identity and scoped authorization
2. Policy-enforced tool gateway
3. Domain tools: business tools, MCP tools, brand intelligence tools
4. Audit and relationship graph
```

## Runtime Flow

```text
AI Agent
  -> register requested scopes
  -> human/admin approval
  -> short-lived scoped JWT
  -> governed tool call
  -> policy decision
  -> domain tool execution
  -> PII/secret redaction
  -> audit log
  -> graph edge write
```

## Policy Boundary

Every tool call is default-deny and must pass:

- valid JWT
- matching tenant id
- approved agent status
- non-revoked agent status
- non-expired token
- token contains required scope
- approval record contains required scope
- sensitive tools have human approval

## Domain Tool Families

### Business Tools

HR, Finance, Legal and Operations mock tools demonstrate classic internal business workflows.

### MCP Security

MCP tool invocation is modeled as a governed tool surface. The platform does not let an agent call MCP tools directly; the request is routed through policy, audit and redaction first.

### Brand Insight

Brand intelligence workflows turn market signals and competitor mentions into structured insight/report outputs. These outputs are governed like any other enterprise tool result.

## Relationship Graph

The graph is stored in SQLite through the `graph_edges` table. It is intentionally simple for the MVP, but it creates a clear seam for a future graph backend such as Neo4j, sqlitegraph or a graph/vector hybrid.

Example edges:

```text
agent -> owned_by -> user
agent -> approved_for_scope -> scope
scope -> allows_tool -> tool
agent -> called_tool -> tool
tool -> produced -> brand_insight
```

This lets operators ask explainability questions:

- which agent produced an output?
- which scope allowed the action?
- which tool produced a report or request?
- which tenant did the chain belong to?
- which audit trail explains the decision?

## Storage

SQLite is used for the MVP:

- `agents`
- `approval_records`
- `audit_logs`
- `graph_edges`

The code keeps SQLAlchemy models and environment-driven `DATABASE_URL` so the same shape can move to PostgreSQL.

## Production Extensions

The natural next steps are:

- PostgreSQL with Alembic migrations
- row-level tenant isolation
- async audit ingestion
- graph backend adapter
- real MCP server proxying
- real brand signal ingestion connectors
- OpenTelemetry traces linked to audit and graph entities
- operator UI for graph exploration
