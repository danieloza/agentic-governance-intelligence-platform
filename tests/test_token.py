def test_issue_token_for_approved_agent(client):
    registration = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "tenant-legal",
            "agent_name": "Legal Risk Bot",
            "agent_type": "legal-agent",
            "requested_scopes": ["legal:risk:summarize"],
            "reason": "Contract risk review",
            "owner_user_id": "owner-4",
        },
    ).json()
    client.post(
        f"/agent-auth/approve/{registration['agent_id']}",
        json={"approved_scopes": ["legal:risk:summarize"], "approved_by": "admin-2", "expires_in_hours": 10},
    )

    response = client.post("/agent-auth/token", json={"agent_id": registration["agent_id"]})
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["tenant_id"] == "tenant-legal"
    assert data["scopes"] == ["legal:risk:summarize"]


def test_refuse_token_for_pending_agent(client):
    registration = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "tenant-ops",
            "agent_name": "Pending Bot",
            "agent_type": "ops-agent",
            "requested_scopes": ["ops:report:create"],
            "reason": "Ops reporting",
            "owner_user_id": "owner-5",
        },
    ).json()

    response = client.post("/agent-auth/token", json={"agent_id": registration["agent_id"]})
    assert response.status_code == 403
    assert response.json()["detail"] == "Agent is not approved"
