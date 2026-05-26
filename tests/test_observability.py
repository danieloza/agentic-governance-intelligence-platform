def _register_approve_issue(client, scopes):
    registration = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "tenant-observability",
            "agent_name": "Observability Agent",
            "agent_type": "business_agent",
            "requested_scopes": scopes,
            "reason": "Observability summary test",
            "owner_user_id": "owner-observability",
        },
    ).json()
    client.post(
        f"/agent-auth/approve/{registration['agent_id']}",
        json={"approved_scopes": scopes, "approved_by": "admin-observability", "expires_in_hours": 8},
    )
    token = client.post("/agent-auth/token", json={"agent_id": registration["agent_id"]}).json()["access_token"]
    return token


def test_observability_summary_counts_tool_calls(client):
    token = _register_approve_issue(client, ["hr:policy:read"])
    client.post(
        "/tools/hr/search_employee_policy",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-observability"},
        json={"employee_query": "remote policy"},
    )

    summary = client.get("/observability/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert data["total_agents"] == 1
    assert data["approved_agents"] == 1
    assert data["total_tool_calls"] == 1
    assert data["allowed_tool_calls"] == 1
    assert data["most_used_tools"][0]["tool_name"] == "hr.search_employee_policy"
