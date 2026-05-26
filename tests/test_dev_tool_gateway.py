def test_dev_tool_call_requires_dev_scope(client):
    registration = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "tenant-dev",
            "agent_name": "Coding Agent",
            "agent_type": "coding_agent",
            "requested_scopes": ["dev:repo:read"],
            "reason": "Read repository context",
            "owner_user_id": "owner-dev",
        },
    ).json()
    client.post(
        f"/agent-auth/approve/{registration['agent_id']}",
        json={"approved_scopes": ["dev:repo:read"], "approved_by": "admin-dev", "expires_in_hours": 4},
    )
    token = client.post("/agent-auth/token", json={"agent_id": registration["agent_id"]}).json()["access_token"]

    response = client.post(
        "/tools/dev/read_repo_file",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-dev"},
        json={"path": "app/main.py"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["scope_used"] == "dev:repo:read"
    assert data["data"]["mode"] == "mock_read_only"
