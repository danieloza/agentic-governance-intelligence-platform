def _register_approve_issue(client, scopes):
    registration = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "langgraph-tenant",
            "agent_name": "LangGraph Governance Agent",
            "agent_type": "stateful_workflow_agent",
            "requested_scopes": scopes,
            "reason": "Demonstrate governed LangGraph execution",
            "owner_user_id": "workflow-owner",
        },
    ).json()
    client.post(
        f"/agent-auth/approve/{registration['agent_id']}",
        json={"approved_scopes": scopes, "approved_by": "governance-admin", "expires_in_hours": 8},
    )
    token = client.post("/agent-auth/token", json={"agent_id": registration["agent_id"]}).json()["access_token"]
    return registration["agent_id"], token


def test_low_risk_workflow_executes_without_interrupt(client):
    agent_id, token = _register_approve_issue(client, ["hr:policy:read"])

    response = client.post(
        "/workflows/langgraph/start",
        json={
            "thread_id": "low-risk-demo",
            "access_token": token,
            "tenant_id": "langgraph-tenant",
            "tool_name": "hr.search_employee_policy",
            "arguments": {"employee_query": "remote work"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["risk_level"] == "low"
    assert payload["result"]["matching_policy"]["contact"]["email"] == "[REDACTED]"
    assert "workflow:completed" in payload["timeline"]

    audit = client.get(f"/agent-auth/audit?agent_id={agent_id}&tool_name=hr.search_employee_policy").json()
    assert any(item["action"] == "langgraph_tool_executed" for item in audit)


def test_workflow_definition_explains_graph(client):
    response = client.get("/workflows/langgraph")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime"] == "LangGraph"
    assert any(node["id"] == "request_human_approval" for node in payload["nodes"])
    assert "human-in-the-loop interrupt and resume" in payload["capabilities"]


def test_high_risk_workflow_pauses_and_resumes_after_human_approval(client):
    _, token = _register_approve_issue(client, ["dev:patch:propose"])

    started = client.post(
        "/workflows/langgraph/start",
        json={
            "thread_id": "high-risk-approved-demo",
            "access_token": token,
            "tenant_id": "langgraph-tenant",
            "tool_name": "dev.propose_patch",
            "arguments": {"path": "README.md", "patch_summary": "Document the LangGraph approval workflow"},
        },
    )

    assert started.status_code == 200
    pending = started.json()
    assert pending["status"] == "awaiting_human_approval"
    assert pending["approval_request"]["type"] == "high_risk_tool_approval"
    assert pending["result"] is None

    resumed = client.post(
        "/workflows/langgraph/high-risk-approved-demo/resume",
        json={"approved": True, "reviewed_by": "security-reviewer", "note": "Safe documentation-only patch"},
    )

    assert resumed.status_code == 200
    completed = resumed.json()
    assert completed["status"] == "completed"
    assert completed["result"]["status"] == "proposed_for_human_review"
    assert "human_review:approved:security-reviewer" in completed["timeline"]
    assert "workflow:completed" in completed["timeline"]


def test_high_risk_workflow_can_be_rejected_by_human(client):
    agent_id, token = _register_approve_issue(client, ["mcp:tool:invoke"])

    started = client.post(
        "/workflows/langgraph/start",
        json={
            "thread_id": "high-risk-rejected-demo",
            "access_token": token,
            "tenant_id": "langgraph-tenant",
            "tool_name": "mcp.invoke_tool",
            "arguments": {
                "mcp_server_id": "mcp_github",
                "tool_name": "repo.delete_file",
                "justification": "Remove a file",
                "estimated_tokens": 100,
                "arguments": {"path": "README.md", "api_key": "secret"},
            },
        },
    )
    assert started.json()["status"] == "awaiting_human_approval"

    rejected = client.post(
        "/workflows/langgraph/high-risk-rejected-demo/resume",
        json={"approved": False, "reviewed_by": "security-reviewer", "note": "Destructive action rejected"},
    )

    assert rejected.status_code == 200
    payload = rejected.json()
    assert payload["status"] == "denied"
    assert payload["result"] is None
    assert "workflow:denied_by_human" in payload["timeline"]

    audit = client.get(f"/agent-auth/audit?agent_id={agent_id}&tool_name=mcp.invoke_tool").json()
    assert any(item["action"] == "langgraph_human_rejected" for item in audit)


def test_policy_denial_ends_without_human_interrupt(client):
    _, token = _register_approve_issue(client, ["ops:report:create"])

    response = client.post(
        "/workflows/langgraph/start",
        json={
            "thread_id": "policy-denied-demo",
            "access_token": token,
            "tenant_id": "langgraph-tenant",
            "tool_name": "finance.get_invoice_summary",
            "arguments": {"invoice_id": "INV-2026-999"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "denied"
    assert "required scope missing from token" in payload["policy_reason"]
    assert payload["approval_request"] is None
    assert "workflow:denied_by_policy" in payload["timeline"]


def test_duplicate_thread_id_is_rejected(client):
    _, token = _register_approve_issue(client, ["hr:policy:read"])
    request = {
        "thread_id": "duplicate-thread-demo",
        "access_token": token,
        "tenant_id": "langgraph-tenant",
        "tool_name": "hr.search_employee_policy",
        "arguments": {"employee_query": "remote work"},
    }

    first = client.post("/workflows/langgraph/start", json=request)
    duplicate = client.post("/workflows/langgraph/start", json=request)

    assert first.status_code == 200
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]
