def _register_approve_issue(client, scopes):
    registration = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "platform-tenant",
            "agent_name": "Integrated Agent",
            "agent_type": "governed-workflow-agent",
            "requested_scopes": scopes,
            "reason": "Integrated platform workflow",
            "owner_user_id": "owner-integrated",
        },
    ).json()
    client.post(
        f"/agent-auth/approve/{registration['agent_id']}",
        json={"approved_scopes": scopes, "approved_by": "platform-admin", "expires_in_hours": 8},
    )
    token = client.post("/agent-auth/token", json={"agent_id": registration["agent_id"]}).json()["access_token"]
    return registration["agent_id"], token


def test_mcp_tool_invocation_is_governed_and_audited(client):
    agent_id, token = _register_approve_issue(client, ["mcp:tool:invoke"])
    response = client.post(
        "/tools/mcp/invoke_tool",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "platform-tenant"},
        json={
            "mcp_server_id": "mcp_github",
            "tool_name": "repo.write_file",
            "justification": "Apply a reviewed patch to a repository",
            "estimated_tokens": 1200,
            "arguments": {"path": "README.md", "api_key": "secret-value"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["scope_used"] == "mcp:tool:invoke"
    assert data["data"]["approval_required"] is True
    assert data["data"]["sanitized_arguments"]["api_key"] == "[REDACTED]"

    audit_response = client.get(f"/agent-auth/audit?agent_id={agent_id}&tool_name=mcp.invoke_tool")
    assert any(log["action"] == "allowed_tool_call" for log in audit_response.json())


def test_brand_insight_tool_creates_graph_edges(client):
    agent_id, token = _register_approve_issue(client, ["brand:insight:read"])
    response = client.post(
        "/tools/brand/analyze_market_signals",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "platform-tenant"},
        json={
            "brand_name": "AcmeFlow",
            "competitor_names": ["Northwind AI"],
            "signals": ["Competitor changed pricing page", "Users mention onboarding is slow"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope_used"] == "brand:insight:read"
    assert payload["data"]["review_owner"]["email"] == "[REDACTED]"

    graph_response = client.get(f"/graph/agents/{agent_id}/explain")
    assert graph_response.status_code == 200
    graph = graph_response.json()
    assert "brand.analyze_market_signals" in graph["called_tools"]
    assert any(output["type"] == "brand_insight" for output in graph["produced_outputs"])


def test_brand_report_requires_its_own_scope(client):
    _, token = _register_approve_issue(client, ["brand:insight:read"])
    response = client.post(
        "/tools/brand/create_report",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "platform-tenant"},
        json={
            "brand_name": "AcmeFlow",
            "report_name": "Weekly market movements",
            "insight_ids": ["BI-12345"],
        },
    )

    assert response.status_code == 403
    assert "required scope missing from token" in response.json()["detail"]
