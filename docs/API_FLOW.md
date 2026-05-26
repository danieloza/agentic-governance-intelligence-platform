# API Flow

This is the core AGIP flow for a governed autonomous agent.

```text
1. Register agent
   POST /agent-auth/register

2. Human approves a subset of scopes
   POST /agent-auth/approve/{agent_id}

3. Issue short-lived scoped token
   POST /agent-auth/token

4. Start runtime run
   POST /runs/start

5. Call governed tool
   POST /tools/{domain}/{tool}

6. Policy engine evaluates
   default deny
   agent approved
   agent not revoked
   token valid
   tenant boundary matches
   token contains required scope
   approval contains required scope

7. Tool output is redacted
   app/redaction.py

8. Evidence is written
   audit_logs
   tool_calls
   policy_decisions
   graph_edges

9. Denied or risky events create incident
   GET /incidents

10. Regression lab validates policy behavior
    POST /regression/run

11. Operator sees aggregate state
    GET /observability/summary
```

## Dashboard-facing APIs

The backend exposes API surfaces for a premium operator dashboard:

- Governance Overview
- Agents
- Tool Calls
- Policy Decisions
- Incidents
- Regression Lab
- Audit Explorer
- OpenAPI Developer Console
- Observability

The MVP dashboard is local and static, but the backend is intentionally shaped for a richer frontend.
