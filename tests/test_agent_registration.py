def test_register_agent(client):
    response = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "tenant-hr",
            "agent_name": "HR Policy Bot",
            "agent_type": "hr-agent",
            "requested_scopes": ["hr:policy:read"],
            "reason": "Need access to policy lookups",
            "owner_user_id": "owner-1",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["tenant_id"] == "tenant-hr"
    assert data["status"] == "pending_approval"
    assert data["requested_scopes"] == ["hr:policy:read"]


def test_reject_invalid_scope(client):
    response = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "tenant-invalid",
            "agent_name": "Bad Bot",
            "agent_type": "unknown",
            "requested_scopes": ["finance:admin:delete"],
            "reason": "Try invalid scope",
            "owner_user_id": "owner-2",
        },
    )
    assert response.status_code == 400
    assert "invalid_scopes" in response.json()["detail"]
