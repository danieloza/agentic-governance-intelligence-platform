def test_approving_agent(client):
    registration = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "tenant-finance",
            "agent_name": "Finance Reader",
            "agent_type": "finance-agent",
            "requested_scopes": ["finance:invoice:read", "finance:expense:create"],
            "reason": "Invoice workflow",
            "owner_user_id": "owner-3",
        },
    ).json()

    response = client.post(
        f"/agent-auth/approve/{registration['agent_id']}",
        json={
            "approved_scopes": ["finance:invoice:read"],
            "approved_by": "admin-1",
            "expires_in_hours": 12,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "tenant-finance"
    assert data["status"] == "approved"
    assert data["approved_scopes"] == ["finance:invoice:read"]
